from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as distribution_version
from pathlib import Path
import re


APP_DISTRIBUTION_NAME = "mesc-scientific-platform"
DEFAULT_VERSION = "0.0.0"


def get_current_version() -> str:
    try:
        return distribution_version(APP_DISTRIBUTION_NAME)
    except PackageNotFoundError:
        return _read_version_from_pyproject()


def is_newer_version(candidate: str, current: str) -> bool:
    return _normalize(candidate) > _normalize(current)


def _normalize(raw: str) -> tuple[int, ...]:
    parts = re.split(r"[^0-9]+", raw.strip())
    numbers = [int(part) for part in parts if part]
    return tuple(numbers or [0])


def _read_version_from_pyproject() -> str:
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    if not pyproject.exists():
        return DEFAULT_VERSION

    for line in pyproject.read_text(encoding="utf-8").splitlines():
        if line.startswith("version = "):
            return line.split("=", 1)[1].strip().strip('"')
    return DEFAULT_VERSION
