"""V4.1 X-only geometry and cross-role exclusion registry.

No oracle/model imports. SQL selects only design identifiers and input columns;
CSV readers immediately project X/ID and never parse or retain target columns.
Geometry follows V4 build_release.py, without importing its label-generating code.
"""
from __future__ import annotations

from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
import random
import re
import sqlite3

ROOT = Path(__file__).resolve().parents[2]
FEATURES = ("pump_power_W", "filter_offset_nm", "filter2_bw_nm", "gain_length_m")
GROUPS = ("slice", "near_slice", "outer_faces", "corners", "reference_core", "reference_expanded")
SEEDS = {"train": 41011, "dev": 41022, "calibration": 41033, "test": 41044}
QUOTAS = {
    "train": dict(zip(GROUPS, (128, 128, 64, 64, 64, 64))),
    "dev": dict(zip(GROUPS[:4], (128, 128, 128, 128))),
    "calibration": dict(zip(GROUPS, (128, 128, 128, 128, 256, 256))),
    "test": dict(zip(GROUPS, (256, 256, 256, 256, 512, 512))),
}
ANCHOR = dict(zip(FEATURES, (4.0, 10.0, 3.0, 4.0)))
SCHEMA = "mamyshev_v41_x_only_sampling_v1"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def canonical_design(value):
    """Normalize numeric representation, never round a supplied coordinate."""
    if set(value) != set(FEATURES):
        raise ValueError("Exactly four input coordinates required")
    result = {}
    for name in FEATURES:
        item = value[name]
        if isinstance(item, bool):
            raise ValueError("Boolean is not a design coordinate")
        try:
            number = float(item)
        except (TypeError, ValueError) as error:
            raise ValueError(f"Invalid coordinate {name}") from error
        if not math.isfinite(number):
            raise ValueError(f"Nonfinite coordinate {name}")
        result[name] = 0.0 if number == 0 else number
    return result


def canonical_id(design):
    return "d_" + hashlib.sha256(canonical(canonical_design(design)).encode()).hexdigest()[:24]


def sha_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(part)
    return digest.hexdigest()


