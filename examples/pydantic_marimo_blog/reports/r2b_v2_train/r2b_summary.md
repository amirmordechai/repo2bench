# `repo2bench-v1.0` Empirical Evaluation Summary (20 Tasks × 9 Candidates = 180 Trials)

- **Total Trials Completed:** `20`
- **Total Campaign Spend:** `$5.87`

## 1. Custom Repo Benchmark (`repo2bench-v1.0`) vs. Public Benchmark (`wb-bench-code-v1.0`)

| Candidate (`Harness + Model + Thinking`) | Custom Pass@1 | Custom Reward | `pydantic-ai` | `marimo` | Custom Cost/Task | Cache Hit % | Mean Time | Public Pass@1 | Public Cost/Task |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `antigravity-gemini-3.8-flash-medium` | **70.0%** | 70.0% | 60% | 80% | **$0.301** | 81.8% | 271s | 35.0% | $0.30 |
| `agy-harness-gemini-3.8-flash-medium` | **90.0%** | 90.0% | 80% | 100% | **$0.285** | 84.1% | 222s | — | — |
