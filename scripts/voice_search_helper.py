"""Browse ElevenLabs voice library with multiple queries to help pick a voice
for hard-to-search characters during the dry-run interactive HITL.

Usage: python scripts/voice_search_helper.py "query 1" "query 2" ...
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

from elevenlabs import ElevenLabs  # noqa: E402  (must follow load_dotenv)


def main(queries: list[str]) -> int:
    key = os.environ.get("ELEVENLABS_API_KEY", "")
    if not key:
        print("FAIL: ELEVENLABS_API_KEY not set")
        return 1
    client = ElevenLabs(api_key=key)

    seen: set[str] = set()
    print()
    for q in queries:
        print(f"=== query: {q!r} ===")
        try:
            results = client.voices.search(search=q, page_size=5)
            voices = getattr(results, "voices", []) or []
        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {e}")
            continue
        if not voices:
            print("  (no candidates)")
            continue
        for v in voices:
            vid = getattr(v, "voice_id", "?")
            name = getattr(v, "name", "?")
            labels = getattr(v, "labels", None) or {}
            desc = getattr(v, "description", "") or ""
            cat = getattr(v, "category", "?")
            tag_str = " | ".join(f"{k}={v}" for k, v in labels.items()) if labels else ""
            marker = "  " if vid not in seen else "* "
            seen.add(vid)
            print(f"{marker}[{vid}] {name}  cat={cat}")
            if tag_str:
                print(f"      labels: {tag_str}")
            if desc:
                print(f"      desc: {desc[:200]}")
        print()
    print(f"Total unique voices shown: {len(seen)}")
    print("* = already shown above (duplicate across queries)")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python scripts/voice_search_helper.py "query 1" "query 2" ...')
        sys.exit(2)
    sys.exit(main(sys.argv[1:]))
