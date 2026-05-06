"""S34 post-patch rerun launcher (Python — no PowerShell quoting hazards).

Usage (from comicast/ directory):
    .venv\\Scripts\\python scripts/rerun_dryrun_post_patch.py

Sets POPPLER_PATH and invokes `comicast process` with --skip-review.
Streams subprocess stdout/stderr live to console.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

POPPLER_PATH = (
    r"C:\Users\cesab\AppData\Local\Microsoft\WinGet\Packages"
    r"\oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\poppler-25.07.0\Library\bin"
)

COMICAST_EXE = ROOT / ".venv" / "Scripts" / "comicast.exe"

ARGS = [
    str(COMICAST_EXE),
    "process",
    r"data\raw\invincible_vol2_ch1.cbz",
    "--series",
    "invincible",
    "--volume",
    "vol_2_ch1",
    "--work-dir",
    r"data\work\dryrun_ch1",
    "--skip-review",
]


def main() -> int:
    env = os.environ.copy()
    env["POPPLER_PATH"] = POPPLER_PATH

    if not COMICAST_EXE.exists():
        print(f"ERROR: comicast.exe not found at {COMICAST_EXE}", file=sys.stderr)
        return 1

    print(f"POPPLER_PATH={POPPLER_PATH}")
    print(f"CWD={ROOT}")
    print(f"CMD={' '.join(ARGS)}")
    print("-" * 60, flush=True)

    proc = subprocess.run(ARGS, env=env, cwd=ROOT)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
