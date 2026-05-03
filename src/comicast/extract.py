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
    elif fmt == "cbr":
        pages = _extract_cbr(source, out_dir)
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
    """Stub — implemented in T20."""
    raise NotImplementedError("T20 implements PDF extraction")


def _extract_cbr(source: Path, out_dir: Path) -> list[Path]:
    """Stub — implemented in T21."""
    raise NotImplementedError("T21 implements CBR extraction")
