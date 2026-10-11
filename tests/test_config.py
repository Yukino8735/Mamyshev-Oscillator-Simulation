"""Bootstrap checks only; these tests do not validate the physical model."""

from pathlib import Path
import sys
import tempfile
import unittest

# Run directly from the source tree without installing extra packages.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mamyshev_ml.config import load_runtime_config


class RuntimeConfigSmokeTest(unittest.TestCase):
    def test_project_config_matches_running_environment(self):
        config = load_runtime_config(ROOT / "pyproject.toml")
        self.assertEqual(Path(sys.prefix).name, config.conda_environment)
        self.assertEqual(
            f"{sys.version_info.major}.{sys.version_info.minor}", config.python_version
        )

    def test_incompatible_runtime_is_rejected(self):
        for environment, version in [("base", "3.11"), ("mamyshev-ml", "3.12")]:
            with self.subTest(environment=environment, version=version):
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "pyproject.toml"
                    path.write_text(
                        f'[tool.mamyshev_ml]\nconda_environment = "{environment}"\n'
                        f'python_version = "{version}"\n',
                        encoding="utf-8",
                    )
                    with self.assertRaises(ValueError):
                        load_runtime_config(path)


if __name__ == "__main__":
    unittest.main()
