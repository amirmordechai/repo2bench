#!/usr/bin/env python3
"""Verify syntax and git diff of modified Python files in /workspace."""
import ast
import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path("/workspace")
    diff_files = subprocess.check_output(
        ["git", "diff", "--name-only"], cwd=root, text=True
    ).splitlines()
    for rel in diff_files:
        p = root / rel
        if p.is_file() and p.suffix == ".py":
            try:
                ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
                print(f"[OK] Syntax valid: {rel}")
            except SyntaxError as exc:
                print(f"[ERROR] Syntax error in {rel}: {exc}", file=sys.stderr)
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

