"""One-shot resize of pages that exceed Anthropic's 5 MB image limit.

Used during S34 dry-run on Invincible Vol 2 Compendium ch1: page_019 is a
double-page spread (~21 MB PNG, 93M pixels) that crashes vision/cast.py.

Long-term fix is EXT-12: add a pre-encode size guard in extract.py or
vision/cast.py. This script is the surgical workaround for today's run.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

# Bypass DecompressionBombWarning for Pillow on legitimately large source pages
Image.MAX_IMAGE_PIXELS = None

ROOT = Path(__file__).resolve().parents[1]
PAGES_DIR = ROOT / "data" / "work" / "dryrun_ch1" / "vol_2_ch1" / "pages"

# Anthropic limit is 5 MB *base64* = ~3.75 MB raw (base64 expansion is 4/3).
# Target 3.0 MB raw to leave headroom; iterate with progressively smaller
# long-side caps until the file fits.
SIZE_LIMIT_BYTES = 3_000_000
LONG_SIDE_LADDER = [2400, 1800, 1400, 1100]  # try in order


def resize_if_oversize(p: Path) -> tuple[bool, str]:
    backup = p.with_suffix(p.suffix + ".original")

    # If a backup exists, always start from it (idempotent re-runs).
    source_bytes = backup.read_bytes() if backup.exists() else p.read_bytes()
    sz = len(source_bytes)
    if sz <= SIZE_LIMIT_BYTES:
        return False, f"{p.name}: {sz/1024/1024:.1f} MB OK (skipped)"

    # Persist original on first oversize encounter
    if not backup.exists():
        backup.write_bytes(source_bytes)

    last_msg = ""
    for max_side in LONG_SIDE_LADDER:
        with Image.open(backup if backup.exists() else p) as img:
            w, h = img.size
            long_side = max(w, h)
            scale = max_side / long_side if long_side > max_side else 1.0
            new_w = int(w * scale)
            new_h = int(h * scale)
            resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            resized.convert("RGB").save(p, format="PNG", optimize=True)

        new_sz = p.stat().st_size
        last_msg = (
            f"{p.name}: orig {sz/1024/1024:.1f} MB ({w}x{h}) -> "
            f"{new_sz/1024/1024:.1f} MB ({new_w}x{new_h}) "
            f"[max_side={max_side} backup={backup.name}]"
        )
        if new_sz <= SIZE_LIMIT_BYTES:
            return True, last_msg

    # Even the smallest rung overshot — return last attempt anyway, caller decides
    return True, f"WARN still oversize: {last_msg}"


def main() -> int:
    if not PAGES_DIR.exists():
        print(f"NOT FOUND: {PAGES_DIR}")
        return 1

    pages = sorted(PAGES_DIR.glob("page_*.png"))
    print(f"Scanning {len(pages)} pages in {PAGES_DIR}")
    print(f"Limit: {SIZE_LIMIT_BYTES/1024/1024:.1f} MB; long-side ladder: {LONG_SIDE_LADDER}")
    print()

    n_resized = 0
    for p in pages:
        changed, msg = resize_if_oversize(p)
        if changed:
            n_resized += 1
            print(f"  RESIZED  {msg}")
        else:
            # only print oversize-skipped (unlikely) or single-line summary at end
            pass

    print()
    print(f"Done: {n_resized}/{len(pages)} resized.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
