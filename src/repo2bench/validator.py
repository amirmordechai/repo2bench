"""Fail-to-Pass (`nop == 0.0` -> `oracle == 1.0`) task validator for repo2bench.

Verifies that a Harbor task emitted by `repo2bench` is deterministic and solvable:
1. Pre-Fix (`nop` state): Applying only `tests/test_patch.diff` on the baseline workspace
   MUST fail at least one unit test (`reward < 1.0`, ideally `0.0`).
2. Post-Fix (`oracle` state): Applying `solution/gold.patch` + `tests/test_patch.diff`
   MUST pass 100% of the target unit tests (`reward == 1.0`).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ValidationResult:
    task_id: str
    valid: bool
    nop_pass_rate: float
    oracle_pass_rate: float
    nop_tests_total: int
    oracle_tests_total: int
    error: str | None = None


def _run_state_check(
    task_dir: Path,
    apply_gold: bool,
    python_bin: str = "python3",
) -> tuple[float, int, str]:
    """Unpack workspace.tar.gz into a temporary dir, optionally apply gold.patch, and run scorer."""
    ws_tar = task_dir / "environment" / "workspace.tar.gz"
    test_patch = task_dir / "tests" / "test_patch.diff"
    gold_patch = task_dir / "solution" / "gold.patch"
    scorer_py = task_dir / "tests" / "scorer.py"
    test_sh = (task_dir / "tests" / "test.sh").read_text(encoding="utf-8")

    # Extract pytest target arguments from test.sh
    pytest_targets = "tests"
    for line in test_sh.splitlines():
        if "-m pytest " in line:
            after = line.split("-m pytest ", 1)[1]
            pytest_targets = after.split("--junitxml")[0].strip().rstrip("\\").strip()
            break

    with tempfile.TemporaryDirectory(prefix=f"r2b_{task_dir.name}_") as tmp:
        tmp_path = Path(tmp)
        ws_dir = tmp_path / "workspace"
        logs_dir = tmp_path / "logs"
        ws_dir.mkdir(parents=True, exist_ok=True)
        logs_dir.mkdir(parents=True, exist_ok=True)

        subprocess.run(["tar", "-xzf", str(ws_tar), "-C", str(ws_dir)], check=True, timeout=60)
        subprocess.run(["git", "init", "-q"], cwd=ws_dir, check=True)
        subprocess.run(["git", "config", "user.email", "bench@local"], cwd=ws_dir, check=True)
        subprocess.run(["git", "config", "user.name", "bench"], cwd=ws_dir, check=True)
        subprocess.run(["git", "add", "-A"], cwd=ws_dir, check=True)
        subprocess.run(["git", "commit", "-q", "--no-verify", "-m", "base"], cwd=ws_dir, check=True)

        if apply_gold and gold_patch.is_file() and gold_patch.stat().st_size > 0:
            res_gold = subprocess.run(
                ["git", "apply", "--whitespace=nowarn", str(gold_patch)],
                cwd=ws_dir,
                capture_output=True,
                text=True,
            )
            if res_gold.returncode != 0:
                subprocess.run(
                    ["patch", "-p1", "--forward", "--batch", "-i", str(gold_patch)],
                    cwd=ws_dir,
                    capture_output=True,
                    text=True,
                )

        # Capture agent.patch
        agent_patch_file = logs_dir / "agent.patch"
        diff_out = subprocess.run(["git", "diff", "HEAD"], cwd=ws_dir, capture_output=True, text=True)
        agent_patch_file.write_text(diff_out.stdout or "", encoding="utf-8")

        # Apply held-out test_patch.diff
        if test_patch.is_file() and test_patch.stat().st_size > 0:
            res_test = subprocess.run(
                ["git", "apply", "--whitespace=nowarn", str(test_patch)],
                cwd=ws_dir,
                capture_output=True,
                text=True,
            )
            if res_test.returncode != 0:
                subprocess.run(
                    ["patch", "-p1", "--forward", "--batch", "-i", str(test_patch)],
                    cwd=ws_dir,
                    capture_output=True,
                    text=True,
                )

        junit_xml = logs_dir / "results.xml"
        env = os.environ.copy()
        extra_paths = [
            str(ws_dir),
            str(ws_dir / "pydantic_ai_slim"),
            str(ws_dir / "pydantic_graph"),
            str(ws_dir / "src" / "pydantic_ai_harness"),
            str(ws_dir / "src" / "pydantic_clai2"),
        ]
        existing_py = env.get("PYTHONPATH", "")
        if existing_py:
            extra_paths.append(existing_py)
        env["PYTHONPATH"] = ":".join(extra_paths)

        reg_test_src = task_dir / "tests" / "test_pr_regression.py"
        if reg_test_src.is_file():
            reg_test_dst = tmp_path / "test_pr_regression.py"
            shutil.copy2(reg_test_src, reg_test_dst)
            target_args = [str(reg_test_dst)]
        else:
            target_args = pytest_targets.split()

        runner_code = """
