"""Multi-agent Harbor evaluation runner, leaderboard aggregator, and Quality-vs-Cost chart generator."""

from __future__ import annotations

import html
import json
import shutil
import statistics
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

# Default per-1M-token USD pricing (override via --pricing-json if needed)
DEFAULT_MODEL_PRICING: dict[str, dict[str, float]] = {
    "gemini-4-carbon": {"in": 2.50, "cache_read": 0.25, "out": 12.00},
    "gemini-4-argon": {"in": 2.00, "cache_read": 0.10, "out": 10.00},
    "gemini-3.8-flash": {"in": 0.75, "cache_read": 0.075, "out": 3.75},
}


@dataclass
class CandidateSummary:
    candidate_key: str
    harness: str
    model: str
    thinking_level: str
    n_trials: int
    n_passed: int
    pass_at_1_pct: float
    mean_cost_usd: float
    mean_turns: float
    mean_duration_sec: float


def _safe_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def resolve_tasks_dir(dataset_dir: Path) -> Path:
    tasks_sub = dataset_dir / "tasks"
    return tasks_sub if tasks_sub.is_dir() else dataset_dir


def build_harbor_job_yaml(
    *,
    job_slug: str,
    tasks_dir: Path,
    jobs_dir: Path,
    agent: str,
    model: str,
    thinking: str,
    concurrency: int,
) -> dict[str, Any]:
    return {
        "job_name": job_slug,
        "jobs_dir": str(jobs_dir),
        "n_concurrent_trials": concurrency,
        "datasets": [{"path": str(tasks_dir)}],
        "agents": [
            {
                "name": agent,
                "model_name": model,
                "kwargs": {"thinking_level": thinking},
            }
        ],
    }


def run_harbor_matrix(
    *,
    dataset_dir: Path,
    output_dir: Path,
    agents: list[str],
    models: list[str],
    thinking_levels: list[str],
    concurrency: int = 4,
    harbor_bin: str = "harbor",
    dry_run: bool = False,
) -> list[tuple[str, str, str, Path]]:
    """Generate Harbor job configs for each (agent x model x thinking) tuple and invoke `harbor run`."""
    tasks_dir = resolve_tasks_dir(dataset_dir.resolve())
    out = output_dir.resolve()
    configs_dir = out / "configs"
    trials_root = out / "trials"
    configs_dir.mkdir(parents=True, exist_ok=True)
    trials_root.mkdir(parents=True, exist_ok=True)

    planned: list[tuple[str, str, str, Path]] = []
    for agent in agents:
        for model in models:
            for thinking in thinking_levels:
                slug = f"{agent}-{model}-{thinking}"
                job_dir = trials_root / slug
                cfg_path = configs_dir / f"{slug}.yaml"
                cfg_data = build_harbor_job_yaml(
                    job_slug=slug,
                    tasks_dir=tasks_dir,
                    jobs_dir=job_dir,
                    agent=agent,
                    model=model,
                    thinking=thinking,
                    concurrency=concurrency,
                )
                cfg_path.write_text(yaml.safe_dump(cfg_data, sort_keys=False), encoding="utf-8")
                cmd = [
                    harbor_bin,
                    "run",
                    "-c",
                    str(cfg_path),
                    "--path",
                    str(tasks_dir),
                    "-n",
                    str(concurrency),
                ]
                planned.append((agent, model, thinking, job_dir))
                if dry_run:
                    print(f"[repo2bench eval --dry-run] {' '.join(cmd)}")
                    continue
                if shutil.which(harbor_bin) is None and not Path(harbor_bin).is_file():
                    raise RuntimeError(
                        f"Harbor CLI binary '{harbor_bin}' not found on PATH. "
                        "Install Harbor (`uv tool install harbor` or see https://github.com/harbor-framework/harbor) "
                        "or pass --harbor-bin /path/to/harbor."
                    )
                print(f"[repo2bench eval] Running {slug} via Harbor (n={concurrency})...")
                subprocess.run(cmd, check=True)
    return planned


