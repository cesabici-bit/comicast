# Comicast

**AI audiobook generator for digital comics — per-character voices, HITL pipeline, cross-volume series memory.**

[![CI](https://github.com/cesabici-bit/comicast/actions/workflows/ci.yml/badge.svg)](https://github.com/cesabici-bit/comicast/actions/workflows/ci.yml)
![status](https://img.shields.io/badge/status-alpha-orange)
![python](https://img.shields.io/badge/python-3.12%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)](CONTRIBUTING.md)
[![Code of Conduct](https://img.shields.io/badge/Code%20of%20Conduct-Contributor%20Covenant-blueviolet)](CODE_OF_CONDUCT.md)

> ⚠️ **Alpha.** Phase 1 (cloud TTS via ElevenLabs library voices) is end-to-end working and validated on a 25-page real-input dry run. Audio quality is **broadcaster-grade, not actor-grade** — see the [Roadmap](#roadmap) for the 3-tier path to actor-grade output.

---

## What it does

Comicast turns a digital comic (`.cbz` / `.cbr` / `.pdf`) into an MP3/M4B audiobook where **each character has their own voice**, lines are recited in the right reading order, and the narration adapts to the panel context (panic, whisper, monologue, action). The pipeline is interactive: a human-in-the-loop reviews any low-confidence VLM decisions, and those corrections feed a per-series memory (`series_profile.json`) that **gets better the more volumes you process**.

```
input.cbz/cbr/pdf
       │
       ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  1. EXTRACT     │  │  2. VISION      │  │  3. DIRECTION   │  │  4. TTS+STITCH  │
│  pages, panels  │─▶│  3-pass VLM:    │─▶│  emotion tags + │─▶│  ElevenLabs v3  │
│  bubbles (OCR)  │  │  cast / attrib  │  │  voice mapping  │  │  → MP3 / M4B    │
│                 │  │  / narrative    │  │  (HITL review)  │  │  with chapters  │
└─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────────┘
                              │
                              └──▶ series_profile.json (in-context learning across volumes)
```

## Why this is interesting

Reading a comic is a **visual** experience — text-to-speech tools (Audible, ElevenLabs Reader, Speechify) handle prose books but break on comics, because attribution requires *visual understanding* (which bubble belongs to whom, in which panel, with what tone), not just NLP. Comicast is — to our knowledge — the first end-to-end pipeline that combines:

- **3-pass VLM attribution** (cast extraction → per-page attribution → narrative consistency check)
- **Confidence-gated HITL** (the human only reviews the cases the model is unsure about)
- **Cross-volume series memory** (`series_profile.json`) that accumulates voice mappings, character archetypes, and recurring corrections
- **Cost-bounded budget guard** with hard ceilings per stage

The closest direct prior work is [arXiv 2509.15253](https://arxiv.org/abs/2509.15253) (Sept 2025), which reports 64.8% attribution accuracy with **no HITL and no public release**. Comicast trades raw automation for higher final quality via interactive review.

## Status & honest limitations

| | |
|---|---|
| **Phase 1 (this repo)** | end-to-end working, dry-run validated 2026-05-06 (Invincible Vol 2 ch.1, 25 pages, 18 min audio) |
| **Audio quality (current)** | broadcaster-grade voices from ElevenLabs Starter library — clear and intelligible, but not theatrical performance |
| **What's next** | F4 Tier-1 audio enrichment (emotion tag expansion, voice slider tuning, SFX layer, music bed) — see [Roadmap](#roadmap) |

The portfolio value of this project is the **pipeline pattern** (HITL + self-improving cross-volume memory + confidence gating), not the absolute audio quality. Tier-1 polish lifts perceived quality to ~6/10; theatrical-grade audio (>8/10) requires Tier-2 voice cloning of real actors and is intentionally Phase 2 / personal-use only.

## Quickstart

### 1. Clone and install

```bash
git clone https://github.com/cesabici-bit/comicast.git
cd comicast
make install
```

This creates `.venv/` and installs Comicast plus dev tooling.

### 2. Install OS-level binaries

Comicast needs `poppler` (PDF input) and `unrar` (CBR input) — see [System dependencies](#system-dependencies) below for platform-specific instructions.

### 3. Configure API keys

Comicast needs **two API keys** (Anthropic for VLM, ElevenLabs for TTS). Copy the template and fill in real keys:

```bash
cp .env.example .env
# edit .env, set ANTHROPIC_API_KEY and ELEVENLABS_API_KEY
```

`.env` is gitignored. The CLI loads it automatically via `python-dotenv` at startup.

> **Windows note:** do **not** set the keys as User-scope environment variables — they collide with Claude Code's Max OAuth, which prefers `ANTHROPIC_API_KEY` over OAuth when present. Use `.env` instead.

### 4. Run

You provide your own legally-acquired comic file (Comicast does not distribute any comic content):

```bash
.venv/Scripts/comicast process path/to/your-comic.cbz --series your-series-name
```

(On Linux/macOS, replace `.venv/Scripts/` with `.venv/bin/`.)

The CLI walks you through:
1. Stage 1: extract pages
2. Stage 2: 3-pass VLM (cast → attribute → narrative)
3. Stage 3: HITL review of low-confidence decisions
4. Stage 4: TTS synthesis + MP3/M4B stitching

Each stage is **idempotent** — rerun with `--force` to redo a specific stage. TTS clips persist incrementally, so a crash post-synthesis costs nothing on retry.

### 5. Run tests without API keys

The full unit + integration suite uses synthetic fixtures (`tests/fixtures/synth_3pages.{pdf,cbz}`) and mocks the Anthropic / ElevenLabs clients. No keys needed:

```bash
make test
make check-all   # types + lint + test + deps-verify
```

## System dependencies

Beyond the Python packages in `pyproject.toml`, the extraction tier needs these **OS-level binaries**:

- **Poppler** (required for PDF input via `pdf2image`)
  - **Windows:** download `oschwartz10612/poppler-windows` v25.12.0-0+ from <https://github.com/oschwartz10612/poppler-windows/releases/latest>, extract, then either add the `Library\bin` directory to `PATH` or pass `poppler_path=r"...\Library\bin"` to `convert_from_path`.
  - **Linux (Debian/Ubuntu):** `sudo apt-get install poppler-utils`
  - **macOS:** `brew install poppler`
  - **Cross-platform:** `conda install -c conda-forge poppler`
- **unrar** (required for CBR input via `rarfile` — preferred backend)
  - **Windows:** download `UnRAR.exe` from <https://www.rarlab.com/rar_add.htm>, then either add it to `PATH` or set `rarfile.UNRAR_TOOL = r"C:\path\to\UnRAR.exe"` programmatically.
  - **Linux (Debian/Ubuntu):** `sudo apt-get install unrar` (may require `multiverse` repo)
  - **macOS:** `brew install unrar`
- **bsdtar** (optional fallback for CBR; image-only single-volume archives only)
  - **Windows:** already shipped with Git for Windows at `C:\Program Files\Git\usr\bin\bsdtar.exe`. Set `rarfile.BSDTAR_TOOL = r"..."` to use it.
  - **Linux (Debian/Ubuntu):** `sudo apt-get install libarchive-tools`
  - **macOS:** `brew install libarchive`

If a binary is missing at runtime, Comicast fails fast with a typed exception (`pdf2image.exceptions.PDFInfoNotInstalledError` for Poppler, `rarfile.RarCannotExec` for the RAR family) — no silent fall-through.

## Architecture

```
src/comicast/
├── cli.py              # main orchestrator (4 stages, idempotent, --force per-stage)
├── extract.py          # CBZ / CBR / PDF → page PNGs
├── vision/
│   ├── cast.py         # pass 1: cast extraction (whole-volume)
│   ├── attribute.py    # pass 2: per-page bubble attribution
│   ├── narrative.py    # pass 3: cross-page narrative consistency
│   └── confidence.py   # confidence threshold gating
├── voice/
│   └── director.py     # emotion tags + voice slider tuning
├── tts.py              # ElevenLabs v3 synthesis (concurrent, idempotent)
├── stitch.py           # clip → MP3 (tolerant decode, silence placeholder)
├── m4b.py              # MP3 → M4B with chapter offsets
├── profile.py          # series_profile.json CRUD + in-context learning
├── review.py           # HITL CLI for low-confidence cases
├── voice_assign.py     # interactive voice assignment per character
├── learn.py            # post-run learning loop (corrections.jsonl → series_profile)
├── budget.py           # cost ceiling guard
├── elevenlabs_client.py / anthropic_client.py
└── schemas.py          # Pydantic schemas (frozen, byte-stable)
```

Anti-hallucination architecture: every dependency in [`verified-deps.toml`](verified-deps.toml) is web-verified (version, doc URL, methods used). Every non-trivial test cites a `# SOURCE:` for the expected value (Anthropic docs, ElevenLabs v3 reference, etc.). The four research notes in [`docs/research/`](docs/research/) document the SDK / market analysis underpinning the design.

## Roadmap

Phase 1 (this repo) is the foundation. The path to higher audio quality is layered:

| Tier | What | Quality ceiling | Status |
|---|---|---|---|
| **Tier 0** | ElevenLabs library voices + minimal tags | ~3/10 ("broadcaster-grade") | ✅ landed (current) |
| **Tier 1** | Tag taxonomy expansion + voice slider tuning + SFX layer (Freesound CC0) + music bed (Incompetech CC-BY) + adaptive pauses | ~6/10 ("indie audiobook") | 🚧 F4 next |
| **Tier 2** | Voice cloning of real actors (5-30 min training clips) — Phase 2, personal-use only (legal posture: cloning celebrity voices is non-commercial) | ~7-8/10 ("Audible Premium") | planned |
| **Tier 3** | Hybrid: TTS for minor characters + real voice actors for protagonists (publishable demo on public-domain or Creative Commons comics) | ~9/10 | planned |

## Development

```bash
make help            # list all targets
make install         # set up venv + dev deps
make check-all       # ruff + mypy + pytest + verified-deps check
make smoke           # E2E mocked smoke test (no API keys)
```

## Contributing

Contributions are very welcome — Comicast is alpha and there's plenty to do. Please read [`CONTRIBUTING.md`](CONTRIBUTING.md) for the development setup, testing conventions, and PR process. Participation is governed by the project's [Code of Conduct](CODE_OF_CONDUCT.md).

For larger ideas (architecture changes, new pipeline stages, Phase 2 / 3 design), please open a [Discussion](https://github.com/cesabici-bit/comicast/discussions) before code.

For security-sensitive findings, please use a [private Security Advisory](https://github.com/cesabici-bit/comicast/security/advisories/new) — see [`SECURITY.md`](SECURITY.md).

## Citing

If you reference Comicast in academic or industry work, see [`CITATION.cff`](CITATION.cff) — GitHub renders a "Cite this repository" button on the project page.

## Acknowledgments

Comicast was built with the assistance of [Claude Code](https://claude.com/claude-code) (Anthropic). Most commits are co-authored by Claude — see commit log.

## Legal

This repo distributes **code only**, not audio. **You provide your own legally-acquired comics.** Generated audio is for **personal use** (analogous to making an audiobook of a CD you own); we do not distribute generated audio of copyrighted works.

The Phase 2 voice cloning pipeline (planned) is non-commercial by design — cloning celebrity voices without permission is for personal listening only, never for distribution or sale. The publishable demo (Tier 3) will use public-domain or Creative Commons comics with hired voice actors.

## License

[MIT](LICENSE) © 2026 cesabici-bit
