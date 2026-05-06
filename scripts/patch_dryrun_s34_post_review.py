"""S34 post-review batch patch.

Applies, in one atomic-ish pass:
- 4 retroactive speaker_id fixes to script.json (with conf=1.0)
- shapesmith cast entry added to series_profiles/invincible.json
- __narrator__ -> Daniel voice mapping added to voice_archetype_library
- 4 retroactive correction entries appended to corrections.jsonl
- backup of script.json + profile.json before mutation
- verification: every non-reserved speaker_id in script.json maps to a voice_id

Idempotent: re-runs detect already-applied changes and skip.
"""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "data" / "work" / "dryrun_ch1" / "vol_2_ch1" / "script.json"
PROFILE_PATH = ROOT / "data" / "series_profiles" / "invincible.json"
CORRECTIONS_PATH = ROOT / "data" / "work" / "dryrun_ch1" / "vol_2_ch1" / "corrections.jsonl"

NARRATOR_VOICE_ID = "onwK4e9ZLuTAKqWW03F9"  # Daniel — broadcaster British formal
SHAPESMITH_VOICE_ID = "iP95p4xoKVk53GoZ742B"  # Chris — charming down-to-earth

RETRO_FIXES = [
    {
        "page": 11,
        "panel": 2,
        "bubble_index": 3,
        "old": "robot",
        "new": "atom_eve",
        "note": "S34 retro fix: bubble 1/7 misattribution (robot speaks to himself in 3rd person); user pressed Enter=keep by mistake",
    },
    {
        "page": 12,
        "panel": 1,
        "bubble_index": 0,
        "old": "darkwing",
        "new": "black_samson",
        "note": "S34 retro fix: bubble 2/7 visible bald Black hero (Black Samson), not Darkwing; user clicked k by mistake",
    },
    {
        "page": 12,
        "panel": 5,
        "bubble_index": 0,
        "old": "unknown_villain",
        "new": "monster_ally",
        "note": "S34 retro fix: bubble 6/7 Monster Girl monster form; user typed 'monster_girl' which fell into else: continue branch",
    },
    {
        "page": 19,
        "panel": 3,
        "bubble_index": 4,
        "old": "unknown_male_combatant",
        "new": "shapesmith",
        "note": "S34 retro fix: bubble 7/7 Shapesmith (Martian Guardian, missing from extracted cast); user pressed Enter at New speaker_id prompt accepting default",
    },
]


def read_text_tolerant(p: Path) -> tuple[str, str]:
    raw = p.read_bytes()
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"{p}: undecodable")


