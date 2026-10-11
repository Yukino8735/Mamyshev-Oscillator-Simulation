"""Plan-first serial scans, durable between-design resume, and un-interpolated plots."""
from __future__ import annotations
import csv
import fcntl
import itertools
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from .v4_evaluators import FEATURES, TARGETS, UNITS, PACKAGE, canonical, design_id, digest, null_evaluation, validate_design

DEFAULT = dict(zip(FEATURES, (4., 10., 3., 4.)))


def make_plan(*, method="grid", axes=None, fixed=None, count=None, seed=0, csv_path=None, designs=None):
    """grid axes support one/two/four dimensions. random/LHS sample discrete legal length."""
    axes, fixed = axes or {}, dict(DEFAULT if fixed is None else fixed)
    if set(axes) - set(FEATURES) or set(fixed) - set(FEATURES):
        raise ValueError("Unknown design axis")
    if set(axes) & set(fixed):
        raise ValueError("Varying axes must not also be fixed")
    domain = json.loads((PACKAGE / "configs/domain.json").read_text())
    if method == "grid":
        if len(axes) not in (1, 2, 4) or set(axes) | set(fixed) != set(FEATURES):
            raise ValueError("Grid requires one/two/four varying axes and explicit other fixed values")
        if any(not isinstance(v, list) or not v for v in axes.values()):
            raise ValueError("Nonempty axis lists required")
        names = list(axes)
        points = [dict(fixed, **dict(zip(names, values))) for values in itertools.product(*(axes[k] for k in names))]
    elif method in ("random", "lhs"):
        import numpy as np
        from scipy.stats import qmc
        if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
            raise ValueError("Positive integer sample count required")
        if axes or fixed:
            raise ValueError("4D random/LHS requires fixed={} and no axes; length samples legal discrete levels")
        u = np.random.default_rng(seed).random((count, 4)) if method == "random" else qmc.LatinHypercube(4, seed=seed).random(count)
        bounds = domain["bounds"]; points = []
        length_levels = [round(1 + k * .1, 10) for k in range(71)]
        for row in u:
            d = {k: bounds[k][0] + row[j] * (bounds[k][1] - bounds[k][0]) for j, k in enumerate(FEATURES[:3])}
            d["gain_length_m"] = length_levels[min(len(length_levels)-1, int(row[3]*len(length_levels)))]; points.append(d)
    elif method == "csv":
        if csv_path is None:
            raise ValueError("CSV path required")
        with Path(csv_path).open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        if any(any(row.get(k, "").strip() for k in TARGETS) for row in rows):
            raise ValueError("Candidate import must be X-only, never prelabel unknown solver outputs")
        points = [{k: float(row[k]) for k in FEATURES} for row in rows]
        axes, fixed = {}, {}
    elif method == "candidates":
        if designs is None:
            raise ValueError("Explicit candidate input list required")
        points = list(designs); axes, fixed = {}, {}
    else:
        raise ValueError("Supported plan methods: grid, random, lhs, csv, candidates")
    unique, invalid = {}, []
    for index, value in enumerate(points):
        try:
            d = validate_design(value); unique.setdefault(design_id(d), d)
        except (ValueError, TypeError) as exc:
            invalid.append({"input_index": index, "reason": str(exc), "submitted_repr": repr(value)})
    plan = {"schema_version": "mamyshev_scan_v4", "method": method, "axes": axes, "fixed": fixed,
            "seed": seed, "designs": [{"design_id": k, "design_config": v} for k, v in unique.items()],
            "input_count": len(points), "unique_designs": len(unique), "duplicates_removed": len(points)-len(invalid)-len(unique),
            "invalid": invalid, "domain_status": domain["status"], "default_action": "plan_only",
            "max_new_real_attempts": 0, "length_sampling": "explicit legal 0.1 m levels; no submitted length rounding"}
    plan["plan_hash"] = digest(plan)
    return plan


