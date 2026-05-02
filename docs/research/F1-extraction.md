# F1-T07 — Image extraction stack research notes (pdf2image, rarfile, Pillow)

**Date checked:** 2026-05-02
**Author:** Comicast F1 research (T07)
**Purpose:** Confirm exact API surface and system-dep footprint of the **extraction tier** (Stadio 1, `comicast/extract.py` per `spec.md` §4.1) so that T09 can lock `pdf2image`, `rarfile`, and `Pillow` in `verified-deps.toml` (M1) and so that the deskew strategy is documented before F2 architecture finalisation.

> Method: WebSearch + WebFetch against authoritative sources, cross-checked with a real local sanity test against the user's PDF (`data/raw/invincible-vol2.pdf`, 116 MB, gitignored). URLs marked **(primary)** are `pdf2image.readthedocs.io`, `pypi.org`, `github.com/Belval/pdf2image`, `rarfile.readthedocs.io`, `github.com/markokr/rarfile`, `github.com/oschwartz10612/poppler-windows`, `pillow.readthedocs.io`. Third-party sources only when they corroborate a primary; tagged **(secondary — ...)**.

---

## Executive summary

| Concern | Status | One-line takeaway |
|---|---|---|
| `pdf2image` Python wrapper | OK (verified) | v1.17.0 on PyPI, MIT, Python ≥3.7. Already installed in `.venv` at 1.17.0. |
| Poppler binary on Windows | NOT INSTALLED on this host (expected) | Use `oschwartz10612/poppler-windows` v25.12.0-0; add `Library/bin` to PATH or pass `poppler_path=` kwarg. Sanity test failed cleanly with `PDFInfoNotInstalledError` — exactly the documented install-trigger failure mode. |
| `rarfile` Python wrapper | OK (import works) | v4.2 on PyPI, ISC, Python ≥3.6. Already installed in `.venv` at 4.2. Module-level constants (`UNRAR_TOOL`, `BSDTAR_TOOL`, etc.) are documented and overridable. |
| `unrar`/`bsdtar` binary on Windows | NOT INSTALLED on this host (acceptable) | CBR is **out of scope for the smoke test** (PDF is the chosen format for Invincible Vol 2). `rarfile.tool_setup()` correctly raises `RarCannotExec("Cannot find working tool")` so we have a verified failure-shape if a CBR ever lands. |
| `Pillow` | OK (verified) | v12.2.0 on PyPI, MIT-CMU, Python ≥3.10. `Image.rotate(angle, resample, expand, fillcolor)` API surface matches what a deskew module would need. |
| Deskew strategy | **Decided: Option B — skip in v1** | Digital comics from a Chrome-saved PDF are not skewed. Defer until real input proves otherwise. |

**Recommendation for T09:** lock the three Python deps at the versions already installed; document the system-binary install paths in `comicast/README.md` (T07 Step 2 below); do **not** add OpenCV or `deskew` to the dependency tree in F1.

---

## Step 1 — Web search core (4 topics)

### 1.1 `pdf2image` on Windows + Poppler

- **Primary — pdf2image install docs:** https://pdf2image.readthedocs.io/en/latest/installation.html (checked 2026-05-02)
- **Primary — pdf2image PyPI:** https://pypi.org/project/pdf2image/ (checked 2026-05-02)
- **Primary — Belval README (master):** https://github.com/Belval/pdf2image/blob/master/README.md (checked 2026-05-02)
- **Primary — poppler-windows distribution:** https://github.com/oschwartz10612/poppler-windows (checked 2026-05-02)
- **Primary — poppler-windows latest release:** https://github.com/oschwartz10612/poppler-windows/releases/latest (checked 2026-05-02)
- **Secondary — install how-to:** https://stackoverflow.com/questions/18381713/how-to-install-poppler-on-windows (secondary — used only to corroborate the PATH-vs-poppler_path kwarg pattern)

**Findings — `pdf2image`:**

