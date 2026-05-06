"""S34 dry-run artifact patcher.

Three issues from S34 stage 2c crash:
1. profile.json has 2 broken voice_id (free-text instead of ElevenLabs ids):
   - mark_grayson: "teen male" -> bIHbv24MWmeRgasZH58o (Will)
   - robot: "River" -> SAz9YHcvj6GT2YYXdXww (River voice_id)
2. monster_ally voice_id needs override (Jessica -> Harry for monster form
   per user feedback "voce mostruosa diversa quando trasformata").
3. script.json has 24 pages instead of 25 (page 14 dropped due to a
   Pydantic ValidationError where Anthropic returned an SFX bubble with
   speaker_id='cecil_stedman' instead of '__sfx__'). The cardinality
   check at cli.py:168 then raises. Insert an empty PageScript stub so
   the relaunch can proceed.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "data" / "series_profiles" / "invincible.json"
SCRIPT = ROOT / "data" / "work" / "dryrun_ch1" / "vol_2_ch1" / "script.json"

VOICE_FIXES: dict[str, str] = {
    "mark_grayson": "bIHbv24MWmeRgasZH58o",  # Will
    "robot": "SAz9YHcvj6GT2YYXdXww",  # River
    "monster_ally": "SOYHLrjzK2X1ezoPC6cr",  # Harry (override Jessica)
}


def backup(p: Path) -> Path:
    bak = p.with_suffix(p.suffix + ".pre_patch.bak")
    if not bak.exists():
        shutil.copy2(p, bak)
    return bak


def patch_profile() -> None:
    print(f"== Patching {PROFILE.name} ==")
    bak = backup(PROFILE)
    print(f"  backup: {bak.name}")
    data = json.loads(PROFILE.read_text(encoding="utf-8"))
    fixed = []
    for entry in data.get("cast", []):
        cid = entry.get("id")
        if cid in VOICE_FIXES:
            old = entry.get("voice_id")
            new = VOICE_FIXES[cid]
            if old != new:
                entry["voice_id"] = new
                fixed.append((cid, old, new))
    if fixed:
        PROFILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        for cid, old, new in fixed:
            print(f"  {cid}: {old!r} -> {new}")
    else:
        print("  (no fixes applied — already correct)")


def _read_json_tolerant(p: Path) -> dict:
    raw = p.read_bytes()
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return json.loads(raw.decode(enc))
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"Could not decode {p} with utf-8/cp1252/latin-1")


def patch_script() -> None:
    print(f"\n== Patching {SCRIPT.name} ==")
    bak = backup(SCRIPT)
    print(f"  backup: {bak.name}")
    data = _read_json_tolerant(SCRIPT)
    pages = data.get("pages", [])
    page_numbers = sorted(p["page"] for p in pages)
    print(f"  current pages: {len(pages)} -> {page_numbers}")
    expected = list(range(1, 26))  # 1..25 inclusive
    missing = [n for n in expected if n not in page_numbers]
    if not missing:
        print("  (no missing pages)")
        return
    for n in missing:
        stub = {"page": n, "panels": []}
        pages.append(stub)
        print(f"  inserted stub page {n} (empty panels)")
    pages.sort(key=lambda p: p["page"])
    data["pages"] = pages
    SCRIPT.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"  new total pages: {len(pages)}")


if __name__ == "__main__":
    patch_profile()
    patch_script()
    print(
        "\nDone. Re-launch with: powershell -ExecutionPolicy Bypass -File .\\scripts\\run_dryrun.ps1"
    )
