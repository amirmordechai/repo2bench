# `repo2bench`: Build the Data Factory for Your Software Factory

Turn your team's Git history into a private, spoiler-free **Harbor** coding agent benchmark (`workbuddy-bench` & `google-research/harness2` compatible).

---

## Why `repo2bench`?

Public coding benchmarks (`SWE-bench`, `WorkBuddy-Bench`, `LiveCodeBench`) measure general coding competence on third-party repositories. However:
1. **Your codebase has its own architecture, conventions, and edge cases.** The `Harness × Model × Thinking` stack that ranks `#1` on a public benchmark often shifts on your private repository.
2. **You don't need human chat logs to benchmark your repo.** Every merged bug-fix or feature PR that includes a unit test diff (`tests/test_*.py`) alongside a source code diff (`src/...`) already encodes the ground-truth behavioral contract.

`repo2bench` mines your Git commit history, separates the **test patch** from the **source fix patch**, synthesizes a spoiler-free task specification (`instruction.md`), and validates the strict **Fail-to-Pass (`nop == 0.0 -> oracle == 1.0`)** gate before emitting ready-to-run Harbor task folders.

---

## Architecture & Pipeline

```text
Git Commit History
  ├─ 1. Signal Filter (repo2bench.git_miner)
  │    • Rejects bot/chore/typo/formatting commits & giant refactors
  │    • Requires paired source code diff + unit test diff
  │    • Boosts commits that survived subsequent reverted/cherry-pick churn
  │
  ├─ 2. Patch Splitter & Contract Prompt Synthesizer (repo2bench.prompt_synthesizer)
  │    • Extracts held-out `tests/test_patch.diff` & `solution/gold.patch`
  │    • Synthesizes a spoiler-free `instruction.md` from test assertions & docstrings
  │
  ├─ 3. Harbor Task Emitter (repo2bench.harbor_emitter)
  │    • Archives `parent_sha` into `environment/workspace.tar.gz`
  │    • Generates `task.toml`, `environment/Dockerfile`, `tests/test.sh`, and `tests/scorer.py`
  │    • Emits `dataset.toml` with split-mount runtime config for `antigravity`, `agy-harness`, and `pi`
  │
  └─ 4. Strict Fail-to-Pass Validator (repo2bench.validator)
       • Pre-Fix (`nop` state): Baseline + `tests/test_patch.diff` MUST fail (`pass_rate == 0.0`)
       • Post-Fix (`oracle` state): Baseline + `solution/gold.patch` + `tests/test_patch.diff` MUST pass (`pass_rate == 1.0`)
```

---

## Quickstart

### 1. Install `repo2bench`

```bash
pip install -e .
```

### 2. Mine Candidate Commits & Emit a Harbor Benchmark Dataset

```bash
repo2bench mine \
  --repo /path/to/your-repo \
  --limit-num-tasks 20 \
  --output ./datasets/my-repo-bench \
  --validate
```

### 4. Validate an Existing Harbor Dataset (`nop == 0.0 -> oracle == 1.0`)

```bash
repo2bench validate ./datasets/repo2bench-v1.0
```

---

## Included Datasets: `repo2bench-v2.0` (`10` Train + `20` Held-Out Test)

This repository ships with **`repo2bench-v2.0`**, a 30-task Harbor benchmark mined from real October 2026 commits across two fast-moving Python repositories (`pydantic/pydantic-ai` and `marimo-team/marimo`), split chronologically to guarantee zero data science leakage during agent harness optimization:
- **`datasets/repo2bench-v2.0-train`** (`10` older PRs: `5` `pydantic-ai` + `5` `marimo`) — used **exclusively** for `Harness²` outer-loop skill & rule evolution.
- **`datasets/repo2bench-v2.0-test`** (`20` newer Held-Out PRs: `10` `pydantic-ai` + `10` `marimo`) — used for blind evaluation across agent harnesses and models.
- **Black-Box Pre-Commit Goal Prompts & Multi-Module Workspaces:** Every `instruction.md` in `v2.0` is synthesized as a pre-commit problem/goal description (`black_box=True`, zero file paths or code spoilers) and packs broad multi-module directories (`30–120` files per task) so agents must genuinely search and localize code before editing.

Every task in `repo2bench-v2.0-train` (`10/10`) and `repo2bench-v2.0-test` (`20/20`) passes the strict `nop == 0.0 -> oracle == 1.0` deterministic verification gate.

---

## Native `AntigravitySubstrate` for `google-research/harness2`

Under [`harness2_substrates/`](./harness2_substrates/), `repo2bench` also provides a native **Google Antigravity (`agy`)** substrate for [`google-research/harness2`](https://github.com/google-research/harness2) (addressing [`google-research/harness2#100`](https://github.com/google-research/harness2/issues/100)):
- [`antigravity.py`](./harness2_substrates/antigravity.py): Defines `AGY_SURFACE` (`GEMINI.md`, `.agents/skills/**/SKILL.md`, `.agents/rules/*.md`, `scripts/**`, `config.yaml`), `AntigravitySubstrate`, and `render_agy_events` trajectory digest extraction.
- [`agy_harness_agent.py`](./harness2_substrates/agy_harness_agent.py): Harbor `AgyAgent` subclass (`agy-harness`) that materializes the evolved `AGY_SURFACE` into `/workspace` before each trial rollout so Antigravity natively auto-discovers `GEMINI.md`, `.agents/rules/`, and `.agents/skills/`.
- [`optimized_agy_ws/`](./harness2_substrates/optimized_agy_ws/): The `Harness²`-optimized Antigravity workspace evolved strictly on `repo2bench-v2.0-train`.

