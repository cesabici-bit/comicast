"""SMOKE: extract a synthetic CBZ end-to-end. M3-mandated 'human readable' test."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURE_CBZ = Path(__file__).parent.parent / "fixtures" / "synth_3pages.cbz"


@pytest.mark.golden
def test_extract_synthetic_cbz_produces_3_pngs(tmp_path: Path) -> None:
    """SMOKE — given a 3-page CBZ, the extractor produces 3 ordered PNGs."""
    extract = pytest.importorskip("comicast.extract", reason="implementation arrives in T19")

    out_dir = tmp_path / "pages"
    pages = extract.extract_pages(FIXTURE_CBZ, out_dir)

    assert len(pages) == 3
    assert pages[0].name == "page_001.png"
    assert pages[1].name == "page_002.png"
    assert pages[2].name == "page_003.png"

    for p in pages:
        assert p.exists()
        # ~8 KB observed for a 1024x1536 solid-color PNG; 5000 B catches truncation.
        assert p.stat().st_size > 5000
