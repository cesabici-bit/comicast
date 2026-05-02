# Comicast

AI-driven audiobook generator for digital comics with per-character voices.

**Status:** Alpha (in development — see `STATUS.md` for current phase).

Full README in T45 (Phase F5).

## System Dependencies

Beyond the Python packages in `pyproject.toml`, the extraction tier needs these **OS-level binaries**. (T45 will polish; this is the F1-T07 minimum viable section.) See `docs/research/F1-extraction.md` for full rationale + sources.

- **Poppler** (required for PDF input via `pdf2image`)
  - Windows: download `oschwartz10612/poppler-windows` v25.12.0-0+ from <https://github.com/oschwartz10612/poppler-windows/releases/latest>, extract, then either add the `Library\bin` directory to `PATH` or pass `poppler_path=r"...\Library\bin"` to `convert_from_path`.
  - Linux (Debian/Ubuntu): `sudo apt-get install poppler-utils`
  - macOS: `brew install poppler`
  - Cross-platform: `conda install -c conda-forge poppler`
- **unrar** (required for CBR input via `rarfile` — preferred backend)
  - Windows: download `UnRAR.exe` from <https://www.rarlab.com/rar_add.htm>, then either add it to `PATH` or set `rarfile.UNRAR_TOOL = r"C:\path\to\UnRAR.exe"` programmatically.
  - Linux (Debian/Ubuntu): `sudo apt-get install unrar` (may require `multiverse` repo)
  - macOS: `brew install unrar`
- **bsdtar** (optional fallback for CBR; image-only single-volume archives only)
  - Windows: already shipped with Git for Windows at `C:\Program Files\Git\usr\bin\bsdtar.exe`. Set `rarfile.BSDTAR_TOOL = r"..."` to use it.
  - Linux (Debian/Ubuntu): `sudo apt-get install libarchive-tools`
  - macOS: `brew install libarchive`

If a binary is missing at runtime, Comicast fails fast with a typed exception (`pdf2image.exceptions.PDFInfoNotInstalledError` for Poppler, `rarfile.RarCannotExec` for the RAR family) — no silent fall-through.

## Legal

This repo distributes **code only**, not audio. Users provide their own legally-acquired comics. Generated audio is for **personal use** (analogous to ripping CDs you own).
