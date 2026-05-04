"""HITL CLI — review low-confidence bubbles + persist corrections.

Two functions exposed:
- run_review(): the interactive Typer CLI loop (called from cli.py)
- summarize_for_user(): non-interactive summary used in tests + dry-run
- append_correction(): persists a single correction to corrections.jsonl
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from comicast.logging_setup import get_logger
from comicast.schemas import BubbleType, ScriptFile
from comicast.vision.confidence import bubbles_needing_review

log = get_logger("comicast.review")
console = Console()


def summarize_for_user(script: ScriptFile, *, threshold: float = 0.7) -> dict[str, int]:
    counts = {
        "total_bubbles": 0,
        "below_threshold": 0,
        "dialogue": 0,
        "thought": 0,
        "narration": 0,
        "sfx": 0,
    }
    for ps in script.pages:
        for panel in ps.panels:
            for b in panel.bubbles:
                counts["total_bubbles"] += 1
                if b.confidence < threshold:
                    counts["below_threshold"] += 1
                counts[b.type.value] += 1
    return counts


def append_correction(
    path: Path,
    *,
    page: int,
    panel: int,
    bubble_index: int,
    before: dict[str, Any],
    after: dict[str, Any],
    correction_type: str,
    user_note: str = "",
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rec = {
        "ts": time.time(),
        "page": page,
        "panel": panel,
        "bubble_index": bubble_index,
        "correction_type": correction_type,
        "before": before,
        "after": after,
        "user_note": user_note,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
    log.info(
        "review.correction.appended",
        page=page,
        panel=panel,
        bubble_index=bubble_index,
        correction_type=correction_type,
    )


def run_review(
    script: ScriptFile,
    *,
    threshold: float = 0.7,
    corrections_log: Path,
) -> ScriptFile:
    """Interactive review loop. Returns the corrected ScriptFile.

    Behavior:
    - Print summary (counts).
    - Iterate through bubbles needing review.
    - For each: show context (page, panel, bubble text, current attribution),
      prompt for action: [k]eep / [c]hange speaker / [e]dit text / [t]ype change / [s]kip.
    - Persist each correction to corrections_log.
    """
    summary = summarize_for_user(script, threshold=threshold)
    table = Table(title="Pre-review summary")
    for k, v in summary.items():
        table.add_row(k, str(v))
    console.print(table)

    flagged = list(bubbles_needing_review(script, threshold=threshold))
    log.info("review.run.start", n_flagged=len(flagged), threshold=threshold)
    if not flagged:
        console.print("[green]No bubbles below confidence threshold. Skipping review.[/green]")
        return script

    console.print(f"\n[yellow]{len(flagged)} bubbles need review.[/yellow]\n")

    for fb in flagged:
        page = next(p for p in script.pages if p.page == fb.page)
        panel = next(pn for pn in page.panels if pn.order == fb.panel_order)
        # Find the bubble inside the panel and its index for safe replacement
        idx = next(i for i, b in enumerate(panel.bubbles) if b is fb.bubble)

        console.rule(f"Page {fb.page} · Panel {fb.panel_order} · Bubble {idx + 1}")
        console.print(f"[bold]Text:[/bold] {fb.bubble.text}")
        console.print(
            f"[bold]Speaker:[/bold] {fb.bubble.speaker_id} ([dim]conf {fb.bubble.confidence:.2f}[/dim])"
        )
        console.print(
            f"[bold]Type:[/bold] {fb.bubble.type.value}    [bold]Emotion:[/bold] {fb.bubble.emotion}"
        )

        action = Prompt.ask(
            "[k]eep / [c]hange speaker / [e]dit text / [t]ype / [s]kip", default="k"
        )
        if action == "k":
            continue
        if action == "s":
            break  # user can resume later — corrections.jsonl preserves what they did

        before = fb.bubble.model_dump()
        if action == "c":
            new_speaker = Prompt.ask("New speaker_id", default=fb.bubble.speaker_id)
            panel.bubbles[idx] = fb.bubble.model_copy(
                update={"speaker_id": new_speaker, "confidence": 1.0}
            )
            ctype = "speaker_attribution"
        elif action == "e":
            new_text = Prompt.ask("New text", default=fb.bubble.text)
            panel.bubbles[idx] = fb.bubble.model_copy(update={"text": new_text, "confidence": 1.0})
            ctype = "text_correction"
        elif action == "t":
            new_type = Prompt.ask("New type", choices=[t.value for t in BubbleType])
            panel.bubbles[idx] = fb.bubble.model_copy(
                update={"type": BubbleType(new_type), "confidence": 1.0}
            )
            ctype = "type_change"
        else:
            continue

        after = panel.bubbles[idx].model_dump()
        append_correction(
            corrections_log,
            page=fb.page,
            panel=fb.panel_order,
            bubble_index=idx,
            before=before,
            after=after,
            correction_type=ctype,
        )

    console.print("\n[green]Review complete.[/green]")
    log.info("review.run.done", n_flagged=len(flagged))
    return script
