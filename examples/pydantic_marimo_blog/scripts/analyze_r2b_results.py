#!/usr/bin/env python3
"""Analyze empirical Harbor trial directories from a `repo2bench` evaluation campaign.

Computes per-candidate:
- Pass@1 (%), File Hit Rate (%), Diff Coverage (%)
- Mean Cost/Task ($), Total Cost ($), Cache Hit Rate (%), Mean Turns, Mean Duration (s)
- Breakdown by repository (`pydantic/pydantic-ai` vs `marimo-team/marimo`) and difficulty
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PRICING = {
    "gemini-4-argon": {"in": 2.00, "cache_read": 0.10, "out": 10.00},
    "gemini-3.8-flash": {"in": 0.75, "cache_read": 0.075, "out": 3.75},
}


def _safe_json(p: Path) -> dict[str, Any]:
    if not p.is_file():
        return {}
    try:
        d = json.loads(p.read_text(encoding="utf-8", errors="replace"))
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def load_turn_logs(turn_log_dir: Path | None) -> dict[str, list[dict[str, Any]]]:
    by_trial: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if not turn_log_dir or not turn_log_dir.is_dir():
        return by_trial
    for p in sorted(turn_log_dir.glob("*.jsonl")):
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

    thinking = "medium"
    model = rest
    for lvl in ("low", "medium", "high"):
        if rest.endswith(f"-{lvl}"):
            thinking = lvl
            model = rest[: -len(f"-{lvl}")]
            break
    cand_key = f"{harness}-{model}-{thinking}"
    return cand_key, harness, model, thinking


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate Harbor trial directories into repo2bench summary reports.")
    parser.add_argument("--trials-dir", type=Path, default=Path("./results/r2b_v2/trials"))
    parser.add_argument("--turn-log-dir", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, default=Path("./reports/r2b_v2"))
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    results_root = args.trials_dir
    turns_by_trial = load_turn_logs(args.turn_log_dir)

    latest_trial_dirs: dict[tuple[str, str], Path] = {}
    if results_root.is_dir():
        for job_dir in sorted(results_root.iterdir()):
            if not job_dir.is_dir() or job_dir.name.startswith("."):
                continue
            for rpath in sorted(job_dir.rglob("result.json")):
                tdir = rpath.parent
                if "__" not in tdir.name and not (tdir / "agent").is_dir():
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

        vturns = turns_by_trial.get(trial_id, [])
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
            }
        )

    summary_rows.sort(
        key=lambda r: (
            r["pass_at_1_pct"],
            -r["mean_cost_usd"],
        ),
        reverse=True,
    )

    out_json = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_trials": len(trials),
        "total_campaign_cost_usd": round(sum(r["total_cost_usd"] for r in summary_rows), 2),
        "candidates": summary_rows,
        "trials": trials,
    }
    (args.out_dir / "r2b_summary.json").write_text(json.dumps(out_json, indent=2) + "\n", encoding="utf-8")

    md_lines = [
        "# `repo2bench` Empirical Evaluation Summary",
        "",
        f"- **Total Trials Completed:** `{len(trials)}`",
        f"- **Total Campaign Spend:** `${out_json['total_campaign_cost_usd']:.2f}`",
        "",
        "| Candidate (`Harness + Model + Thinking`) | Pass@1 | `pydantic-ai` | `marimo` | Cost / Task | Cache Hit % | Mean Time |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in summary_rows:
        md_lines.append(
            f"| `{r['candidate_key']}` | **{r['pass_at_1_pct']:.1f}%** | "
            f"{r['pydantic_pass_pct']:.0f}% | {r['marimo_pass_pct']:.0f}% | **${r['mean_cost_usd']:.3f}** | "
            f"{r['cache_hit_pct']:.1f}% | {r['mean_duration_sec']:.0f}s |"
        )

    (args.out_dir / "r2b_summary.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print("\n".join(md_lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