class ExclusionRegistry:
    """Canonical X is authoritative; arbitrary source IDs remain traceable aliases."""
    def __init__(self, domain=None):
        self.domain = domain
        self.entries = {}
        self.mappings = []
        self.sources = []
        self.sampled_roles = {}
        self.rejection_events = []
        self._source_ids = {}

    def add(self, design, *, original_id, source, reason, row=None):
        x = canonical_design(design); key = canonical_id(x)
        alias = str(original_id) if original_id not in (None, "") else None
        alias_key = (str(source), alias)
        if alias is not None and alias_key in self._source_ids and self._source_ids[alias_key] != key:
            raise ValueError("One source reuses an original ID for different X; resolve the source before sampling")
        if alias is not None:
            self._source_ids[alias_key] = key
        existed = key in self.entries
        entry = self.entries.setdefault(key, {"canonical_id": key, "design": x, "original_ids": [], "reasons": [], "sources": []})
        if entry["design"] is None:
            entry["design"] = x
        elif entry["design"] != x:
            raise ValueError("Canonical ID collision with differing coordinates")
        for field, value in (("original_ids", alias), ("reasons", reason), ("sources", str(source))):
            if value is not None and value not in entry[field]:
                entry[field].append(value)
        self.mappings.append({"original_id": alias, "canonical_id": key, "source": str(source),
                              "source_row": row, "reason": reason, "mapping": "recomputed_from_exact_four_X"})
        return key, existed

    def add_canonical_id_only(self, key, *, source, reason, row=None):
        if not re.fullmatch(r"d_[0-9a-f]{24}", key):
            raise ValueError("Legacy ID-only exclusion requires the documented V3/V4 canonical ID scheme")
        entry = self.entries.setdefault(key, {"canonical_id": key, "design": None,
            "original_ids": [], "reasons": [], "sources": []})
        for field, value in (("original_ids", key), ("reasons", reason), ("sources", str(source))):
            if value not in entry[field]: entry[field].append(value)
        self.mappings.append({"original_id": key, "canonical_id": key, "source": str(source),
                              "source_row": row, "reason": reason,
                              "mapping": "legacy_canonical_id_only_X_not_provided"})

    def contains(self, design):
        return canonical_id(design) in self.entries

    def summary(self):
        return {"schema_version": SCHEMA, "canonical_exclusions": len(self.entries),
                "source_mapping_rows": len(self.mappings),
                "canonical_entries_missing_X": sum(v["design"] is None for v in self.entries.values()),
                "reason_mapping_counts": dict(Counter(m["reason"] for m in self.mappings)),
                "sources": self.sources, "sampled_roles": self.sampled_roles,
                "sampling_rejection_events": len(self.rejection_events),
                "target_columns_selected": False, "oracle_calls": 0, "model_calls": 0}

    def save(self, directory):
        """Write a new auditable X/ID exclusion snapshot; never overwrite evidence."""
        out = Path(directory); out.mkdir(parents=True, exist_ok=False)
        (out / "summary.json").write_text(json.dumps(self.summary(), ensure_ascii=False, indent=2) + "\n")
        with (out / "exclusions.jsonl").open("x") as stream:
            for key in sorted(self.entries): stream.write(canonical(self.entries[key]) + "\n")
        with (out / "id_mappings.jsonl").open("x") as stream:
            for mapping in self.mappings: stream.write(canonical(mapping) + "\n")
        with (out / "sampling_rejections.jsonl").open("x") as stream:
            for event in self.rejection_events: stream.write(canonical(event) + "\n")
        return {"summary": str(out / "summary.json"), "exclusions": str(out / "exclusions.jsonl"),
                "id_mappings": str(out / "id_mappings.jsonl"), "sampling_rejections": str(out / "sampling_rejections.jsonl")}


def _input_columns(headers, columns=None):
    mapping = columns or {k: k for k in FEATURES}
    if set(mapping) != set(FEATURES) or not set(mapping.values()).issubset(headers):
        raise ValueError("X source lacks an explicit complete four-coordinate schema")
    return mapping


def _csv_x_rows(path, columns=None):
    with Path(path).open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream); headers = next(reader)
        mapping = _input_columns(headers, columns)
        positions = {k: headers.index(name) for k, name in mapping.items()}
        id_name = next((k for k in ("design_id", "case_id", "id") if k in headers), None)
        id_position = headers.index(id_name) if id_name else None
        for index, row in enumerate(reader, start=2):
            # Unselected columns may contain labels, but are never converted,
            # retained, returned, or used in acceptance/sampling decisions.
            x = {k: row[j] for k, j in positions.items()}
            yield index, row[id_position] if id_position is not None else None, x


def _sql_x_rows(path, columns=None):
    with sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True) as db:
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "designs" not in tables:
            raise ValueError("X-only SQL import requires a designs table")
        headers = {row[1] for row in db.execute("PRAGMA table_info(designs)")}
        if "design_json" in headers and "design_id" in headers:
            # This table contains input coordinates only, not evaluation JSON.
            query = "SELECT design_id,design_json FROM designs ORDER BY design_id"
            for index, (original, encoded) in enumerate(db.execute(query), 1):
                value = json.loads(encoded)
                yield index, original, {k: value[k] for k in FEATURES}
        else:
            mapping = _input_columns(headers, columns)
            if "design_id" not in headers:
                raise ValueError("SQL design identifier required")
            names = ["design_id", *mapping.values()]
            if any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) for name in names):
                raise ValueError("Unsafe SQL identifier")
            query = "SELECT " + ",".join('"' + name + '"' for name in names) + " FROM designs ORDER BY design_id"
            for index, row in enumerate(db.execute(query), 1):
                yield index, row[0], dict(zip(mapping, row[1:]))


