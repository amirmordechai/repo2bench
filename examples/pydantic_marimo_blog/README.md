# Example Case Study: Benchmarking & Optimizing Coding Agents on `pydantic-ai` and `marimo`

This folder contains the complete datasets, scripts, empirical evaluation reports, and `Harness²`-optimized Antigravity configuration from the blog post:
> **Build your own custom coding benchmark**
> *Build the Data Factory for Your Software Factory: Benchmark Coding Agents on Your Own Repo with `repo2bench` & Optimize with `Harness²`*

---

## Contents

- **`datasets/repo2bench-v2.0-train/`** — **10 chronological `Train` tasks** mined from older October 2026 PRs in `pydantic/pydantic-ai` and `marimo-team/marimo`. Used exclusively by `Harness²` to evolve repo-specific harness rules and skills.
- **`datasets/repo2bench-v2.0-test/`** — **20 chronological `Held-Out Test` tasks** mined from newer October 2026 PRs (`30–120` workspace files per task, zero solution leakage). Used for blind evaluation across all 8 baseline Gemini configurations + `Harness²`.
- **`datasets/repo2bench-v1.0/`** — Initial 20-task benchmark snapshot (`v1.0`).
- **`optimized_agy_ws/`** — The `Harness²`-evolved Antigravity workspace (`GEMINI.md`, `.agents/skills/pytest-loop/SKILL.md`, and `scripts/verify_diff.py`) evolved on the 10 `Train` tasks (`90.0%` Train Pass@1) and evaluated blind on the 20 `Held-Out Test` tasks.
- **`reports/r2b_v2/`** — Blind evaluation results across the 20 `Held-Out Test` tasks (`179/180` completed trials across 9 configurations).
- **`reports/r2b_v2_train/`** — `Train` set evaluation results (`10` tasks, stock vs. `Harness²`).
- **`scripts/`** — Reproducible dataset mining (`build_repo2bench_v2.py`), campaign execution (`run_r2b_campaign.sh`), and telemetry aggregation (`analyze_r2b_results.py`).

---

## Held-Out Test Set Results (`repo2bench-v2.0-test`, 20 Unseen October 2026 PRs)

| Rank | Agent Configuration | Held-Out Test Pass@1 | Continuous Reward | Mean Cost / Task | Mean Turns | Mean Speed |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **#1 (Overall)** | **`Harness²` Antigravity + Gemini 3.8 Flash (`med`)** | **`70.0%` (`14/20`)** | **`75.0%`** | **`$0.315` (`-18%`)** | **`38.6`** | **`4.4m`** |
| **#1 (Baseline)** | **Pi + Gemini 4 Argon (`med`)** | **`70.0%` (`14/20`)** | `70.0%` | **`$0.216`** | `24.1` | `4.6m` |
| **#2 (Baseline)** | **Antigravity + Gemini 4 Argon (`med`)** | `60.0%` (`12/20`) | `61.7%` | `$0.290` | `28.4` | `5.3m` |
| **#3 (Baseline)** | **Antigravity + Gemini 4 Argon (`high`)** | `60.0%` (`12/20`) | `60.0%` | `$0.422` | `25.8` | `5.2m` |
| **#4 (Baseline)** | **Stock Antigravity + Gemini 3.8 Flash (`med`)** | `50.0%` (`10/20`) | `53.3%` | `$0.384` | `50.1` | `5.6m` |
| **#5 (Baseline)** | **Pi + Gemini 3.8 Flash (`med`)** | `50.0%` (`10/20`) | `50.0%` | `$0.382` | `36.7` | `5.2m` |
| **#6 (Baseline)** | **Pi + Gemini 4 Argon (`high`)** | `50.0%` (`10/20`) | `50.0%` | `$0.376` | `22.9` | `5.4m` |
| **#7 (Baseline)** | **Pi + Gemini 3.8 Flash (`high`)** | `47.4%` (`9/19`) | `47.4%` | `$0.425` | `35.2` | `5.6m` |
| **#8 (Baseline)** | **Antigravity + Gemini 3.8 Flash (`high`)** | `45.0%` (`9/20`) | `45.0%` | `$0.461` | `44.1` | `5.7m` |

---

## Disclaimer

Disclaimer: This code is provided "as-is" as a demonstration only to illustrate a potential solution. The code does not constitute a Google product or service of any kind, and Google offers no support, warranties, or liability of any kind with its regard. Whoever chooses to use this code accepts all responsibility related to it, including for its implementation, use, and ongoing maintenance. For the avoidance of doubt, this code is not eligible for the Google Open Source Software Vulnerability Rewards Program.
