# Changelog

All notable changes to Comicast are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the project predates SemVer releases and is currently pre-1.0 alpha.

## [Unreleased]

### Phase 4 (in progress) — Tier-1 audio enrichment

- T41a: ElevenLabs v3 emotion tag taxonomy expansion (6 → 20+ tags), voice slider tuning per archetype, SFX layer (Freesound CC0), music bed (Incompetech CC-BY), adaptive pauses

## [0.1.0-alpha] — 2026-05-06 (initial public release)

End-to-end pipeline working and validated on a 25-page real-input dry run (Invincible Vol 2 ch.1 → 18 min audio). Phase 1 complete.

### Phase 0 (2026-05-02) — Project scaffolding

- T01-T04: skeleton, dependencies, framework files (`CLAUDE.md`, `KNOWN_ISSUES.md`, `STATUS.md`, `Makefile`, `verified-deps.toml`), `make check-all` infrastructure (ruff + mypy + pytest)

### Phase 1 (2026-05-02 → 2026-05-03) — Research & dependency lock

- T05: Anthropic SDK + Claude vision research (strict-mode confirmed on Sonnet 4.6)
- T06: ElevenLabs v3 + director tags research (verb-form `[whispers]`/`[shouts]`, `[reflective]` for internal monologue)
- T07: extraction stack research (PDF → poppler, CBR → unrar/bsdtar) + real-PDF sanity test
- T08: competitor analysis (Tier A confirmed; arXiv 2509.15253 is closest direct prior work)
- T09: `verified-deps.toml` lock — 20 entries (14 runtime + 6 dev), all web-verified. Major bumps absorbed: elevenlabs 1→2, Pillow 10→12, rich 13→15, structlog 24→25, pytest 8→9. **Critical finding:** pydub 0.25.1 broken on Python 3.13 (audioop removed, PEP 594) — `audioop-lts` 0.2.2 is the fix

### Phase 2 (2026-05-03) — Spec absorption

- T10-T11: spec finalization, 9-flag absorption (verb-form tags, reflective mapping, cost realistic ranges, deskew Option B, runtime binaries, source format PDF, Pydub Py 3.13 fix, etc.)

### Phase 3 (2026-05-03 → 2026-05-05) — Phase-1 implementation

- **F3.1 Foundations:** Pydantic schemas (frozen, byte-stable), Hypothesis property tests, structlog setup, `BudgetTracker` + `BudgetGuard`, `AnthropicClient`. Critical bug intercepted: budget formula `(input - cached - cache_write) / 1M * INPUT_RATE` would have produced negative `spent_usd` on cache-hits — caught by code-quality review with M2 oracle test
- **F3.2 Extraction:** CBZ + PDF input (CBR skipped in v1, planned later). ZipInfo timestamp pinning for fixture determinism
- **F3.3 Vision (3-pass):** `vision/cast.py` (whole-volume cast extraction), `vision/attribute.py` (per-page bubble attribution), `vision/narrative.py` (cross-page consistency). `confidence.py` with `HITL_CONFIDENCE_THRESHOLD = 0.7` constant. Golden snapshot infrastructure (Pydantic byte-stability verified)
- **F3.4 Audio:** `voice/director.py` (emotion tags), `tts.py` (ThreadPoolExecutor.map order-preserved concurrency), `stitch.py` (silence-aware pause computation), `m4b.py` (chapter detection + ffmpeg passthrough)
- **F3.5 HITL:** `profile.py` (`series_profile.json` CRUD), `review.py` (HITL CLI), `voice_assign.py` (interactive voice mapping), `learn.py` (corrections feed back into profile)
- **F3.6 Orchestrator:** `cli.py` main entry, `comicast process` command. T40 E2E mocked smoke test (5 scenarios, 115 PASSED total)

### S34 dry-run validation (2026-05-06) — real-input E2E

- 25-page real-input pipeline run (Invincible Vol 2 ch.1) → 17.8 MB MP3 / 18 min audio generated. Cost: ~$8.02 total ($0.13 Anthropic + $7.89 ElevenLabs)
- 6 bugs surfaced that the mocked smoke could not catch — fixes landed in-task:
  - **TTS-06:** ElevenLabs Starter max 3 concurrent vs hardcode 8 → 429 cascade. Fix: `max_concurrent=2`
  - **STITCH-07:** ElevenLabs occasionally returns 0-byte MP3 (1 in 200). Fix: tolerant decode + 200ms silence placeholder
  - **EXT-12:** oversize page (>5MB base64) crash. Workaround: `scripts/resize_oversize_pages.py`. Permanent fix in F4
  - **CAST-01:** Shapesmith missing from cast extraction. Patched profile manually. VLM prompt enrichment in F4
  - **M4B-09:** ffmpeg EINVAL on M4B export. Defer to F4 (MP3 OK)
  - **VOICE-09/10:** voice_assign UX issues. Defer to F4
- **Resilience patches (in-task):** `tts.py` incremental clip persistence (`clip_NNNN_*.mp3`), `stitch.py` tolerant decode, `cli.py` stage-4 idempotency (skip TTS when clips/ already complete)
- **Listening test verdict:** pipeline OK (recognition + reading order "quasi ottimo"), recitation broadcaster-grade not actor-grade — see Roadmap for the 3-tier improvement path

## Notes on history

Pre-release commits use a session-numbered prefix (`Comicast Sxx`) and are co-authored by Claude — see git log for the development trail.
