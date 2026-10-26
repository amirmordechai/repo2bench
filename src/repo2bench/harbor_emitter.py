"""Harbor benchmark task emitter for repo2bench.

Packages a `MinedCommit` into a self-contained Harbor task folder compatible with
`harbor`, `workbuddy-bench`, and `google-research/harness2`:

tasks/<task-id>/
├── instruction.md
├── task.toml
├── environment/
│   ├── Dockerfile
│   ├── docker-compose.yaml
│   └── workspace.tar.gz
├── solution/
│   ├── solve.sh
│   └── gold.patch
└── tests/
    ├── test.sh
    ├── test_patch.diff
    ├── gold.patch
    └── scorer.py
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from .prompt_synthesizer import synthesize_instruction_md

if TYPE_CHECKING:
    from .git_miner import MinedCommit


SCORER_PY_TEMPLATE = '''#!/usr/bin/env python3
"""Standalone Harbor & WorkBuddy Bench compatible scorer for repo2bench tasks."""

import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

_IGNORE_DIRS = {"__pycache__", ".pytest_cache", ".git", "node_modules"}


def parse_patch_files(patch_text: str) -> dict[str, list[str]]:
    files: dict[str, list[str]] = {}
    current_file = None
    for line in patch_text.splitlines():
        if line.startswith("Binary files"):
            current_file = None
            continue
        m = re.match(r"^diff --git a/(.*) b/(.*)", line)
        if m:
            dest = m.group(2)
            if any(p in _IGNORE_DIRS for p in dest.split("/")) or dest.endswith(".pyc"):
                current_file = None
                continue
            current_file = dest
            files[current_file] = []
            continue
        if current_file and line.startswith("+") and not line.startswith("+++"):
            files[current_file].append(line[1:])
    return files


def normalize_line(line: str) -> str:
    s = re.sub(r"#.*$", "", line.strip()).rstrip()
    if not s:
        return ""
    s = re.sub(r"\\s+", " ", s).replace("'", '"')
    return s


def compute_file_hit_rate(agent_files: set[str], gold_files: set[str]) -> float:
    if not gold_files:
        return 1.0
    return len(agent_files & gold_files) / len(gold_files)


def compute_diff_coverage(agent_patch: dict[str, list[str]], gold_patch: dict[str, list[str]]) -> float:
    if not gold_patch:
        return 1.0
    scores = []
    for fname, gold_lines in gold_patch.items():
        gold_set = {normalize_line(l) for l in gold_lines if normalize_line(l)}
        if not gold_set:
            scores.append(1.0)
            continue
        agent_set = {normalize_line(l) for l in agent_patch.get(fname, []) if normalize_line(l)}
        scores.append(len(agent_set & gold_set) / len(gold_set))
    return sum(scores) / len(scores) if scores else 0.0


def parse_junit_xml(xml_path: str) -> tuple[int, int, int]:
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        suites = root.findall("testsuite") if root.tag == "testsuites" else [root]
        total = sum(int(s.get("tests", 0)) for s in suites)
        failures = sum(int(s.get("failures", 0)) for s in suites)
        errors = sum(int(s.get("errors", 0)) for s in suites)
        skipped = sum(int(s.get("skipped", 0)) for s in suites)
        passed = max(0, total - failures - errors - skipped)
        return passed, failures, errors
    except Exception:
        return 0, 0, 0


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--agent-patch", required=True)
    p.add_argument("--gold-patch", required=True)
    p.add_argument("--junit-xml", default=None)
    p.add_argument("--test-pass", type=float, default=None)
    p.add_argument("--output-score", default="/logs/verifier/score.json")
    p.add_argument("--output-reward", default="/logs/verifier/reward.json")
    args = p.parse_args()

    passed, failed, errors = (0, 0, 0)
    total = 0
    tpr = args.test_pass
    if args.junit_xml and Path(args.junit_xml).is_file():
        passed, failed, errors = parse_junit_xml(args.junit_xml)
        total = passed + failed + errors
        tpr = round(passed / total, 4) if total > 0 else 0.0
    if tpr is None:
        tpr = 0.0

    agent_txt = Path(args.agent_patch).read_text(errors="replace") if Path(args.agent_patch).is_file() else ""
    gold_txt = Path(args.gold_patch).read_text(errors="replace") if Path(args.gold_patch).is_file() else ""
    ap = parse_patch_files(agent_txt)
    gp = parse_patch_files(gold_txt)

    fhr = round(compute_file_hit_rate(set(ap.keys()), set(gp.keys())), 4)
    dcov = round(compute_diff_coverage(ap, gp), 4)
    status = "full_pass" if tpr >= 1.0 else ("partial_pass" if tpr > 0 else "no_pass")

    score_obj = {
        "test_pass_rate": round(tpr, 4),
        "test_status": status,
        "overall": round(tpr, 4),
        "reward": round(tpr, 4),
        "file_hit_rate": fhr,
        "diff_coverage": dcov,
        "agent_files_changed": len(ap),
        "gold_files_changed": len(gp),
        "tests_passed": passed,
        "tests_total": total,
    }
    reward_obj = {
        "reward": round(tpr, 4),
        "test_pass_rate": round(tpr, 4),
        "file_hit_rate": fhr,
        "diff_coverage": dcov,
    }

    for out_p, payload in ((args.output_score, score_obj), (args.output_reward, reward_obj)):
        path_obj = Path(out_p)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        path_obj.write_text(json.dumps(payload, indent=2) + "\\n")
    print(json.dumps(score_obj, indent=2))


if __name__ == "__main__":
    main()
'''


def _build_dockerfile(
    repo_name: str,
    extra_pip_packages: list[str] | None = None,
    base_image: str | None = None,
) -> str:
    py_path = (
        "/workspace:/workspace/pydantic_ai_slim:/workspace/pydantic_graph:"
        "/workspace/src/pydantic_ai_harness:/workspace/src/pydantic_clai2"
    )
    if base_image:
        return f"""FROM {base_image}

