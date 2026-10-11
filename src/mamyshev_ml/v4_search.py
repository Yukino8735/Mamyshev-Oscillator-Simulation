"""Independent, budgeted V4 synthetic search using only locked evaluator queries.

No supervised dataset, fitted production model, or synthetic formula is imported.
The GP is an acquisition model of this experiment's own <=64 observations.
"""
from __future__ import annotations

import csv
import dataclasses
import hashlib
import json
import math
import os
from pathlib import Path
import time
from typing import Any

import numpy as np
from scipy.special import ndtr
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern

FEATURES = ("pump_power_W", "filter_offset_nm", "filter2_bw_nm", "gain_length_m")
TARGETS = ("compressed_energy_nJ", "compressed_duration_fs", "compressed_peak_power_MW")
SEEDS = (11, 22, 33)
METHODS = ("gp", "random")
INITIAL = 16
BUDGET = 64
BATCH = 4
POOL_LIMIT = 4096
MAX_EVENTS = 1536
PROTOCOL = {
    "schema_version": "v4_independent_search_v1",
    "seeds": list(SEEDS), "methods": list(METHODS),
    "initial_queries": INITIAL, "queries_per_experiment": BUDGET,
    "batch_size": BATCH, "candidate_pool_limit": POOL_LIMIT,
    "max_logical_events": MAX_EVENTS, "evaluator_seed": 0,
    "random_streams": {"pool": "SeedSequence([paired_seed,scenario_index,100])",
                       "initial": "SeedSequence([paired_seed,scenario_index,101])",
                       "random_batches": "SeedSequence([paired_seed,scenario_index,102])"},
    "feature_scaling": "declared_domain_bounds_only",
    "target_transform": "natural_log_positive_targets",
    "gp": {"kernel": "1.0 * Matern(nu=2.5,length_scale=0.35)",
           "alpha": 1e-6, "normalize_y": True, "optimizer": None,
           "max_training_rows": 64, "shared_kernel_independent_outputs": True},
    "acquisition": "no_actual_feasible: product_constraint_probability; otherwise EI_in_log_objective_times_product_constraint_probability",
    "constraint_probability": "independent_marginals_product_approximation_uncalibrated_not_physical_probability",
    "batch_rule": "fit_once_lock_all_four_before_any_query_no_fantasies",
    "degenerate_acquisition": "nonfinite_or_all_le_1e-15_or_exactly_constant: descending_mean_log_std_then_lexicographic_design_id",
    "uncertainty_fallback": "nonfinite_or_all_le_1e-15: lexicographic_design_id",
    "tie_rule": "exact_equal_score_then_lexicographic_design_id",
    "point_prediction": "exp(log_mean), a median in original units, not lognormal mean",
    "random_predictions": "null: random method does not fit a prediction model",
    "reference": "posthoc_best_in_union_of_actual_queries_within_scenario_not_global_optimum_or_regret",
    "real_execution": "pending_manual_approval", "max_new_real_attempts": 0,
}


class SearchDeadline(RuntimeError):
    """An experiment stopped without pretending its unused queries were spent."""


def _check_deadline(deadline: float) -> None:
    if time.monotonic() >= deadline:
        raise SearchDeadline("search internal wall-clock budget exhausted")


