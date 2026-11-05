"""Command-line interface for repo2bench (`repo2bench mine`, `repo2bench eval`, `repo2bench validate`, `repo2bench list`)."""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path

from .evaluator import aggregate_trials, run_harbor_matrix, write_eval_reports
from .git_miner import mine_repository
from .harbor_emitter import emit_harbor_task
from .validator import validate_harbor_task


def cmd_mine(args: argparse.Namespace) -> int:
    repo_path = Path(args.repo).resolve()
    out_dir = Path(args.output).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[repo2bench] Scanning Git repository at {repo_path} (since={args.since}, limit_num_tasks={args.limit_num_tasks})...")
    commits = mine_repository(
        repo_path,
        repo_name=args.repo_name,
        since=args.since,
        max_commits_scan=args.max_scan,
        limit=args.limit_num_tasks,
    )
    print(f"[repo2bench] Found {len(commits)} candidate commits with paired code + test diffs.")

    extra_pkgs = _split_csv(args.pip_packages) if args.pip_packages else None
    emitted: list[str] = []
    for c in commits:
        tdir = emit_harbor_task(
            c,
            out_dir,
            extra_pip_packages=extra_pkgs,
            base_image=args.base_image,
        )
        emitted.append(tdir.name)
        print(f"  + Emitted Harbor task: {tdir.name} [{c.difficulty}] ({len(c.src_files)} src, {len(c.test_files)} test)")

    if args.validate:
        print(f"\n[repo2bench] Running Fail -> Pass validation gate on {len(emitted)} tasks...")
        passed = 0
        for tid in emitted:
            res = validate_harbor_task(out_dir / "tasks" / tid, python_bin=args.python_bin)
            status = "PASS" if res.valid else "FAIL"
            print(f"  [{status}] {tid}: nop={res.nop_pass_rate:.2f} -> oracle={res.oracle_pass_rate:.2f} (tests={res.oracle_tests_total})")
            if res.valid:
                passed += 1
        print(f"[repo2bench] Validated {passed}/{len(emitted)} tasks.")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    dataset_dir = Path(args.dataset).resolve()
    tasks_dir = dataset_dir / "tasks" if (dataset_dir / "tasks").is_dir() else dataset_dir
    task_dirs = sorted(d for d in tasks_dir.iterdir() if d.is_dir() and (d / "task.toml").is_file())
    if not task_dirs:
        print(f"[repo2bench] No Harbor tasks found under {tasks_dir}", file=sys.stderr)
        return 1

    print(f"[repo2bench] Validating {len(task_dirs)} Harbor tasks in {tasks_dir}...")
    all_valid = True
    results = []
    for td in task_dirs:
        res = validate_harbor_task(td, python_bin=args.python_bin)
        results.append(res)
        status = "PASS" if res.valid else "FAIL"
        print(
            f"  [{status}] {res.task_id:<48} nop={res.nop_pass_rate:.2f} ({res.nop_tests_total}) -> "
            f"oracle={res.oracle_pass_rate:.2f} ({res.oracle_tests_total})"
        )
        if not res.valid:
            all_valid = False
            if res.error:
                print(f"         Error: {res.error}")

    n_ok = sum(1 for r in results if r.valid)
    print(f"\n[repo2bench] Summary: {n_ok}/{len(results)} tasks passed the Fail -> Pass gate.")
    return 0 if all_valid else 1


def cmd_list(args: argparse.Namespace) -> int:
    dataset_dir = Path(args.dataset).resolve()
    tasks_dir = dataset_dir / "tasks" if (dataset_dir / "tasks").is_dir() else dataset_dir
    task_dirs = sorted(d for d in tasks_dir.iterdir() if d.is_dir() and (d / "task.toml").is_file())

    rows = []
    for td in task_dirs:
        cfg = tomllib.loads((td / "task.toml").read_text(encoding="utf-8"))
        meta = cfg.get("metadata") or {}
        rows.append(
            {
                "id": td.name,
                "repo": meta.get("repo", ""),
                "difficulty": meta.get("difficulty", "medium"),
                "commit_sha": str(meta.get("commit_sha", ""))[:10],
            }
        )
    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        print(f"{'TASK ID':<50} {'DIFFICULTY':<10} {'REPO':<26} {'COMMIT'}")
        print("-" * 100)
        for r in rows:
            print(f"{r['id']:<50} {r['difficulty']:<10} {r['repo']:<26} {r['commit_sha']}")
    return 0


