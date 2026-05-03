"""L1 unit tests for PDF extraction."""

from __future__ import annotations

from pathlib import Path

import pytest

from comicast.extract import extract_pages

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"
PDF = FIXTURE_DIR / "synth_3pages.pdf"


@pytest.mark.skipif(not PDF.exists(), reason="run build_synthetic_pdf.py first")
def test_extract_pdf_produces_3_pngs(tmp_path: Path) -> None:
    pages = extract_pages(PDF, tmp_path, target_dpi=150)
    assert len(pages) == 3
    for p in pages:
        # ~33 KB observed for a 1024x1536 solid-color PNG at 150 DPI;
        # 5000 B catches truncation while staying safe across Pillow majors.
        assert p.exists() and p.stat().st_size > 5000


@pytest.mark.skipif(not PDF.exists(), reason="run build_synthetic_pdf.py first")
def test_extract_pdf_dpi_changes_size(tmp_path: Path) -> None:
    low = extract_pages(PDF, tmp_path / "low", target_dpi=100)
    high = extract_pages(PDF, tmp_path / "high", target_dpi=300)
    assert low[0].stat().st_size < high[0].stat().st_size
