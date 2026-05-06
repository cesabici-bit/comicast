# Contributing to Comicast

Thanks for your interest in helping! Comicast is alpha — there's a lot to do, and outside contributions are welcome.

## Quick orientation

- **Status:** Phase 1 (cloud TTS via ElevenLabs library voices) end-to-end working, dry-run validated. F4 (Tier-1 audio enrichment) is the active milestone.
- **What's interesting:** the pattern (3-pass VLM attribution + confidence-gated HITL + cross-volume series memory + cost-bounded budget guard). See `README.md` for the architecture diagram.
- **What we explicitly *don't* want:** PRs that stretch scope into Phase 2 (voice cloning) or Phase 3 (live reader) — those are intentionally deferred. Read `CHANGELOG.md` for the phase plan.

## Reporting bugs

Open an issue with the **Bug report** template. Include:

- Comicast version (`pip show comicast`)
- Python version + OS
- Reproducer (command + minimal input if possible — synthetic fixtures in `tests/fixtures/` are fair game)
- Expected vs actual output
- Logs (set `COMICAST_LOG_LEVEL=DEBUG` for verbose structlog output)

If it's a **security** issue, please **don't open a public issue** — see [SECURITY.md](SECURITY.md).

## Requesting features

Open an issue with the **Feature request** template. Frame the request around:

1. **The problem** — what user-visible behaviour is wrong / missing today?
2. **Why it matters** — who is blocked, how often, how hard is the workaround?
3. **Sketched solution** — only if you have one. We may suggest a different angle.

For larger ideas (architecture changes, new pipeline stages, etc.), please open a **GitHub Discussion** first instead — that's the right place for shaping a proposal before code.

## Development setup

```bash
git clone https://github.com/cesabici-bit/comicast.git
cd comicast
make install          # creates .venv/, installs package + dev deps
cp .env.example .env  # fill in ANTHROPIC_API_KEY + ELEVENLABS_API_KEY (optional for tests)
```

Install the OS-level binaries listed in `README.md#system-dependencies` (poppler, unrar/bsdtar) if you intend to run the extraction tier.

### Running checks

```bash
make check-all   # ruff + mypy + pytest + verified-deps consistency
make test        # pytest only
make smoke       # E2E mocked smoke test (no API keys needed)
make lint        # ruff check
make format      # ruff format
make types       # mypy strict
```

CI runs `make check-all` on every push and PR. Pre-commit hooks are also configured (`pre-commit install` after `make install`).

### Project conventions

- **Anti-hallucination architecture:** every dependency in `verified-deps.toml` is web-verified (version, doc URL, methods used). PRs that add a dependency must also add or update the corresponding entry. Every non-trivial test cites a `# SOURCE:` for the expected value (Anthropic docs, ElevenLabs v3 reference, etc.).
- **Strict typing:** mypy strict is enforced on `src/`. Tests are not strict-typed but should still pass mypy at default settings.
- **Lint:** ruff with project rules. `pre-commit run --all-files` before pushing avoids surprises.
- **Tests on the boundary:** prefer mocking external services (Anthropic, ElevenLabs) at the SDK boundary. Do not mock the comicast modules themselves.
- **Idempotency:** every pipeline stage must be idempotent; a re-run with the same inputs must produce the same outputs (or skip if outputs already exist). The CLI exposes `--force` per-stage to override.
- **Cost discipline:** any new ElevenLabs / Anthropic call must respect the budget guard (`budget.py`). PRs that bypass it will be asked to integrate.

### Pull request process

1. Fork and create a topic branch (`git checkout -b fix/AAA-123-something-descriptive`).
2. Make the change. Keep the diff focused — one logical change per PR.
3. Add or update tests. Aim to make the failure mode you're fixing (or feature you're adding) explicit in a test.
4. Run `make check-all` locally; CI will run it again on push.
5. Write a clear PR description: what changes, why, how it was verified. Link the issue it closes (`Closes #N`).
6. Be responsive to review. We may ask for changes that look stylistic but are about consistency with the existing codebase — those are usually quick to address.

We **squash-merge** by default. The merge commit message is what becomes the historical record, so PR titles should be self-contained.

## Code of Conduct

Participation in this project is governed by the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By contributing, you agree to abide by it.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE) (the same license as the project).
