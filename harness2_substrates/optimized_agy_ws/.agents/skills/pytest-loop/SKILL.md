---
name: pytest-loop
description: Fast pre-commit verification workflow for Python bug fixes and feature tasks.
---

# Pytest & AST Self-Verification Skill

Before concluding your response:
1. Run `python3 scripts/verify_diff.py` to syntax-check all modified Python files and inspect your `git diff`.
2. Run a focused `python3 -c "..."` assertion check exercising both the failing bug case and normal baseline cases.
3. Clean up any temporary test files so `git status` only shows the intended source modifications.

