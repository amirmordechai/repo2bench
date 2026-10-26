# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""AntigravitySubstrate: Google Antigravity (`agy` / `google-antigravity` SDK) as a solver substrate.

Carries the c1..c8 surface (`AGY_SURFACE`), the workspace root install mode (`agy_root`:
`GEMINI.md`, `AGENTS.md`, `.agents/skills/<name>/SKILL.md`, `.agents/hooks.json`, and
`scripts/<name>.py` staged at the workspace root where `google.antigravity.Agent` auto-discovers
them), and the `agy-output.jsonl` trajectory renderer into the shared Harness2 grammar.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Mapping

from ..core import runmark as RM
from ..core import tree as HT
from ..core.tree import SurfaceSpec
from .base import Install, Launcher, RunRequest

AGY_SURFACE = SurfaceSpec(
    name="antigravity",
    always_on=("GEMINI.md",),
    always_on_max=8_000,
    always_on_cap_reason=(
        "GEMINI.md is auto-discovered at workspace root and injected into EVERY turn "
        "as an always-on workspace rule by Google Antigravity"
    ),
    skill_dir=".agents/skills",
    skill_name_rule="overrides_dir",
    trigger_hint=(
        'Fix it by adding a trigger line naming `{name}` to GEMINI.md, e.g. "When '
        "<the situation this skill handles>, read .agents/skills/{name}/SKILL.md "
        'and follow it."'
    ),
    autotrigger_file="GEMINI.md",
    trigger_line="- When {desc}, read .agents/skills/{name}/SKILL.md and follow it.\n",
    subagent_requires_mode=False,
    plugin_dir=None,
    hooks_file=".agents/hooks.json",
    hook_events=frozenset(
        {
            "SessionStart",
            "UserPromptSubmit",
            "PreToolUse",
            "PostToolUse",
            "Stop",
        }
    ),
    compile_skill_scripts=True,
    reject_empty_always_on=True,
    stubs=(
        (
            "scripts/README.md",
            "<!-- c7: deterministic helpers, run as `python3 scripts/<name>.py`. "
            "Add one by emitting scripts/<name>.py. -->\n",
        ),
        (
            "sub_agents/README.md",
            "<!-- c5: delegated agent roles. Add one as sub_agents/<name>/AGENT.md "
            "with frontmatter `description:`. -->\n",
        ),
        (
            ".agents/README.md",
            "<!-- c8: Antigravity lifecycle hooks -- acts inside the tool execution loop. "
            "Add ONE file, .agents/hooks.json, with event keys SessionStart, UserPromptSubmit, "
            'PreToolUse, PostToolUse, or Stop: {"hooks": {"PostToolUse": [{"matcher": ".*", '
            '"hooks": [{"type": "command", "command": "..."}]}]}}. Exit code 2 blocks and '
            "feeds stderr back to the model. -->\n",
        ),
        (
            ".agents/skills/README.md",
            "<!-- c6: reusable workflows auto-discovered by Antigravity at .agents/skills/. "
            "Add one as .agents/skills/<name>/SKILL.md with YAML frontmatter (`description:` "
            "REQUIRED; `name:` optional and must match directory). -->\n",
        ),
    ),
)

AGY_ROOT_ENTRIES = ("GEMINI.md", "AGENTS.md", ".agents", "scripts")

_TRUNC_FMT = "…(+{n} chars — render truncation)"


def _clip(s, n: int) -> str:
    s = "" if s is None else str(s)
    s = s.replace("\x00", "")
    if n <= 0 or len(s) <= n:
        return s
    return s[:n] + _TRUNC_FMT.format(n=len(s) - n)


class AntigravitySubstrate:
    """Google Antigravity (`agy` / `google-antigravity` SDK) behind the Substrate interface."""

    name = "agy"

    def __init__(self, launcher: Launcher | None = None):
        self._launcher = launcher

    def surface(self) -> SurfaceSpec:
        return AGY_SURFACE

    def materialise(self, tree_dir: Path, spec, ctx: Mapping[str, str]) -> Install:
        """Stage the agy_root entries for copying into /workspace prior to agent execution."""
        if spec.install_mode != "agy_root":
            raise ValueError(
                f"install_mode {spec.install_mode!r} is not the antigravity mode; this substrate "
                f"has exactly one: 'agy_root'"
            )
        tree_dir = Path(tree_dir)
        if not HT.is_tree(AGY_SURFACE, tree_dir):
            raise ValueError(f"{tree_dir} is not an antigravity harness tree (no GEMINI.md)")
        staged = Path(tempfile.mkdtemp(prefix="adapt-agy-root-"))
        for entry in AGY_ROOT_ENTRIES:
            src = tree_dir / entry
            if not src.exists():
                continue
            if src.is_dir():
                shutil.copytree(src, staged / entry)
            else:
                shutil.copy2(src, staged / entry)
        # Mirror GEMINI.md to AGENTS.md if AGENTS.md was not explicitly emitted
        gemini_md = staged / "GEMINI.md"
        agents_md = staged / "AGENTS.md"
        if gemini_md.is_file() and not agents_md.is_file():
            shutil.copy2(gemini_md, agents_md)
        return Install(
            staging_dir=staged,
            fingerprint=RM.fingerprint(tree_dir),
            extras={
                "install_mode": "agy_root",
                **{k: v for k, v in ctx.items() if not k.startswith("file:")},
            },
        )

    def execute(
        self, task_ref: str, install: Install, run_ids: list[str], timeout: int
    ) -> list[Path]:
        if self._launcher is None:
            raise RuntimeError(
                "AntigravitySubstrate was constructed without a launcher body; the benchmark "
                "adapter must supply one"
            )
        return self._launcher(
            RunRequest(task_ref=task_ref, run_ids=tuple(run_ids), timeout=int(timeout)), install
        )

    def read_trajectory(
        self, stream_path: Path, *, obs_trunc: int, max_chars: int, args_trunc: int = 2000
    ) -> str:
        return render_agy_events(
            Path(stream_path), obs_trunc=obs_trunc, max_chars=max_chars, args_trunc=args_trunc
        )

    def preflight(self) -> None:
        """Check that the environment is ready for Antigravity execution."""
        return None


