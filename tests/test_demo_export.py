"""Small export-only fixtures. No model is unpickled, scored, fitted or relabelled."""
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("_demo_export_under_test", ROOT / "scripts/export_demo.py")
EXPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXPORT)


class DemoExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mamyshev-export-fixture-")
        self.base = Path(self.temp.name).resolve()
        self.source = self.base / "restricted-source"
        self.source.mkdir()
        self.profile = json.loads((ROOT / EXPORT.PROFILE).read_text())
        # Only declared source dependencies exist. No deployment snapshot,
        # private templates, reports/local, training data, MAT, DB or old model.
        for name in EXPORT.required_sources(self.profile):
            dst = self.source / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, dst)

    def tearDown(self):
        self.temp.cleanup()

    def test_restricted_source_export_exact_manifest_and_reproducibility(self):
        first, second = self.base / "first", self.base / "second"
        a = EXPORT.export_demo(self.source, first)
        b = EXPORT.export_demo(self.source, second)
        self.assertEqual(a, b)
        files = sorted(p.relative_to(first).as_posix() for p in first.rglob("*") if p.is_file())
        manifest = json.loads((first / EXPORT.MANIFEST).read_text())
        self.assertEqual(files, sorted([EXPORT.MANIFEST] + [r["path"] for r in manifest["files"]]))
        for name in files:
            self.assertFalse((first / name).is_symlink())
            self.assertEqual((first / name).read_bytes(), (second / name).read_bytes())
        for row in manifest["files"]:
            value = (first / row["path"]).read_bytes()
            self.assertEqual(row["bytes"], len(value))
            self.assertEqual(row["sha256"], EXPORT.sha(value))
        self.assertEqual(a["manifest_sha256"], EXPORT.sha((first / EXPORT.MANIFEST).read_bytes()))
        self.assertEqual(manifest["model_ids"], ["demo_10k_v1"])
        self.assertIsNone(manifest["source_commit"])
        self.assertEqual(manifest["q_joint_log"], json.loads(
            (self.source / "demo/assets/models/demo_10k_v1/calibration.json").read_text())["q_joint_log"])
        self.assertFalse(any("v42" in p or "reports" in p or p.endswith((".csv", ".mat", ".db")) for p in files))
        self.assertNotIn(str(self.source), (first / EXPORT.MANIFEST).read_text())

    def test_missing_assets_fail_together_before_destination_creation(self):
        names = ["demo/assets/models/demo_10k_v1/model.joblib",
                 "demo/assets/models/demo_10k_v1/calibration.json"]
        for name in names:
            (self.source / name).unlink()
        out = self.base / "missing"
        with self.assertRaises(EXPORT.ExportError) as error:
            EXPORT.export_demo(self.source, out)
        for name in names:
            self.assertIn(name, str(error.exception))
        self.assertFalse(out.exists())

    def test_changed_asset_and_public_dependency_fail_closed(self):
        model = self.source / "demo/assets/models/demo_10k_v1/model.joblib"
        original = model.read_bytes()
        model.write_bytes(original + b"artificial-tamper-fixture")
        with self.assertRaisesRegex(EXPORT.ExportError, "frozen model asset"):
            EXPORT.export_demo(self.source, self.base / "altered")
        self.assertFalse((self.base / "altered").exists())
        model.write_bytes(original)
        self.profile["requirements"] = ["numpy==0.0.0" if p.startswith("numpy==") else p
                                        for p in self.profile["requirements"]]
        (self.source / EXPORT.PROFILE).write_bytes(EXPORT.encoded(self.profile))
        with self.assertRaisesRegex(EXPORT.ExportError, "dependency differs"):
            EXPORT.export_demo(self.source, self.base / "dependencies")
        self.assertFalse((self.base / "dependencies").exists())

    def test_existing_output_traversal_and_symlinks_refused(self):
        out = self.base / "already"
        out.mkdir()
        marker = out / "user-file"
        marker.write_text("preserve")
        with self.assertRaisesRegex(EXPORT.ExportError, "already exists"):
            EXPORT.export_demo(self.source, out)
        self.assertEqual(marker.read_text(), "preserve")
        with self.assertRaisesRegex(EXPORT.ExportError, "traversal"):
            EXPORT.export_demo(self.source, self.base / "x/../escape")
        with self.assertRaisesRegex(EXPORT.ExportError, "outside"):
            EXPORT.export_demo(self.source, self.source / "nested")
        linked = self.base / "linked-parent"
        linked.symlink_to(self.base, target_is_directory=True)
        with self.assertRaisesRegex(EXPORT.ExportError, "Symlink destination"):
            EXPORT.export_demo(self.source, linked / "new")
        card = self.source / "demo/assets/models/demo_10k_v1/model_card.json"
        backup = self.base / "external-card.json"
        card.rename(backup)
        card.symlink_to(backup)
        with self.assertRaisesRegex(EXPORT.ExportError, "Symlink source"):
            EXPORT.export_demo(self.source, self.base / "linked-source")

    def test_profile_rejects_undeclared_scope_and_duplicate_output(self):
        self.profile["copy"].append("reports/local/private.json")
        with self.assertRaisesRegex(EXPORT.ExportError, "Excluded publication path"):
            EXPORT.validate_profile(self.profile)
        self.profile["copy"].pop()
        self.profile["copy"].append("demo/app.py")
        with self.assertRaisesRegex(EXPORT.ExportError, "Duplicate/reserved"):
            EXPORT.validate_profile(self.profile)
        self.profile["copy"].pop()
        self.profile["copy"].append("../secret.json")
        with self.assertRaisesRegex(EXPORT.ExportError, "Unsafe relative path"):
            EXPORT.validate_profile(self.profile)

    def test_pure_dependency_drift_is_rejected(self):
        name = "src/mamyshev_ml/v4_evaluators.py"
        source = (self.source / name).read_text()
        source = source.replace("return hashlib.sha256(canonical(value).encode()).hexdigest()",
                                "return unknown_oracle(value)")
        with self.assertRaisesRegex(EXPORT.ExportError, "Undeclared pure dependencies: unknown_oracle"):
            EXPORT.extract_module(source, self.profile["pure_modules"][name])
        source = "import forbidden_oracle\n" + source.replace("unknown_oracle(value)", "forbidden_oracle.evaluate(value)")
        with self.assertRaisesRegex(EXPORT.ExportError, "Unapproved pure import"):
            EXPORT.extract_module(source, self.profile["pure_modules"][name])

    def test_generated_helpers_match_authoritative_semantics_including_csv(self):
        out = self.base / "semantics"
        EXPORT.export_demo(self.source, out)
        loaded = []
        def package(path, prefix):
            pkg = types.ModuleType(prefix)
            pkg.__path__ = [str(path / "src/mamyshev_ml")]
            sys.modules[prefix] = pkg
            loaded.append(prefix)
            result = []
            for name in ("v4_evaluators", "v4_scan"):
                full = prefix + "." + name
                spec = importlib.util.spec_from_file_location(full, path / "src/mamyshev_ml" / (name + ".py"))
                module = importlib.util.module_from_spec(spec)
                sys.modules[full] = module
                loaded.append(full)
                spec.loader.exec_module(module)
                result.append(module)
            return result
        try:
            original, scan = package(self.source, "_original_export_fixture")
            generated, thin = package(out, "_generated_export_fixture")
            design = dict(zip(original.FEATURES, (4., 10., 3., 4.)))
            for name in ("FEATURES", "TARGETS", "UNITS"):
                self.assertEqual(getattr(original, name), getattr(generated, name))
            for name in ("canonical", "digest", "validate_design", "design_id"):
                self.assertEqual(getattr(original, name)(design), getattr(generated, name)(design))
            self.assertEqual(scan.DEFAULT, thin.DEFAULT)
            for kwargs in ({"method": "candidates", "designs": [design, design]},
                           {"method": "grid", "axes": {"filter2_bw_nm": [2., 3.]},
                            "fixed": {k: v for k, v in design.items() if k != "filter2_bw_nm"}}):
                expected = scan.make_plan(**kwargs)
                actual = thin.make_plan(**kwargs)
                self.assertEqual(expected, actual)
                self.assertIsNone(scan.verify_plan(actual))
                self.assertIsNone(thin.verify_plan(actual))
                self.assertEqual(actual["max_new_real_attempts"], 0)
            csv = self.base / "artificial_x_only_fixture.csv"
            csv.write_text(",".join(original.FEATURES) + "\n4,10,3,4\n")
            self.assertEqual(scan.make_plan(method="csv", csv_path=csv),
                             thin.make_plan(method="csv", csv_path=csv))
            self.assertTrue(hasattr(thin, "Path"))
            self.assertFalse(hasattr(thin, "execute_scan"))
            self.assertFalse(hasattr(generated, "SyntheticEvaluator"))
        finally:
            for name in reversed(loaded):
                sys.modules.pop(name, None)


if __name__ == "__main__":
    unittest.main()
