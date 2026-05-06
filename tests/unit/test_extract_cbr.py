"""L1 unit tests for CBR extraction (v1: not supported, dispatcher raises with
conversion guidance).

CBR support is deferred in v1: CBZ dominates digital comics and adding CBR would
require an `unrar` or `bsdtar` runtime binary on the host. Users with .cbr files
should convert to .cbz with 7-Zip first.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from comicast.extract import detect_format, extract_pages


def test_detect_format_cbr() -> None:
    assert detect_format(Path("foo.cbr")) == "cbr"


def test_extract_cbr_raises_not_implemented(tmp_path: Path) -> None:
    """v1 fallback: dispatcher raises NotImplementedError with conversion guidance."""
    # SOURCE: design contract — verbatim error message lock
    source = tmp_path / "fake.cbr"
    source.write_bytes(b"")  # body irrelevant; raise occurs before any parsing
    out_dir = tmp_path / "out"
    with pytest.raises(NotImplementedError, match="CBR not supported in v1"):
        extract_pages(source, out_dir)


def test_extract_cbr_raises_even_when_stale_pages_exist(tmp_path: Path) -> None:
    """Idempotency-skip must NOT mask the unsupported-format error.

    Regression guard: dispatcher's existing-glob check (extract.py:54-60) runs
    after the cbr fail-fast branch, so stale page_*.png from a previous run
    cannot silently swallow the NotImplementedError. CBR must always raise.
    """
    source = tmp_path / "fake.cbr"
    source.write_bytes(b"")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "page_001.png").write_bytes(b"stale")
    with pytest.raises(NotImplementedError, match="CBR not supported in v1"):
        extract_pages(source, out_dir)
