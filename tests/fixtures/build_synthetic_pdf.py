"""Build a 3-page synthetic PDF for testing.

The output is bit-deterministic across rebuilds: ``creationDate`` and
``modDate`` are pinned to 2026-01-01 00:00:00 UTC, overriding Pillow's
default ``time.gmtime()`` metadata embedding (analogous to the pinned
``ZipInfo.date_time`` in ``build_synthetic_cbz.py`` per KNOWN_ISSUES
EXT-01). Pillow major version stability is required: built/verified with
Pillow 12.x; if rebuilt under a different Pillow major, expect drift in
the inner page-image bytes and rebuild on the same OS to recommit.
"""

from __future__ import annotations

import time
from pathlib import Path

from PIL import Image, ImageDraw

PINNED_TIME = time.struct_time((2026, 1, 1, 0, 0, 0, 0, 1, 0))


def build(out_path: Path) -> None:
    pages = []
    for i, color in enumerate(["red", "green", "blue"], start=1):
        img = Image.new("RGB", (1024, 1536), color=color)
        ImageDraw.Draw(img).text((50, 50), f"Page {i}", fill="white")
        pages.append(img)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pages[0].save(
        out_path,
        save_all=True,
        append_images=pages[1:],
        format="PDF",
        creationDate=PINNED_TIME,
        modDate=PINNED_TIME,
    )


if __name__ == "__main__":
    here = Path(__file__).parent
    build(here / "synth_3pages.pdf")
    print(f"Built {here / 'synth_3pages.pdf'}")