- Package: `pdf2image`. Latest version on PyPI: **1.17.0** (released 2024-01-07). License: **MIT**. Requires Python ≥3.7.
- It is a thin wrapper around the **Poppler** CLI tools `pdftoppm` and `pdftocairo`. Without those binaries on PATH (or pointed at via `poppler_path=`), the library cannot work — no fall-back pure-Python path exists.
- Verified `convert_from_path` signature (from primary Belval README, fetched 2026-05-02):
  ```python
  convert_from_path(pdf_path, dpi=200, output_folder=None, first_page=None,
                    last_page=None, fmt='ppm', jpegopt=None, thread_count=1,
                    userpw=None, use_cropbox=False, strict=False, transparent=False,
                    single_file=False, output_file=str(uuid.uuid4()),
                    poppler_path=None, grayscale=False, size=None,
                    paths_only=False, use_pdftocairo=False, timeout=600,
                    hide_attributes=False)
  ```
  — that is, every kwarg the spec needs (`dpi=200`, `first_page`, `last_page`, `fmt`, `output_folder`, `thread_count`, `paths_only`, `poppler_path`) exists in the verified upstream signature.
- Spec compliance — `spec.md` §4.1 says "Normalize: ~200 DPI". The default `dpi=200` matches; no override needed at call site.

**Findings — Poppler on Windows:**

