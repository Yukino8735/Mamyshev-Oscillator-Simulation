#!/usr/bin/env python3
"""Export the public Demo from authoritative main-project files, without execution.

No inference, fitting, oracle, database, MATLAB, network or Git write is used.
The public profile is an explicit file allowlist, not a directory-copy policy.
"""
from __future__ import annotations

import argparse
import ast
import builtins
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import symtable

PROFILE = "demo/deploy/profile.json"
SELF = "scripts/export_demo.py"
MANIFEST = "deploy_manifest.json"
FORBIDDEN_PARTS = {".git", "reports", "data", "results", "archive", "third_party",
                   "__pycache__", "v42", "node_modules", ".venv"}
FORBIDDEN_SUFFIXES = {".csv", ".sqlite", ".sqlite3", ".db", ".jsonl", ".mat",
                      ".zip", ".log", ".pyc", ".pyo"}


class ExportError(ValueError):
    """Fail closed before creating the destination whenever possible."""


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False,
                       allow_nan=False) + "\n").encode()


def decode(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ExportError("Duplicate JSON key: " + key)
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=pairs)


def relative(value):
    if not isinstance(value, str) or not value or "\\" in value:
        raise ExportError("Expected an explicit POSIX relative file path")
    path = PurePosixPath(value)
    if path.is_absolute() or str(path) != value or any(p in {".", ".."} for p in path.parts):
        raise ExportError("Unsafe relative path: " + value)
    if set(path.parts) & FORBIDDEN_PARTS or path.suffix.lower() in FORBIDDEN_SUFFIXES:
        raise ExportError("Excluded publication path: " + value)
    return value


def regular(root, name):
    relative(name)
    path = root
    for part in PurePosixPath(name).parts:
        path = path / part
        if path.is_symlink():
            raise ExportError("Symlink source refused: " + name)
    if not path.is_file():
        raise ExportError("Missing required source: " + name)
    return path


def required_sources(profile):
    return sorted({PROFILE, SELF, *profile["copy"], *profile["templates"].values(),
                   *profile["pure_modules"]})


def _globals(text):
    table = symtable.symtable(text, "<selected-source>", "exec")
    names = set()
    def visit(scope):
        names.update(s.get_name() for s in scope.get_symbols()
                     if s.is_referenced() and s.is_global())
        for child in scope.get_children():
            visit(child)
    visit(table)
    return names - set(vars(builtins)) - {"__file__"}


def extract_module(source, spec):
    """Keep exact selected source nodes; close/check every global dependency.

    Import names are taken from the full authoritative module, including Path
    used by the CSV branch. New undeclared functions/constants/imports fail
    rather than silently importing an execution backend into the public tree.
    """
    tree = ast.parse(source)
    definitions, imports, future = {}, {}, []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            definitions[node.name] = node
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            definitions[node.targets[0].id] = node
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom) and node.module == "__future__":
                future.append(node)
                continue
            for alias in node.names:
                imports[alias.asname or alias.name.split(".")[0]] = (node, alias)
    selected = set(spec["functions"]) | set(spec["constants"])
    if len(selected) != len(spec["functions"]) + len(spec["constants"]):
        raise ExportError("Duplicate selected pure symbol")
    for name in selected:
        node = definitions.get(name)
        expected = ast.FunctionDef if name in spec["functions"] else ast.Assign
        if not isinstance(node, expected):
            raise ExportError("Missing/changed pure symbol: " + name)
    segments = [ast.get_source_segment(source, definitions[name]) for name in selected]
    needs = set().union(*(_globals(segment) for segment in segments)) - selected
    unexpected = needs - set(imports)
    if unexpected:
        raise ExportError("Undeclared pure dependencies: " + ", ".join(sorted(unexpected)))
    selected_imports = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            aliases = [a for a in node.names if (a.asname or a.name.split(".")[0]) in needs]
            if aliases:
                selected_imports.append(ast.Import(names=aliases))
        elif isinstance(node, ast.ImportFrom) and node.module != "__future__":
            aliases = [a for a in node.names if (a.asname or a.name) in needs]
            if aliases:
                selected_imports.append(ast.ImportFrom(module=node.module, names=aliases, level=node.level))
    ordered = [node for node in tree.body if node in [definitions[n] for n in selected]]
    import_names = set()
    for node in [*selected_imports, *(child for n in ordered for child in ast.walk(n))]:
        if isinstance(node, ast.Import):
            import_names.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            import_names.add("." * node.level + (node.module or ""))
    if import_names - set(spec["imports"]):
        raise ExportError("Unapproved pure import: " + ", ".join(sorted(import_names - set(spec["imports"]))))
    header = '"""Generated from authoritative main-project pure helpers; do not edit here."""\n'
    text = header + "\n".join(ast.unparse(n) for n in future + selected_imports) + "\n\n"
    text += "\n\n\n".join(ast.get_source_segment(source, n) for n in ordered) + "\n"
    generated = ast.parse(text)
    copied_nodes = [n for n in generated.body if isinstance(n, (ast.FunctionDef, ast.Assign))]
    if [ast.dump(n, include_attributes=False) for n in copied_nodes] != [ast.dump(n, include_attributes=False) for n in ordered]:
        raise ExportError("Generated pure-node AST differs from authoritative source")
    # Resolve generated globals again; unresolved names cannot hide in an unused branch.
    bound = selected | needs
    if _globals(text) - bound:
        raise ExportError("Generated pure module has unresolved globals")
    return text.encode(), {"functions": spec["functions"], "constants": spec["constants"],
                          "imports": sorted(import_names), "selected_ast_equal": True,
                          "global_dependency_check": "passed"}