ENV DEBIAN_FRONTEND=noninteractive \\
    PIP_DISABLE_PIP_VERSION_CHECK=1 \\
    PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    PYTHONPATH="{py_path}"

WORKDIR /workspace
COPY workspace.tar.gz /tmp/workspace.tar.gz
RUN tar -xzf /tmp/workspace.tar.gz -C /workspace && \\
    rm -f /tmp/workspace.tar.gz && \\
    git config --global user.email "bench@repo2bench.local" && \\
    git config --global user.name "repo2bench" && \\
    git config --global --add safe.directory /workspace && \\
    git init -q && git add -A && git commit -q --no-verify -m "baseline ({repo_name})" && \\
    chmod -R a+rwX /workspace
"""
    pkgs = " ".join(
        extra_pip_packages
        or ["pytest", "pytest-asyncio", "pydantic", "httpx", "anyio", "typing-extensions"]
    )
    return f"""FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive \\
    PIP_DISABLE_PIP_VERSION_CHECK=1 \\
    PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    PYTHONPATH="{py_path}"

RUN apt-get update && apt-get install -y --no-install-recommends \\
    git curl bash procps patch ca-certificates && \\
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir {pkgs}

WORKDIR /workspace
COPY workspace.tar.gz /tmp/workspace.tar.gz
RUN tar -xzf /tmp/workspace.tar.gz -C /workspace && \\
    rm -f /tmp/workspace.tar.gz && \\
    git config --global user.email "bench@repo2bench.local" && \\
    git config --global user.name "repo2bench" && \\
    git config --global --add safe.directory /workspace && \\
    git init -q && git add -A && git commit -q --no-verify -m "baseline ({repo_name})" && \\
    chmod -R a+rwX /workspace
"""


def emit_harbor_task(
    commit: MinedCommit,
    dataset_root: Path,
    *,
    task_id_override: str | None = None,
    custom_instruction: str | None = None,
    pytest_targets: list[str] | None = None,
    extra_pip_packages: list[str] | None = None,
    subset_paths: list[str] | None = None,
    regression_test_code: str | None = None,
    base_image: str | None = None,
) -> Path:
    """Emit a complete Harbor task folder under `<dataset_root>/tasks/<task_id>/`."""
    task_id = task_id_override or commit.task_id
    task_dir = dataset_root / "tasks" / task_id
    env_dir = task_dir / "environment"
    tests_dir = task_dir / "tests"
    sol_dir = task_dir / "solution"

    for d in (env_dir, tests_dir, sol_dir):
        d.mkdir(parents=True, exist_ok=True)

    # 1. instruction.md
    instruction_text = synthesize_instruction_md(commit, custom_prompt=custom_instruction)
    (task_dir / "instruction.md").write_text(instruction_text, encoding="utf-8")

    # 2. task.toml
    base_timeout = 600 if commit.difficulty == "easy" else (900 if commit.difficulty == "medium" else 1200)
    task_toml = f'''version = "1.0"

[metadata]
id = "{task_id}"
repo = "{commit.repo_name}"
commit_sha = "{commit.commit_sha}"
parent_sha = "{commit.parent_sha}"
committed_date = "{commit.committed_date}"
difficulty = "{commit.difficulty}"
category = "code"
role = "swe"

[environment]
os = "linux"

[agent]
timeout_sec = {base_timeout}

[verifier]
timeout_sec = 300
'''
    (task_dir / "task.toml").write_text(task_toml, encoding="utf-8")

    # 3. environment/docker-compose.yaml (with host.docker.internal gateway)
    compose_yaml = """services:
  main:
    extra_hosts:
      - host.docker.internal:host-gateway
