# Example Case Study: Benchmarking & Auto-Tuning Coding Agents on `pydantic-ai` and `marimo`

This folder contains the complete datasets, scripts, empirical evaluation reports, and [`Harness²`](https://github.com/google-research/harness2)-auto-tuned Antigravity configuration from the Google Cloud blog post:
> **[Build your own custom code benchmark](https://medium.com/google-cloud/build-your-own-custom-code-benchmark-12b2673f1906)**
> *Build the Eval Factory for Your Software Factory: Benchmark Coding Agents on Your Own Repo with [`repo2bench`](https://github.com/amirmordechai/repo2bench) (Built on [`Harbor`](https://github.com/harbor-framework/harbor)), and Auto-Tune with [`Harness²`](https://github.com/google-research/harness2)*

---

## Try the Bundled Benchmark Locally

From the `repo2bench` repository root:

```bash
# 1. List all 20 Held-Out Test PR tasks
repo2bench list --dataset examples/pydantic_marimo_blog/datasets/repo2bench-v2.0-test

# 2. Verify the Fail -> Pass (nop=0.0 -> oracle=1.0) test gate locally
repo2bench validate --dataset examples/pydantic_marimo_blog/datasets/repo2bench-v2.0-test

# 3. Preview (or execute) the 8-agent Harbor matrix evaluation
repo2bench eval \
  --dataset examples/pydantic_marimo_blog/datasets/repo2bench-v2.0-test \
  --agents antigravity,pi \
  --models gemini-4-argon,gemini-3.8-flash \
  --thinking medium,high \
  --output ./results/r2b_v2 \
  --dry-run
```

---

## Contents

- **`datasets/repo2bench-v2.0-train/`** — **10 chronological `Train` tasks** mined from older October 2026 PRs in `pydantic/pydantic-ai` and `marimo-team/marimo`. Used exclusively by `Harness²` to auto-tune repo-specific harness rules and skills.
- **`datasets/repo2bench-v2.0-test/`** — **20 chronological `Held-Out Test` tasks** mined from newer October 2026 PRs (`30–120` workspace files per task, zero solution leakage). Used for blind evaluation across all 8 baseline Gemini configurations + `Harness²`.
- **`datasets/repo2bench-v1.0/`** — Initial 20-task benchmark snapshot (`v1.0`).
- **`optimized_agy_ws/`** — The `Harness²`-evolved Antigravity workspace (`GEMINI.md`, `.agents/skills/pytest-loop/SKILL.md`, and `scripts/verify_diff.py`) evolved on the 10 `Train` tasks (`90.0%` Train Pass@1) and evaluated blind on the 20 `Held-Out Test` tasks.
- **`reports/r2b_v2/`** — Blind evaluation results across the 20 `Held-Out Test` tasks (`179/180` completed trials across 9 configurations).
- **`reports/r2b_v2_train/`** — `Train` set evaluation results (`10` tasks, stock vs. `Harness²`).
- **`scripts/`** — Reproducible dataset construction (`build_repo2bench_v2.py`), campaign execution (`run_r2b_campaign.sh`), and telemetry aggregation (`analyze_r2b_results.py`).

---

## Held-Out Test Set Results (`repo2bench-v2.0-test`, 20 Unseen October 2026 PRs)

| Rank | Agent Configuration | Held-Out Test Pass@1 | Mean Cost / Task | Mean Turns | Mean Speed |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Tie #1** | **`Harness²` Antigravity + Gemini 3.8 Flash (`med`)** | **`70.0%` (`14/20`)** | **`$0.315` (`-18%`)** | **`38.6`** | **`4.4m`** |
| **Tie #1** | **Pi + Gemini 4 Argon (`med`)** | **`70.0%` (`14/20`)** | **`$0.216`** | `24.1` | `4.6m` |
| **#3** | **Antigravity + Gemini 4 Argon (`med`)** | `60.0%` (`12/20`) | `$0.290` | `28.4` | `5.3m` |
| **#4** | **Antigravity + Gemini 4 Argon (`high`)** | `60.0%` (`12/20`) | `$0.422` | `25.8` | `5.2m` |
| **#5** | **Pi + Gemini 4 Argon (`high`)** | `50.0%` (`10/20`) | `$0.376` | `22.9` | `5.4m` |
| **#6** | **Pi + Gemini 3.8 Flash (`med`)** | `50.0%` (`10/20`) | `$0.382` | `36.7` | `5.2m` |
| **#7** | **Stock Antigravity + Gemini 3.8 Flash (`med`)** | `50.0%` (`10/20`) | `$0.384` | `50.1` | `5.6m` |
| **#8** | **Pi + Gemini 3.8 Flash (`high`)** | `47.4%` (`9/19`) | `$0.425` | `35.2` | `5.6m` |
| **#9** | **Antigravity + Gemini 3.8 Flash (`high`)** | `45.0%` (`9/20`) | `$0.461` | `44.1` | `5.7m` |

---

## Disclaimer

Disclaimer: This code is provided "as-is" as a demonstration only to illustrate a potential solution. The code does not constitute a Google product or service of any kind, and Google offers no support, warranties, or liability of any kind with its regard. Whoever chooses to use this code accepts all responsibility related to it, including for its implementation, use, and ongoing maintenance. For the avoidance of doubt, this code is not eligible for the Google Open Source Software Vulnerability Rewards Program.