def parse_agy_items(path: Path) -> list[dict]:
    """Parse `agy-output.jsonl` lines emitted by `AgyAgent` / `AgyHarnessAgent`."""
    try:
        raw = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return [{"type": "_read_error", "message": str(e)}]
    raw = raw.replace("\x00", "")
    events: list[dict] = []
    for ln in raw.splitlines():
        ln = ln.strip()
        if not ln.startswith("{"):
            continue
        try:
            ev = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if isinstance(ev, dict):
            events.append(ev)
    return events


def render_agy_events(
    path: Path, *, obs_trunc: int, max_chars: int, args_trunc: int = 2000
) -> str:
    """Render an `agy-output.jsonl` trajectory stream into the shared Harness2 grammar."""
    lines: list[str] = []
    for ev in parse_agy_items(Path(path)):
        et = ev.get("type", "")
        if et == "_read_error":
            return f"(failed to read trajectory: {ev.get('message')})"

        if et == "step":
            st = ev.get("step") or {}
            role = str(st.get("role") or st.get("source") or "").lower()
            thinking = st.get("thinking") or st.get("reasoning_content")
            if isinstance(thinking, str) and thinking.strip():
                lines.append(f"[REASONING] {_clip(thinking.strip(), obs_trunc)}")

            content = st.get("content")
            if isinstance(content, str) and content.strip():
                if role in ("user", "system"):
                    lines.append(f"[USER] {_clip(content.strip(), obs_trunc)}")
                elif role in ("tool", "observation"):
                    lines.append(f"[OBSERVATION] {_clip(content.strip(), obs_trunc)}")
                else:
                    lines.append(f"[ASSISTANT] {_clip(content.strip(), obs_trunc)}")

            tool_calls = st.get("tool_calls") or []
            if isinstance(tool_calls, list):
                for tc in tool_calls:
                    if not isinstance(tc, dict):
                        continue
                    fn_name = tc.get("name") or tc.get("function_name") or "tool"
                    fn_args = tc.get("arguments") or tc.get("args") or {}
                    if not isinstance(fn_args, str):
                        fn_args = json.dumps(fn_args, ensure_ascii=False)
                    lines.append(f"[ACTION] {fn_name}: {_clip(fn_args, args_trunc)}")
                    res = tc.get("result") or tc.get("output")
                    if res is not None:
                        res_str = res if isinstance(res, str) else json.dumps(res, ensure_ascii=False)
                        is_err = bool(tc.get("is_error") or tc.get("error"))
                        lines.append(
                            f"[OBSERVATION{' ERROR' if is_err else ''}] {_clip(res_str, obs_trunc)}"
                        )
            continue

        if et == "result":
            usage = ev.get("usage")
            if isinstance(usage, dict) and usage:
                lines.append(
                    "[HARNESS] turn completed | tokens in={i} cached={c} out={o} "
                    "reasoning={r}".format(
                        i=usage.get("input_tokens", 0),
                        c=usage.get("cached_input_tokens", 0),
                        o=usage.get("output_tokens", 0),
                        r=usage.get("reasoning_tokens", 0),
                    )
                )
            err = ev.get("error")
            if err:
                lines.append(f"[ERROR] {_clip(err, 1000)}")
            final_txt = ev.get("final_text")
            if isinstance(final_txt, str) and final_txt.strip():
                lines.append(f"[ASSISTANT] {_clip(final_txt.strip(), obs_trunc)}")
            continue

    rendered = "\n".join(lines).strip()
    if not rendered:
        return "(no parseable events in trajectory)"
    if len(rendered) > max_chars:
        dropped = len(rendered) - max_chars
        rendered = rendered[:max_chars] + "\n" + _TRUNC_FMT.format(n=dropped)
    return rendered


__all__ = ["AGY_SURFACE", "AGY_ROOT_ENTRIES", "AntigravitySubstrate", "render_agy_events"]