def verify_plan(plan):
    if plan.get("plan_hash") != digest({k: v for k, v in plan.items() if k != "plan_hash"}):
        raise ValueError("Plan hash mismatch")
    if plan["invalid"]:
        raise ValueError("Plan contains invalid inputs; execute refused")
    ids = []
    for row in plan["designs"]:
        if row["design_id"] != design_id(row["design_config"]):
            raise ValueError("Plan design identity mismatch")
        ids.append(row["design_id"])
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate designs in executable plan")


def write_plan(plan, path):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        stream.write(json.dumps(plan, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def execute_scan(store, plan, evaluator, *, scan_id, budget, stop_path, cancel_after=None, authorization=None):
    """Commit every point. Re-entry requires identical plan, identity and cumulative budget."""
    verify_plan(plan)
    if set(budget) != {"max_new_attempts", "total_wall_s"} or budget["max_new_attempts"] < 0 or not math.isfinite(budget["total_wall_s"]) or budget["total_wall_s"] <= 0:
        raise ValueError("Explicit finite scan budget required")
    from .v4_evaluators import GMMNLSEEvaluator, SurrogateEvaluator
    live = isinstance(evaluator, GMMNLSEEvaluator)
    if live:
        if canonical(authorization or {}) != canonical(evaluator.authorization):
            raise ValueError("Scan and live authorization must be identical")
        if budget["total_wall_s"] < evaluator.authorization["total_wall_limit_s"]:
            raise ValueError("Scan total wall cap is tighter than live authorization; refuse rather than overrun")
    auth_hash = digest(authorization or {})
    identity_json = canonical(evaluator.identity)
    stop_path = Path(stop_path)
    lock = store.path.with_suffix(store.path.suffix + ".scan.lock").open("a+")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        row = store.db.execute("SELECT * FROM scans WHERE scan_id=?", (scan_id,)).fetchone()
        if row is None:
            for item in plan["designs"]:
                store.add_design(item["design_config"])
            with store.db:
                store.db.execute("INSERT INTO scans VALUES (?,?,?,?,?,?,?,?)", (scan_id, plan["plan_hash"], identity_json, canonical(budget), auth_hash, 0., 0, "pending"))
                store.db.executemany("INSERT INTO scan_items VALUES (?,?,?,?,?,?)", [(scan_id, d["design_id"], i, "pending", None, None) for i, d in enumerate(plan["designs"])])
        elif row["plan_hash"] != plan["plan_hash"] or row["evaluator_identity"] != identity_json or row["budget_json"] != canonical(budget) or row["authorization_hash"] != auth_hash:
            raise ValueError("Resume cannot change plan, source identity, authorization or cumulative budget")
        unknown = store.db.execute("SELECT attempt_id FROM attempts WHERE scan_id=? AND status='running'", (scan_id,)).fetchall()
        if unknown:
            raise RuntimeError("Unknown running attempts require independent ownership reconciliation; no restart")
        status = "completed"; session_attempts = 0
        for item in plan["designs"]:
            did, d = item["design_id"], item["design_config"]
            state = store.db.execute("SELECT status FROM scan_items WHERE scan_id=? AND design_id=?", (scan_id, did)).fetchone()[0]
            if state != "pending":
                continue  # completed skipped; failed/not_available never automatically retried
            if stop_path.exists():
                status = "cancelled"; break
            prior = store.lookup(d, evaluator.identity)
            if prior is not None:
                with store.db:
                    store.db.execute("UPDATE scan_items SET status='completed',evaluation_id=?,reason='Exact identity cache; no new attempt' WHERE scan_id=? AND design_id=?", (prior["evaluation_id"], scan_id, did))
                continue
            ledger = store.db.execute("SELECT * FROM scans WHERE scan_id=?", (scan_id,)).fetchone()
            if ledger["new_attempts"] >= budget["max_new_attempts"] or ledger["spent_wall_s"] >= budget["total_wall_s"]:
                status = "budget_stopped"; break
            if live and budget["total_wall_s"]-ledger["spent_wall_s"] < evaluator.authorization["per_run_timeout_s"]:
                status = "budget_stopped"; break  # Never start a live point whose full cap does not fit.
            index = ledger["new_attempts"] + 1
            attempt_id = f"{scan_id}_attempt_{index:06d}"
            start = datetime.now(timezone.utc).isoformat(); clock = time.monotonic()
            with store.db:
                store.db.execute("INSERT INTO attempts VALUES (?,?,?,?,?,?,?,?)", (attempt_id, scan_id, did, "running", start, None, None, canonical({"identity": evaluator.identity, "plan_hash": plan["plan_hash"]})))
                store.db.execute("UPDATE scans SET new_attempts=new_attempts+1,status='running' WHERE scan_id=?", (scan_id,))
                store.db.execute("UPDATE scan_items SET status='running' WHERE scan_id=? AND design_id=?", (scan_id, did))
            try:
                record = evaluator.evaluate(d, run_id=attempt_id, request_id=attempt_id)
                if record.get("kind") == "Prediction":
                    eid = store.save_prediction(record); point_status = "predicted"
                else:
                    eid = store.save_evaluation(record); point_status = record["job_status"]
                reason = record.get("missing_reason", "")
            except Exception as exc:
                reason = f"{type(exc).__name__}: {exc}"
                if isinstance(evaluator, SurrogateEvaluator):
                    record = {"kind": "Prediction", "prediction_id": "p_" + digest(attempt_id)[:24],
                              "design": d, "design_id": did, "identity": evaluator.identity,
                              "model_identity": evaluator.model_identity, "targets": dict.fromkeys(TARGETS),
                              "units": UNITS, "job_status": "failed", "missing_reason": reason,
                              "waveforms": None, "waveforms_missing_reason": "No field from failed prediction",
                              "eligible_as_validated_training_truth": False}
                    eid = store.save_prediction(record)
                else:
                    record = null_evaluation(d, evaluator.identity, reason, "failed")
                    record["evaluation_id"] = "e_" + digest(attempt_id)[:24]
                    eid = store.save_evaluation(record)
                point_status = "failed"
            elapsed = time.monotonic() - clock
            with store.db:
                store.db.execute("UPDATE attempts SET status=?,end_utc=?,elapsed_s=?,record_json=? WHERE attempt_id=?", (point_status, datetime.now(timezone.utc).isoformat(), elapsed, canonical(record), attempt_id))
                store.db.execute("UPDATE scan_items SET status=?,evaluation_id=?,reason=? WHERE scan_id=? AND design_id=?", (point_status, eid, reason, scan_id, did))
                store.db.execute("UPDATE scans SET spent_wall_s=spent_wall_s+? WHERE scan_id=?", (elapsed, scan_id))
            session_attempts += 1
            if cancel_after is not None and session_attempts >= cancel_after:
                stop_path.parent.mkdir(parents=True, exist_ok=True); stop_path.touch(exist_ok=False)
        with store.db:
            store.db.execute("UPDATE scans SET status=? WHERE scan_id=?", (status, scan_id))
        result = dict(store.db.execute("SELECT * FROM scans WHERE scan_id=?", (scan_id,)).fetchone())
        result["state_counts"] = dict(store.db.execute("SELECT status,count(*) FROM scan_items WHERE scan_id=? GROUP BY status", (scan_id,)).fetchall())
        result["new_attempts_this_invocation"] = session_attempts
        return result
    finally:
        lock.close()


def plot_scan(store, plan, scan_id, output_dir, *, source_title=None, limitation_note=None):
    """Only regular fixed slices: no scatter interpolation or invented missing values."""
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    axes = list(plan["axes"])
    if plan["method"] != "grid" or len(axes) not in (1, 2):
        raise ValueError("Plot requires explicit 1D or fixed-other-input 2D grid")
    rows = store.scan_records(scan_id); out = Path(output_dir); out.mkdir(parents=True, exist_ok=False)
    paths = []
    for target in TARGETS:
        fig, ax = plt.subplots(figsize=(7, 4.5))
        if len(axes) == 1:
            key = axes[0]; ordered = sorted(rows, key=lambda r: r["design"][key])
            values = [r["evaluation"]["targets"][target] if r["evaluation"] and r["status"] in ("completed", "predicted") else np.nan for r in ordered]
            ax.plot([r["design"][key] for r in ordered], values, "o-"); ax.set_xlabel(key); ax.set_ylabel(f"{target} [{UNITS[target]}]")
        else:
            x, y = axes; xv = sorted(set(plan["axes"][x])); yv = sorted(set(plan["axes"][y]))
            grid = np.full((len(yv), len(xv)), np.nan)
            for row in rows:
                if row["evaluation"] and row["status"] in ("completed", "predicted"):
                    value = row["evaluation"]["targets"][target]
                    if value is not None:
                        grid[yv.index(row["design"][y]), xv.index(row["design"][x])] = value
            image = ax.pcolormesh(xv, yv, np.ma.masked_invalid(grid), shading="nearest")
            fig.colorbar(image, ax=ax, label=f"{target} [{UNITS[target]}]"); ax.set_xlabel(x); ax.set_ylabel(y)
        title = source_title or ("Surrogate prediction" if any(r["status"] == "predicted" for r in rows) else "Synthetic/recorded responses")
        if source_title:
            compact_fixed = ", ".join(f"{name}={value:g}" for name, value in plan["fixed"].items())
            ax.set_title(title + "\nFixed " + compact_fixed, fontsize=9)
        else:
            ax.set_title(title + "; fixed " + canonical(plan["fixed"]), fontsize=9)
        if limitation_note:
            from textwrap import fill
            fig.text(.5, .01, fill(limitation_note, width=100), ha="center", fontsize=7)
        fig.tight_layout(rect=(0, .09 if limitation_note else 0, 1, 1))
        path = out / (target + ".png"); fig.savefig(path, dpi=130); plt.close(fig); paths.append(str(path))
    return paths


def read_saved_waveform(evaluation, output_dir):
    """Read actual MAT complex arrays and plot time/spectrum, never generate a field."""
    import numpy as np
    from scipy.io import loadmat
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    refs = evaluation.get("waveforms")
    if not refs or not refs.get("final"):
        return {"status": "not_available", "reason": evaluation.get("waveforms_missing_reason", "No saved complex field")}
    manifest_path = Path(refs["manifest"]); manifest = json.loads(manifest_path.read_text())
    final_path = manifest_path.parent / manifest["final"]["path"]
    data = loadmat(final_path, squeeze_me=False)
    t, f = data["t_ps"].reshape(-1), data["f_THz"].reshape(-1)
    dt = float(t[1]-t[0]); n = len(t)
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=False)
    fig, axes = plt.subplots(2, 1, figsize=(8, 7)); summaries = {}
    for name in ("output_field", "pigtail_output_field", "compressed_field"):
        field = data[name]
        if not field.size:
            summaries[name] = {"value": None, "reason": "Empty saved field"}; continue
        if field.shape[0] != n or not np.isfinite(field).all() or not np.isfinite(t).all() or not np.isfinite(f).all():
            raise ValueError("Nonfinite or inconsistent saved field/grid")
        power = np.sum(np.abs(field)**2, axis=1)
        spectrum = np.fft.fftshift(np.fft.ifft(field, axis=0), axes=0)
        psd = np.sum(np.abs(spectrum)**2, axis=1)*(n*dt)**2/1000
        trapz = np.trapezoid if hasattr(np, "trapezoid") else np.trapz
        summaries[name] = {"energy_nJ": float(trapz(power, t)/1000), "peak_W": float(power.max()), "shape": list(field.shape), "finite": True}
        axes[0].plot(t, power, label=name); axes[1].plot(f, psd, label=name)
    axes[0].set(xlabel="time [ps]", ylabel="power [W]"); axes[1].set(xlabel="absolute frequency [THz]", ylabel="spectral density [nJ/THz]")
    for ax in axes: ax.legend(); ax.grid()
    fig.tight_layout(); fig.savefig(out / "saved_waveforms.png", dpi=130); plt.close(fig)
    report = {"status": "read_actual_saved_mat", "mat": str(final_path), "run_id": evaluation["run_id"], "summaries": summaries,
              "definition": "Original saved complex samples; fftshift(ifft), no compression optimization, smoothing or interpolation", "new_physical_runs": 0}
    (out / "waveform_read.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