def _search_x_rows(path):
    # Do not decode event targets/predictions/feasibility into Python values.
    # The existing event schema writes a flat four-coordinate design object.
    with Path(path).open() as stream:
        for index, line in enumerate(stream, 1):
            match = re.search(r'"design"\s*:\s*(\{[^{}]*\})', line)
            identifier = re.search(r'"design_id"\s*:\s*("(?:[^"\\]|\\.)*")', line)
            if match is None or identifier is None:
                raise ValueError("Search event lacks its explicit X/ID projection")
            x = json.loads(match.group(1))
            yield index, json.loads(identifier.group(1)), {k: x[k] for k in FEATURES}


def _include_source(registry, source):
    path, kind = Path(source["path"]), source["kind"]
    reason = source["reason"]; columns = source.get("columns")
    if reason == "v4_candidate_X_only_20000":
        with path.open(newline="", encoding="utf-8-sig") as stream:
            headers = next(csv.reader(stream))
        if any(name in headers for name in ("compressed_energy_nJ", "compressed_duration_fs", "compressed_peak_power_MW")):
            raise ValueError("The fixed candidate file must remain X-only, with no target columns")
    if kind == "csv": rows = _csv_x_rows(path, columns)
    elif kind == "sqlite": rows = _sql_x_rows(path, columns)
    elif kind == "search_jsonl": rows = _search_x_rows(path)
    else: raise ValueError("Supported X sources: csv, sqlite, search_jsonl")
    projection_digest = hashlib.sha256(); count = aliases = 0
    for index, original_id, design in rows:
        x = canonical_design(design)
        key, existed = registry.add(x, original_id=original_id, source=path, reason=reason, row=index)
        aliases += int(existed); count += 1
        projection_digest.update((canonical({"original_id": original_id, "canonical_id": key, "design": x}) + "\n").encode())
    value = {"path": str(path), "kind": kind, "reason": reason, "projected_rows": count,
             "existing_canonical_aliases": aliases, "x_id_projection_sha256": projection_digest.hexdigest(),
             "target_columns_selected": False}
    if reason == "v4_candidate_X_only_20000":
        value["candidate_X_only_file_sha256"] = sha_file(path)
        if count != 20000: raise ValueError("Expected all 20000 existing X-only candidates")
    registry.sources.append(value)


def build_exclusions(root=ROOT, extra_sources=()):
    """Build global exclusions from old X/IDs, never from old Y or predictions.

    extra_sources entries: {path,kind,reason,columns?}; columns maps the four
    canonical feature names to explicitly supplied legacy column names.
    Missing required release files raise instead of claiming a complete audit.
    """
    root = Path(root); package = root / "mamyshev_accuracy_v4"
    domain = json.loads((package / "configs/domain.json").read_text())
    registry = ExclusionRegistry(domain)
    registry.add(ANCHOR, original_id="phase2_config_waveform_default_anchor", source="explicit_existing_default_design",
                 reason="existing_anchor")
    sources = [
        {"path": package / "data/development.sqlite", "kind": "sqlite", "reason": "v4_old_labeled_development_X"},
        {"path": package / "evaluation_only/evaluation.sqlite", "kind": "sqlite", "reason": "v4_old_labeled_evaluation_X_only"},
        {"path": package / "data/candidates_unlabeled_20000.csv", "kind": "csv", "reason": "v4_candidate_X_only_20000"},
    ]
    for name in ("train_pool_512.csv", "validation_128.csv", "oracle_parity_cases_24.csv"):
        sources.append({"path": package / "provenance" / name, "kind": "csv", "reason": "v3_provenance_or_parity_X_only"})
    search_paths = sorted((root / "reports/local/accuracy_v4_001/search").glob("**/events.jsonl"))
    if not search_paths:
        raise FileNotFoundError("Previous V4 search events are required for complete exclusions")
    for path in search_paths:
        sources.append({"path": path, "kind": "search_jsonl", "reason": "v4_previously_queried_search_X"})
    for path in sorted((root / "reports/local/accuracy_v4_001/data_chain").glob("**/*.sqlite")):
        sources.append({"path": path, "kind": "sqlite", "reason": "v4_previous_datastore_design_seen"})
    sources.extend(extra_sources)
    for source in sources: _include_source(registry, source)
    legacy_path = package / "provenance/v3_design_ids.json"
    legacy = json.loads(legacy_path.read_text())
    for role, ids in legacy.items():
        for index, key in enumerate(ids, 1):
            registry.add_canonical_id_only(key, source=str(legacy_path) + ":" + role,
                reason="legacy_v3_ids_excluded_even_when_X_unavailable", row=index)
    registry.sources.append({"path": str(legacy_path), "kind": "canonical_ids_only",
        "projected_rows": sum(map(len, legacy.values())), "sha256": sha_file(legacy_path),
        "limitation": "Archived IDs without coordinates are excluded by their documented canonical scheme; no X is reconstructed."})
    return registry, registry.summary()


