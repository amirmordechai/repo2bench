# `repo2bench-v2.0` Held-Out Test Empirical Evaluation Summary (20 Held-Out Tasks × 9 Candidates)

- **Train Split (`repo2bench-v2.0-train`, 10 older PRs):** Stock `antigravity-gemini-3.8-flash-medium` `70.0%` Pass@1 (`$0.301/task`, `271s`) → `Harness²` `agy-harness-gemini-3.8-flash-medium` **`90.0%` Pass@1 (`$0.285/task`, `222s`)**
- **Held-Out Test Split (`repo2bench-v2.0-test`, 20 unseen PRs):** `179 / 180` trials completed (`$65.00` total spend)

## 1. Custom Repo Held-Out Test Benchmark (`repo2bench-v2.0-test`) vs. Public Benchmark (`wb-bench-code-v1.0`)

| Candidate (`Harness + Model + Thinking`) | Held-Out Pass@1 | Held-Out Reward | `pydantic-ai` | `marimo` | Custom Cost/Task | Cache Hit % | Mean Time | Public Pass@1 | Public Cost/Task |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `agy-harness-gemini-3.8-flash-medium` (`Harness²`) | **70.0%** | **75.0%** | 70% | 70% | **$0.315** | 85.6% | 266s | — | — |
| `pi-gemini-4-argon-medium` | **70.0%** | 70.0% | 70% | 70% | **$0.216** | 70.0% | 273s | 25.0% | $0.89 |
| `antigravity-gemini-4-argon-medium` | **60.0%** | 61.7% | 60% | 60% | **$0.290** | 76.9% | 315s | 35.0% | $1.44 |
| `antigravity-gemini-4-argon-high` | **60.0%** | 60.0% | 50% | 70% | **$0.422** | 83.1% | 309s | 20.0% | $2.08 |
| `antigravity-gemini-3.8-flash-medium` | **50.0%** | 53.3% | 50% | 50% | **$0.384** | 84.9% | 334s | 35.0% | $0.30 |
| `pi-gemini-4-argon-high` | **50.0%** | 50.0% | 50% | 50% | **$0.376** | 79.8% | 325s | 25.0% | $2.38 |
| `pi-gemini-3.8-flash-medium` | **50.0%** | 50.0% | 60% | 40% | **$0.382** | 80.0% | 313s | 35.0% | $0.37 |
| `pi-gemini-3.8-flash-high` | **47.4%** | 47.4% | 33% | 60% | **$0.425** | 83.8% | 334s | 25.0% | $0.65 |
| `antigravity-gemini-3.8-flash-high` | **45.0%** | 45.0% | 30% | 60% | **$0.461** | 86.7% | 339s | 25.0% | $0.25 |
