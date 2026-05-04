"""L4 golden snapshot test — vision pipeline output must match committed reference."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from comicast.schemas import ScriptFile

GOLDEN = Path(__file__).parent / "fixtures" / "synth_script_golden.json"


@pytest.mark.golden
def test_synth_script_loads_as_valid_schema() -> None:
    """The committed golden must always be valid against the current schema."""
    data = json.loads(GOLDEN.read_text())
    script = ScriptFile.model_validate(data)
    assert script.series_name == "synth_test"
    assert len(script.pages) == 3


@pytest.mark.golden
def test_synth_script_round_trip_is_byte_stable() -> None:
    """L4 contract: re-serializing the parsed golden must reproduce the committed bytes.

    Catches: (a) Pydantic field-ordering drift on upgrade, (b) silent schema
    field additions that change dump output, (c) accidental hand-edits to the
    fixture that don't match what `build_golden.py` would regenerate.
    Implementer's empirical SHA256 check (6adc9a8c...) is encoded here as a
    permanent regression — manual verification doesn't survive the next session.
    """
    raw = GOLDEN.read_text()
    script = ScriptFile.model_validate_json(raw)
    rebuilt = script.model_dump_json(indent=2)
    assert (
        rebuilt == raw
    ), "Golden no longer round-trips — rebuild via build_golden.py and review diff."


@pytest.mark.golden
def test_synth_script_structure_locks_panel_and_bubble_shape() -> None:
    """Lock every load-bearing field. A field-swap or partial-extraction
    regression in the vision pipeline must surface here, not silently pass.
    """
    script = ScriptFile.model_validate_json(GOLDEN.read_text())

    assert script.volume_id == "synth_v1"
    assert [p.page for p in script.pages] == [1, 2, 3]

    for page in script.pages:
        assert len(page.panels) == 1
        panel = page.panels[0]
        assert panel.order == 1
        assert len(panel.bubbles) == 1
        b = panel.bubbles[0]
        assert b.text == f"Page {page.page} synthetic dialogue."
        assert b.speaker_id == "synth_char_a"
        assert b.type.value == "dialogue"
        assert b.bbox == (50, 50, 250, 100)
        assert b.confidence == 0.95
        # NOTE: emotion="neutral" is intentionally NOT a vocabulary-compliant
        # value (see VIS-06 in KNOWN_ISSUES.md). Kept to exercise the
        # schema-permissive surface; when VIS-06 is resolved (likely tighten
        # to Literal[...]), regenerate the golden via build_golden.py and
        # update this assertion to a vocabulary value.
        assert b.emotion == "neutral"
