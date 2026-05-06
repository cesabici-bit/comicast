# Security Policy

## Supported versions

Comicast is in **alpha** (pre-1.0). Only the `main` branch is supported; there are no point releases yet.

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security-sensitive findings.

Instead, open a [private GitHub Security Advisory](https://github.com/cesabici-bit/comicast/security/advisories/new). This is a built-in GitHub feature that lets you report privately to the maintainer.

Please include:

- A description of the issue and its potential impact.
- Steps to reproduce, or a proof-of-concept if you have one.
- The version / commit hash you tested against.
- Any suggested mitigations, if you have ideas.

You can expect an initial acknowledgement within 7 days. We aim to release fixes for confirmed vulnerabilities within 30 days, depending on severity and complexity.

## Scope

In scope:

- Comicast source code in this repository.
- Build / dependency configuration (`pyproject.toml`, `verified-deps.toml`, `.pre-commit-config.yaml`, `.github/workflows/`).

Out of scope:

- Third-party services Comicast integrates with (Anthropic, ElevenLabs) — please report those upstream.
- The user's local API keys, `.env` files, or generated audio output (these never leave the user's machine and are not part of this repository).
- Issues in external dependencies; please report those to the upstream project. We will track and update via Dependabot.

## Disclosure policy

We follow a coordinated disclosure model. Once a fix has been released and users have had a reasonable window to update, we will publish the security advisory with credit to the reporter (unless they prefer to remain anonymous).

Thanks for helping keep Comicast and its users safe.
