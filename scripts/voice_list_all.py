"""List all voices available to the account (premade + cloned + community
shared if accessible). Used during dry-run HITL when search returns 0
candidates and we need to browse the library manually.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

from elevenlabs import ElevenLabs  # noqa: E402  (must follow load_dotenv)


def main() -> int:
    key = os.environ.get("ELEVENLABS_API_KEY", "")
    if not key:
        print("FAIL: ELEVENLABS_API_KEY not set")
        return 1
    client = ElevenLabs(api_key=key)

    print("=== voices.search (no query, full library page 1) ===")
    try:
        results = client.voices.search(page_size=100)
        voices = getattr(results, "voices", []) or []
        print(f"Got {len(voices)} voices")
        for v in voices:
            vid = getattr(v, "voice_id", "?")
            name = getattr(v, "name", "?")
            cat = getattr(v, "category", "?")
            labels = getattr(v, "labels", None) or {}
            desc = getattr(v, "description", "") or ""
            tag_str = " | ".join(f"{k}={vv}" for k, vv in labels.items()) if labels else ""
            print(f"  [{vid}] {name}  cat={cat}")
            if tag_str:
                print(f"      labels: {tag_str}")
            if desc:
                print(f"      desc: {desc[:150]}")
    except Exception as e:
        print(f"  ERROR: {type(e).__name__}: {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
