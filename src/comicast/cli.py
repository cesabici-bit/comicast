"""Comicast CLI entry point — orchestrates all 4 stages.

Idempotency by design: each stage checks `<output>.exists() and not force` before
re-running, so `comicast process <input>` is safely re-invocable on the same
volume without redoing completed stages. Pass `--force` to invalidate all
intermediate artifacts and re-run from scratch. The HITL review path (`run_review`)
preserves user corrections via `corrections.jsonl` (T36 writer); a re-invocation
re-flags un-corrected bubbles without losing prior decisions.
"""

from __future__ import annotations

from importlib.metadata import version as pkg_version
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from comicast.anthropic_client import AnthropicClient
from comicast.budget import BudgetTracker
from comicast.elevenlabs_client import ElevenLabsClient
from comicast.extract import extract_pages
from comicast.learn import update_common_errors_from_log
from comicast.logging_setup import get_logger, setup_logging
from comicast.m4b import detect_scene_breaks, export_m4b_with_chapters
from comicast.profile import (
    load_profile,
    save_profile,
    upsert_cast_from_extraction,
)
from comicast.review import run_review
from comicast.schemas import ScriptFile
from comicast.stitch import export_mp3, stitch_clips
from comicast.tts import generate_audio
from comicast.vision.attribute import attribute_pages
from comicast.vision.cast import extract_cast
from comicast.vision.narrative import check_narrative
from comicast.voice.director import build_directed_script
from comicast.voice_assign import assign_voices_interactive

app = typer.Typer(name="comicast", help="AI audiobook generator for digital comics")
console = Console()
log = get_logger("comicast.cli")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(pkg_version("comicast"))
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool, typer.Option("--version", callback=_version_callback, is_eager=True)
    ] = False,
    log_level: Annotated[str, typer.Option("--log-level")] = "INFO",
    json_logs: Annotated[bool, typer.Option("--json-logs")] = False,
) -> None:
    setup_logging(level=log_level, json_output=json_logs)


@app.command()
def process(
    input_path: Annotated[Path, typer.Argument(help="Path to CBZ/CBR/PDF")],
    series: Annotated[str, typer.Option("--series", help="Series name (e.g. 'Invincible')")],
    volume_id: Annotated[str, typer.Option("--volume", help="Volume id (e.g. 'vol_2')")],
    work_dir: Annotated[Path, typer.Option("--work-dir")] = Path("./data/work"),
    profile_dir: Annotated[Path, typer.Option("--profile-dir")] = Path("./data/series_profiles"),
    estimate_usd: Annotated[float, typer.Option("--budget", help="Estimated cost USD")] = 35.0,
    skip_narrative_check: Annotated[bool, typer.Option("--skip-narrative-check")] = False,
    skip_review: Annotated[
        bool, typer.Option("--skip-review", help="Skip HITL (for batch)")
    ] = False,
    force: Annotated[bool, typer.Option("--force", help="Re-run all stages from scratch")] = False,
) -> None:
    """Generate an audiobook from a comic file."""
    volume_dir = work_dir / volume_id
    volume_dir.mkdir(parents=True, exist_ok=True)
    log.info("cli.start", input=str(input_path), series=series, volume=volume_id)

    budget = BudgetTracker(
        estimate_usd=estimate_usd,
        log_path=volume_dir / "budget.log",
    )
    anth = AnthropicClient(budget=budget)
    el = ElevenLabsClient(budget=budget)

    # Stage 1
    pages_dir = volume_dir / "pages"
    pages = extract_pages(input_path, pages_dir, force=force)

    # Profile
    profile_path = profile_dir / f"{series.lower().replace(' ', '_')}.json"
    profile = load_profile(profile_path, series_name=series)

    # Stage 2a — Cast
    cast_path = volume_dir / "cast.json"
    if cast_path.exists() and not force:
        from comicast.schemas import CastFile

        cast = CastFile.model_validate_json(cast_path.read_text())
    else:
        cast = extract_cast(pages, series_name=series, client=anth, budget=budget)
        cast_path.write_text(cast.model_dump_json(indent=2))
    profile = upsert_cast_from_extraction(profile, cast)
    save_profile(profile, profile_path)

    # Voice assignment (HITL — if any cast member missing voice_id)
    if not skip_review:
        profile = assign_voices_interactive(profile, el_client=el)
        save_profile(profile, profile_path)

    # Stage 2b — Per-page attribution
    script_path = volume_dir / "script.json"
    if script_path.exists() and not force:
        script = ScriptFile.model_validate_json(script_path.read_text())
    else:
        script = attribute_pages(
            pages,
            cast=cast,
            common_errors=profile.common_errors_learned,
            series_name=series,
            volume_id=volume_id,
            client=anth,
            budget=budget,
        )
        script_path.write_text(script.model_dump_json(indent=2))

    # Stage 2c — Narrative consistency
    flags_path = volume_dir / "flags.json"
    if not skip_narrative_check and (not flags_path.exists() or force):
        flags = check_narrative(script, cast=cast, client=anth, budget=budget)
        flags_path.write_text(flags.model_dump_json(indent=2))

    # HITL Review
    corrections_log = volume_dir / "corrections.jsonl"
    if not skip_review:
        script = run_review(script, threshold=0.7, corrections_log=corrections_log)
        script_path.write_text(script.model_dump_json(indent=2))

    # Self-improving — update common_errors_learned
    profile = update_common_errors_from_log(profile, corrections_log, client=anth, budget=budget)
    # PROF-04: version bumps once per CLI invocation, consistent with the
    # volumes_processed.append() semantic — version tracks "how many runs touched this profile".
    profile.version += 1
    if volume_id not in profile.volumes_processed:
        profile.volumes_processed.append(volume_id)
    save_profile(profile, profile_path)

    # Stage 3 — Voice direction
    directed = build_directed_script(script, profile=profile)
    (volume_dir / "script_with_voices.json").write_text(directed.model_dump_json(indent=2))

    # Stage 4 — TTS + Stitching
    clips = generate_audio(directed, client=el, budget=budget, max_concurrent=8)
    final = stitch_clips(clips, scene_breaks_at_pages=detect_scene_breaks(script))
    mp3_path = volume_dir / "output.mp3"
    export_mp3(final, mp3_path)

    # Stage 4 (cont) — M4B with chapters (if scene breaks exist)
    breaks = detect_scene_breaks(script)
    if breaks:
        # Compute offsets by walking clips with stitched durations
        # (T34 will need the per-clip durations from final segment timestamps)
        chapters: list[tuple[int, str]] = [(0, f"{series} {volume_id}")]
        # F4 may add per-scene chapter detection. For F3 first cut, single chapter.
        m4b_path = volume_dir / "output.m4b"
        export_m4b_with_chapters(mp3_path, m4b_path, chapters)

    budget.flush()
    console.print(f"\n[green]Done.[/green] MP3: {mp3_path}  Cost: ${budget.spent_usd:.2f}")
