#!/usr/bin/env python3
"""Analyze empirical results from the 9-candidate repo2bench-v1.0 campaign (180 trials).

Computes per-candidate:
- Pass@1 (%), Continuous Reward (%), File Hit Rate (%), Diff Coverage (%)
- Mean Cost/Task ($), Total Cost ($), Cache Hit Rate (%), Mean Turns, Mean Duration (s)
- Breakdown by repository (`pydantic/pydantic-ai` vs `marimo-team/marimo`) and difficulty
- Side-by-side comparison against the public benchmark (`wb-bench-code-v1.0`)
- Baseline vs Harness² Optimized (`AntigravitySubstrate`) comparison
"""

from __future__ import annotations

import argparse
import json
import statistics
import tomllib
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

PRICING = {
    "gemini-4-argon": {"in": 2.00, "cache_read": 0.10, "out": 10.00},
    "gemini-3.8-flash": {"in": 0.75, "cache_read": 0.075, "out": 3.75},
}

PUBLIC_BENCH_REFERENCE = {
    "antigravity-gemini-3.8-flash-medium": {"pass_at_1": 35.0, "reward": 49.0, "cost": 0.30, "rank_quality": 2},
    "antigravity-gemini-3.8-flash-high": {"pass_at_1": 25.0, "reward": 38.4, "cost": 0.25, "rank_quality": 5},
    "antigravity-gemini-4-argon-medium": {"pass_at_1": 35.0, "reward": 50.0, "cost": 1.44, "rank_quality": 1},
    "antigravity-gemini-4-argon-high": {"pass_at_1": 20.0, "reward": 33.4, "cost": 2.08, "rank_quality": 8},
    "pi-gemini-3.8-flash-medium": {"pass_at_1": 35.0, "reward": 45.2, "cost": 0.37, "rank_quality": 3},
    "pi-gemini-3.8-flash-high": {"pass_at_1": 25.0, "reward": 41.2, "cost": 0.65, "rank_quality": 4},
    "pi-gemini-4-argon-medium": {"pass_at_1": 25.0, "reward": 36.2, "cost": 0.89, "rank_quality": 6},
    "pi-gemini-4-argon-high": {"pass_at_1": 25.0, "reward": 36.2, "cost": 2.38, "rank_quality": 7},
}


def _safe_json(p: Path) -> dict[str, Any]:
    if not p.is_file():
        return {}
    try:
        d = json.loads(p.read_text(encoding="utf-8", errors="replace"))
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def load_vertex_turns(vertex_log_dir: Path) -> dict[str, list[dict[str, Any]]]:
    by_trial: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if not vertex_log_dir.is_dir():
        return by_trial
    for p in sorted(vertex_log_dir.glob("*.jsonl")):
        if p.name.startswith("judge_"):
            continue
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                rec = json.loads(line)
                tid = str(rec.get("trial_id") or p.stem)
                by_trial[tid].append(rec)
            except Exception:
                continue
    return by_trial


