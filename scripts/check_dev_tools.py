#!/usr/bin/env python3
"""Doctor for the local lefthook toolchain.

This repository runs its pre-commit / commit-msg checks through lefthook. Those
git hooks only fire after ``lefthook install`` has wired them into
``.git/hooks``, and even then each hook shells out to tools that must already be
on ``PATH`` (ruff, mypy, markdownlint, and commitizen). If lefthook or any of
those tools is missing the local checks are silently skipped on commit, or fail
with a cryptic ``command not found`` -- and the gap only surfaces later in CI.

Run this from the repository root before committing to find what is missing and
exactly how to install it::

    python scripts/check_dev_tools.py

Exit status:
    0  every required tool is present
    1  a required tool, or the installed git hook, is missing

NOTE: the pinned versions in the install hints below mirror ``lefthook.yml``'s
header (the single source of truth). Keep them in sync when a tool is bumped
there.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# Install hints. Versions mirror lefthook.yml's header comment.
BREW_INSTALL = "brew install lefthook commitizen"
PIP_INSTALL = "pip install ruff==0.13.1 mypy==1.18.2"
NPM_INSTALL = "npm install -g markdownlint-cli@0.45.0"
LEFTHOOK_INSTALL = "lefthook install"


class Check:
    """A single tool/state check and the command that fixes it."""

    def __init__(self, name: str, ok: bool, fix: str):
        self.name = name
        self.ok = ok
        self.fix = fix


def _hooks_dir() -> Path | None:
    """Return the directory git uses for hooks, honoring core.hooksPath."""
    try:
        configured = subprocess.run(
            ["git", "config", "--get", "core.hooksPath"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if configured.returncode == 0 and configured.stdout.strip():
            path = Path(configured.stdout.strip())
            return path if path.is_absolute() else (ROOT / path)

        resolved = subprocess.run(
            ["git", "rev-parse", "--git-path", "hooks"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    path = Path(resolved.stdout.strip())
    return path if path.is_absolute() else (ROOT / path)


def _lefthook_hook_installed() -> bool:
    """True when ``lefthook install`` has wired the pre-commit hook in."""
    hooks_dir = _hooks_dir()
    if hooks_dir is None:
        return False
    pre_commit = hooks_dir / "pre-commit"
    if not pre_commit.is_file():
        return False
    try:
        return "lefthook" in pre_commit.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False


def collect_checks() -> list[Check]:
    lefthook_present = shutil.which("lefthook") is not None
    return [
        Check("lefthook", lefthook_present, BREW_INSTALL),
        # Only meaningful once the binary exists; surface the install step
        # regardless so a half-finished setup is obvious.
        Check(
            "lefthook git hooks (lefthook install)",
            lefthook_present and _lefthook_hook_installed(),
            LEFTHOOK_INSTALL,
        ),
        Check("ruff", shutil.which("ruff") is not None, PIP_INSTALL),
        Check("mypy", shutil.which("mypy") is not None, PIP_INSTALL),
        # markdownlint is the markdownlint-cli binary, installed globally via npm.
        Check("markdownlint", shutil.which("markdownlint") is not None, NPM_INSTALL),
        Check("cz (commitizen)", shutil.which("cz") is not None, BREW_INSTALL),
    ]


def _fix_lines(missing: list[Check]) -> list[str]:
    """Unique fix commands, preserving first-seen order."""
    seen: list[str] = []
    for check in missing:
        if check.fix not in seen:
            seen.append(check.fix)
    return seen


def main() -> int:
    checks = collect_checks()

    print("lefthook toolchain:")
    for check in checks:
        mark = "OK  " if check.ok else "MISS"
        print(f"  [{mark}] {check.name}")
    print()

    missing = [c for c in checks if not c.ok]
    if missing:
        print("Missing required tooling. Install with:")
        for line in _fix_lines(missing):
            print(f"  {line}")
        print()
        print("Dev tooling check FAILED. See the commands above.")
        return 1

    print("All dev tooling present. Local lefthook checks will run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
