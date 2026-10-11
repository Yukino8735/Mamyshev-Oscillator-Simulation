"""Read the bootstrap runtime contract, independent of any physics schema."""

from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class RuntimeConfig:
    conda_environment: str
    python_version: str

    def __post_init__(self) -> None:
        if self.conda_environment != "mamyshev-ml":
            raise ValueError("The project requires the mamyshev-ml Conda environment")
        if self.python_version != "3.11":
            raise ValueError("The bootstrap requires Python 3.11")


def load_runtime_config(path: Path) -> RuntimeConfig:
    """Load [tool.mamyshev_ml] from a TOML file; reject incompatible settings."""
    with path.open("rb") as stream:
        document = tomllib.load(stream)
    return RuntimeConfig(**document["tool"]["mamyshev_ml"])
