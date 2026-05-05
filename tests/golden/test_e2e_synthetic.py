"""SMOKE E2E (4 scenarios): synthetic CBZ → MP3 with all external APIs mocked.

D-EXT-3 (CLI-07): 4 scenarios instead of 1 plan-verbatim, to lock CLI-01/CLI-03/CLI-07.

DEVIATION D-EXT-3a: cycle is 3 cast + 3 attr = 6 calls (not "1+3+1+1=6").
  extract_cast() iterates over ALL pages and calls client.call_with_image once per
  page. For 3 pages this yields 3 cast calls. All 4 scenarios pass
  --skip-narrative-check to keep the cycle predictable at 6 total.

DEVIATION D-EXT-3b: --skip-review scenarios pre-seed the series profile with
  voice_id="EL_test" for character "synth". Without this, build_directed_script
  raises RuntimeError (voice_by_id is empty → 0 bubbles receive voice → total_out=0).

DEVIATION D-EXT-3c: pydub AudioSegment is mocked to avoid ffmpeg dependency in CI.
  stitch_clips and export_mp3 are patched via comicast.stitch.AudioSegment; the
  export mock writes SILENCE_MP3 bytes to disk so the mp3.stat().st_size > 0 check
  still holds. This is appropriate for a pipeline-wiring smoke test.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

# Module-level constant — cross-module constant drift prevention (lesson L11+)
SILENCE_MP3 = b"\xff\xfb\x90\x00" + b"\x00" * 1000  # minimal MP3-ish bytes (used as mock audio)

FIXTURE = Path(__file__).parent.parent / "fixtures" / "synth_3pages.cbz"

# Pre-seeded profile JSON for --skip-review scenarios.
# voice_id="EL_test" so build_directed_script has a voice to work with.
_SEED_PROFILE = {
    "series_name": "Synth",
    "version": 0,
    "volumes_processed": [],
    "cast": [
        {
            "id": "synth",
            "canonical_name": "Synth",
            "aliases": [],
            "description": "synthetic test character desc here",
            "confidence": 0.9,
            "voice_id": "EL_test",
            "voice_archetype": None,
            "user_confirmations": 0,
            "user_corrections": 0,
        }
    ],
    "common_errors_learned": [],
    "voice_archetype_library": {},
}


def _seed_profile(profile_dir: Path) -> None:
    """Write a pre-seeded profile so --skip-review scenarios have a voice to use."""
    profile_dir.mkdir(parents=True, exist_ok=True)
    (profile_dir / "synth.json").write_text(json.dumps(_SEED_PROFILE, indent=2))


def _make_audio_segment_mock() -> MagicMock:
    """Return a MagicMock that behaves like pydub.AudioSegment for stitching purposes.

    Patched into comicast.stitch.AudioSegment (D-EXT-3c).
    - from_file() → mock segment
    - silent() → mock segment
    - segment + segment → mock segment (via __add__)
    - len(segment) → 1000 (for duration_ms log)
    - segment.export(path, ...) → writes SILENCE_MP3 bytes to path
    """
    seg = MagicMock()
    seg.__add__ = lambda self, other: seg
    seg.__len__ = lambda self: 1000  # duration_ms placeholder

    def _export(out: object, **kwargs: object) -> None:
        path = Path(str(out))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(SILENCE_MP3)

    seg.export.side_effect = _export

    mock_cls = MagicMock()
    mock_cls.from_file.return_value = seg
    mock_cls.silent.return_value = seg
    return mock_cls


def _build_mocks(
    MockAnth: MagicMock,  # noqa: N803
    MockEL: MagicMock,  # noqa: N803
) -> tuple[str, str]:
    """Set up shared mock responses.  Returns (cast_response, page_response).

    D-FIX-4 (MIN-3): narrative/learn responses removed from return signature —
    all 4 scenarios pass --skip-narrative-check, and learn graceful-degrades when
    corrections.jsonl is absent. Re-add narr/learn to return when T40-04 lands a
    narrative-coverage scenario.

    Cycle NOT set here — each scenario has its own cycle because cycle is consumed
    destructively (list.pop(0)) and each scenario invokes runner.invoke independently.
    """
    cast_response = json.dumps(
        {
            "cast": [
                {
                    "id": "synth",
                    "canonical_name": "Synth",
                    "aliases": ["S"],
                    "description": "synthetic test character desc here",
                    "confidence": 0.9,
                }
            ]
        }
    )
    page_response = json.dumps(
        {
            "page": 1,
            "panels": [
                {
                    "order": 1,
                    "bubbles": [
                        {
                            "text": "hi",
                            "speaker_id": "synth",
                            "emotion": "casual",
                            "type": "dialogue",
                            "bbox": [0, 0, 1, 1],
                            "confidence": 0.95,
                        }
                    ],
                }
            ],
        }
    )

    # ElevenLabs mock: every synthesize returns SILENCE_MP3; voice search returns 1 voice
    MockEL.return_value.text_to_speech.convert.return_value = iter([SILENCE_MP3])
    MockEL.return_value.voices.search.return_value = MagicMock(
        voices=[
            MagicMock(voice_id="EL_test", name="Test Voice", description="x"),
        ]
    )

    return cast_response, page_response


def _make_create_fn(cycle: list[str]) -> MagicMock:
    """Build a side_effect function that pops items from cycle sequentially."""
    usage = MagicMock(
        input_tokens=100,
        output_tokens=50,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
    )

    def _create(**kwargs: object) -> MagicMock:  # noqa: ANN001
        text = cycle.pop(0) if cycle else "{}"
        m = MagicMock()
        m.content = [MagicMock(type="text", text=text)]
        m.usage = usage
        return m

    return _create  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Scenario (a) — cold path, --skip-review
# ---------------------------------------------------------------------------


@pytest.mark.golden
@patch("comicast.stitch.AudioSegment")
@patch("comicast.elevenlabs_client.ElevenLabs")
@patch("comicast.anthropic_client.anthropic.Anthropic")
def test_e2e_cold_path_skip_review(
    MockAnth: MagicMock,  # noqa: N803
    MockEL: MagicMock,  # noqa: N803
    MockAudioSeg: MagicMock,  # noqa: N803
    tmp_path: Path,
) -> None:
    """SMOKE (a): cold path, --skip-review.  Plan-verbatim baseline + D-EXT-3 locks.

    Profile pre-seeded with voice_id="EL_test" (see D-EXT-3b deviation note).
    Cycle: 3 cast calls + 3 attribute calls = 6 total (see D-EXT-3a deviation note).
    AudioSegment mocked to avoid ffmpeg (see D-EXT-3c deviation note).

    Locks: 5 cardinality invariants (D-EXT-2), 4 intermediate artifacts on disk,
    profile round-trip post-run (version==1 / volumes_processed=='v1' / 1 cast entry).
    """
    cast_response, page_response = _build_mocks(MockAnth, MockEL)
    audio_mock = _make_audio_segment_mock()
    MockAudioSeg.from_file = audio_mock.from_file
    MockAudioSeg.silent = audio_mock.silent

    def _fake_export_mp3(segment: object, out: Path, **kwargs: object) -> None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(SILENCE_MP3)

    # 3 cast calls (extract_cast iterates all 3 pages) + 3 attr calls = 6
    cycle: list[str] = [cast_response] * 3 + [page_response] * 3
    MockAnth.return_value.messages.create.side_effect = _make_create_fn(cycle)

    profile_dir = tmp_path / "profiles"
    _seed_profile(profile_dir)

    runner = CliRunner()
    with patch("comicast.stitch.export_mp3", side_effect=_fake_export_mp3):
        result = runner.invoke(
            __import__("comicast.cli", fromlist=["app"]).app,
            [
                "process",
                str(FIXTURE),
                "--series",
                "Synth",
                "--volume",
                "v1",
                "--work-dir",
                str(tmp_path / "work"),
                "--profile-dir",
                str(profile_dir),
                "--budget",
                "5.0",
                "--skip-review",
                "--skip-narrative-check",
            ],
            catch_exceptions=False,
            env={"ANTHROPIC_API_KEY": "sk-test", "ELEVENLABS_API_KEY": "el-test"},
        )
    assert result.exit_code == 0, result.stdout

    mp3 = tmp_path / "work" / "v1" / "output.mp3"
    assert mp3.exists()
    assert mp3.stat().st_size > 0

    # D-EXT-3 locks: intermediate artifact existence
    volume_dir = tmp_path / "work" / "v1"
    pages_dir = volume_dir / "pages"
    assert pages_dir.exists()
    assert len(list(pages_dir.glob("page_*.png"))) == 3
    assert (volume_dir / "cast.json").exists()
    assert (volume_dir / "script.json").exists()
    assert (volume_dir / "script_with_voices.json").exists()

    # Series profile round-trip: version==1, volumes_processed=["v1"], 1 cast entry with id=="synth"
    profile_data = json.loads((profile_dir / "synth.json").read_text())
    assert profile_data["version"] == 1
    assert profile_data["volumes_processed"] == ["v1"]
    assert len(profile_data["cast"]) == 1
    assert profile_data["cast"][0]["id"] == "synth"


# ---------------------------------------------------------------------------
# Scenario (b) — warm path (resume), no --force
# ---------------------------------------------------------------------------


@pytest.mark.golden
@patch("comicast.stitch.AudioSegment")
@patch("comicast.elevenlabs_client.ElevenLabs")
@patch("comicast.anthropic_client.anthropic.Anthropic")
def test_e2e_warm_path_resume(
    MockAnth: MagicMock,  # noqa: N803
    MockEL: MagicMock,  # noqa: N803
    MockAudioSeg: MagicMock,  # noqa: N803
    tmp_path: Path,
) -> None:
    """SMOKE (b): warm path — re-invoke after cold run; all Anthropic stages skip-by-existence.

    After the cold run populates work dir, the sentinel replaces Anthropic's side_effect
    so that any call to messages.create raises AssertionError.  The pipeline must complete
    with exit_code==0 because cast.json and script.json exist and force is False.

    TTS runs unconditionally (no skip branch in current cli.py) so MockEL stays valid.
    """
    cast_response, page_response = _build_mocks(MockAnth, MockEL)
    audio_mock = _make_audio_segment_mock()
    MockAudioSeg.from_file = audio_mock.from_file
    MockAudioSeg.silent = audio_mock.silent

    def _fake_export_mp3(segment: object, out: Path, **kwargs: object) -> None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(SILENCE_MP3)

    profile_dir = tmp_path / "profiles"
    _seed_profile(profile_dir)

    base_args = [
        "process",
        str(FIXTURE),
        "--series",
        "Synth",
        "--volume",
        "v1",
        "--work-dir",
        str(tmp_path / "work"),
        "--profile-dir",
        str(profile_dir),
        "--budget",
        "5.0",
        "--skip-review",
        "--skip-narrative-check",
    ]

    runner = CliRunner()

    # --- Cold run first ---
    cycle_cold: list[str] = [cast_response] * 3 + [page_response] * 3
    MockAnth.return_value.messages.create.side_effect = _make_create_fn(cycle_cold)

    with patch("comicast.stitch.export_mp3", side_effect=_fake_export_mp3):
        cold_result = runner.invoke(
            __import__("comicast.cli", fromlist=["app"]).app,
            base_args,
            catch_exceptions=False,
            env={"ANTHROPIC_API_KEY": "sk-test", "ELEVENLABS_API_KEY": "el-test"},
        )
    assert cold_result.exit_code == 0, cold_result.stdout

    # CONCERN-2 lock: cold run must invoke Anthropic exactly 6 times (3 cast + 3 attr).
    # Locks the cycle structure so a future plumbing change that drops/adds a stage
    # call produces a loud test failure instead of silent cycle exhaustion.
    assert MockAnth.return_value.messages.create.call_count == 6

    # --- Warm run: Anthropic must NOT be called ---
    MockAnth.return_value.messages.create.side_effect = AssertionError(
        "warm-path must not call Anthropic"
    )
    # EL still needed (TTS runs unconditionally — no skip branch for TTS in current cli.py)
    MockEL.return_value.text_to_speech.convert.return_value = iter([SILENCE_MP3])

    with patch("comicast.stitch.export_mp3", side_effect=_fake_export_mp3):
        warm_result = runner.invoke(
            __import__("comicast.cli", fromlist=["app"]).app,
            base_args,  # same args, no --force
            catch_exceptions=False,
            env={"ANTHROPIC_API_KEY": "sk-test", "ELEVENLABS_API_KEY": "el-test"},
        )
    assert warm_result.exit_code == 0, warm_result.stdout

    # MP3 still exists (TTS ran again, overwriting with fresh silence bytes)
    mp3 = tmp_path / "work" / "v1" / "output.mp3"
    assert mp3.exists()


# ---------------------------------------------------------------------------
# Scenario (c) — --force pre-clean (CLI-01 lock)
# ---------------------------------------------------------------------------


@pytest.mark.golden
@patch("comicast.stitch.AudioSegment")
@patch("comicast.elevenlabs_client.ElevenLabs")
@patch("comicast.anthropic_client.anthropic.Anthropic")
def test_e2e_force_pre_clean_fewer_pages(
    MockAnth: MagicMock,  # noqa: N803
    MockEL: MagicMock,  # noqa: N803
    MockAudioSeg: MagicMock,  # noqa: N803
    tmp_path: Path,
) -> None:
    """SMOKE (c): --force pre-clean removes stale extra pages (CLI-01 lock — D-EXT-1).

    After the cold run, two extra stale PNG files are injected into the pages dir.
    Re-invoking with --force must produce EXACTLY 3 page_*.png (stale files gone).
    """
    cast_response, page_response = _build_mocks(MockAnth, MockEL)
    audio_mock = _make_audio_segment_mock()
    MockAudioSeg.from_file = audio_mock.from_file
    MockAudioSeg.silent = audio_mock.silent

    def _fake_export_mp3(segment: object, out: Path, **kwargs: object) -> None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(SILENCE_MP3)

    profile_dir = tmp_path / "profiles"
    _seed_profile(profile_dir)

    base_args = [
        "process",
        str(FIXTURE),
        "--series",
        "Synth",
        "--volume",
        "v1",
        "--work-dir",
        str(tmp_path / "work"),
        "--profile-dir",
        str(profile_dir),
        "--budget",
        "5.0",
        "--skip-review",
        "--skip-narrative-check",
    ]

    runner = CliRunner()

    # --- Cold run ---
    cycle_cold: list[str] = [cast_response] * 3 + [page_response] * 3
    MockAnth.return_value.messages.create.side_effect = _make_create_fn(cycle_cold)

    with patch("comicast.stitch.export_mp3", side_effect=_fake_export_mp3):
        cold_result = runner.invoke(
            __import__("comicast.cli", fromlist=["app"]).app,
            base_args,
            catch_exceptions=False,
            env={"ANTHROPIC_API_KEY": "sk-test", "ELEVENLABS_API_KEY": "el-test"},
        )
    assert cold_result.exit_code == 0, cold_result.stdout

    # Verify 3 pages after cold run
    volume_dir = tmp_path / "work" / "v1"
    pages_dir = volume_dir / "pages"
    assert len(list(pages_dir.glob("page_*.png"))) == 3

    # Inject stale extra pages (minimal PNG header bytes)
    minimal_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    (pages_dir / "page_004.png").write_bytes(minimal_png)
    (pages_dir / "page_005.png").write_bytes(minimal_png)
    assert len(list(pages_dir.glob("page_*.png"))) == 5  # confirm stale files exist

    # --- Force run: re-arm cycle; profile already on disk from cold run ---
    cycle_force: list[str] = [cast_response] * 3 + [page_response] * 3
    MockAnth.return_value.messages.create.side_effect = _make_create_fn(cycle_force)
    MockEL.return_value.text_to_speech.convert.return_value = iter([SILENCE_MP3])

    with patch("comicast.stitch.export_mp3", side_effect=_fake_export_mp3):
        force_result = runner.invoke(
            __import__("comicast.cli", fromlist=["app"]).app,
            [*base_args, "--force"],
            catch_exceptions=False,
            env={"ANTHROPIC_API_KEY": "sk-test", "ELEVENLABS_API_KEY": "el-test"},
        )
    assert force_result.exit_code == 0, force_result.stdout

    # CLI-01 LOCK: stale files are gone, exactly 3 pages remain
    remaining = sorted(p.name for p in pages_dir.glob("page_*.png"))
    assert remaining == ["page_001.png", "page_002.png", "page_003.png"]
    assert not (pages_dir / "page_004.png").exists()
    assert not (pages_dir / "page_005.png").exists()


# ---------------------------------------------------------------------------
# Scenario (d) — interactive review path (CLI-07 HITL lock)
# ---------------------------------------------------------------------------


@pytest.mark.golden
@patch("comicast.stitch.AudioSegment")
@patch("comicast.elevenlabs_client.ElevenLabs")
@patch("comicast.anthropic_client.anthropic.Anthropic")
def test_e2e_interactive_review_path(
    MockAnth: MagicMock,  # noqa: N803
    MockEL: MagicMock,  # noqa: N803
    MockAudioSeg: MagicMock,  # noqa: N803
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SMOKE (d): interactive review path — HITL voice assignment + no --skip-review (CLI-07).

    All bubbles have confidence 0.95 > HITL_CONFIDENCE_THRESHOLD (0.7), so run_review
    short-circuits with no flagged bubbles — no Prompt.ask called from review path.

    Voice assignment loop iterates the 1 cast member (synth, no voice_id initially).
    Profile NOT pre-seeded here so that assign_voices_interactive is triggered.

    Monkeypatches Prompt.ask to return "1" uniformly:
      - query refinement → "1"
      - pick voice candidate #1 → voice_id = "EL_test"
      - save as archetype → "1" (non-empty → saves archetype label "1")

    Post-run assertion: profile.cast[0].voice_id == "EL_test".

    Cycle: 3 cast + 3 attr = 6 calls; no narrative (--skip-narrative-check);
    no learn (no corrections.jsonl — run_review short-circuits on empty flagged).
    """
    cast_response, page_response = _build_mocks(MockAnth, MockEL)

    audio_mock = _make_audio_segment_mock()
    MockAudioSeg.from_file = audio_mock.from_file
    MockAudioSeg.silent = audio_mock.silent

    def _fake_export_mp3(segment: object, out: Path, **kwargs: object) -> None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(SILENCE_MP3)

    cycle: list[str] = [cast_response] * 3 + [page_response] * 3
    MockAnth.return_value.messages.create.side_effect = _make_create_fn(cycle)

    # Monkeypatch Prompt.ask to drive interactive voice assignment
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *a, **kw: "1")

    # Profile NOT pre-seeded — voice_id starts as None, assign_voices_interactive fills it
    profile_dir = tmp_path / "profiles"

    runner = CliRunner()
    with patch("comicast.stitch.export_mp3", side_effect=_fake_export_mp3):
        result = runner.invoke(
            __import__("comicast.cli", fromlist=["app"]).app,
            [
                "process",
                str(FIXTURE),
                "--series",
                "Synth",
                "--volume",
                "v1",
                "--work-dir",
                str(tmp_path / "work"),
                "--profile-dir",
                str(profile_dir),
                "--budget",
                "5.0",
                # NO --skip-review: triggers assign_voices_interactive + run_review
                "--skip-narrative-check",
            ],
            catch_exceptions=False,
            env={"ANTHROPIC_API_KEY": "sk-test", "ELEVENLABS_API_KEY": "el-test"},
        )
    assert result.exit_code == 0, result.stdout

    # CLI-07 LOCK: voice was assigned interactively
    profile_path = profile_dir / "synth.json"
    assert profile_path.exists()
    profile_data = json.loads(profile_path.read_text())
    assert profile_data["cast"][0]["voice_id"] == "EL_test"
    assert profile_data["version"] == 1

    mp3 = tmp_path / "work" / "v1" / "output.mp3"
    assert mp3.exists()


