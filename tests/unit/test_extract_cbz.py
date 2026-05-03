"""L1 unit tests for CBZ extraction."""

from __future__ import annotations

from pathlib import Path

import pytest

from comicast.extract import detect_format, extract_pages

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"


def test_detect_format_cbz() -> None:
    assert detect_format(FIXTURE_DIR / "synth_3pages.cbz") == "cbz"


def test_detect_format_unknown_raises() -> None:
    with pytest.raises(ValueError):
        detect_format(Path("foo.xyz"))


def test_extract_orders_pages_by_filename(tmp_path: Path) -> None:
    pages = extract_pages(FIXTURE_DIR / "synth_3pages.cbz", tmp_path)
    names = [p.name for p in pages]
    assert names == ["page_001.png", "page_002.png", "page_003.png"]


def test_extract_idempotent_skips_if_exists(tmp_path: Path) -> None:
    """Running extract twice does not re-extract (idempotency)."""
    pages_1 = extract_pages(FIXTURE_DIR / "synth_3pages.cbz", tmp_path)
    mtimes_1 = [p.stat().st_mtime_ns for p in pages_1]
    pages_2 = extract_pages(FIXTURE_DIR / "synth_3pages.cbz", tmp_path)
    mtimes_2 = [p.stat().st_mtime_ns for p in pages_2]
    assert mtimes_1 == mtimes_2


def test_extract_force_re_extracts(tmp_path: Path) -> None:
    pages_1 = extract_pages(FIXTURE_DIR / "synth_3pages.cbz", tmp_path)
    mtimes_1 = [p.stat().st_mtime_ns for p in pages_1]
    pages_2 = extract_pages(FIXTURE_DIR / "synth_3pages.cbz", tmp_path, force=True)
    mtimes_2 = [p.stat().st_mtime_ns for p in pages_2]
    assert mtimes_1 != mtimes_2
