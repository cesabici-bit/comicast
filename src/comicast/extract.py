"""Stage 1 — Page extraction from CBZ/CBR/PDF.

Output: ordered PNGs in <out_dir>/page_NNN.png.
Idempotent: skips work if outputs exist (use force=True to override).
"""

from __future__ import annotations

import time
import zipfile
from pathlib import Path
from typing import Literal

from PIL import Image

from comicast.logging_setup import get_logger

log = get_logger("comicast.extract")

Format = Literal["cbz", "cbr", "pdf"]
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def detect_format(path: Path) -> Format:
    suffix = path.suffix.lower()
    if suffix == ".cbz":
        return "cbz"
    if suffix == ".cbr":
        return "cbr"
    if suffix == ".pdf":
        return "pdf"
    raise ValueError(f"Unknown format: {suffix}")


def extract_pages(
    source: Path,
    out_dir: Path,
    *,
    target_dpi: int = 200,
    force: bool = False,
) -> list[Path]:
    """Extract pages as PNGs ordered numerically.

    Returns list of created PNG paths in reading order.
    """
    fmt = detect_format(source)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Fail-fast: unsupported formats must raise BEFORE the idempotency-skip
    # check, otherwise stale page_*.png from a prior run would silently mask
    # the NotImplementedError. When CBR is implemented (KNOWN_ISSUES EXT-10),
    # reconcile this branch with the idempotency check below.
    if fmt == "cbr":
        return _extract_cbr(source, out_dir)

    # D-EXT-1 (CLI-01): force pre-clean removes stale page_*.png before re-extract.
    # Uses glob+unlink (NOT shutil.rmtree) to preserve unrelated files in out_dir.
    # Placed AFTER the cbr fail-fast branch so CBR never reaches this code.
    if force:
        stale = list(out_dir.glob("page_*.png"))
        for stale_path in stale:
            stale_path.unlink()
        if stale:
            log.info("extract.force_clean", n_removed=len(stale), out_dir=str(out_dir))

    existing = sorted(out_dir.glob("page_*.png"))
    if existing and not force:
        log.info(
            "extract.skip", reason="outputs exist", n_pages=len(existing), out_dir=str(out_dir)
        )
        return existing

    if fmt == "cbz":
        pages = _extract_cbz(source, out_dir)
    elif fmt == "pdf":
        pages = _extract_pdf(source, out_dir, target_dpi)
    else:
        raise ValueError(f"Unsupported format: {fmt}")

    log.info("extract.done", n_pages=len(pages), source=str(source), out_dir=str(out_dir))
    return pages


def _extract_cbz(source: Path, out_dir: Path) -> list[Path]:
    t0 = time.perf_counter()
    out_paths: list[Path] = []
    with zipfile.ZipFile(source) as zf:
        names = sorted(n for n in zf.namelist() if Path(n).suffix.lower() in IMAGE_EXTS)
        for idx, name in enumerate(names, start=1):
            with zf.open(name) as f:
                img = Image.open(f)
                img.load()
            out = out_dir / f"page_{idx:03d}.png"
            img.convert("RGB").save(out, "PNG")
            out_paths.append(out)
    log.debug("extract.cbz.done", n=len(out_paths), elapsed_s=time.perf_counter() - t0)
    return out_paths


def _extract_pdf(source: Path, out_dir: Path, dpi: int) -> list[Path]:
    """Convert PDF pages to PNG using pdf2image (requires poppler).

    Poppler is discovered via the POPPLER_PATH environment variable when set
    (programmatic injection, NOT PATH mutation, per CLAUDE.md gotcha and
    docs/research/F1-extraction.md §1.1). When unset, pdf2image falls back
    to PATH lookup; if poppler is also missing from PATH, the call raises
    pdf2image.exceptions.PDFInfoNotInstalledError (typed, fail-fast).

    See docs/research/F1-extraction.md for system dep notes.
    """
    import os

    from pdf2image import convert_from_path  # imported lazily to avoid poppler at import time

    t0 = time.perf_counter()
    poppler_path: str | None = os.environ.get("POPPLER_PATH") or None
    if poppler_path is not None:
        images = convert_from_path(str(source), dpi=dpi, poppler_path=poppler_path)
    else:
        images = convert_from_path(str(source), dpi=dpi)
    out_paths: list[Path] = []
    for idx, img in enumerate(images, start=1):
        out = out_dir / f"page_{idx:03d}.png"
        img.convert("RGB").save(out, "PNG")
        out_paths.append(out)
    log.debug("extract.pdf.done", n=len(out_paths), elapsed_s=time.perf_counter() - t0)
    return out_paths


def _extract_cbr(source: Path, out_dir: Path) -> list[Path]:
    """CBR extraction is deferred in v1.

    Per plan T21 Step 1 fallback (and F1-extraction.md decision): CBR is rare for
    digital comics (CBZ dominates) and would require an `unrar` or `bsdtar` runtime
    binary. Users with .cbr files should convert to .cbz with 7-Zip before running
    Comicast.
    """
    raise NotImplementedError("CBR not supported in v1. Convert to CBZ via 7-Zip first.")
