"""Verify that verified-deps.toml is consistent with installed packages.

M1 mechanism: every dep in verified-deps.toml must be installed at the
declared version (or compatible). Fails CI if drift is detected.
"""

from __future__ import annotations

import sys
import tomllib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[3]
    deps_file = repo_root / "verified-deps.toml"
    if not deps_file.exists():
        print(f"ERROR: {deps_file} not found", file=sys.stderr)
        return 1
    with deps_file.open("rb") as f:
        data = tomllib.load(f)

    deps: list[dict[str, str]] = data.get("dependency", [])
    if not deps:
        print("WARN: no dependencies registered (F1 not yet completed)")
        return 0

    failures: list[str] = []
    for dep in deps:
        name = dep["name"]
        expected = dep["version"]
        try:
            installed = version(name)
        except PackageNotFoundError:
            failures.append(f"{name}: NOT INSTALLED (expected {expected})")
            continue
        # Accept any installed version in the same major line (pyproject uses >=X.Y pins)
        if installed.split(".")[0] != expected.split(".")[0]:
            failures.append(
                f"{name}: major version drift (installed={installed}, declared={expected})"
            )
        else:
            print(f"  OK  {name} {installed} (declared {expected})")

    if failures:
        print("\nFAILURES:", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 1

    print(f"\nAll {len(deps)} verified deps OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
