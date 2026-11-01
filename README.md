# `repo2bench`: Build your own custom code benchmark
### Build the Eval Factory for Your Software Factory: Benchmark Coding Agents on Your Own Repo

<p align="center">
  <img src="docs/assets/overview_flow.png" alt="Software Factory to Eval Factory Flywheel" width="100%">
</p>

**`repo2bench`** turns any Git repository's activity history into a verified, container-isolated **[Harbor](https://github.com/harbor-bench/harbor)** coding agent benchmark in a single CLI command—so you can evaluate and compare coding agents (`Harness × Model × Thinking Budget`) directly on your own codebase.

---

## Why `repo2bench`?

Easy code generation makes verification the bottleneck. When everyone has access to the same frontier models and agent harnesses, your unique advantage is your engineering judgment—and how systematically you turn that judgment into a custom benchmark that evaluates and improves agents on your own codebase.

Public coding benchmarks test generic repositories (`pytest`, `copier`, `django`) that look nothing like your codebase. When you evaluate `Harness × Model × Thinking Budget` on your own repo:
- **Leaderboard rankings flip:** Configurations that rank `#6` on generic public benchmarks can jump to `#1` on your architecture at a fraction of the cost.
- **Hidden harness bottlenecks surface:** You immediately see where an agent's tool loop, context caching, or test-execution strategy breaks down on your repo's layout—giving you a concrete target to tune your agent rules, skills, and prompts.

---

## Quickstart

### 1. Install `repo2bench`

```bash
pip install -e .
```

### 2. Mine Verified Harbor Tasks from Any Git Repo

```bash
repo2bench mine \
  --repo /path/to/your-repo \
  --limit-num-tasks 20 \
  --output ./my-repo-bench
```

<p align="center">
  <img src="docs/assets/how_repo2bench_works.png" alt="How repo2bench Turns Git Activity into Benchmark Tasks" width="100%">
</p>

What `repo2bench` does automatically:
1. **Filters Git Signals:** Scans merged PRs/commits, keeps changes that touch both source code and unit tests, and drops noisy commits (`git revert`, force-pushes, docs/typos, or massive refactors).
2. **Verifies `Fail → Pass` Test Signal:** Validates every task in a clean container—the PR's unit test **must fail** before the fix (`score = 0.0`) and **must pass** after the developer's fix (`score = 1.0`).
3. **Eliminates Solution Leakage:** Splits each PR into:
   - **Starting Workspace (`environment/`):** Repository checked out at `base_commit` before the fix, with future Git history stripped.
   - **Goal-Oriented Prompt (`instruction.md`):** Synthesizes a pre-commit problem statement from the issue/PR motivation and test expectations—stripping target file paths and commit-message solution spoilers.
   - **Hidden Test Grader (`tests/`):** Runs only after the agent finishes.

---

## Repository Structure

```text
repo2bench/
├── src/repo2bench/                 # Core CLI & Harbor task mining pipeline
├── tests/                          # Unit tests for repo2bench
├── docs/assets/                    # Architecture & pipeline diagrams
└── examples/
    └── pydantic_marimo_blog/       # Full empirical case study ("Build your own custom code benchmark")
        ├── README.md               # Case study walkthrough & reproduction guide
        ├── datasets/               # Mined Harbor datasets (10 Train + 20 Held-Out Test PRs)
        ├── reports/                # Empirical Pass@1, Reward, Cost & Speed summaries (180 trials)
        ├── optimized_agy_ws/       # Optimized Antigravity workspace (GEMINI.md + pytest-loop skill)
        └── scripts/                # Mining & evaluation scripts used in the blog post
```

---

## End-to-End Case Study (`examples/pydantic_marimo_blog/`)

See **[`examples/pydantic_marimo_blog/README.md`](examples/pydantic_marimo_blog/README.md)** for the full datasets, empirical evaluation reports across 8 Gemini agent configurations, and the [`Harness²`](https://github.com/google-research/harness2) optimization case study from the accompanying blog post (*"Build your own custom code benchmark — Build the Eval Factory for Your Software Factory"*).

---

## License

Apache 2.0

---

## Disclaimer

Disclaimer: This code is provided "as-is" as a demonstration only to illustrate a potential solution. The code does not constitute a Google product or service of any kind, and Google offers no support, warranties, or liability of any kind with its regard. Whoever chooses to use this code accepts all responsibility related to it, including for its implementation, use, and ongoing maintenance. For the avoidance of doubt, this code is not eligible for the Google Open Source Software Vulnerability Rewards Program.