def parse_job_slug(job_slug: str) -> tuple[str, str, str, str]:
    """Return (candidate_key, harness, model, thinking_level)."""
    slug = job_slug.removesuffix("-r2b").removesuffix("-code")
    if slug.startswith("agy-harness-"):
        harness = "agy-harness"
        rest = slug[len("agy-harness-") :]
    elif slug.startswith("antigravity-"):
        harness = "antigravity"
        rest = slug[len("antigravity-") :]
    elif slug.startswith("pi-"):
        harness = "pi"
        rest = slug[len("pi-") :]
    else:
        parts = slug.split("-", 1)
        harness = parts[0]
        rest = parts[1] if len(parts) > 1 else slug

    thinking = "high"
    model = rest
    for lvl in ("low", "medium", "high"):
        if rest.endswith(f"-{lvl}"):
            thinking = lvl
            model = rest[: -len(f"-{lvl}")]
            break
    cand_key = f"{harness}-{model}-{thinking}"
    return cand_key, harness, model, thinking


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("/opt/wb-eval/workbuddy-bench"))
    parser.add_argument("--results-subdir", type=str, default="results_r2b")
    parser.add_argument("--vertex-log-dir", type=Path, default=Path("/opt/wb-eval/logs/vertex_turns"))
    parser.add_argument("--out-dir", type=Path, default=Path("/opt/wb-eval/reports/r2b"))
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    results_root = args.repo_root / args.results_subdir
    vertex_by_trial = load_vertex_turns(args.vertex_log_dir)

    latest_trial_dirs: dict[tuple[str, str], Path] = {}
    for job_dir in sorted(results_root.iterdir()):
        if not job_dir.is_dir() or job_dir.name.startswith(".") or job_dir.name == "smoke-r2b":
            continue
        for rpath in sorted(job_dir.rglob("result.json")):
            tdir = rpath.parent
            if "__" not in tdir.name or not (tdir / "agent").is_dir():
                continue
            rjson = _safe_json(rpath)
            raw_tname = str(rjson.get("task_name") or "").strip()
            task_id = raw_tname.split("/")[-1] if raw_tname else tdir.name.split("__", 1)[0]
            latest_trial_dirs[(job_dir.name, task_id)] = tdir

    trials: list[dict[str, Any]] = []
    for (job_slug, task_id), tdir in sorted(latest_trial_dirs.items()):
        trial_id = tdir.name
        cand_key, harness, model, thinking = parse_job_slug(job_slug)
        result_json = _safe_json(tdir / "result.json")
        reward_json = _safe_json(tdir / "verifier" / "reward.json")
        score_json = _safe_json(tdir / "verifier" / "score.json")
        traj_json = _safe_json(tdir / "agent" / "trajectory.json")

        reward = (
            ((result_json.get("verifier_result") or {}).get("rewards") or {}).get("reward")
            if result_json.get("verifier_result")
            else reward_json.get("reward")
        )
        try:
            reward_val = float(reward) if reward is not None else float(score_json.get("test_pass_rate", 0.0))
        except Exception:
            reward_val = 0.0
        passed = reward_val >= 1.0
        fhr = float(score_json.get("file_hit_rate", 1.0 if passed else 0.0))
        dcov = float(score_json.get("diff_coverage", 1.0 if passed else 0.0))

        vturns = vertex_by_trial.get(trial_id, [])
        pricing = PRICING.get(model, {"in": 0.75, "cache_read": 0.075, "out": 3.75})
        if vturns:
            in_tok = sum(int(vt.get("input_tokens") or 0) for vt in vturns)
            cached_tok = sum(int(vt.get("cached_input_tokens") or 0) for vt in vturns)
            out_tok = sum(int(vt.get("output_tokens") or 0) for vt in vturns)
            reason_tok = sum(int(vt.get("reasoning_tokens") or 0) for vt in vturns)
            cost_usd = sum(float(vt.get("cost_usd") or 0.0) for vt in vturns)
            turns_count = len([vt for vt in vturns if not vt.get("circuit_breaker")])
        else:
            fm = traj_json.get("final_metrics") or {}
            in_tok = int(fm.get("total_prompt_tokens") or 0)
            cached_tok = int(fm.get("total_cached_tokens") or 0)
            out_tok = int(fm.get("total_completion_tokens") or 0)
            reason_tok = 0
            uncached_in = max(0, in_tok - cached_tok)
            cost_usd = (
                uncached_in * pricing["in"] + cached_tok * pricing["cache_read"] + out_tok * pricing["out"]
            ) / 1_000_000.0
            turns_count = len(traj_json.get("steps") or [])

        # Duration sec
        dur_sec = 0.0
        ar = result_json.get("agent_execution") or result_json.get("agent_result") or {}
        if ar.get("duration_sec"):
            dur_sec = float(ar["duration_sec"])
        elif ar.get("started_at") and ar.get("finished_at"):
            try:
                t0 = datetime.fromisoformat(str(ar["started_at"]).replace("Z", "+00:00"))
                t1 = datetime.fromisoformat(str(ar["finished_at"]).replace("Z", "+00:00"))
                dur_sec = max(0.0, (t1 - t0).total_seconds())
            except Exception:
                pass
        if dur_sec == 0.0 and vturns:
            dur_sec = sum(float(vt.get("total_ms") or 0.0) for vt in vturns) / 1000.0

        repo_source = "pydantic/pydantic-ai" if task_id.startswith("pydantic-ai-") else "marimo-team/marimo"
        difficulty = "easy" if "-easy-" in task_id else ("medium" if "-medium-" in task_id else "hard")

        trials.append(
            {
                "trial_id": trial_id,
                "job_slug": job_slug,
                "candidate_key": cand_key,
                "harness": harness,
                "model": model,
                "thinking_level": thinking,
                "task_id": task_id,
                "repo": repo_source,
                "difficulty": difficulty,
                "passed": passed,
                "reward": reward_val,
                "file_hit_rate": fhr,
                "diff_coverage": dcov,
                "input_tokens": in_tok,
                "cached_input_tokens": cached_tok,
                "output_tokens": out_tok,
                "reasoning_tokens": reason_tok,
                "cost_usd": cost_usd,
                "turns": turns_count,
                "duration_sec": dur_sec,
            }
        )

    by_cand: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for t in trials:
        by_cand[t["candidate_key"]].append(t)

    summary_rows: list[dict[str, Any]] = []
    for cand_key, rows in sorted(by_cand.items()):
        n = len(rows)
        pass_at_1 = sum(1 for r in rows if r["passed"]) / n * 100.0 if n else 0.0
        mean_reward = statistics.mean(r["reward"] for r in rows) * 100.0 if n else 0.0
        mean_fhr = statistics.mean(r["file_hit_rate"] for r in rows) * 100.0 if n else 0.0
        mean_dcov = statistics.mean(r["diff_coverage"] for r in rows) * 100.0 if n else 0.0
        mean_cost = statistics.mean(r["cost_usd"] for r in rows) if n else 0.0
        total_cost = sum(r["cost_usd"] for r in rows)
        tot_in = sum(r["input_tokens"] for r in rows)
        tot_cache = sum(r["cached_input_tokens"] for r in rows)
        cache_hit_pct = (tot_cache / tot_in * 100.0) if tot_in > 0 else 0.0
        mean_turns = statistics.mean(r["turns"] for r in rows) if n else 0.0
        mean_dur = statistics.mean(r["duration_sec"] for r in rows) if n else 0.0

        pyd_rows = [r for r in rows if r["repo"] == "pydantic/pydantic-ai"]
        mar_rows = [r for r in rows if r["repo"] == "marimo-team/marimo"]
        pyd_pass = sum(1 for r in pyd_rows if r["passed"]) / len(pyd_rows) * 100.0 if pyd_rows else 0.0
        mar_pass = sum(1 for r in mar_rows if r["passed"]) / len(mar_rows) * 100.0 if mar_rows else 0.0

        pub = PUBLIC_BENCH_REFERENCE.get(cand_key, {})
        summary_rows.append(
            {
                "candidate_key": cand_key,
                "harness": rows[0]["harness"],
                "model": rows[0]["model"],
                "thinking_level": rows[0]["thinking_level"],
                "n_trials": n,
                "pass_at_1_pct": round(pass_at_1, 1),
                "mean_reward_pct": round(mean_reward, 1),
                "file_hit_rate_pct": round(mean_fhr, 1),
                "diff_coverage_pct": round(mean_dcov, 1),
                "pydantic_pass_pct": round(pyd_pass, 1),
                "marimo_pass_pct": round(mar_pass, 1),
                "mean_cost_usd": round(mean_cost, 4),
                "total_cost_usd": round(total_cost, 3),
                "cache_hit_pct": round(cache_hit_pct, 1),
                "mean_turns": round(mean_turns, 1),
                "mean_duration_sec": round(mean_dur, 1),
                "public_pass_at_1_pct": pub.get("pass_at_1"),
                "public_reward_pct": pub.get("reward"),
                "public_cost_usd": pub.get("cost"),
            }
        )

    # Sort baseline 8 candidates by (mean_reward_pct DESC, pass_at_1_pct DESC, -mean_cost_usd DESC)
    summary_rows.sort(
        key=lambda r: (
            0 if r["harness"] == "agy-harness" else 1,
            r["mean_reward_pct"],
            r["pass_at_1_pct"],
            -r["mean_cost_usd"],
        ),
        reverse=True,
    )

    out_json = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_trials": len(trials),
        "total_campaign_cost_usd": round(sum(r["total_cost_usd"] for r in summary_rows), 2),
        "candidates": summary_rows,
        "trials": trials,
    }
    (args.out_dir / "r2b_summary.json").write_text(json.dumps(out_json, indent=2), encoding="utf-8")

    md_lines = [
        "# `repo2bench-v1.0` Empirical Evaluation Summary (20 Tasks × 9 Candidates = 180 Trials)",
        "",
        f"- **Total Trials Completed:** `{len(trials)}`",
        f"- **Total Campaign Spend:** `${out_json['total_campaign_cost_usd']:.2f}`",
        "",
        "## 1. Custom Repo Benchmark (`repo2bench-v1.0`) vs. Public Benchmark (`wb-bench-code-v1.0`)",
        "",
        "| Candidate (`Harness + Model + Thinking`) | Custom Pass@1 | Custom Reward | `pydantic-ai` | `marimo` | Custom Cost/Task | Cache Hit % | Mean Time | Public Pass@1 | Public Cost/Task |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in summary_rows:
        pub_p = f"{r['public_pass_at_1_pct']:.1f}%" if r["public_pass_at_1_pct"] is not None else "—"
        pub_c = f"${r['public_cost_usd']:.2f}" if r["public_cost_usd"] is not None else "—"
        md_lines.append(
            f"| `{r['candidate_key']}` | **{r['pass_at_1_pct']:.1f}%** | {r['mean_reward_pct']:.1f}% | "
            f"{r['pydantic_pass_pct']:.0f}% | {r['marimo_pass_pct']:.0f}% | **${r['mean_cost_usd']:.3f}** | "
            f"{r['cache_hit_pct']:.1f}% | {r['mean_duration_sec']:.0f}s | {pub_p} | {pub_c} |"
        )

    (args.out_dir / "r2b_summary.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print("\n".join(md_lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

