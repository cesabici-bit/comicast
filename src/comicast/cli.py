"""Comicast CLI entry point — orchestrates all 4 stages.

Idempotency by design: each stage checks `<output>.exists() and not force` before
re-running, so `comicast process <input>` is safely re-invocable on the same
volume without redoing completed stages. Pass `--force` to invalidate all
intermediate artifacts and re-run from scratch. The HITL review path (`run_review`)
preserves user corrections via `corrections.jsonl` (T36 writer); a re-invocation
re-flags un-corrected bubbles without losing prior decisions.

The self-improving step (`update_common_errors_from_log`) graceful-degrades to a
no-op when `corrections.jsonl` is absent (e.g. `--skip-review` on a fresh volume),
emitting `learn.no_corrections` and returning the profile unchanged.
"""

from __future__ import annotations

from importlib.metadata import version as pkg_version
from pathlib import Path
from typing import Annotated

import typer
from dotenv import load_dotenv
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
from comicast.tts import AudioClip, generate_audio
from comicast.vision.attribute import attribute_pages
from comicast.vision.cast import extract_cast
from comicast.vision.narrative import check_narrative
from comicast.vision.thresholds import HITL_CONFIDENCE_THRESHOLD
from comicast.voice.director import build_directed_script
from comicast.voice_assign import assign_voices_interactive

app = typer.Typer(name="comicast", help="AI audiobook generator for digital comics")
console = Console()
log = get_logger("comicast.cli")


def _assert_cardinalities(stage: str, **invariants: int) -> None:
    """Guard: raise RuntimeError if any invariant value is <= 0.

    D-EXT-2 (CLI-03): cardinality helper for 5 pipeline stages.
    Uses RuntimeError (NOT assert keyword — assert is stripped under python -O,
    see KNOWN_ISSUES BG-01 lesson). Equality invariants are checked by the caller
    before calling this helper; this helper is the >0 guard.
    """
    failed = {k: v for k, v in invariants.items() if v <= 0}
    if failed:
        log.error("cli.cardinality.failed", stage=stage, **invariants)
        raise RuntimeError(f"Cardinality invariant violated at stage {stage}: {invariants}")
    log.info("cli.cardinality.ok", stage=stage, **invariants)


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
    # Load comicast/.env into os.environ before any client construction.
    # override=False so explicit env vars (CI secrets) still win over the file —
    # avoids stale local .env shadowing intended overrides.
    load_dotenv(override=False)
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
    _assert_cardinalities("extract", n_pages=len(pages))

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
    _assert_cardinalities("vision_cast", n_cast=len(cast.cast))

    # D-FIX-1 (T40-01 / IMP-1): fail-fast under --skip-review on a profile with
    # no voice_id assignments. Without this guard, build_directed_script raises
    # RuntimeError deep in stage 3 (director.py:128-132) when voice_by_id is empty,
    # giving the operator a cryptic error. Surface the missing prerequisite here.
    if skip_review and not any(c.voice_id for c in profile.cast):
        raise RuntimeError(
            f"Profile '{profile.series_name}' has 0/{len(profile.cast)} cast members "
            "with voice_id assigned. --skip-review requires pre-populated voice_ids; "
            "rerun without --skip-review to assign voices interactively."
        )

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
    if len(script.pages) != len(pages):
        raise RuntimeError(
            f"attribution produced {len(script.pages)} script pages, expected {len(pages)}"
        )
    _assert_cardinalities("attribute", n_script_pages=len(script.pages))

    # Stage 2c — Narrative consistency
    # `flags.json` is a write-only artifact for F4 dashboards; not consumed
    # downstream in F3 (HITL review reads `script.json`, not `flags.json`).
    flags_path = volume_dir / "flags.json"
    if not skip_narrative_check and (not flags_path.exists() or force):
        flags = check_narrative(script, cast=cast, client=anth, budget=budget)
        flags_path.write_text(flags.model_dump_json(indent=2))

    # HITL Review
    corrections_log = volume_dir / "corrections.jsonl"
    if not skip_review:
        script = run_review(
            script, threshold=HITL_CONFIDENCE_THRESHOLD, corrections_log=corrections_log
        )
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
    if len(directed.pages) != len(script.pages):
        raise RuntimeError(
            f"direction produced {len(directed.pages)} pages, expected {len(script.pages)}"
        )
    _assert_cardinalities("direction", n_directed_pages=len(directed.pages))

    # Stage 4 — TTS + Stitching (idempotent by clips/ dir presence + count match)
    clips_dir = volume_dir / "clips"
    n_expected = sum(len(p.bubbles) for pg in directed.pages for p in pg.panels)
    existing_clips = sorted(clips_dir.glob("clip_*.mp3")) if clips_dir.exists() else []
    if not force and len(existing_clips) == n_expected and n_expected > 0:
        log.info("tts.skip", n_clips=n_expected, reason="clips dir matches expected count")
        clips: list[AudioClip] = []
        t_idx = 0
        for pg in directed.pages:
            for p in pg.panels:
                for b_idx, bubble in enumerate(p.bubbles):
                    audio = existing_clips[t_idx].read_bytes()
                    clips.append(
                        AudioClip(
                            page=pg.page,
                            panel_order=p.order,
                            bubble_index=b_idx,
                            bubble=bubble,
                            audio=audio,
                        )
                    )
                    t_idx += 1
    else:
        clips = generate_audio(
            directed, client=el, budget=budget, max_concurrent=2, clips_dir=clips_dir
        )
    _assert_cardinalities("tts", n_clips=len(clips))
    scene_breaks = detect_scene_breaks(script)
    final = stitch_clips(clips, scene_breaks_at_pages=scene_breaks)
    mp3_path = volume_dir / "output.mp3"
    export_mp3(final, mp3_path)

    # Stage 4 (cont) — M4B with chapters (if scene breaks exist)
    had_m4b = bool(scene_breaks)
    if had_m4b:
        # Compute offsets by walking clips with stitched durations
        # (T34 will need the per-clip durations from final segment timestamps)
        chapters: list[tuple[int, str]] = [(0, f"{series} {volume_id}")]
        # F4 may add per-scene chapter detection. For F3 first cut, single chapter.
        m4b_path = volume_dir / "output.m4b"
        export_m4b_with_chapters(mp3_path, m4b_path, chapters)

    budget.flush()
    log.info(
        "cli.done",
        mp3_path=str(mp3_path),
        cost_usd=round(budget.spent_usd, 4),
        n_clips=len(clips),
        had_m4b=had_m4b,
    )
    console.print(f"\n[green]Done.[/green] MP3: {mp3_path}  Cost: ${budget.spent_usd:.2f}")
