"""Smoke test: package imports and version is correct."""

from __future__ import annotations

import comicast


def test_package_imports() -> None:
    """The package must be importable."""
    assert comicast is not None


def test_package_has_version() -> None:
    """The package must declare its version (from pyproject.toml via importlib)."""
    from importlib.metadata import version

    v = version("comicast")
    assert v == "0.1.0"