def _parse_slug_metadata(slug: str) -> tuple[str, str, str]:
    thinking = "medium"
    rem = slug
    for lvl in ("low", "medium", "high"):
        if rem.endswith(f"-{lvl}"):
            thinking = lvl
            rem = rem[: -len(f"-{lvl}")]
            break
    parts = rem.split("-", 1)
    harness = parts[0]
    model = parts[1] if len(parts) > 1 else rem
    return harness, model, thinking


def aggregate_trials(
    trials_root: Path,
    pricing_map: dict[str, dict[str, float]] | None = None,
) -> list[CandidateSummary]:
    """Aggregate Harbor trial directories (`<trials_root>/<job_slug>/**/result.json`) into ranked summaries."""
    pricing_table = dict(DEFAULT_MODEL_PRICING)
    if pricing_map:
        pricing_table.update(pricing_map)

    summaries: list[CandidateSummary] = []
    if not trials_root.is_dir():
        return summaries

    for job_dir in sorted(d for d in trials_root.iterdir() if d.is_dir() and not d.name.startswith(".")):
        slug = job_dir.name
        harness, model, thinking = _parse_slug_metadata(slug)
        latest_by_task: dict[str, Path] = {}
        for rpath in sorted(job_dir.rglob("result.json")):
            tdir = rpath.parent
            if "__" not in tdir.name and not (tdir / "verifier").is_dir() and not (tdir / "agent").is_dir():
                continue
            rjson = _safe_json(rpath)
            raw_tname = str(rjson.get("task_name") or "").strip()
            task_id = raw_tname.split("/")[-1] if raw_tname else tdir.name.split("__", 1)[0]
            latest_by_task[task_id] = tdir

        if not latest_by_task:
            continue

        passed_flags: list[int] = []
        costs: list[float] = []
        turns_list: list[float] = []
        durations: list[float] = []
        rates = pricing_table.get(model, {"in": 0.75, "cache_read": 0.075, "out": 3.75})

        for _, tdir in sorted(latest_by_task.items()):
            rjson = _safe_json(tdir / "result.json")
            rwjson = _safe_json(tdir / "verifier" / "reward.json")
            traj = _safe_json(tdir / "agent" / "trajectory.json")

            reward = (
                ((rjson.get("verifier_result") or {}).get("rewards") or {}).get("reward")
                if rjson.get("verifier_result")
                else rwjson.get("reward")
            )
            reward_val = float(reward) if reward is not None else 0.0
            passed_flags.append(1 if reward_val >= 1.0 else 0)

            fm = traj.get("final_metrics") or rjson.get("metrics") or {}
            if "cost_usd" in fm and fm["cost_usd"] is not None:
                cost = float(fm["cost_usd"])
            else:
                in_tok = int(fm.get("total_prompt_tokens") or fm.get("input_tokens") or 0)
                cached_tok = int(fm.get("total_cached_tokens") or fm.get("cached_input_tokens") or 0)
                out_tok = int(fm.get("total_completion_tokens") or fm.get("output_tokens") or 0)
                uncached_in = max(0, in_tok - cached_tok)
                cost = (
                    uncached_in * rates["in"]
                    + cached_tok * rates["cache_read"]
                    + out_tok * rates["out"]
                ) / 1_000_000.0
            costs.append(cost)

            steps = traj.get("steps")
            n_turns = float(fm.get("total_turns") or (len(steps) if isinstance(steps, list) else 0))
            turns_list.append(n_turns)

            dur = float(rjson.get("duration_sec") or fm.get("duration_sec") or 0.0)
            durations.append(dur)

        n_trials = len(passed_flags)
        n_passed = sum(passed_flags)
        summaries.append(
            CandidateSummary(
                candidate_key=slug,
                harness=harness,
                model=model,
                thinking_level=thinking,
                n_trials=n_trials,
                n_passed=n_passed,
                pass_at_1_pct=round(100.0 * n_passed / n_trials, 1),
                mean_cost_usd=round(statistics.mean(costs), 4) if costs else 0.0,
                mean_turns=round(statistics.mean(turns_list), 1) if turns_list else 0.0,
                mean_duration_sec=round(statistics.mean(durations), 1) if durations else 0.0,
            )
        )

    summaries.sort(key=lambda c: (-c.pass_at_1_pct, c.mean_cost_usd))
    return summaries