# ---------------------------------------------------------------------------
# Scenario (e) — fail-fast on --skip-review with no voice_id (D-FIX-1 / IMP-1 lock)
# ---------------------------------------------------------------------------


@pytest.mark.golden
@patch("comicast.stitch.AudioSegment")
@patch("comicast.elevenlabs_client.ElevenLabs")
@patch("comicast.anthropic_client.anthropic.Anthropic")
def test_e2e_skip_review_fresh_profile_fails_fast(
    MockAnth: MagicMock,  # noqa: N803
    MockEL: MagicMock,  # noqa: N803
    MockAudioSeg: MagicMock,  # noqa: N803
    tmp_path: Path,
) -> None:
    """SMOKE (e): --skip-review on a profile with no voice_id must fail-fast at stage 2.

    D-FIX-1 (T40-01 / IMP-1): the CLI guard at cli.py post-vision_cast cardinality
    raises a descriptive RuntimeError when skip_review is True and no cast member
    has voice_id assigned. Without this guard, the pipeline crashes deep in stage 3
    (build_directed_script, voice_by_id empty → total_out==0). This scenario locks
    the early-fail behavior and verifies the error message is actionable.

    Profile NOT pre-seeded — extract_cast populates 1 cast entry without voice_id.
    """
    cast_response, page_response = _build_mocks(MockAnth, MockEL)

    audio_mock = _make_audio_segment_mock()
    MockAudioSeg.from_file = audio_mock.from_file
    MockAudioSeg.silent = audio_mock.silent

    cycle: list[str] = [cast_response] * 3 + [page_response] * 3
    MockAnth.return_value.messages.create.side_effect = _make_create_fn(cycle)

    profile_dir = tmp_path / "profiles"
    # Profile NOT pre-seeded — guard must fire after upsert populates cast.

    runner = CliRunner()
    result = runner.invoke(
        __import__("comicast.cli", fromlist=["app"]).app,
        [
            "process",
            str(FIXTURE),
            "--series",
            "Synth",
            "--volume",
            "v1",
            "--work-dir",
            str(tmp_path / "work"),
            "--profile-dir",
            str(profile_dir),
            "--budget",
            "5.0",
            "--skip-review",
            "--skip-narrative-check",
        ],
        catch_exceptions=True,
        env={"ANTHROPIC_API_KEY": "sk-test", "ELEVENLABS_API_KEY": "el-test"},
    )

    # CLI exits non-zero with a RuntimeError surfacing the missing prerequisite.
    assert result.exit_code != 0
    assert isinstance(result.exception, RuntimeError)
    msg = str(result.exception)
    assert "voice_id" in msg
    assert "--skip-review" in msg
    # Stage-3 (director) must NOT have been reached — script_with_voices.json absent.
    assert not (tmp_path / "work" / "v1" / "script_with_voices.json").exists()
