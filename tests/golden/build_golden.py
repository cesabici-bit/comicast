"""One-shot — generate the golden script for the synthetic CBZ.

Run once. Re-run only when changing prompts (and bumping prompt version) — review diff.

Pinned to: schemas.py contract as of F3-T13 (commit d8ad394).
If schemas.py adds a non-default field, re-run + carefully review the diff +
bump the prompt version in src/comicast/vision/prompts.py if the change is
semantic. The byte-stability of `model_dump_json(indent=2)` for plain types
is locked by `tests/golden/test_vision_golden.py::test_synth_script_round_trip_is_byte_stable`.
"""

from __future__ import annotations

from pathlib import Path

from comicast.schemas import (
    Bubble,
    BubbleType,
    PageScript,
    Panel,
    ScriptFile,
)


def main() -> None:
    here = Path(__file__).parent
    out = here / "fixtures" / "synth_script_golden.json"
    out.parent.mkdir(parents=True, exist_ok=True)

    pages = []
    for i in (1, 2, 3):
        bubble = Bubble(
            text=f"Page {i} synthetic dialogue.",
            speaker_id="synth_char_a",
            # NOTE: "neutral" is the schema default but NOT in PER_PAGE_SYSTEM
            # prompt vocabulary (see VIS-06 in KNOWN_ISSUES.md). Kept here
            # intentionally so this golden exercises the schema-permissive
            # surface; will need regeneration if VIS-06 is resolved by
            # tightening to Literal[...].
            emotion="neutral",
            type=BubbleType.DIALOGUE,
            bbox=(50, 50, 250, 100),
            confidence=0.95,
        )
        pages.append(PageScript(page=i, panels=[Panel(order=1, bubbles=[bubble])]))

    script = ScriptFile(series_name="synth_test", volume_id="synth_v1", pages=pages)
    out.write_text(script.model_dump_json(indent=2))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
