"""Build a synthetic CBZ with 3 colored pages for testing extraction.

This is a build script — run once to produce `tests/fixtures/synth_3pages.cbz`.
The CBZ is committed to the repo (legal — synthetic, no copyright).
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw


def build(out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, color in enumerate(["red", "green", "blue"], start=1):
            img = Image.new("RGB", (1024, 1536), color=color)
            d = ImageDraw.Draw(img)
            d.text((50, 50), f"Page {i}", fill="white")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            zf.writestr(f"page_{i:03d}.png", buf.getvalue())


if __name__ == "__main__":
    here = Path(__file__).parent
    build(here / "synth_3pages.cbz")
    print(f"Built {here / 'synth_3pages.cbz'}")