def validate_profile(profile):
    expected = {"schema_version", "profile_version", "python_requested", "model_id",
                "model_sha256", "model_manifest_sha256", "class_sha256", "copy",
                "templates", "pure_modules", "requirements", "streamlit_config"}
    if set(profile) != expected or profile["schema_version"] != "mamyshev_public_demo_profile_v1":
        raise ExportError("Unknown public profile schema/fields")
    outputs = [*profile["copy"], *profile["templates"], *profile["pure_modules"],
               "requirements.txt", ".streamlit/config.toml"]
    if len(outputs) != len(set(outputs)) or MANIFEST in outputs:
        raise ExportError("Duplicate/reserved destination in profile")
    for value in outputs + required_sources(profile):
        relative(value)
    if any(not re.fullmatch(r"[A-Za-z0-9_-]+==[0-9]+(?:\.[0-9]+)+", p)
           for p in profile["requirements"]):
        raise ExportError("Public dependencies must be exact pinned versions")
    for spec in profile["pure_modules"].values():
        if set(spec) != {"functions", "constants", "imports"}:
            raise ExportError("Unexpected pure-module selection schema")
    return sorted(outputs)


def validate_assets(data, profile):
    folder = "demo/assets/models/" + profile["model_id"] + "/"
    inner = decode(data[folder + "manifest.json"])
    catalog = decode(data["demo/assets/models/catalog.json"])
    if (sha(data[folder + "manifest.json"]) != profile["model_manifest_sha256"]
            or inner.get("model_id") != profile["model_id"]
            or catalog.get("default_model_id") != profile["model_id"]
            or set(catalog.get("models", {})) != {profile["model_id"]}):
        raise ExportError("Trusted model/catalog/manifest identity mismatch")
    for name, expected in inner["files"].items():
        if "/" in name or folder + name not in data or sha(data[folder + name]) != expected:
            raise ExportError("Missing/changed frozen model asset: " + name)
    entry = catalog["models"][profile["model_id"]]
    if (sha(data[folder + "model.joblib"]) != profile["model_sha256"]
            or sha(data[folder + "models_v4.py"]) != profile["class_sha256"]
            or entry["directory"] != profile["model_id"]
            or entry["model_sha256"] != profile["model_sha256"]
            or entry["manifest_sha256"] != profile["model_manifest_sha256"]):
        raise ExportError("Frozen model/class/catalog identity mismatch")
    if data[folder + "domain.json"] != data["mamyshev_accuracy_v4/configs/domain.json"]:
        raise ExportError("Inference and pure planning domain differ")
    pins = dict(p.split("==", 1) for p in profile["requirements"])
    for name, version in decode(data[folder + "dependencies.json"])["packages"].items():
        if pins.get(name) != version:
            raise ExportError("Public dependency differs from frozen model: " + name)
    return decode(data[folder + "calibration.json"])["q_joint_log"]


def source_git_identity(source):
    if not (source / ".git").exists():
        return {"source_commit": None, "source_dirty": None}
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
    def read(*args):
        result = subprocess.run(["git", "-c", "core.fsmonitor=false", *args], cwd=source,
                                env=env, capture_output=True, text=True, timeout=10, check=True)
        return result.stdout.strip()
    return {"source_commit": read("rev-parse", "HEAD"),
            "source_dirty": bool(read("status", "--porcelain=v1", "--untracked-files=all"))}


