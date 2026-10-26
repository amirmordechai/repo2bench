# Repository Agent Instructions (Harness² Optimized via `AntigravitySubstrate`)

## CRITICAL ENVIRONMENT RULE (DO NOT VIOLATE)
- **Lightweight Subset Snapshot:** This `/workspace` contains only the target module and test files extracted by `repo2bench`. Full monorepo third-party test dependencies (`genai`, `boto3`, `playwright`, `duckdb`, etc.) and virtualenvs are **NOT** installed.
- **NEVER run `pytest` on the repository's `tests/` directory, and NEVER waste turns searching for virtualenvs, `uv`, `poetry`, or installed packages.** Doing so will waste turns and cause a timeout.
- **Fast Verification Only:** After editing the target source file(s), verify your changes ONLY by running:
  1. `python3 scripts/verify_diff.py` (which validates AST syntax and prints modified files)
  2. If needed, a single self-contained `python3 -c "..."` check using only Python's standard library (`ast`, `re`, `json`, `hashlib`, `urllib.parse`, `html`).
  3. Immediately conclude your turn once `python3 scripts/verify_diff.py` reports `[OK]`.

## Step-by-Step Execution Protocol
1. **Turn 1 — Read Target File(s) Directly:**
   - Open and view the exact source file(s) named in the task instruction. Do not list directories or inspect git logs.
2. **Turn 2 — Apply the Exact Edit:**
   - Implement every numbered requirement in the task instruction cleanly and completely.
   - Do not modify test files under `tests/` unless explicitly instructed; focus on the source module(s) listed in the requirements.
3. **Turn 3 — Run `python3 scripts/verify_diff.py` & Finish:**
   - Run `python3 scripts/verify_diff.py` to confirm valid Python syntax and clean `git diff`, then immediately return your final answer.