def _levels(bounds, step):
    lo, hi = bounds
    first, last = lo / step, hi / step
    if abs(first - round(first)) > 1e-9 or abs(last - round(last)) > 1e-9:
        raise ValueError("Declared length bounds must already lie on the legal grid")
    # Integers are sampled first. This never rounds a submitted design length.
    return [tick / 10 for tick in range(int(round(first)), int(round(last)) + 1)]


def _uniform(rng, bounds, step):
    value = {k: round(rng.uniform(*bounds[k]), 6) for k in FEATURES[:3]}
    value["gain_length_m"] = rng.choice(_levels(bounds["gain_length_m"], step))
    return value


def in_core(design, domain):
    return all(lo <= design[k] <= hi for k, (lo, hi) in domain["historical_core"].items())


def _draw(group, rng, index, domain):
    bounds, step = domain["bounds"], domain["gain_length_step_m"]
    if step != 0.1:
        raise ValueError("This frozen sampler implements the existing 0.1 m grid only")
    if group == "reference_core": return _uniform(rng, domain["historical_core"], step)
    if group == "near_slice":
        x = _uniform(rng, bounds, step)
        x["pump_power_W"] = round(rng.uniform(3.5, 4.5), 6)
        x["gain_length_m"] = rng.choice([tick / 10 for tick in range(37, 44)])
        return x
    if group == "corners":
        x = {}
        for j, key in enumerate(FEATURES):
            lo, hi = bounds[key]; side = (index // (2 ** j)) % 2
            if j < 3:
                u = rng.random() * 0.05
                x[key] = round(lo + (hi-lo) * (u if side == 0 else 1-u), 6)
            else:
                levels = _levels(bounds[key], step); span = max(1, math.ceil(.05 * len(levels)))
                x[key] = rng.choice(levels[:span] if side == 0 else levels[-span:])
        return x
    x = _uniform(rng, bounds, step)
    if group == "slice": x.update(pump_power_W=4.0, gain_length_m=4.0)
    elif group == "outer_faces":
        axis, side = index % 4, (index // 4) % 2
        x[FEATURES[axis]] = float(bounds[FEATURES[axis]][side])
    elif group != "reference_expanded": raise ValueError("Unknown sampling group")
    return x


def _stream_seed(role, seed, group):
    return int.from_bytes(hashlib.sha256(canonical([SCHEMA, role, seed, group]).encode()).digest(), "big")


def sample_role(role, seed, registry, protocol):
    """Return (X-only rows, rejection logs); mutate one shared cross-role registry.

    One invocation per role. Roles cannot be silently rerolled with new seeds or
    quotas; a failed/partial invocation remains in the registry's role ledger.
    """
    if role not in QUOTAS or protocol.get("role_quotas", {}).get(role) != QUOTAS[role]:
        raise ValueError("Role quotas differ from the fixed V4.1 allocation")
    if seed != SEEDS[role] or protocol.get("sampling_seeds", {}).get(role) != seed:
        raise ValueError("Role seed differs from the fixed V4.1 protocol")
    cap = protocol.get("max_sampling_proposals_per_group")
    if isinstance(cap, bool) or not isinstance(cap, int) or not 1 <= cap <= 100000:
        raise ValueError("Explicit X-only proposal cap in [1,100000] required")
    if registry.domain is None: raise ValueError("Registry requires declared domain geometry")
    if role in registry.sampled_roles: raise ValueError("Role already started; no silent resampling")
    registry.sampled_roles[role] = {"seed": seed, "status": "started", "accepted": 0,
        "protocol_sha256": hashlib.sha256(canonical(protocol).encode()).hexdigest(), "groups": {}}
    rows, collisions = [], []
    domain = registry.domain
    try:
        for group in GROUPS:
            quota = QUOTAS[role].get(group, 0)
            if not quota: continue
            rng = random.Random(_stream_seed(role, seed, group)); accepted = proposals = 0
            group_ledger = {"quota": quota, "proposals": 0, "accepted": 0, "rejected": 0,
                            "stream_seed": str(_stream_seed(role, seed, group))}
            registry.sampled_roles[role]["groups"][group] = group_ledger
            while accepted < quota:
                if proposals >= cap: raise RuntimeError(f"X-only proposal budget exhausted for {role}/{group}")
                x = _draw(group, rng, accepted, domain); proposals += 1
                group_ledger["proposals"] = proposals
                exclusion = None
                if group == "reference_expanded" and in_core(x, domain): exclusion = "expanded_draw_landed_in_core"
                elif group == "near_slice" and x["pump_power_W"] == 4 and x["gain_length_m"] == 4:
                    exclusion = "near_slice_excludes_exact_slice"
                key = canonical_id(x)
                if exclusion is None and key in registry.entries: exclusion = "existing_canonical_X_or_legacy_ID"
                if exclusion is not None:
                    prior = registry.entries.get(key)
                    event = {"role": role, "group": group, "proposal": proposals, "canonical_id": key,
                        "design": x, "reason": exclusion, "existing_reasons": prior["reasons"][:] if prior else [],
                        "existing_original_ids": prior["original_ids"][:] if prior else []}
                    collisions.append(event); registry.rejection_events.append(event)
                    group_ledger["rejected"] += 1
                    continue
                registry.add(x, original_id=key, source=f"v41_new_X/{role}/{group}", reason=f"new_role_{role}", row=accepted+1)
                rows.append({"design_id": key, "role": role, "group": group, **x})
                accepted += 1; registry.sampled_roles[role]["accepted"] += 1
                group_ledger["accepted"] = accepted
        random.Random(_stream_seed(role, seed, "row_order")).shuffle(rows)
        for index, row in enumerate(rows, 1): row["order_in_role"] = index
        registry.sampled_roles[role]["status"] = "completed"
        return rows, collisions
    except BaseException:
        registry.sampled_roles[role]["status"] = "failed_partial_no_resampling"
        raise


def write_role(rows, collisions, directory):
    out = Path(directory); out.mkdir(parents=True, exist_ok=False)
    columns = ["design_id", "role", "group", "order_in_role", *FEATURES]
    with (out / "inputs.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns); writer.writeheader(); writer.writerows(rows)
    with (out / "rejections.jsonl").open("x") as stream:
        for row in collisions: stream.write(canonical(row) + "\n")
    return {"inputs": str(out / "inputs.csv"), "rejections": str(out / "rejections.jsonl"),
            "inputs_sha256": sha_file(out / "inputs.csv"), "rows": len(rows), "rejected_proposals": len(collisions)}