def render_xy_svg(summaries: list[CandidateSummary], title: str = "Coding Agents on Your Repo: Quality vs. Cost") -> str:
    """Render a clean standalone SVG Quality-vs-Cost scatter chart (higher & further right = better)."""
    w, h = 980, 540
    pad_l, pad_r, pad_t, pad_b = 88, 44, 78, 66
    pw, ph = w - pad_l - pad_r, h - pad_t - pad_b

    if not summaries:
        return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}"></svg>'

    costs = [c.mean_cost_usd for c in summaries]
    accs = [c.pass_at_1_pct for c in summaries]
    max_c = max(max(costs) * 1.12, 0.10)
    min_c = max(0.0, min(costs) * 0.82)
    if max_c - min_c < 0.05:
        max_c = min_c + 0.10

    min_y = max(0.0, min(accs) - 10.0)
    max_y = min(100.0, max(accs) + 10.0)
    if max_y - min_y < 15.0:
        max_y = min(100.0, min_y + 20.0)

    # X axis inverted so cheaper is to the right (matching repo2bench frontier convention)
    def x_px(cost: float) -> float:
        return pad_l + ((max_c - cost) / (max_c - min_c)) * pw

    def y_px(acc: float) -> float:
        return pad_t + ((max_y - acc) / (max_y - min_y)) * ph

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
        'style="font-family:-apple-system,BlinkMacSystemFont,Inter,Segoe UI,sans-serif;background:#ffffff;border:2px solid #cbd5e1;border-radius:18px;">',
        f'<text x="32" y="42" font-size="23" font-weight="800" fill="#0f172a">{html.escape(title)}</text>',
        '<text x="32" y="64" font-size="14" font-weight="600" fill="#64748b">Container-isolated Harbor trials · Higher &amp; further right is better</text>',
        f'<rect x="{pad_l}" y="{pad_t}" width="{pw}" height="{ph}" fill="#f8fafc" />',
        f'<rect x="{pad_l + pw * 0.55:.1f}" y="{pad_t}" width="{pw * 0.45:.1f}" height="{ph * 0.48:.1f}" '
        'fill="#ecfdf5" stroke="#10b981" stroke-dasharray="5 4" stroke-width="1.5" />',
        f'<text x="{pad_l + pw - 14:.1f}" y="{pad_t + 22}" text-anchor="end" font-size="12.5" font-weight="800" fill="#047857">BEST QUALITY · COST ZONE</text>',
        f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{pad_t + ph}" stroke="#94a3b8" stroke-width="2"/>',
        f'<line x1="{pad_l}" y1="{pad_t + ph}" x2="{pad_l + pw}" y2="{pad_t + ph}" stroke="#94a3b8" stroke-width="2"/>',
    ]

    for step in range(5):
        yv = min_y + (max_y - min_y) * step / 4.0
        yp = y_px(yv)
        parts.append(f'<line x1="{pad_l}" y1="{yp:.1f}" x2="{pad_l + pw}" y2="{yp:.1f}" stroke="#e2e8f0" stroke-dasharray="4 4"/>')
        parts.append(f'<text x="{pad_l - 10}" y="{yp + 5:.1f}" text-anchor="end" font-size="13" font-weight="700" fill="#64748b">{yv:.0f}%</text>')

    for step in range(5):
        cv = max_c - (max_c - min_c) * step / 4.0
        xp = x_px(cv)
        parts.append(f'<line x1="{xp:.1f}" y1="{pad_t}" x2="{xp:.1f}" y2="{pad_t + ph}" stroke="#e2e8f0" stroke-dasharray="4 4"/>')
        parts.append(f'<text x="{xp:.1f}" y="{pad_t + ph + 22}" text-anchor="middle" font-size="13" font-weight="700" fill="#64748b">${cv:.2f}</text>')

    parts.append(
        f'<text x="24" y="{pad_t + ph / 2:.1f}" transform="rotate(-90 24 {pad_t + ph / 2:.1f})" '
        'text-anchor="middle" font-size="15" font-weight="800" fill="#0f172a">Pass@1 Accuracy</text>'
    )
    parts.append(
        f'<text x="{pad_l + pw / 2:.1f}" y="{h - 16}" text-anchor="middle" font-size="15" font-weight="800" fill="#0f172a">'
        'Mean Cost per Task (USD)   Cheaper →</text>'
    )

    palette = ["#059669", "#10b981", "#2563eb", "#dc2626", "#7c3aed", "#ea580c", "#d97706", "#475569"]
    for idx, c in enumerate(summaries):
        cx, cy = x_px(c.mean_cost_usd), y_px(c.pass_at_1_pct)
        col = palette[idx % len(palette)]
        lbl = f"{c.harness} · {c.model} ({c.thinking_level})  {c.pass_at_1_pct:.0f}% · ${c.mean_cost_usd:.2f}"
        parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="12" fill="{col}" fill-opacity="0.20"/>')
        parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="6" fill="{col}"/>')
        ty = cy - 14 if idx % 2 == 0 else cy + 22
        anchor = "end" if cx > pad_l + pw * 0.68 else ("start" if cx < pad_l + pw * 0.25 else "middle")
        parts.append(
            f'<text x="{cx:.1f}" y="{ty:.1f}" text-anchor="{anchor}" font-size="12.5" font-weight="700" fill="#0f172a">'
            f"{html.escape(lbl)}</text>"
        )

    parts.append("</svg>")
    return "\n".join(parts)