"""
    (env_dir / "docker-compose.yaml").write_text(compose_yaml, encoding="utf-8")

    # 4. environment/workspace.tar.gz at parent_sha
    ws_tar = env_dir / "workspace.tar.gz"
    archive_cmd = ["git", "-C", str(commit.repo_path), "archive", "--format=tar.gz", "-o", str(ws_tar), commit.parent_sha]
    if subset_paths:
        valid_subsets = []
        for sp in subset_paths:
            chk = subprocess.run(
                ["git", "-C", str(commit.repo_path), "cat-file", "-e", f"{commit.parent_sha}:{sp}"],
                capture_output=True,
            )
            if chk.returncode == 0:
                valid_subsets.append(sp)
        if valid_subsets:
            archive_cmd.extend(["--", *valid_subsets])
    subprocess.run(archive_cmd, check=True, timeout=120)

    # 5. environment/Dockerfile
    dockerfile_txt = _build_dockerfile(
        commit.repo_name,
        extra_pip_packages=extra_pip_packages,
        base_image=base_image,
    )
    (env_dir / "Dockerfile").write_text(dockerfile_txt, encoding="utf-8")

    # 6. tests/gold.patch & tests/test_patch.diff & tests/scorer.py & tests/test.sh
    (tests_dir / "gold.patch").write_text(commit.src_patch, encoding="utf-8")
    (tests_dir / "test_patch.diff").write_text(commit.test_patch, encoding="utf-8")
    scorer_path = tests_dir / "scorer.py"
    scorer_path.write_text(SCORER_PY_TEMPLATE, encoding="utf-8")
    scorer_path.chmod(0o755)

    if regression_test_code:
        reg_file = tests_dir / "test_pr_regression.py"
        reg_file.write_text(regression_test_code, encoding="utf-8")
        targets = "/tests/test_pr_regression.py"
    else:
        targets = " ".join(pytest_targets or commit.test_files)

    py_path = (
        "/workspace:/workspace/pydantic_ai_slim:/workspace/pydantic_graph:"
        "/workspace/src/pydantic_ai_harness:/workspace/src/pydantic_clai2"
    )
    test_sh = f"""#!/usr/bin/env bash
set -uo pipefail

cd /workspace
mkdir -p /logs/verifier

# Capture agent's source diff before applying held-out tests
git add -N . >/dev/null 2>&1 || true
BASE_SHA=$(git rev-list --max-parents=0 HEAD 2>/dev/null || echo HEAD)
git diff "$BASE_SHA" > /logs/verifier/agent.patch 2>/dev/null || true

# Apply held-out unit test diff from the PR
git apply --whitespace=nowarn /tests/test_patch.diff >/dev/null 2>&1 || \\
  patch -p1 --forward --batch < /tests/test_patch.diff >/dev/null 2>&1 || true

# Run pytest and generate JUnit XML
PYTHONPATH="{py_path}:${{PYTHONPATH:-}}" python3 -m pytest {targets} \\
  --junitxml=/logs/verifier/results.xml -q > /logs/verifier/test_output.txt 2>&1
PYTEST_RC=$?

python3 /tests/scorer.py \\
  --agent-patch /logs/verifier/agent.patch \\
  --gold-patch /tests/gold.patch \\
  --junit-xml /logs/verifier/results.xml \\
  --output-score /logs/verifier/score.json \\
  --output-reward /logs/verifier/reward.json

exit 0
"""
    test_sh_path = tests_dir / "test.sh"
    test_sh_path.write_text(test_sh, encoding="utf-8")
    test_sh_path.chmod(0o755)

    # 7. solution/gold.patch & solution/solve.sh
    (sol_dir / "gold.patch").write_text(commit.src_patch, encoding="utf-8")
    solve_sh = """#!/usr/bin/env bash
set -euo pipefail
cd /workspace
git apply --whitespace=nowarn /solution/gold.patch || patch -p1 < /solution/gold.patch
"""
    solve_sh_path = sol_dir / "solve.sh"
    solve_sh_path.write_text(solve_sh, encoding="utf-8")
    solve_sh_path.chmod(0o755)

    # 8. dataset.toml at dataset_root if not present
    ds_toml = dataset_root / "dataset.toml"
    if not ds_toml.is_file():
        ds_id = dataset_root.name
        ds_toml.write_text(
            f'''[dataset]
id = "{ds_id}"
schema = "workbuddy.dataset.v1"
version = "1.0"
description = "Custom repository benchmark generated by repo2bench"
task_count = 20

[runtime]
harness_delivery = "harness-free"
requires_harness_mount = false

[runtime.harness_delivery_by_harness]
antigravity = "split-mount"
agy-harness = "split-mount"
pi = "split-mount"
claude-code = "split-mount"
cbc-agent = "split-mount"

[layout]
task_root        = "tasks"
environment      = "environment"
workspace_archive = "environment/workspace.tar.gz"
tests            = "tests"
diff_capture     = "git"
''',
            encoding="utf-8",
        )

    return task_dir