def export_demo(source, output):
    source = Path(source).resolve()
    output = Path(output).expanduser()
    if ".." in output.parts:
        raise ExportError("Output path traversal refused")
    output = output.absolute()
    for part in (output, *output.parents):
        if part.is_symlink():
            raise ExportError("Symlink destination/ancestor refused")
    if output.exists():
        raise ExportError("Output already exists; preserve it and choose only an explicitly authorized destination")
    if not output.parent.is_dir():
        raise ExportError("Output parent must already exist")
    if source == output or source in output.parents:
        raise ExportError("Output must be outside the authoritative source tree")
    profile_bytes = regular(source, PROFILE).read_bytes()
    profile = decode(profile_bytes)
    expected_outputs = validate_profile(profile)
    missing = []
    for name in required_sources(profile):
        try:
            regular(source, name)
        except ExportError as exc:
            missing.append(str(exc))
    if missing:
        raise ExportError("Required export sources unavailable; no output created:\n" + "\n".join(missing))
    data = {name: regular(source, name).read_bytes() for name in required_sources(profile)}
    if data[PROFILE] != profile_bytes:
        raise ExportError("Profile changed during export")
    q = validate_assets(data, profile)
    payload = {name: data[name] for name in profile["copy"]}
    transforms = {name: {"source": name, "transform": "byte_copy"} for name in profile["copy"]}
    for destination, template in profile["templates"].items():
        payload[destination] = data[template]
        transforms[destination] = {"source": template, "transform": "public_template"}
    pure_checks = {}
    for name, spec in profile["pure_modules"].items():
        payload[name], pure_checks[name] = extract_module(data[name].decode(), spec)
        transforms[name] = {"source": name, "transform": "selected_authoritative_ast"}
    payload["requirements.txt"] = ("\n".join(profile["requirements"]) + "\n").encode()
    payload[".streamlit/config.toml"] = profile["streamlit_config"].encode()
    for name in ("requirements.txt", ".streamlit/config.toml"):
        transforms[name] = {"source": PROFILE, "transform": "public_profile"}
    if sorted(payload) != expected_outputs:
        raise ExportError("Undeclared or missing export payload")
    for name, value in payload.items():
        if not name.endswith(".joblib") and any(p in value for p in (b"/Users/", b"/opt/homebrew/", b"/private/var/")):
            raise ExportError("Private absolute path in public payload: " + name)
    manifest = {"schema_version": "mamyshev_main_export_v1", "profile_version": profile["profile_version"],
                "profile_sha256": sha(profile_bytes), "model_ids": [profile["model_id"]],
                "default_model_id": profile["model_id"], "model_sha256": profile["model_sha256"],
                "q_joint_log": q, "python_requested": profile["python_requested"],
                "publication_approval": "separate_owner_authorization_required_not_granted_by_exporter",
                "full_backend_included": False, "training_rows_included": 0,
                "source_git_history_copied": False, **source_git_identity(source),
                "source_files": [{"path": n, "bytes": len(v), "sha256": sha(v)} for n, v in sorted(data.items())],
                "pure_module_checks": pure_checks,
                "files": [{"path": n, "bytes": len(v), "sha256": sha(v), **transforms[n]}
                          for n, v in sorted(payload.items())],
                "allowlist_sha256": sha(encoded(expected_outputs)),
                "manifest_self_hash": "external receipt; not included in its own file list"}
    payload[MANIFEST] = encoded(manifest)
    # Read-only consistency check before the first destination write.
    for name, value in data.items():
        if regular(source, name).read_bytes() != value:
            raise ExportError("Source changed during export: " + name)
    output.mkdir(exist_ok=False)
    for name, value in sorted(payload.items()):
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(value)
    actual = sorted(p.relative_to(output).as_posix() for p in output.rglob("*") if p.is_file())
    if actual != sorted(payload):
        raise ExportError("Unexpected output files; preserve partial directory for diagnosis")
    return {"schema_version": "mamyshev_export_receipt_v1", "files": len(payload),
            "total_bytes": sum(len(v) for v in payload.values()),
            "manifest_sha256": sha(payload[MANIFEST]), "allowlist_sha256": manifest["allowlist_sha256"],
            "profile_version": profile["profile_version"], "source_commit": manifest["source_commit"],
            "source_dirty": manifest["source_dirty"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Nonexistent directory outside the source tree")
    args = parser.parse_args()
    try:
        result = export_demo(Path(__file__).resolve().parents[1], args.output)
    except (ExportError, OSError, KeyError, subprocess.SubprocessError) as exc:
        parser.exit(2, "Export refused: " + str(exc) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
