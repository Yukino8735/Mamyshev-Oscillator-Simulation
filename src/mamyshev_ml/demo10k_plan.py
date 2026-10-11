"""Strict X-only plan preparation; the existing serial scan runner executes it.

This module never imports the synthetic oracle and cannot launch MATLAB.
The complete plan and selection tables belong in ignored local evidence only.
"""
from __future__ import annotations

import csv
from pathlib import Path

from .v4_evaluators import FEATURES, TARGETS, design_id, digest, validate_design
from .v4_scan import make_plan, verify_plan

INPUT_UNITS = dict(zip(FEATURES, ("W", "nm", "nm", "m")))
METADATA_COLUMNS = {"design_id", "role", "group", "order_in_role"}


def read_input_rows(path, *, expected_count):
    """Accept the frozen X-only sampling table, never labels or unit aliases."""
    if isinstance(expected_count, bool) or not isinstance(expected_count, int) or expected_count <= 0:
        raise ValueError("Explicit positive N required")
    with Path(path).open(newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)) or not set(FEATURES) <= set(fields):
            raise ValueError("Unique headers and all four input columns required")
        if set(fields) - set(FEATURES) - METADATA_COLUMNS:
            raise ValueError("X-only input cannot contain targets, unknown fields or unit aliases")
        rows = []
        ids = set()
        for ordinal, row in enumerate(reader):
            if None in row:
                raise ValueError("Extra CSV cells are not accepted")
            design = validate_design({key: float(row[key]) for key in FEATURES})
            identifier = design_id(design)
            if row.get("design_id", identifier) != identifier:
                raise ValueError("Input ID differs from exact canonical four-input identity")
            if identifier in ids:
                raise ValueError("Duplicate design is rejected, not silently removed")
            ids.add(identifier)
            rows.append({"design_id": identifier, "design_config": design, "source_ordinal": ordinal})
    if len(rows) != expected_count:
        raise ValueError(f"Expected exactly {expected_count} unique X rows, found {len(rows)}")
    return rows


def pending_plan(rows):
    plan = make_plan(method="candidates", designs=[row["design_config"] for row in rows])
    if plan["duplicates_removed"] or plan["invalid"] or plan["unique_designs"] != len(rows):
        raise ValueError("Input validation must preserve every submitted design")
    plan.update(backend="gmmnlse", input_units=INPUT_UNITS, job_status="not_run",
                source_kind="pending_original_solver_not_synthetic_labels",
                execution_order="serial", max_new_real_attempts=0,
                waveform_allocation="One existing single-run result at a time; no N-design field allocation")
    for row in plan["designs"]:
        row.update(real_targets=dict.fromkeys(TARGETS), job_status="not_run",
                   real_targets_missing_reason="Pending separate explicit GMMNLSE authorization")
    plan["plan_hash"] = digest({key: value for key, value in plan.items() if key != "plan_hash"})
    validate_pending_plan(plan, expected_count=len(rows))
    return plan


def validate_pending_plan(plan, *, expected_count):
    verify_plan(plan)
    if plan.get("backend") != "gmmnlse" or plan.get("input_units") != INPUT_UNITS:
        raise ValueError("Explicit GMMNLSE backend and named SI-derived units required")
    if plan.get("max_new_real_attempts") != 0 or plan.get("job_status") != "not_run":
        raise ValueError("Preparation grants no real attempts")
    if any(plan.get(key) != expected_count for key in ("input_count", "unique_designs")):
        raise ValueError("Plan count differs from requested N")
    if len(plan["designs"]) != expected_count or plan.get("duplicates_removed") != 0:
        raise ValueError("Plan rows or unique count disagree")
    for row in plan["designs"]:
        if row.get("real_targets") != dict.fromkeys(TARGETS) or row.get("job_status") != "not_run":
            raise ValueError("Pending solver rows must retain null targets and not_run")
    return plan


def select_rows(plan, *, start=0, stop=None, design_ids=None):
    """Read-only selection references the full immutable plan; no new allowance."""
    verify_plan(plan)
    n = len(plan["designs"])
    stop = n if stop is None else stop
    if any(isinstance(v, bool) or not isinstance(v, int) for v in (start, stop)) or not 0 <= start <= stop <= n:
        raise ValueError("Explicit valid zero-based half-open selection required")
    if design_ids is not None:
        if len(design_ids) != len(set(design_ids)) or not set(design_ids) <= {row["design_id"] for row in plan["designs"]}:
            raise ValueError("Filter IDs must be unique and belong to the full plan")
        selected = set(design_ids)
    else:
        selected = None
    rows = [row for row in plan["designs"][start:stop] if selected is None or row["design_id"] in selected]
    return {"parent_plan_hash": plan["plan_hash"], "start_inclusive": start, "stop_exclusive": stop,
            "design_ids": [row["design_id"] for row in rows], "row_count": len(rows),
            "rows_hash": digest(rows), "max_new_real_attempts": 0}


def chunk_rows(plan, *, chunk_size=256):
    """Validate once, then enumerate scalar plan rows without loading any MAT."""
    verify_plan(plan)
    if isinstance(chunk_size, bool) or not isinstance(chunk_size, int) or chunk_size <= 0:
        raise ValueError("Positive integer chunk size required")
    for start in range(0, len(plan["designs"]), chunk_size):
        stop = min(start + chunk_size, len(plan["designs"]))
        rows = plan["designs"][start:stop]
        yield {"parent_plan_hash": plan["plan_hash"], "start_inclusive": start,
               "stop_exclusive": stop, "design_ids": [row["design_id"] for row in rows],
               "row_count": len(rows), "rows_hash": digest(rows), "max_new_real_attempts": 0}


def zero_authorization(plan):
    """Shape-valid denied authorization, suitable for existing default-denial tests."""
    return {"authorization_id": "demo10k_pending_no_real_permission", "plan_hash": plan["plan_hash"],
            "allowed_design_ids": [row["design_id"] for row in plan["designs"]], "max_new_attempts": 0,
            "per_run_timeout_s": 1800, "total_wall_limit_s": 1800, "seed": 0, "save_waveforms": True,
            "observation_protocol": {"mode": "legacy"}}
