---
name: repo2bench
description: Mine a Git repository's pull-request history into leak-free Harbor coding agent benchmark tasks, validate Fail->Pass unit test gates, and evaluate Harness x Model x Thinking Budget matrices with Quality-vs-Cost leaderboards.
---

# `repo2bench` Skill

Use `repo2bench` whenever the user wants to:
1. Build a custom coding agent benchmark from their own Git repository (`repo2bench mine`).
2. Verify that benchmark tasks fail before the fix and pass after the gold patch (`repo2bench validate`).
3. Inspect tasks in a dataset (`repo2bench list`).
4. Run or aggregate multi-agent container evaluations via Harbor and generate Quality-vs-Cost charts (`repo2bench eval`).

## Workflow

### 1. Ensure `repo2bench` Is Installed
```bash
pip install -e .
```

### 2. Mine & Validate Tasks from a Local Git Clone
```bash
repo2bench mine \
  --repo /path/to/repo \
  --since 2026-01-01 \
  --limit-num-tasks 20 \
  --validate \
  --output ./my-repo-bench
```
- If the target repository needs custom system dependencies or a prebuilt image, pass `--base-image <docker-image>` and/or `--pip-packages pkg1,pkg2`.
- Always create a chronological split (older PRs in `train/`, newer PRs in `test/`) if the user plans to optimize prompts/skills on the benchmark.

### 3. Evaluate Coding Agents (`repo2bench eval`)
- Preview generated Harbor job configs first with `--dry-run`:
  ```bash
  repo2bench eval \
    --dataset ./my-repo-bench \
    --agents antigravity,pi \
    --models gemini-4-argon,gemini-3.8-flash \
    --thinking medium,high \
    --output ./results/my-repo-eval \
    --dry-run
  ```
- Run live container trials (requires Docker + `harbor` on `PATH` + model API key in environment):
  ```bash
  repo2bench eval \
    --dataset ./my-repo-bench \
    --agents antigravity,pi \
    --models gemini-4-argon,gemini-3.8-flash \
    --thinking medium,high \
    --concurrency 4 \
    --output ./results/my-repo-eval
  ```
- Re-aggregate existing Harbor trial directories without re-running containers:
  ```bash
  repo2bench eval --results-only --trials-dir ./results/my-repo-eval/trials --output ./results/my-repo-eval
  ```