def _split_csv(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


def cmd_eval(args: argparse.Namespace) -> int:
    out_dir = Path(args.output).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    pricing_map = None
    if args.pricing_json:
        pricing_map = json.loads(Path(args.pricing_json).read_text(encoding="utf-8"))

    if not args.results_only:
        agents = _split_csv(args.agents)
        models = _split_csv(args.models)
        thinking_levels = _split_csv(args.thinking)
        run_harbor_matrix(
            dataset_dir=Path(args.dataset),
            output_dir=out_dir,
            agents=agents,
            models=models,
            thinking_levels=thinking_levels,
            concurrency=args.concurrency,
            harbor_bin=args.harbor_bin,
            dry_run=args.dry_run,
        )
        if args.dry_run:
            return 0

    trials_root = Path(args.trials_dir).resolve() if args.trials_dir else (out_dir / "trials")
    summaries = aggregate_trials(trials_root, pricing_map=pricing_map)
    if not summaries:
        print(f"[repo2bench eval] No completed Harbor trial results found under {trials_root}.", file=sys.stderr)
        return 1

    written = write_eval_reports(summaries, out_dir)
    print(f"\n{'RANK':<6} {'AGENT CONFIGURATION':<44} {'PASS@1':<16} {'COST/TASK':<12} {'TURNS':<8} {'SPEED'}")
    print("-" * 98)
    for idx, s in enumerate(summaries, start=1):
        cfg_lbl = f"{s.harness} + {s.model} ({s.thinking_level})"
        p_lbl = f"{s.pass_at_1_pct:.1f}% ({s.n_passed}/{s.n_trials})"
        c_lbl = f"${s.mean_cost_usd:.3f}"
        sp_lbl = f"{s.mean_duration_sec / 60.0:.1f}m" if s.mean_duration_sec else "-"
        print(f"#{idx:<5} {cfg_lbl:<44} {p_lbl:<16} {c_lbl:<12} {s.mean_turns:<8.1f} {sp_lbl}")

    print(f"\n[repo2bench eval] Wrote leaderboard & Quality-vs-Cost chart to {out_dir}:")
    for kind, p in written.items():
        print(f"  - {kind}: {p}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="repo2bench",
        description="Mine Git PR history into verified benchmarks and evaluate coding agents via Harbor.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    p_mine = sub.add_parser("mine", help="Mine commits/PRs from a Git repo and emit Harbor tasks")
    p_mine.add_argument("--repo", required=True, help="Path to local Git repository clone")
    p_mine.add_argument("--repo-name", default=None, help="Override repository slug (e.g., org/repo)")
    p_mine.add_argument("--since", default="2025-06-01", help="Minimum commit ISO date")
    p_mine.add_argument("--max-scan", type=int, default=500, help="Maximum commits to scan")
    p_mine.add_argument(
        "--limit-num-tasks",
        "--limit",
        dest="limit_num_tasks",
        type=int,
        default=20,
        help="Maximum number of benchmark tasks to emit",
    )
    p_mine.add_argument("--output", required=True, help="Output Harbor dataset directory")
    p_mine.add_argument("--base-image", default=None, help="Custom Docker base image for emitted tasks (default: python:3.12-slim)")
    p_mine.add_argument("--pip-packages", default=None, help="Comma-separated extra pip packages to pre-install in task containers")
    p_mine.add_argument("--validate", action="store_true", help="Run Fail -> Pass validation after emitting")
    p_mine.add_argument("--python-bin", default=sys.executable, help="Python executable for pytest validation")
    p_mine.set_defaults(func=cmd_mine)

    p_eval = sub.add_parser(
        "eval",
        help="Evaluate a matrix of coding agents on a mined dataset (via Harbor) and plot Quality vs. Cost",
    )
    p_eval.add_argument("--dataset", required=False, default=".", help="Path to mined dataset directory")
    p_eval.add_argument("--agents", default="antigravity,pi", help="Comma-separated agent harnesses (e.g., antigravity,pi)")
    p_eval.add_argument(
        "--models",
        default="gemini-4-argon,gemini-3.8-flash",
        help="Comma-separated model IDs (e.g., gemini-4-argon,gemini-3.8-flash)",
    )
    p_eval.add_argument("--thinking", default="medium,high", help="Comma-separated thinking budgets (e.g., medium,high)")
    p_eval.add_argument("--concurrency", "-n", type=int, default=4, help="Concurrent container trials per job")
    p_eval.add_argument("--output", required=True, help="Output directory for trials, leaderboard, and XY chart")
    p_eval.add_argument("--harbor-bin", default="harbor", help="Harbor CLI executable")
    p_eval.add_argument("--pricing-json", default=None, help="Optional JSON file overriding per-1M-token USD pricing")
    p_eval.add_argument("--results-only", action="store_true", help="Aggregate existing Harbor trial directories without running")
    p_eval.add_argument("--trials-dir", default=None, help="Custom Harbor trials directory when using --results-only")
    p_eval.add_argument("--dry-run", action="store_true", help="Write Harbor job configs and print commands without executing")
    p_eval.set_defaults(func=cmd_eval)

    p_val = sub.add_parser("validate", help="Run Fail -> Pass (`nop=0 -> oracle=1`) validation on emitted Harbor tasks")
    p_val.add_argument("--dataset", required=True, help="Path to Harbor dataset or tasks directory")
    p_val.add_argument("--python-bin", default=sys.executable, help="Python executable for pytest validation")
    p_val.set_defaults(func=cmd_validate)

    p_ls = sub.add_parser("list", help="List tasks in a Harbor dataset directory")
    p_ls.add_argument("--dataset", required=True, help="Path to Harbor dataset or tasks directory")
    p_ls.add_argument("--json", action="store_true", help="Output JSON")
    p_ls.set_defaults(func=cmd_list)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

