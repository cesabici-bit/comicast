"""L1 tests for HITL review module (non-interactive paths)."""

from __future__ import annotations

import json
from pathlib import Path

from comicast.review import append_correction, summarize_for_user
from comicast.schemas import (
    Bubble,
    BubbleType,
    PageScript,
    Panel,
    ScriptFile,
)


def test_summarize_counts_by_type() -> None:
    script = ScriptFile(
        series_name="X",
        volume_id="v1",
        pages=[
            PageScript(
                page=1,
                panels=[
                    Panel(
                        order=1,
                        bubbles=[
                            Bubble(
                                text="x",
                                speaker_id="a",
                                emotion="x",
                                type=BubbleType.DIALOGUE,
                                bbox=(0, 0, 1, 1),
                                confidence=0.5,
                            ),
                            Bubble(
                                text="x",
                                speaker_id="b",
                                emotion="x",
                                type=BubbleType.DIALOGUE,
                                bbox=(0, 0, 1, 1),
                                confidence=0.95,
                            ),
                            Bubble(
                                text="x",
                                speaker_id="__sfx__",
                                emotion="x",
                                type=BubbleType.SFX,
                                bbox=(0, 0, 1, 1),
                                confidence=0.8,
                            ),
                        ],
                    )
                ],
            ),
        ],
    )
    summary = summarize_for_user(script, threshold=0.7)
    assert summary["total_bubbles"] == 3
    assert summary["below_threshold"] == 1
    assert summary["dialogue"] == 2
    assert summary["sfx"] == 1


def test_append_correction_writes_jsonl(tmp_path: Path) -> None:
    log_path = tmp_path / "corrections.jsonl"
    append_correction(
        log_path,
        page=5,
        panel=2,
        bubble_index=0,
        before={"speaker_id": "atom_eve"},
        after={"speaker_id": "mark_grayson"},
        correction_type="speaker_attribution",
        user_note="Mark is in costume here, not Eve",
    )
    line = log_path.read_text().strip()
    rec = json.loads(line)
    assert rec["page"] == 5
    assert rec["before"]["speaker_id"] == "atom_eve"