def main() -> int:
    print("=== S34 post-review batch patch ===")

    # 1. Backup
    for path in (SCRIPT_PATH, PROFILE_PATH):
        bak = path.with_suffix(path.suffix + ".pre_batch_patch.bak")
        if not bak.exists():
            shutil.copy2(path, bak)
            print(f"  backup: {path.name} -> {bak.name}")
        else:
            print(f"  backup exists (skip): {bak.name}")

    # 2. Load
    script_text, script_enc = read_text_tolerant(SCRIPT_PATH)
    script = json.loads(script_text)
    print(f"  script.json loaded (encoding={script_enc}, n_pages={len(script['pages'])})")

    profile_text, profile_enc = read_text_tolerant(PROFILE_PATH)
    profile = json.loads(profile_text)
    print(
        f"  profile loaded (encoding={profile_enc}, n_cast={len(profile['cast'])}, version={profile['version']})"
    )

    # 3. Apply 4 retroactive fixes to script
    correction_records: list[dict] = []
    for fix in RETRO_FIXES:
        page = next(p for p in script["pages"] if p["page"] == fix["page"])
        panel = next(pn for pn in page["panels"] if pn["order"] == fix["panel"])
        bubble = panel["bubbles"][fix["bubble_index"]]
        if bubble["speaker_id"] == fix["new"]:
            print(
                f"  retro fix p{fix['page']}/p{fix['panel']}/b{fix['bubble_index']}: ALREADY APPLIED ({fix['new']})"
            )
            continue
        if bubble["speaker_id"] != fix["old"]:
            raise RuntimeError(
                f"unexpected state at p{fix['page']}/p{fix['panel']}/b{fix['bubble_index']}: "
                f"expected speaker_id={fix['old']!r}, got {bubble['speaker_id']!r}"
            )
        before = dict(bubble)
        bubble["speaker_id"] = fix["new"]
        bubble["confidence"] = 1.0
        after = dict(bubble)
        correction_records.append(
            {
                "ts": time.time(),
                "page": fix["page"],
                "panel": fix["panel"],
                "bubble_index": fix["bubble_index"],
                "correction_type": "speaker_attribution",
                "before": before,
                "after": after,
                "user_note": fix["note"],
            }
        )
        print(
            f"  retro fix p{fix['page']}/p{fix['panel']}/b{fix['bubble_index']}: {fix['old']} -> {fix['new']} (conf=1.0)"
        )

    # 4. Add shapesmith to profile cast
    if not any(c["id"] == "shapesmith" for c in profile["cast"]):
        profile["cast"].append(
            {
                "id": "shapesmith",
                "canonical_name": "Shapesmith",
                "aliases": ["Martian", "Robert"],
                "description": "Martian shapeshifter, member of the Guardians of the Globe; humanoid green alien who can transform shape; goofy-friendly demeanor.",
                "confidence": 1.0,
                "voice_id": SHAPESMITH_VOICE_ID,
                "voice_archetype": None,
                "user_confirmations": 0,
                "user_corrections": 0,
            }
        )
        print(f"  cast: added shapesmith (voice_id={SHAPESMITH_VOICE_ID} Chris)")
    else:
        print("  cast: shapesmith already present (skip)")

    # 5. Add __narrator__ to voice_archetype_library
    arch = profile.setdefault("voice_archetype_library", {})
    if "__narrator__" not in arch:
        arch["__narrator__"] = NARRATOR_VOICE_ID
        print(f"  voice_archetype_library: __narrator__ -> {NARRATOR_VOICE_ID} (Daniel)")
    else:
        print("  voice_archetype_library: __narrator__ already mapped (skip)")

    # 6. Verify integrity: every non-reserved speaker_id has a voice_id
    voice_by_id: dict[str, str] = {c["id"]: c.get("voice_id") for c in profile["cast"]}
    voice_by_id["__narrator__"] = arch.get("__narrator__")
    voice_by_id["__sfx__"] = arch.get("__sfx__")  # may be None — SFX skipped per spec
    missing: set[str] = set()
    for p in script["pages"]:
        for pn in p["panels"]:
            for b in pn["bubbles"]:
                spk = b["speaker_id"]
                if spk == "__sfx__":
                    continue  # SFX intentionally skipped
                if not voice_by_id.get(spk):
                    missing.add(spk)
    if missing:
        raise RuntimeError(
            f"speaker_ids in script.json with no voice_id mapping: {sorted(missing)}"
        )
    print("  integrity: OK (every non-SFX speaker_id has a voice_id)")

    # 7. Write
    SCRIPT_PATH.write_text(json.dumps(script, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  script.json: written (encoding=utf-8 — was {script_enc})")
    PROFILE_PATH.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")
    print("  invincible.json: written (encoding=utf-8)")

    # 8. Append correction records
    if correction_records:
        with CORRECTIONS_PATH.open("a", encoding="utf-8") as f:
            for rec in correction_records:
                f.write(json.dumps(rec) + "\n")
        print(f"  corrections.jsonl: appended {len(correction_records)} retro records")
    else:
        print("  corrections.jsonl: nothing to append (all retro fixes already applied)")

    # 9. Delete script_with_voices.json so stage 3 regenerates with fixes
    swv = SCRIPT_PATH.parent / "script_with_voices.json"
    if swv.exists():
        swv.unlink()
        print("  script_with_voices.json: deleted (will regenerate)")

    print("=== DONE ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
