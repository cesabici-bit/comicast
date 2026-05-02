"""Verify that verified-deps.toml is consistent with pyproject.toml.

Pre-F1 stub: just confirms the file exists. F1/T09 expands this to
match each [[dependency]] entry against installed packages.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[3]
    deps_file = repo_root / "verified-deps.toml"
    if not deps_file.exists():
        print(f"ERROR: {deps_file} not found", file=sys.stderr)
        return 1
    with deps_file.open("rb") as f:
        data = tomllib.load(f)
    print(f"verified-deps.toml loaded. last_verified={data.get('last_verified')}")
    deps = data.get("dependency", [])
    print(f"  {len(deps)} dependencies registered")
    return 0


if __name__ == "__main__":
    sys.exit(main())
