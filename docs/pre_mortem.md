# Pre-Mortem — Comicast Phase 1

For each risk in `spec.md` sez. 9, this file enumerates concrete test cases that prevent regression.
Risk 5 and Risk 6 were discovered during F2 and F1 respectively; they are not in the original spec.

> **Note (post-T11.5):** `spec.md` sez. 9 was normalized in T11.5 (this commit) to use the
> reconciled wording (`type` field instead of `bubble_type`, `[reflective]` instead of
> `[internal monologue]`, etc.). This pre-mortem and `spec.md` are now aligned; the historical
> override is no longer needed.

---

## Risk 1: SFX/onomatopee/narrazione confondono speaker attribution

**Test cases:**

- `tests/unit/test_sfx_classification.py::test_krang_is_sfx_not_dialogue`:
  Bubble text "KRRAAANG!" with no character nearby → `type == "sfx"`, `speaker_id == "__sfx__"`.
- `tests/unit/test_narration_box.py::test_narration_box_attributed_to_narrator`:
  Rectangular caption box (not balloon) → `type == "narration"`, `speaker_id == "__narrator__"`.
- `tests/unit/test_thought_balloon.py::test_thought_balloon_uses_reflective_tag`:
  Bubble with cloud-edge balloon → `type == "thought"`, voice direction emits `[reflective]`
  (optionally combined with `[whispers]` for sotto-voce thoughts).
  **Note:** `[internal monologue]` is not a documented ElevenLabs v3 tag and must not be emitted.
  See `docs/research/F1-elevenlabs.md` §1.2.

**Implementation guard:** Schema enforces `type ∈ {dialogue, thought, narration, sfx}` (field name
is `type` per `spec.md §4.2` JSON example, line 125). The Pass 2b prompt explicitly defines each
type with examples. Pass 3 maps `type == "thought"` to `[reflective]` (or `[reflective][whispers]`)
— never to `[internal monologue]`.

---

## Risk 2: Costume/morfologia confondono character recognition

**Test cases:**

- `tests/golden/test_mark_costume_consistency.py`:
  Run on a curated 5-panel sequence where Mark is in costume (panels 1-2) and out of costume
  (panels 3-5). All 5 panels must attribute to `mark_grayson`.
- `tests/unit/test_cast_description_includes_visual_cues.py`:
  Cast description for Mark must include both "in suit" and "out of suit" visual markers.

**Implementation guard:** Cast extraction prompt (Pass 2a) explicitly asks for "key visual cues
across all appearances" (in suit vs out, civilian vs costumed). HITL corrections accumulate in
`corrections.jsonl` and are fed back into `series_profile.json` for subsequent pages.

---

## Risk 3: Cost runaway

**Test cases:**

- `tests/unit/test_budget_guard_halts_pipeline.py::test_fails_fast_at_2x_estimate`:
  Mock cost reaches 2× estimate → pipeline raises `BudgetExceededError` and halts.
- `tests/unit/test_budget_guard_warns_at_1.5x.py::test_warns_at_soft_threshold`:
  Mock cost reaches 1.5× estimate → emits structured warning (`structlog` event
  `budget.soft_warning`), pipeline continues.
- `tests/unit/test_budget_tracker_records_per_call.py`:
  Each API call increments tracker; tracker persists to `budget.log`.

**Implementation guard:** `comicast.budget.BudgetGuard` is a context manager that wraps the entire
pipeline. Every API client (Anthropic, ElevenLabs) reports cost before/after via callback. Hard
ceiling is 2× per-volume cost estimate; soft warning at 1.5×.

---

## Risk 4: Quality regression silente quando ElevenLabs aggiorna i modelli

**Test cases:**

- `tests/golden/test_audio_hash_stable.py::test_chapter_1_audio_hash_matches`:
  Run pipeline on golden fixture (Invincible Vol 1 Chapter 1, ~25 pages) → audio waveform hash
  must match committed reference (within tolerance for floating-point drift).
- CI runs this nightly with real ElevenLabs API (marked `slow` + `golden`).

**Note on scope split:** This golden snapshot intentionally uses a smaller scope (Vol 1 Chapter 1,
~25 pages) than the smoke test target (full Vol 2, ~144 pages — see `docs/smoke_test.md`). The two
artifacts serve different purposes: the L4 audio-hash snapshot is a fast daily regression check;
the smoke test is the full-volume integration gate. This is the resolution of `docs/smoke_test.md`
"Open spec inconsistencies" appendix item #2: `spec.md §8` references Vol 1 Cap 1 for the L4
golden snapshot, while the smoke test targets Vol 2 — both are correct and intentionally distinct.

**Implementation guard:** Golden snapshot committed to
`tests/golden/fixtures/invincible_chapter_1_audio_hash.txt`. CI alert if drift detected. See also
`spec.md §8` L4 row: "Invincible Vol 1 Cap 1 (~25 pagine) processato con series_profile di
riferimento."

---

## Risk 5 (NEW — discovered during F2): Anthropic prompt cache TTL expires mid-volume

If processing a volume takes >5 min and the cache is ephemeral, Pass 2b calls late in the volume
miss the cache and pay full input cost. Anthropic ephemeral cache TTL is 5 minutes
per `docs/research/F1-anthropic.md`.

**Test cases:**

- `tests/unit/test_cache_window_pacing.py::test_pages_batched_within_5min_window`:
  Mock 200 pages → orchestrator batches them into ≤5min windows, refreshing cache between windows.

**Implementation guard:** `comicast.vision.attribute.process_pages` paces requests so a single
cache write covers ≤25 pages (well under 5min at parallelism=5). Cache refresh is triggered
proactively before the TTL window expires.

---

## Risk 6 (NEW — discovered during F1): Dependency breakage on Python stdlib changes

`pydub 0.25.1` (latest, 2024) imports the stdlib `audioop` module, which was removed in Python
3.13 per PEP 594. F1-T09 caught this BEFORE any F3 audio code ran. Fix: `audioop-lts>=0.2.2`
conditionally added in `pyproject.toml` for `python_version >= '3.13'`.

**Test cases:**

- `tests/unit/test_audio_imports.py::test_pydub_imports_on_current_interpreter`:
  Smoke import: `from pydub import AudioSegment` must succeed on every supported Python version.
  Fails fast if a future stdlib removal breaks pydub again.
- `tests/unit/test_verified_deps_includes_audioop_lts_when_py313.py`:
  When `sys.version_info >= (3, 13)`, `verified-deps.toml` must contain an `audioop-lts` entry.
  Catches drift between `pyproject.toml` and the `verified-deps.toml` lock.

**Implementation guard:** `verify_deps.py` (M1 enforcer) parses `verified-deps.toml` and confirms
each entry installs at the declared major version. Adding the test above turns import-time silent
failures into CI-time loud failures.

**Reference:** `KNOWN_ISSUES.md::PYAUDIOOP-001`.