import sys, importlib.util, inspect, asyncio, traceback, xml.etree.ElementTree as ET
from pathlib import Path

targets = sys.argv[1:-1]
xml_out = sys.argv[-1]

# Try pytest first if installed
try:
    import pytest
    rc = pytest.main([*targets, f"--junitxml={xml_out}", "-q"])
    if Path(xml_out).is_file():
        sys.exit(0)
except ImportError:
    pass

# Fallback stdlib runner for test_* functions in target files
suite = ET.Element("testsuite", name="repo2bench")
total = failures = errors = 0
for t in targets:
    p = Path(t)
    if not p.is_file():
        continue
    spec = importlib.util.spec_from_file_location(p.stem, p)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:
        total += 1
        errors += 1
        tc = ET.SubElement(suite, "testcase", classname=p.stem, name="import_module")
        ET.SubElement(tc, "error", message=str(e)).text = traceback.format_exc()
        continue
    for name, fn in inspect.getmembers(mod, inspect.isfunction):
        if not name.startswith("test_"):
            continue
        total += 1
        tc = ET.SubElement(suite, "testcase", classname=p.stem, name=name)
        try:
            if inspect.iscoroutinefunction(fn):
                asyncio.run(fn())
            else:
                fn()
        except AssertionError as e:
            failures += 1
            ET.SubElement(tc, "failure", message=str(e)).text = traceback.format_exc()
        except Exception as e:
            errors += 1
            ET.SubElement(tc, "error", message=str(e)).text = traceback.format_exc()

suite.set("tests", str(total))
suite.set("failures", str(failures))
suite.set("errors", str(errors))
suite.set("skipped", "0")
ET.ElementTree(suite).write(xml_out, encoding="utf-8", xml_declaration=True)
"""
        pytest_proc = subprocess.run(
            [python_bin, "-c", runner_code, *target_args, str(junit_xml)],
            cwd=ws_dir,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )

        score_json = logs_dir / "score.json"
        reward_json = logs_dir / "reward.json"
        subprocess.run(
            [
                python_bin,
                str(scorer_py),
                "--agent-patch",
                str(agent_patch_file),
                "--gold-patch",
                str(gold_patch),
                "--junit-xml",
                str(junit_xml),
                "--output-score",
                str(score_json),
                "--output-reward",
                str(reward_json),
            ],
            cwd=ws_dir,
            check=True,
            capture_output=True,
            text=True,
        )

        data = json.loads(score_json.read_text(encoding="utf-8"))
        return (
            float(data.get("test_pass_rate", 0.0)),
            int(data.get("tests_total", 0)),
            (pytest_proc.stdout or "") + "\n" + (pytest_proc.stderr or ""),
        )


def validate_harbor_task(task_dir: Path, python_bin: str = "python3") -> ValidationResult:
    """Validate that a Harbor task fails before the fix (`nop < 1.0`) and passes after (`oracle == 1.0`)."""
    task_id = task_dir.name
    try:
        nop_rate, nop_total, nop_out = _run_state_check(task_dir, apply_gold=False, python_bin=python_bin)
        oracle_rate, oracle_total, oracle_out = _run_state_check(task_dir, apply_gold=True, python_bin=python_bin)
    except Exception as exc:
        return ValidationResult(
            task_id=task_id,
            valid=False,
            nop_pass_rate=0.0,
            oracle_pass_rate=0.0,
            nop_tests_total=0,
            oracle_tests_total=0,
            error=str(exc),
        )

    valid = (oracle_total > 0) and (oracle_rate >= 1.0) and (nop_rate < 1.0)
    err = None
    if not valid:
        err = (
            f"Validation gate failed (nop_rate={nop_rate}, oracle_rate={oracle_rate}, "
            f"oracle_total={oracle_total}). Oracle output tail: {oracle_out[-400:]}"
        )
    return ValidationResult(
        task_id=task_id,
        valid=valid,
        nop_pass_rate=nop_rate,
        oracle_pass_rate=oracle_rate,
        nop_tests_total=nop_total,
        oracle_tests_total=oracle_total,
        error=err,
    )


def validate_dataset(dataset_root: Path, python_bin: str = "python3") -> list[ValidationResult]:
    """Validate all tasks under `<dataset_root>/tasks/`."""
    tasks_dir = dataset_root / "tasks" if (dataset_root / "tasks").is_dir() else dataset_root
    results: list[ValidationResult] = []
    for task_dir in sorted(d for d in tasks_dir.iterdir() if d.is_dir()):
        results.append(validate_harbor_task(task_dir, python_bin=python_bin))
    return results
