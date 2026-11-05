# `repo2bench-v2.0-test` Held-Out Test Evaluation Summary (20 Unseen PRs × 9 Candidates)

- **Train Split (`repo2bench-v2.0-train`, 10 older PRs):** Stock `antigravity-gemini-3.8-flash-medium` `70.0%` Pass@1 (`$0.301/task`, `271s`) → `Harness²` `agy-harness-gemini-3.8-flash-medium` **`90.0%` Pass@1 (`$0.285/task`, `222s`)**
- **Held-Out Test Split (`repo2bench-v2.0-test`, 20 unseen PRs):** `179 / 180` trials completed (`$65.00` total spend)

## Held-Out Test Benchmark (`repo2bench-v2.0-test`)

| Candidate (`Harness + Model + Thinking`) | Held-Out Pass@1 | `pydantic-ai` | `marimo` | Cost / Task | Cache Hit % | Mean Time |
|---|---:|---:|---:|---:|---:|---:|
| `agy-harness-gemini-3.8-flash-medium` (`Harness²`) | **70.0%** | 70% | 70% | **$0.315** | 85.6% | 266s |
| `pi-gemini-4-argon-medium` | **70.0%** | 70% | 70% | **$0.216** | 70.0% | 273s |
| `antigravity-gemini-4-argon-medium` | **60.0%** | 60% | 60% | **$0.290** | 76.9% | 315s |
| `antigravity-gemini-4-argon-high` | **60.0%** | 50% | 70% | **$0.422** | 83.1% | 309s |
| `antigravity-gemini-3.8-flash-medium` | **50.0%** | 50% | 50% | **$0.384** | 84.9% | 334s |
| `pi-gemini-3.8-flash-medium` | **50.0%** | 60% | 40% | **$0.382** | 80.0% | 313s |
| `pi-gemini-4-argon-high` | **50.0%** | 50% | 50% | **$0.376** | 79.8% | 325s |
| `pi-gemini-3.8-flash-high` | **47.4%** | 33% | 60% | **$0.425** | 83.8% | 334s |
| `antigravity-gemini-3.8-flash-high` | **45.0%** | 30% | 60% | **$0.461** | 86.7% | 339s |