def write_json(path: Path, value: Any) -> None:
    """Atomic local write; filenames never involve random number generation."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def append_json(path: Path, value: Any) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, allow_nan=False, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_candidates(path: Path, bounds: dict) -> list[dict]:
    """Reject a labelled table instead of silently ignoring forbidden columns."""
    required = {"design_id", "candidate_group", *FEATURES}
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if set(reader.fieldnames or []) != required:
            raise ValueError("Search candidate CSV must have exactly the six X-only columns")
        rows = []
        seen = set()
        for record in reader:
            identifier = record["design_id"]
            if not identifier or identifier in seen:
                raise ValueError("Candidate design IDs must be unique and nonempty")
            seen.add(identifier)
            x = {name: float(record[name]) for name in FEATURES}
            if any(not math.isfinite(x[name]) or not bounds[name][0] <= x[name] <= bounds[name][1]
                   for name in FEATURES):
                raise ValueError("Candidate has nonfinite or out-of-domain inputs")
            rows.append({"design_id": identifier, "candidate_group": record["candidate_group"], **x})
    return rows


def satisfies(values: dict, constraints: dict) -> bool:
    for name, limits in constraints.items():
        for operator, boundary in limits.items():
            if operator == "lte" and not values[name] <= boundary:
                return False
            if operator == "gte" and not values[name] >= boundary:
                return False
            if operator not in ("lte", "gte"):
                raise ValueError(f"Unsupported constraint operator: {operator}")
    return True


def eligible_rows(rows: list[dict], scenario: dict) -> list[dict]:
    return [row for row in rows
            if row["candidate_group"] == scenario["candidate_group"]
            and all(row[name] == value for name, value in scenario["fixed_inputs"].items())
            and satisfies(row, scenario["input_constraints"])]


def paired_pool(rows: list[dict], scenario: dict, seed: int, index: int) -> tuple[list[dict], list[int], dict]:
    eligible = sorted(eligible_rows(rows, scenario), key=lambda row: row["design_id"])
    rng = np.random.default_rng(np.random.SeedSequence([seed, index, 100]))
    chosen = rng.choice(len(eligible), size=min(POOL_LIMIT, len(eligible)), replace=False)
    pool = sorted((eligible[int(i)] for i in chosen), key=lambda row: row["design_id"])
    if len(pool) < BUDGET:
        raise ValueError(f"Scenario {scenario['id']} has fewer than {BUDGET} candidates")
    init_rng = np.random.default_rng(np.random.SeedSequence([seed, index, 101]))
    initial = [int(i) for i in init_rng.choice(len(pool), size=INITIAL, replace=False)]
    return pool, initial, {"eligible_input_count": len(eligible), "pool_count": len(pool),
                           "pool_design_ids": [row["design_id"] for row in pool],
                           "initial_design_ids": [pool[i]["design_id"] for i in initial]}


def scaled_inputs(pool: list[dict], bounds: dict) -> np.ndarray:
    low = np.array([bounds[name][0] for name in FEATURES])
    high = np.array([bounds[name][1] for name in FEATURES])
    if np.any(high <= low):
        raise ValueError("Invalid declared scaling domain")
    return (np.array([[row[name] for name in FEATURES] for row in pool]) - low) / (high - low)


def acquisition(mean: np.ndarray, std: np.ndarray, y: np.ndarray, scenario: dict) -> tuple[np.ndarray, np.ndarray]:
    """Product probability is an explicit approximate acquisition, not calibrated."""
    feasible_probability = np.ones(len(mean))
    for target, constraints in scenario["output_constraints"].items():
        j = TARGETS.index(target)
        s = np.maximum(std[:, j], 1e-15)
        for operator, value in constraints.items():
            z = (math.log(value) - mean[:, j]) / s
            feasible_probability *= ndtr(z if operator == "lte" else -z)
    feasible = np.array([satisfies(dict(zip(TARGETS, row)), scenario["output_constraints"]) for row in y])
    if not feasible.any():
        return feasible_probability, feasible_probability
    j = TARGETS.index(scenario["objective"]["target"])
    direction = 1 if scenario["objective"]["direction"] == "maximize" else -1
    best = np.max(direction * np.log(y[feasible, j]))
    improvement = direction * mean[:, j] - best
    sigma = np.maximum(std[:, j], 1e-15)
    z = improvement / sigma
    ei = np.maximum(0, improvement * ndtr(z) + sigma * np.exp(-0.5 * z * z) / math.sqrt(2 * math.pi))
    return ei * feasible_probability, feasible_probability


def rank_acquisition(scores: np.ndarray, std: np.ndarray, identifiers: list[str]) -> tuple[np.ndarray, str]:
    if (not np.isfinite(scores).all() or np.max(scores, initial=0) <= 1e-15
            or np.ptp(scores) == 0):
        uncertainty = np.mean(std, axis=1)
        if not np.isfinite(uncertainty).all() or np.max(uncertainty, initial=0) <= 1e-15:
            return np.argsort(np.asarray(identifiers), kind="stable"), "design_id_fallback"
        return np.lexsort((identifiers, -uncertainty)), "uncertainty_then_id_fallback"
    return np.lexsort((identifiers, -scores)), "acquisition_then_id"


def gp_batch(x: np.ndarray, selected: list[int], outputs: list[dict], remaining: list[int],
             pool: list[dict], scenario: dict) -> tuple[list[int], dict[int, dict], str]:
    if not 1 <= len(selected) <= BUDGET:
        raise ValueError("GP fitting outside the experiment query budget")
    y = np.array([[row[name] for name in TARGETS] for row in outputs])
    kernel = ConstantKernel(1.0, constant_value_bounds="fixed") * Matern(
        length_scale=0.35, length_scale_bounds="fixed", nu=2.5)
    model = GaussianProcessRegressor(kernel=kernel, alpha=1e-6, normalize_y=True, optimizer=None)
    model.fit(x[selected], np.log(y))
    mean, std = model.predict(x[remaining], return_std=True)
    if std.ndim == 1:
        std = np.repeat(std[:, None], len(TARGETS), axis=1)
    if mean.shape != (len(remaining), 3) or std.shape != mean.shape:
        raise ValueError("Unexpected multioutput GP prediction shape")
    score, probability = acquisition(mean, std, y, scenario)
    order, rule = rank_acquisition(score, std, [pool[i]["design_id"] for i in remaining])
    chosen_positions = [int(i) for i in order[:BATCH]]
    chosen = [remaining[i] for i in chosen_positions]
    predictions = {}
    for pos, index in zip(chosen_positions, chosen):
        values = np.exp(mean[pos])
        if not np.isfinite(values).all() or not np.isfinite(std[pos]).all():
            raise ValueError("GP produced nonfinite recommendation predictions")
        predictions[index] = {"targets": dict(zip(TARGETS, map(float, values))),
                              "log_standard_deviation": dict(zip(TARGETS, map(float, std[pos]))),
                              "approximate_constraint_probability": float(probability[pos]),
                              "acquisition": float(score[pos]) if math.isfinite(score[pos]) else None}
    return chosen, predictions, rule


def _record(result: Any) -> dict:
    return dataclasses.asdict(result) if dataclasses.is_dataclass(result) else dict(result)


def best_actual(events: list[dict], scenario: dict) -> dict:
    available = [event for event in events if event["actual_feasible"]]
    if not available:
        return {"design_id": None, "value": None, "targets": None, "missing_reason": "no_actual_feasible_query"}
    objective = scenario["objective"]
    sign = -1 if objective["direction"] == "maximize" else 1
    chosen = min(available, key=lambda event: (sign * event["targets"][objective["target"]], event["design_id"]))
    return {"design_id": chosen["design_id"], "value": chosen["targets"][objective["target"]],
            "targets": chosen["targets"], "missing_reason": None}


def summarize_experiment(events: list[dict], scenario: dict, method: str, seed: int,
                         status: str, reason: str | None, elapsed: float, model_seconds: float) -> dict:
    predicted = [event for event in events if event["prediction"] is not None]
    predicted_feasible = [event for event in predicted if event["predicted_feasible"]]
    errors = {}
    for target in TARGETS:
        e = [event["prediction_errors"][target] for event in predicted]
        errors[target] = {"n": len(e), "mean_absolute_error": float(np.mean([r["absolute_error"] for r in e])) if e else None,
                          "mean_relative_error": float(np.mean([r["relative_error"] for r in e])) if e else None,
                          "missing_reason": None if e else "no_GP_recommendation_predictions"}
    return {"scenario_id": scenario["id"], "method": method, "seed": seed,
            "status": status, "stop_reason": reason, "logical_queries": len(events),
            "cache_hits": sum(bool(e["cache_hit"]) for e in events),
            "actual_new_evaluator_computations": sum(not bool(e["cache_hit"]) for e in events),
            "wall_seconds": elapsed, "GP_fit_and_predict_seconds": model_seconds,
            "best_actual_feasible": {str(n): best_actual(events[:n], scenario) if len(events) >= n else
                {"design_id": None, "value": None, "targets": None, "missing_reason": "budget_not_reached"}
                for n in (16, 32, 64)},
            "false_feasible": {"count": sum(not e["actual_feasible"] for e in predicted_feasible) if predicted else None,
                               "predicted_feasible_count": len(predicted_feasible) if predicted else None,
                               "prediction_count": len(predicted),
                               "missing_reason": None if predicted else "random_or_initial_queries_have_no_prediction"},
            "recommendation_prediction_error": errors,
            "trajectory": [{"query": i, **best_actual(events[:i], scenario)} for i in range(1, len(events) + 1)]}


def run_experiment(*, evaluator: Any, pool: list[dict], initial: list[int], scenario: dict,
                   bounds: dict, method: str, seed: int, scenario_index: int,
                   directory: Path, deadline: float, global_events: list[dict]) -> dict:
    directory.mkdir(parents=True, exist_ok=False)
    x = scaled_inputs(pool, bounds)
    selected: list[int] = []
    outputs: list[dict] = []
    events: list[dict] = []
    random_rng = np.random.default_rng(np.random.SeedSequence([seed, scenario_index, 102]))
    started = time.monotonic()
    model_seconds = 0.0
    status, reason = "completed", None
    try:
        for batch_index in range(13):
            _check_deadline(deadline)
            remaining = [i for i in range(len(pool)) if i not in selected]
            if batch_index == 0:
                chosen, predictions, rule = list(initial), {}, "paired_initial_16"
            elif method == "random":
                chosen = [int(i) for i in random_rng.choice(remaining, size=BATCH, replace=False)]
                predictions, rule = {}, "uniform_without_replacement"
            elif method == "gp":
                model_start = time.monotonic()
                chosen, predictions, rule = gp_batch(x, selected, outputs, remaining, pool, scenario)
                model_seconds += time.monotonic() - model_start
            else:
                raise ValueError("Unknown search method")
            # This durable lock precedes every evaluation of the batch.
            append_json(directory / "batch_locks.jsonl", {
                "batch_index": batch_index, "observations_before_lock": len(events), "selection_rule": rule,
                "design_ids": [pool[i]["design_id"] for i in chosen],
                "predictions": {pool[i]["design_id"]: predictions.get(i) for i in chosen}})
            for index in chosen:
                _check_deadline(deadline)
                if len(global_events) >= MAX_EVENTS:
                    raise SearchDeadline("logical evaluation limit reached")
                row = pool[index]
                design = {name: row[name] for name in FEATURES}
                request_id = f"{scenario['id']}/{seed}/{method}/{len(events) + 1:02d}"
                query_start = time.monotonic()
                try:
                    result = _record(evaluator.evaluate(design, request_id=request_id, design_id=row["design_id"]))
                except Exception as exc:
                    append_json(directory / "failed_queries.jsonl", {
                        "request_id": request_id, "design_id": row["design_id"], "design": design,
                        "targets": None, "missing_reason": "evaluator_exception",
                        "error": f"{type(exc).__name__}: {exc}",
                        "query_wall_seconds": time.monotonic() - query_start})
                    raise
                query_seconds = time.monotonic() - query_start
                targets = result.get("targets", {})
                if result.get("job_status") != "completed" or set(targets) != set(TARGETS) or any(
                    not isinstance(targets[name], (int, float)) or not math.isfinite(targets[name]) or targets[name] <= 0
                    for name in TARGETS):
                    # Keep the failed query evidence before aborting; never fill labels.
                    failure = {"request_id": request_id, "design_id": row["design_id"], "design": design,
                               "evaluator_result": result, "query_wall_seconds": query_seconds}
                    append_json(directory / "failed_queries.jsonl", failure)
                    raise RuntimeError("Synthetic evaluator failed or returned invalid positive targets")
                prediction = predictions.get(index)
                predicted_targets = prediction["targets"] if prediction else None
                event = {"request_id": request_id, "query": len(events) + 1, "batch_index": batch_index,
                         "scenario_id": scenario["id"], "method": method, "seed": seed,
                         "design_id": row["design_id"], "design": design, "targets": targets,
                         "identity": result.get("identity"), "source_kind": result.get("source_kind"),
                         "evaluation_id": result.get("evaluation_id"), "cache_hit": bool(result["cache_hit"]),
                         "actual_feasible": satisfies(targets, scenario["output_constraints"]),
                         "prediction": prediction,
                         "predicted_feasible": satisfies(predicted_targets, scenario["output_constraints"]) if prediction else None,
                         "prediction_errors": {target: {"absolute_error": abs(predicted_targets[target] - targets[target]),
                                                        "relative_error": abs(predicted_targets[target] - targets[target]) / abs(targets[target])}
                                               for target in TARGETS} if prediction else None,
                         "prediction_missing_reason": None if prediction else "initial_or_random_query_has_no_prediction",
                         "query_wall_seconds": query_seconds}
                append_json(directory / "events.jsonl", event)
                global_events.append(event)
                events.append(event)
                selected.append(index)
                outputs.append(targets)
        if len(events) != BUDGET:
            raise AssertionError("Completed search does not match its frozen budget")
    except SearchDeadline as exc:
        status, reason = "budget_exhausted", str(exc)
    except Exception as exc:
        status, reason = "failed", f"{type(exc).__name__}: {exc}"
    summary = summarize_experiment(events, scenario, method, seed, status, reason,
                                   time.monotonic() - started, model_seconds)
    write_json(directory / "summary.json", summary)
    return summary


def _trajectory_aggregates(experiments: list[dict], scenarios: list[dict]) -> dict:
    aggregates = {}
    for scenario in scenarios:
        group = {}
        for method in METHODS:
            runs = [r for r in experiments if r["scenario_id"] == scenario["id"] and r["method"] == method]
            trajectory = []
            for n in range(1, BUDGET + 1):
                values = [r["trajectory"][n - 1]["value"] for r in runs if len(r["trajectory"]) >= n]
                finite = [v for v in values if v is not None]
                trajectory.append({"query": n, "observed_seed_count": len(values), "feasible_seed_count": len(finite),
                                   "no_feasible_seed_count": sum(v is None for v in values),
                                   "median": float(np.median(finite)) if finite else None,
                                   "minimum": min(finite) if finite else None, "maximum": max(finite) if finite else None,
                                   "missing_reason": None if finite else "no_feasible_seed_observation_at_budget"})
            group[method] = trajectory
        aggregates[scenario["id"]] = group
    return aggregates


def export_recommendations(directory: Path, events: list[dict], scenarios: list[dict]) -> list[dict]:
    """Only actually evaluated synthetic designs; no implied live authorization."""
    from scipy.io import savemat
    recommendations = []
    for scenario in scenarios:
        unique = {e["design_id"]: e for e in events if e["scenario_id"] == scenario["id"] and e["actual_feasible"]}
        objective = scenario["objective"]
        sign = -1 if objective["direction"] == "maximize" else 1
        ranked = sorted(unique.values(), key=lambda e: (sign * e["targets"][objective["target"]], e["design_id"]))[:3]
        for rank, event in enumerate(ranked, 1):
            recommendations.append({"scenario_id": scenario["id"], "rank": rank, "design_id": event["design_id"],
                                    "design": event["design"], "synthetic_targets": event["targets"],
                                    "synthetic_identity": event["identity"], "evaluation_id": event["evaluation_id"],
                                    "status": "pending_manual_approval", "max_new_real_attempts": 0,
                                    "physical_state": "undetermined", "eligible_as_validated_training_truth": False,
                                    "waveforms": None, "missing_reason": "synthetic_scalar_evaluation_has_no_waveforms",
                                    "requested_backend": "gmmnlse", "real_targets": None})
    write_json(directory / "matlab_requests.json", {"status": "pending_manual_approval", "max_new_real_attempts": 0,
               "scope": "at_most_three_actual_synthetic_feasible_candidates_per_scenario", "requests": recommendations})
    # MATLAB receives JSON and X, with synthetic Y in a separately labelled array.
    savemat(directory / "matlab_requests.mat", {
        "requests_json": json.dumps(recommendations, allow_nan=False),
        "feature_names": np.array(FEATURES, dtype=object), "target_names": np.array(TARGETS, dtype=object),
        "X": np.array([[r["design"][name] for name in FEATURES] for r in recommendations]).reshape(-1, 4),
        "synthetic_Y": np.array([[r["synthetic_targets"][name] for name in TARGETS] for r in recommendations]).reshape(-1, 3),
        "status": "pending_manual_approval", "max_new_real_attempts": 0})
    with (directory / "matlab_requests.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["scenario_id", "rank", "design_id", *FEATURES, "status", "max_new_real_attempts"])
        writer.writeheader()
        for row in recommendations:
            writer.writerow({"scenario_id": row["scenario_id"], "rank": row["rank"], "design_id": row["design_id"],
                             **row["design"], "status": row["status"], "max_new_real_attempts": 0})
    return recommendations


def plot_trajectories(directory: Path, experiments: list[dict], scenarios: list[dict], aggregates: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    figure, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    for ax, scenario in zip(axes.flat, scenarios):
        for method, color in (("gp", "tab:blue"), ("random", "tab:orange")):
            for run in experiments:
                if run["scenario_id"] == scenario["id"] and run["method"] == method:
                    ax.plot([p["query"] for p in run["trajectory"]],
                            [np.nan if p["value"] is None else p["value"] for p in run["trajectory"]],
                            color=color, alpha=.35, linewidth=.9, label=f"{method} seed {run['seed']}")
            values = aggregates[scenario["id"]][method]
            x = [r["query"] for r in values]
            y = lambda key: [np.nan if r[key] is None else r[key] for r in values]
            ax.plot(x, y("median"), color=color, linewidth=2.2, label=f"{method} median (feasible seeds)")
            ax.fill_between(x, y("minimum"), y("maximum"), color=color, alpha=.1)
        ax.set_title(scenario["id"])
        ax.set_xlabel("Logical evaluator queries (cached initial queries included)")
        ax.set_ylabel(f"Best actual feasible {scenario['objective']['target']}")
        ax.grid(alpha=.2)
        ax.legend(fontsize=6)
    figure.suptitle("Synthetic-only paired search; 3 seeds; gaps mean no actual feasible query")
    figure.savefig(directory / "all_seed_trajectories.png", dpi=150)
    plt.close(figure)


def run_search(*, package: Path, output: Path, evaluator: Any, wall_seconds: float = 350) -> dict:
    if not 0 < wall_seconds <= 350:
        raise ValueError("Search wall time must be in (0,350] seconds")
    if output.exists():
        raise FileExistsError("Search output already exists; no overwrite or automatic rerun")
    if getattr(evaluator, "calls", 0) != 0:
        raise ValueError("Independent search must start with a fresh evaluator query ledger")
    candidates_path = package / "data/candidates_unlabeled_20000.csv"
    scenario_path, domain_path = package / "configs/scenarios.json", package / "configs/domain.json"
    scenarios = json.loads(scenario_path.read_text())["scenarios"]
    bounds = json.loads(domain_path.read_text())["bounds"]
    if len(scenarios) != 4 or len({s["id"] for s in scenarios}) != 4:
        raise ValueError("V4 requires exactly four distinct frozen scenarios")
    rows = load_candidates(candidates_path, bounds)
    if len(rows) != 20000:
        raise ValueError("The frozen V4 X-only candidate table must contain 20000 rows")
    output.mkdir(parents=True)
    started = time.monotonic()
    deadline = started + wall_seconds
    write_json(output / "frozen_search_protocol.json", {**PROTOCOL, "wall_seconds": wall_seconds,
        "candidate_count": len(rows), "input_hashes": {"X_only_candidates": sha256(candidates_path),
            "scenarios": sha256(scenario_path), "domain": sha256(domain_path), "search_source": sha256(Path(__file__))},
        "scenarios": scenarios, "bounds": bounds, "forbidden_data_access": "no_supervised_roles_or_formula_internals",
        "evaluator_identity": getattr(evaluator, "identity", None)})
    experiments, events, pools = [], [], []
    status, reason = "completed", None
    try:
        for scenario_index, scenario in enumerate(scenarios):
            for seed in SEEDS:
                _check_deadline(deadline)
                pool, initial, pool_record = paired_pool(rows, scenario, seed, scenario_index)
                pools.append({"scenario_id": scenario["id"], "seed": seed, **pool_record})
                write_json(output / "paired_candidate_pools.json", pools)
                for method in METHODS:
                    _check_deadline(deadline)
                    summary = run_experiment(evaluator=evaluator, pool=pool, initial=initial, scenario=scenario,
                        bounds=bounds, method=method, seed=seed, scenario_index=scenario_index,
                        directory=output / scenario["id"] / f"seed_{seed}" / method,
                        deadline=deadline, global_events=events)
                    experiments.append(summary)
                    write_json(output / "experiment_summaries.json", experiments)
                    if summary["status"] != "completed":
                        status, reason = summary["status"], summary["stop_reason"]
                        raise SearchDeadline(reason)
    except SearchDeadline as exc:
        if status == "completed":
            status, reason = "budget_exhausted", str(exc)
    except Exception as exc:
        status, reason = "failed", f"{type(exc).__name__}: {exc}"
    aggregates = _trajectory_aggregates(experiments, scenarios)
    write_json(output / "trajectory_aggregates.json", aggregates)
    recommendations = export_recommendations(output, events, scenarios)
    finite_reference = {s["id"]: {**best_actual([e for e in events if e["scenario_id"] == s["id"]], s),
                        "unique_queried_designs": len({e["design_id"] for e in events if e["scenario_id"] == s["id"]}),
                        "meaning": "posthoc_finite_union_of_actual_queries_not_global_optimum"} for s in scenarios}
    plot_trajectories(output, experiments, scenarios, aggregates)
    total_calls = getattr(evaluator, "calls", len(events))
    unique_calls = getattr(evaluator, "unique_computations", len({e["evaluation_id"] for e in events}))
    cache_hits = getattr(evaluator, "cache_hits", sum(e["cache_hit"] for e in events))
    if status == "completed" and (len(experiments) != 24 or len(events) != MAX_EVENTS or total_calls != MAX_EVENTS):
        status, reason = "failed", "completed_budget_accounting_mismatch"
    summary = {"schema_version": PROTOCOL["schema_version"], "status": status, "stop_reason": reason,
               "source": "synthetic_only", "physical_state": "undetermined", "eligible_as_validated_training_truth": False,
               "experiment_count": len(experiments), "completed_experiment_count": sum(e["status"] == "completed" for e in experiments),
               "logical_evaluation_events": total_calls, "successful_ledger_events": len(events),
               "failed_evaluation_events": total_calls - len(events),
               "unique_evaluator_computations": unique_calls, "cache_hits": cache_hits,
               "unique_queried_designs": len({e["design_id"] for e in events}),
               "candidate_X_only_count": len(rows), "finite_queried_reference": finite_reference,
               "recommendations_exported": len(recommendations), "full_GMMNLSE_runs": 0,
               "wall_seconds": time.monotonic() - started,
               "GP_fit_and_predict_seconds": sum(e["GP_fit_and_predict_seconds"] for e in experiments),
               "real_solver_error": None, "real_solver_error_missing_reason": "no_real_execution_authorized",
               "limitations": ["Only 3 paired seeds; no general statistical superiority claim",
                   "GP constraint probabilities are approximate and uncalibrated",
                   "Finite queried reference is not a continuous global optimum or full-domain regret",
                   "Scalar synthetic model does not establish GMMNLSE accuracy or physical stability"]}
    write_json(output / "search_summary.json", summary)
    return summary