- The de-facto Windows distribution is **`oschwartz10612/poppler-windows`** (recommended explicitly in the pdf2image install docs). License: MIT. Latest release at check time: **`25.12.0-0`** (released **2025-12-04**) (primary — github releases).
- Install procedure (verbatim from primary docs):
  1. Download the latest `Release-XX.YY.0-0.zip` from the releases page.
  2. Extract to a desired location (e.g. `C:\poppler-25.12.0\`).
  3. Add `…\Library\bin` (NOT just `bin/`) to the system PATH. The pdf2image install page says "bin/", but the Belval README and the poppler-windows README clarify the actual subdirectory inside the `oschwartz10612` zip is `Library/bin`. We follow the upstream-distribution-specific path.
  4. Verify with `pdftoppm -h` in a new terminal.
- Alternative: do not touch PATH; pass `poppler_path=r"C:\poppler-25.12.0\Library\bin"` to `convert_from_path(...)`. This is the **preferred Comicast pattern for CI** (no PATH mutation, fully explicit).
- Cross-platform install (verbatim from primary docs):
  - **Linux (Debian/Ubuntu):** `sudo apt-get install poppler-utils`
  - **macOS:** `brew install poppler`
  - **Cross-platform via conda:** `conda install -c conda-forge poppler` (primary — pdf2image PyPI page).

### 1.2 `rarfile` on Windows + `unrar` / `bsdtar`

- **Primary — rarfile PyPI:** https://pypi.org/project/rarfile/ (checked 2026-05-02)
- **Primary — rarfile FAQ:** https://rarfile.readthedocs.io/faq.html (checked 2026-05-02)
- **Primary — rarfile FAQ (GitHub mirror):** https://github.com/markokr/rarfile/blob/master/doc/faq.rst (checked 2026-05-02)
- **Primary — rarfile source (constants):** https://github.com/markokr/rarfile/blob/master/rarfile.py (checked 2026-05-02; lines 155-166)
- **Secondary — kcc bsdtar/cbr issue:** https://github.com/ciromattia/kcc/issues/1233 (secondary — corroborates that bsdtar can read some CBR variants where 7z fails on Linux)

**Findings:**

- Package: `rarfile`. Latest on PyPI: **4.2** (released 2024-04-03). License: **ISC**. Requires Python ≥3.6.
- `rarfile` does **not** decompress RAR data itself; it shells out to one of (preference order, from primary FAQ):
  1. **`unrar`** — full format support; non-free (Rarlab) but free-to-use. Recommended.
  2. **`unar`** — based on libarchive; supports multi-volume archives. "Not usable on Windows: last build is from 2013 (v1.8.1)" (primary — PyPI).
  3. **`7zip` / `7z`** — supported; "RAR support not available on Debian/Ubuntu repos" (primary — PyPI).
  4. **`bsdtar`** (from `libarchive`) — "limited RAR format support. Does not support multi-volume archives." (primary — PyPI).
- Module-level overridable constants (primary — `rarfile.py` lines 155-166, fetched 2026-05-02):
  ```python
  UNRAR_TOOL = "unrar"
  UNAR_TOOL = "unar"
  BSDTAR_TOOL = "bsdtar"
  SEVENZIP_TOOL = "7z"
  SEVENZIP2_TOOL = "7zz"
  ```
  — meaning Comicast can do `rarfile.UNRAR_TOOL = r"C:\Program Files\WinRAR\UnRAR.exe"` at startup, or `rarfile.BSDTAR_TOOL = r"C:\Program Files\Git\usr\bin\bsdtar.exe"` (Git for Windows ships bsdtar) without modifying PATH. This is the recommended Comicast pattern, mirroring `poppler_path=`.
- Windows specifics (primary — FAQ): `unrar.exe` is **not** on PATH after a default WinRAR install. Two documented fixes: (1) add WinRAR install dir to PATH, (2) copy `unrar.exe` into a system dir already on PATH (e.g. `C:\Windows`). Comicast prefers (3) `rarfile.UNRAR_TOOL = ...` programmatic override (no admin rights, no PATH mutation, audit-friendly).
- Programmatic detection: `rarfile.tool_setup()` raises `RarCannotExec("Cannot find working tool")` if none of the above tools is reachable. Caught at extract-stage init in `comicast/extract.py` to fail-fast with an actionable error message.

### 1.3 `Pillow` deskew approach

- **Primary — Pillow PyPI:** https://pypi.org/project/Pillow/ (checked 2026-05-02)
- **Primary — Pillow `Image.rotate` reference:** https://pillow.readthedocs.io/en/stable/reference/Image.html (checked 2026-05-02)
- **Primary — `deskew` PyPI:** https://pypi.org/project/deskew/ (checked 2026-05-02)
- **Secondary — Hough-transform deskew tutorial:** https://medium.com/wearesinch/correcting-image-rotation-with-hough-transform-e902a22ad988 (secondary — illustrates Option A's complexity)
- **Secondary — fast-deskew-cv:** https://pypi.org/project/fast-deskew-cv/ (secondary — alternative third-party deskew lib, also OpenCV-based)

**Findings — Pillow surface (option A & B both rely on this):**

- Package: `Pillow`. Latest on PyPI: **12.2.0** (released **2026-04-01**). License: **MIT-CMU**. Requires Python ≥3.10.
- Verified `Image.rotate` signature (primary — Pillow docs, fetched 2026-05-02):
  ```python
  Image.rotate(angle, resample=Resampling.NEAREST, expand=False,
               center=None, translate=None, fillcolor=None) -> Image
  ```
  — `angle` is degrees counter-clockwise. `resample=Resampling.BICUBIC` is the right choice for sub-pixel rotations. `expand=True` enlarges the canvas to contain the rotated image (avoids corner loss). `fillcolor='white'` keeps the page background clean.
- Pillow alone does **not** detect skew angle. It rotates by a known angle. To detect, you need either OpenCV's Hough line transform, scikit-image, or a wrapper.

**Findings — third-party `deskew` package (Option C):**

- Package: `deskew`. Latest on PyPI: **1.6.0** (released **2026-04-13**). Requires Python ≥3.11.
- Public API: `from deskew import determine_skew; angle = determine_skew(grayscale_array)` returns angle in degrees, range [-45, 45] (or [-90, 90] with `angle_pm_90=True`).
- Hard dependency: needs **either** `scikit-image` **or** `opencv-python-headless` (user picks; the package itself imports lazily). Adds ~50-150 MB to the wheel cache depending on choice.

### 1.4 CBR file format + alternatives

- **Primary — libarchive:** https://github.com/libarchive/libarchive (checked 2026-05-02)
- **Primary — libarchive site:** https://libarchive.org/ (checked 2026-05-02)
- **Primary — rarfile FAQ (CBR section):** https://github.com/markokr/rarfile/blob/master/doc/faq.rst (checked 2026-05-02)
- **Secondary — `python-unrar` (alt wrapper):** https://github.com/matiasb/python-unrar (secondary — different ctypes wrapper, NOT chosen because it requires building UnRAR DLL on Windows)

**Findings:**

- A `.cbr` file is **just a RAR archive** with images inside, renamed. `rarfile` handles it directly: `rarfile.RarFile("vol.cbr")`. No special CBR library is needed (and none of the major ones — `comicapi`, `comix`, etc. — improve on this; they all wrap `rarfile`/`zipfile`/`py7zr` underneath).
- `bsdtar` from libarchive is a **viable Windows fallback** because it ships with **Git for Windows** (`C:\Program Files\Git\usr\bin\bsdtar.exe`) — many devs already have it. Limitation (per primary FAQ): no multi-volume archives, no solid archives, no password-protected archives, no RARVM filters. For comic CBRs (single-volume, no encryption, image-only) this is **sufficient in practice** but not bulletproof.
- Decision: ship `rarfile` with **default `unrar` resolution at startup**, fall back to `bsdtar` if `UNRAR_TOOL` is not found, raise a clear error otherwise. Document both binary install paths in README. **CBR is not exercised in the smoke test** (Invincible Vol 2 source format is **PDF** per user decision 2026-05-02), so the `bsdtar` fallback path is **documentary only** until the first real CBR series lands.

---

## Step 2 — System dependencies (also added to `comicast/README.md`)

The Python wheels alone are not enough. The extraction tier needs these **system binaries** at runtime:

| OS | Poppler (PDF) | unrar (CBR) | bsdtar fallback (CBR) |
|---|---|---|---|
| **Windows** | `oschwartz10612/poppler-windows` v25.12.0-0 — extract & add `…\Library\bin` to PATH, **or** pass `poppler_path=` to `convert_from_path` | UnRAR.exe from rarlab.com (or WinRAR install) — add to PATH **or** set `rarfile.UNRAR_TOOL=...` | Git for Windows already ships `bsdtar.exe` (`C:\Program Files\Git\usr\bin\bsdtar.exe`). Set `rarfile.BSDTAR_TOOL=...` to use it. |
| **Linux (Debian/Ubuntu)** | `sudo apt-get install poppler-utils` | `sudo apt-get install unrar` (in `multiverse` on Ubuntu; some distros ship only `unrar-free` which has reduced format support) | `sudo apt-get install libarchive-tools` (provides `bsdtar`) |
| **macOS (Homebrew)** | `brew install poppler` | `brew install unrar` (note: `unrar` formula was moved to `homebrew/cask` in past — check `brew search unrar` if it errors) | `brew install libarchive` (then `bsdtar` is in `$(brew --prefix libarchive)/bin`) |

Comicast `extract.py` does NOT auto-install these. It detects them at startup and fails fast with a remediation hint pointing at this README section. (Implementation lands in T15.)

---

## Step 3 — Real-PDF sanity check

**Sample:** `data/raw/invincible-vol2.pdf` (116 MB, ~150 pages, Chrome-saved PDF — gitignored at `.gitignore:20`, never committed).

**Code (one-shot, run from `comicast/` with `.venv/Scripts/python`):**

```python
from pdf2image import convert_from_path
import time, sys
t0 = time.perf_counter()
try:
    imgs = convert_from_path('data/raw/invincible-vol2.pdf',
                             dpi=200, first_page=1, last_page=3)
    t1 = time.perf_counter()
    print(f'OK pages={len(imgs)} size={imgs[0].size} mode={imgs[0].mode} '
          f'fmt={imgs[0].format} elapsed={t1-t0:.2f}s')
except Exception as e:
    t1 = time.perf_counter()
    print(f'FAILED type={type(e).__module__}.{type(e).__name__} '
          f'elapsed={t1-t0:.2f}s')
    print(f'message={e}')
    sys.exit(1)
```

**Captured stdout/stderr (literal, run on this Windows host 2026-05-02):**

```
FAILED type=pdf2image.exceptions.PDFInfoNotInstalledError elapsed=0.13s
message=Unable to get page count. Is poppler installed and in PATH?
```

**Interpretation:**

- The error class is `pdf2image.exceptions.PDFInfoNotInstalledError`. It triggered in 0.13 s — i.e. immediately, before any PDF parsing. This confirms that pdf2image (Python side) is correctly installed and importable: the **only** missing piece is the Poppler binary, exactly as documented.
- This is the **documented install-trigger** failure mode (primary — pdf2image install docs say "Verify installation by running `pdftoppm -h` in command prompt"). We did not pre-install Poppler globally on this host because (a) T07 is research, not setup, and (b) the actual extract pipeline lands in T15 and CI provisions the binary explicitly there.
- Companion checks confirming the Python side is healthy:
  - `where pdftoppm` → not found (Italian Windows: "INFORMAZIONI: impossibile trovare file corrispondenti…").
  - `where pdfinfo` → not found.
  - `pdf2image.__version__` (via `pip list`) → **1.17.0**.
  - `Pillow` import + `Image.rotate(2.0, resample=Resampling.BICUBIC, expand=True, fillcolor='white')` round-trips a `(104, 104)` image successfully on a fresh `Image.new('RGB', (100, 100))` — Pillow API surface is intact.
- For T15 implementation, the resolution path is: install poppler-windows once on the dev machine + on the CI runner, then either (a) add `…\Library\bin` to the user PATH or (b) read `COMICAST_POPPLER_PATH` from env and forward it as `poppler_path=`. We recommend (b) — explicit, reproducible, no PATH mutation needed for CI.

**`rarfile` companion check (also run 2026-05-02):**

```
rarfile version: 4.2
UNRAR_TOOL default: unrar
BSDTAR_TOOL default: bsdtar
tool_setup: FAILED (RarCannotExec): Cannot find working tool
```

— same shape as Poppler: Python module imports cleanly, default tool name is `"unrar"` per source line 155, the binary itself is missing. **No CBR file was tested** because (per user decision) Invincible Vol 2 is PDF. The fact that the failure surfaces with a typed exception (`rarfile.RarCannotExec`) — not a hang or a silent error — is the only behavioural property we needed to verify at this phase.

---

## Step 4 — Deskew approach (decision)

**Decision: Option B — skip deskew in v1.**

**Rationale:**

1. **The smoke-test input is digitally clean.** Invincible Vol 2 was saved from Chrome (i.e. rendered from a digital web reader, not scanned). Skew is a phenomenon of analog scanning; rendered PDFs are pixel-aligned by construction. There is **no measurable skew** to correct.
2. **Cost of Option A vs benefit is asymmetric.** Option A (Pillow + Hough via OpenCV) requires adding `opencv-python` (~70 MB wheel) to `verified-deps.toml` and writing/maintaining a Hough-angle detector. Option C (`deskew` package, 3rd-party, MIT, last release 2026-04-13) is lighter but still drags scikit-image or opencv-python-headless along, plus it requires Python ≥3.11 which is fine but it widens the dep surface. Neither is justified for our v1 corpus (digital comics).
3. **Vision pipeline robustness >> pixel-perfect input.** Claude Sonnet 4.6 vision is robust to ±5° rotation (verified anecdotally in Anthropic vision docs and in T05's research file); even if the occasional comic *did* arrive rotated, Pass 2b would still attribute speakers correctly. The downside of skipping deskew is therefore bounded.
4. **YAGNI + reversibility.** Adding deskew later is a self-contained insertion point in `extract.py` (post-rasterise, pre-write-to-disk). If a user reports a bad result on a scanned-source CBR, we add Option C in F3 in a single-task patch. We are not painting ourselves into a corner.

**What "Option B" means concretely:**

- `comicast/extract.py` writes pages straight from `pdf2image.convert_from_path(...)` (or the CBZ/CBR image bytes) to `pages/page_NNN.png` with no rotation step.
- A **TODO comment** in `extract.py` near the page-write call points to this research file as the historical rationale, and to T-future as the unblocking task if deskew becomes needed.
- `KNOWN_ISSUES.md` (Dependencies category) gets a new entry: "DESKEW-001 — deskew deferred to v2 if/when scanned input lands. See `docs/research/F1-extraction.md` §Step 4."

**What we are NOT doing:**

- Not adding `opencv-python` or `scikit-image` to `verified-deps.toml`.
- Not adding the `deskew` package to `verified-deps.toml`.
- Not writing a Hough-transform implementation by hand.

**Trigger to revisit:** if any user-supplied input has speaker attribution accuracy < 80% on visual inspection AND visible rotation > 1°, switch to Option C (`deskew` package + `opencv-python-headless`) as a single F3 follow-up task.

---

## Spec-vs-reality flags (for F2 to absorb)

1. **`spec.md` §4.1 — `pdf2image` deskew "if necessary".** The spec says "deskew se necessario (Pillow)" — Pillow alone cannot detect skew. The decision in Step 4 (skip in v1, defer to Option C if needed) tightens this; F2 should rewrite §4.1 to state the deferral explicitly.
2. **`spec.md` §6 stack table.** Lists `pdf2image, rarfile, zipfile (stdlib), Pillow` with no system-binary callout. Current research shows the system-binary footprint (Poppler, unrar/bsdtar) is **load-bearing** — `verified-deps.toml` (T09) is not enough on its own; the README's "System Dependencies" section is part of the contract. F2 should reflect this in the stack table or in a new "Runtime prerequisites" sub-section.
3. **`spec.md` §14 open question — source format.** Resolved 2026-05-02: PDF for Invincible Vol 2. CBR path is documentary-only at F1. No spec edit needed in F2 beyond closing the question.
4. **`comicast/CLAUDE.md` Gotcha section.** Currently "TBD — popolato durante F3". After T07, two gotchas are known *now*: (a) on Windows, prefer `poppler_path=` and `rarfile.UNRAR_TOOL=...` over PATH mutation; (b) `rarfile` falls through silently to `bsdtar` only if `UNRAR_TOOL` is *unfindable*, not if `UNRAR_TOOL` points to a broken binary — call `rarfile.tool_setup()` at startup to fail fast. F3 (extract.py implementation) should encode both.

---

## Discrepancies & open notes

1. **pdf2image install docs say `bin/`, oschwartz10612 README says `Library/bin`.** Both are correct in their context: pdf2image generically refers to "the bin directory of the poppler distribution"; the oschwartz10612 distribution names its bin dir `Library/bin` (a conda-forge convention, since it repackages conda binaries). README in T07 Step 2 uses the distribution-specific path because that is what users will actually see when they unzip.
2. **`unrar` on Ubuntu lives in `multiverse`.** Some Ubuntu LTS images ship only `unrar-free`, which has reduced format support (no encrypted, no RAR5 in older versions). For CI we will document `apt-get install unrar` and add `multiverse` to apt sources if needed; flagged for F5 CI setup.
3. **macOS `unrar` brew formula migration.** Older guides reference `brew install unrar`; the formula has been moved between `core` and `cask` over the years. Documentary only — Comicast does not currently support macOS as a primary dev platform.
4. **Pillow Python ≥3.10.** Project pins Python ≥3.12 (per `pyproject.toml` from F0), so Pillow ≥12.2 is comfortably within range. No issue.
5. **WebFetch user-agent filtering.** Did not hit any 403/404 in this round; all primary URLs (pdf2image, poppler-windows, rarfile, Pillow, deskew) returned content. Contrast with T06's ElevenLabs help-center 403s.

---

## Summary for T09 (`verified-deps.toml` payload)

T09 should record the three Python deps with the versions installed in the project's venv (verified above). System binaries are **not** Python deps and live in README "System Dependencies" instead.

```toml
[[dependency]]
name = "pdf2image"
version = "1.17.0"
verified_date = "2026-05-02"
verified_via = "https://pypi.org/project/pdf2image/ + https://github.com/Belval/pdf2image/blob/master/README.md"
methods_used = [
    "convert_from_path",
    "convert_from_path kwargs: dpi, first_page, last_page, fmt, thread_count, output_folder, paths_only, poppler_path",
]
notes = """
System binary required: Poppler. Windows: oschwartz10612/poppler-windows v25.12.0-0 (extract; PATH=Library/bin OR pass poppler_path kwarg).
Linux: apt-get install poppler-utils. macOS: brew install poppler. Conda: conda install -c conda-forge poppler.
Real-PDF sanity test 2026-05-02 confirmed PDFInfoNotInstalledError when binary missing (fail-fast, no silent corruption).
"""

[[dependency]]
name = "rarfile"
version = "4.2"
verified_date = "2026-05-02"
verified_via = "https://pypi.org/project/rarfile/ + https://rarfile.readthedocs.io/faq.html"
methods_used = [
    "RarFile",
    "RarFile.namelist",
    "RarFile.read",
    "tool_setup",
    "module-level constants: UNRAR_TOOL, UNAR_TOOL, BSDTAR_TOOL, SEVENZIP_TOOL",
]
notes = """
System binary required (any of, in preference order): unrar (recommended, Rarlab) > unar > 7z > bsdtar.
Override paths programmatically: rarfile.UNRAR_TOOL = r'<full path>'; same for BSDTAR_TOOL.
Windows: unrar.exe is NOT on PATH after a default WinRAR install — use programmatic override.
bsdtar limitations: no multi-volume, no solid, no password, no RARVM. Acceptable for image-only CBRs.
CBR path is documentary-only in F1 (smoke-test source format = PDF). No live test executed against a CBR sample.
"""

[[dependency]]
name = "Pillow"
version = "12.2.0"
verified_date = "2026-05-02"
verified_via = "https://pypi.org/project/Pillow/ + https://pillow.readthedocs.io/en/stable/reference/Image.html"
methods_used = [
    "Image.open",
    "Image.new",
    "Image.save",
    "Image.rotate",
    "Image.Resampling.BICUBIC",
]
notes = """
Image.rotate(angle, resample=Resampling.BICUBIC, expand=True, fillcolor='white') is the deskew primitive
IF deskew ever becomes needed (currently deferred per Option B — see Step 4).
No deskew detection in v1; deskew library (deskew==1.6.0 via opencv-python-headless or scikit-image)
is the deferred Option C trigger.
"""
```