def write_eval_reports(summaries: list[CandidateSummary], out_dir: Path) -> dict[str, Path]:
    """Write leaderboard JSON, Markdown table, and Quality-vs-Cost XY chart (SVG + PNG when Chrome is present)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "leaderboard.json"
    md_path = out_dir / "leaderboard.md"
    svg_path = out_dir / "leaderboard_xy.svg"

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "candidates": [asdict(s) for s in summaries],
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    md_lines = [
        "# `repo2bench` Agent Leaderboard",
        "",
        "| Rank | Harness | Model | Thinking | Pass@1 | Cost / Task | Turns | Speed |",
        "| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |",
    ]
    for rank, s in enumerate(summaries, start=1):
        mins = f"{s.mean_duration_sec / 60.0:.1f}m" if s.mean_duration_sec else "-"
        md_lines.append(
            f"| #{rank} | `{s.harness}` | `{s.model}` | `{s.thinking_level}` | "
            f"**{s.pass_at_1_pct:.1f}%** ({s.n_passed}/{s.n_trials}) | `${s.mean_cost_usd:.3f}` | "
            f"{s.mean_turns:.1f} | {mins} |"
        )
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    svg_str = render_xy_svg(summaries)
    svg_path.write_text(svg_str, encoding="utf-8")

    written = {"json": json_path, "markdown": md_path, "svg": svg_path}
    chrome_bin = shutil.which("google-chrome") or shutil.which("chromium")
    if chrome_bin and summaries:
        png_path = out_dir / "leaderboard_xy.png"
        tmp_html = out_dir / ".leaderboard_xy_tmp.html"
        tmp_html.write_text(
            f"<!DOCTYPE html><html><body style='margin:0;padding:16px;background:#f8fafc;'>{svg_str}</body></html>",
            encoding="utf-8",
        )
        try:
            subprocess.run(
                [
                    chrome_bin,
                    "--headless",
                    "--disable-gpu",
                    "--no-sandbox",
                    "--hide-scrollbars",
                    "--force-device-scale-factor=2",
                    "--window-size=1040,600",
                    f"--screenshot={png_path}",
                    f"file://{tmp_html.resolve()}",
                ],
                check=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            written["png"] = png_path
        except Exception:
            pass
        finally:
            tmp_html.unlink(missing_ok=True)

    return written
