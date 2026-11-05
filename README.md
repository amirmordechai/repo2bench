# `repo2bench`: Build your own custom code benchmark
### Build the Eval Factory for Your Software Factory: Benchmark Coding Agents on Your Own Repo with [`repo2bench`](https://github.com/amirmordechai/repo2bench) (Built on [`Harbor`](https://github.com/harbor-framework/harbor))

<p align="center">
  <img src="docs/assets/overview_flow.png" alt="Software Factory to Eval Factory Flywheel" width="100%">
</p>

**`repo2bench`** mines any Git repository's pull-request history into a verified, leak-free coding agent benchmark and evaluates **`Harness × Model × Thinking Budget`** configurations in isolated **[Harbor](https://github.com/harbor-framework/harbor)** Docker sandboxes—producing your repo's Quality-vs.-Cost leaderboard and chart in two CLI commands.

📖 **Read the accompanying Google Cloud blog post:** [**Build your own custom code benchmark**](https://medium.com/google-cloud/build-your-own-custom-code-benchmark-12b2673f1906)

---

## Why `repo2bench`?

How do most teams pick their coding agent today? Brand hype, top-down mandates, 30 minutes of manual "vibe testing," or checking generic public leaderboards like **[Terminal-Bench 4.0](https://www.vals.ai/benchmarks/terminal-bench-4)**, **[Vibe Code Bench](https://www.vals.ai/benchmarks/vibe-code)**, or **[Artificial Analysis](https://artificialanalysis.ai/leaderboards/models)**. None of those test *your* architecture, *your* conventions, or *your* test suite.

When everyone has access to the same frontier models and agent harnesses, your unique advantage is your engineering judgment—and how systematically you turn that judgment into an **Eval Factory** for your **Software Factory**:
- **Counter-intuitive quality & cost winners emerge:** Models with higher per-token list prices can cost **40%+ less per task** when they localize bugs in half the turns, while cranking `Thinking Budget` from `medium` to `high` can actually *lower* `Pass@1` accuracy on multi-module repos.
- **Hidden harness bottlenecks surface:** Container trajectories immediately reveal where an agent's tool loop, prefix caching, or `pytest` strategy breaks down on your repo's layout—giving you a concrete chronological `Train / Held-Out Test` split to auto-tune repo-specific rules, skills, and verification scripts via [`Harness²`](https://github.com/google-research/harness2).

---

## Prerequisites & Supported Repositories

- **Supported Repositories:** Python + `pytest` repositories out of the box (`flat`, `src/`, and multi-package layouts; `requirements.txt` and `pyproject.toml` are installed automatically inside task containers). Custom languages, monorepo toolchains, or prebuilt test images are supported via `--base-image` and `--pip-packages`.
- **Requirements:**
  - **Mining & Local Validation (`mine`, `validate`, `list`):** Python `3.11+` and `git`.
  - **Containerized Agent Evaluation (`eval`):** [Docker](https://docs.docker.com/get-docker/), [`Harbor`](https://github.com/harbor-framework/harbor) (`uv tool install harbor` or `pip install harbor`), and your model provider API key (e.g., `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, or `OPENAI_API_KEY`).

---

## Try It in 60 Seconds (No Docker or API Keys Needed)

Clone the repository, install `repo2bench`, and test the pipeline immediately using the bundled 20-PR benchmark mined from `pydantic/pydantic-ai` and `marimo-team/marimo`:

```bash
git clone https://github.com/amirmordechai/repo2bench.git
cd repo2bench
pip install -e .

# 1. Inspect the 20 bundled real-world PR tasks (Easy / Medium / Hard)
repo2bench list --dataset examples/pydantic_marimo_blog/datasets/repo2bench-v2.0-test

# 2. Verify the Fail -> Pass (nop=0.0 -> oracle=1.0) test gate locally
repo2bench validate --dataset examples/pydantic_marimo_blog/datasets/repo2bench-v2.0-test

# 3. Preview a multi-agent Harbor evaluation matrix & generated job configs
repo2bench eval \
  --dataset examples/pydantic_marimo_blog/datasets/repo2bench-v2.0-test \
  --agents antigravity,pi \
  --models gemini-4-argon,gemini-3.8-flash \
  --thinking medium,high \
  --output ./tmp-eval-preview \
  --dry-run
```

---

## Benchmark Your Own Repository

### Step 1: Mine Verified Benchmark Tasks (`repo2bench mine`)

Point `repo2bench mine` at any local Git clone:

```bash
repo2bench mine \
  --repo /path/to/your-repo \
  --since 2026-01-01 \
  --limit-num-tasks 20 \
  --validate \
  --output ./my-repo-bench
```

<p align="center">
  <img src="docs/assets/how_repo2bench_works.png" alt="How repo2bench Turns Git Activity into Benchmark Tasks" width="100%">
</p>

What `repo2bench mine` does automatically:
1. **Filters Git Signals:** Scans merged PRs/commits, keeps self-contained changes that touch both source code and unit tests, classifies difficulty (`easy`: 1 file & ≤30 LOC; `medium`: 1–2 files & ≤100 LOC; `hard`: 3+ files or >100 LOC), and drops noisy commits (`git revert`, docs/typos, or massive refactors).
2. **Verifies `Fail → Pass` Test Signal (`--validate`):** Checks every candidate task cleanly—the PR's held-out unit test **must fail** before the fix (`nop = 0.0`) and **must pass 100%** when the developer's gold patch is applied (`oracle = 1.0`).
3. **Eliminates Solution Leakage:** Splits each PR into an isolated Harbor task directory:
   - **`environment/`:** Repository archived at `parent_sha` *before* the fix, with future Git history removed.
   - **`instruction.md`:** Pre-commit problem statement synthesized from motivation and test expectations—stripping modified file paths and commit-message solution spoilers.
   - **`tests/`:** Hidden `test_patch.diff` + JUnit XML scorer (`scorer.py`), mounted only after the agent finishes.

### Step 2: Evaluate & Rank Coding Agents (`repo2bench eval`)

Run any grid of `Harness × Model × Thinking Budget` candidates in parallel Harbor Docker containers:

```bash
repo2bench eval \
  --dataset ./my-repo-bench \
  --agents antigravity,pi \
  --models gemini-4-argon,gemini-3.8-flash \
  --thinking medium,high \
  --concurrency 4 \
  --output ./results/my-repo-eval
```

`repo2bench eval` executes each `(agent × model × thinking)` configuration in isolated containers, aggregates `Pass@1` (`% of PRs with 100% passing unit tests`), mean API cost per task, turn count, and wall-clock speed, and writes:
- `leaderboard.md` — Ranked Markdown summary table
- `leaderboard.json` — Machine-readable metrics for CI/dashboards
- `leaderboard_xy.svg` (and `leaderboard_xy.png` when Chrome/Chromium is available) — Quality-vs.-Cost frontier chart

### Step 3 (Optional): Auto-Tune Your Agent (`Harness²`)

To optimize an agent's repo-specific instructions (`GEMINI.md` / `CLAUDE.md`), skills, and verification scripts without overfitting:
1. Mine **older** PRs into `./bench-train` and **newer** PRs into `./bench-test` (chronological split).
2. Point **[`Harness²`](https://github.com/google-research/harness2)** at `./bench-train` so its proposer diagnoses failed Harbor container trajectories and evolves targeted workspace rules/skills.
3. Re-run `repo2bench eval` on the unseen `./bench-test` split to verify held-out `Pass@1` and cost gains.

---

## CLI Reference

| Command | Purpose | Key Options |
| :--- | :--- | :--- |
| `repo2bench mine` | Mine paired code+test PRs from a Git clone into Harbor tasks | `--repo`, `--output`, `--since`, `--limit-num-tasks`, `--validate`, `--base-image`, `--pip-packages` |
| `repo2bench validate` | Run local `Fail → Pass` (`nop < 1.0 → oracle == 1.0`) check on tasks | `--dataset`, `--python-bin` |
| `repo2bench list` | List task IDs, difficulty tiers, repos, and base commits | `--dataset`, `--json` |
| `repo2bench eval` | Run multi-agent Harbor container trials & emit leaderboard + XY chart | `--dataset`, `--agents`, `--models`, `--thinking`, `--concurrency`, `--output`, `--pricing-json`, `--results-only`, `--dry-run` |

---

## Repository Structure

```text
repo2bench/
├── src/repo2bench/                 # Core CLI, Git miner, validator, Harbor emitter & evaluator
├── tests/                          # End-to-end pytest suite (mining, Fail->Pass gate, eval aggregation)
├── docs/assets/                    # Architecture & pipeline diagrams
├── .agents/skills/repo2bench/      # Skill file for AI coding agents (Antigravity, Claude Code, Gemini CLI)
└── examples/
    └── pydantic_marimo_blog/       # Full empirical case study ("Build your own custom code benchmark")
        ├── README.md               # Case study walkthrough & reproduction commands
        ├── datasets/               # Mined Harbor datasets (10 Train + 20 Held-Out Test PRs)
        ├── reports/                # Empirical Pass@1, Cost & Speed summaries (180 container trials)
        ├── optimized_agy_ws/       # Auto-tuned Antigravity workspace (GEMINI.md + pytest-loop skill)
        └── scripts/                # Dataset construction, campaign runner & telemetry scripts
```

---

## End-to-End Case Study (`examples/pydantic_marimo_blog/`)

See **[`examples/pydantic_marimo_blog/README.md`](examples/pydantic_marimo_blog/README.md)** for the full datasets, empirical evaluation reports across 8 Gemini agent configurations, and the [`Harness²`](https://github.com/google-research/harness2) auto-tuning case study from the accompanying Google Cloud blog post ([**"Build your own custom code benchmark — Build the Eval Factory for Your Software Factory"**](https://medium.com/google-cloud/build-your-own-custom-code-benchmark-12b2673f1906)).

---

## License

Apache 2.0

---

## Disclaimer

Disclaimer: This code is provided "as-is" as a demonstration only to illustrate a potential solution. The code does not constitute a Google product or service of any kind, and Google offers no support, warranties, or liability of any kind with its regard. Whoever chooses to use this code accepts all responsibility related to it, including for its implementation, use, and ongoing maintenance. For the avoidance of doubt, this code is not eligible for the Google Open Source Software Vulnerability Rewards Program.
