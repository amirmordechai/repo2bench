# `repo2bench-v1.0` Empirical Evaluation Summary (20 Tasks × 9 Candidates = 180 Trials)

- **Total Trials Completed:** `180`
- **Total Campaign Spend:** `$66.48`

## 1. Custom Repo Benchmark (`repo2bench-v1.0`) vs. Public Benchmark (`wb-bench-code-v1.0`)

| Candidate (`Harness + Model + Thinking`) | Custom Pass@1 | Custom Reward | `pydantic-ai` | `marimo` | Custom Cost/Task | Cache Hit % | Mean Time | Public Pass@1 | Public Cost/Task |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `antigravity-gemini-4-argon-medium` | **95.0%** | 95.0% | 100% | 90% | **$0.388** | 85.2% | 202s | 35.0% | $1.44 |
| `pi-gemini-4-argon-medium` | **90.0%** | 93.3% | 100% | 80% | **$0.248** | 78.9% | 179s | 25.0% | $0.89 |
| `antigravity-gemini-4-argon-high` | **75.0%** | 75.0% | 60% | 90% | **$0.454** | 88.1% | 277s | 20.0% | $2.08 |
| `pi-gemini-4-argon-high` | **65.0%** | 70.0% | 70% | 60% | **$0.371** | 84.5% | 293s | 25.0% | $2.38 |
| `pi-gemini-3.8-flash-high` | **65.0%** | 65.0% | 60% | 70% | **$0.468** | 79.7% | 289s | 25.0% | $0.65 |
| `pi-gemini-3.8-flash-medium` | **55.0%** | 58.3% | 50% | 60% | **$0.322** | 78.2% | 302s | 35.0% | $0.37 |
| `antigravity-gemini-3.8-flash-high` | **40.0%** | 40.0% | 30% | 50% | **$0.538** | 83.9% | 316s | 25.0% | $0.25 |
| `antigravity-gemini-3.8-flash-medium` | **35.0%** | 35.0% | 30% | 40% | **$0.372** | 79.3% | 322s | 35.0% | $0.30 |
| `agy-harness-gemini-3.8-flash-medium` | **90.0%** | 93.3% | 90% | 90% | **$0.165** | 76.3% | 134s | — | — |
