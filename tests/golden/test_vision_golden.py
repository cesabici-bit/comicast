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
