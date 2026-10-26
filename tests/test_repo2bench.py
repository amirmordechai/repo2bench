"""End-to-end unit and integration tests for repo2bench."""

from __future__ import annotations

import subprocess
from pathlib import Path

from repo2bench.git_miner import classify_difficulty, is_src_path, is_test_path, mine_repository
from repo2bench.harbor_emitter import emit_harbor_task
from repo2bench.prompt_synthesizer import extract_test_contract_from_diff, synthesize_instruction_md
from repo2bench.validator import validate_harbor_task


def test_path_classifiers() -> None:
    assert is_test_path("tests/test_models.py")
    assert is_test_path("marimo/_utils/test_url.py")
    assert not is_test_path("pydantic_ai/models/cohere.py")
    assert is_src_path("pydantic_ai/models/cohere.py")
    assert not is_src_path("docs/index.md")
    assert classify_difficulty(1, 12) == "easy"
    assert classify_difficulty(2, 55) == "medium"
    assert classify_difficulty(3, 140) == "hard"


def test_end_to_end_mine_emit_validate(tmp_path: Path) -> None:
    """Create a synthetic Git repo with a real bug-fix PR commit, mine it, emit a Harbor task, and verify nop=0 -> oracle=1."""
    repo = tmp_path / "sample_repo"
    (repo / "pkg").mkdir(parents=True)
    (repo / "tests").mkdir(parents=True)

    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "dev@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Dev"], cwd=repo, check=True)

    # Baseline commit (has a bug: single-digit port rejected)
    (repo / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (repo / "pkg" / "url.py").write_text(
        "import re\n\ndef is_valid_port(url: str) -> bool:\n    return bool(re.search(r':\\d{2,5}$', url))\n",
        encoding="utf-8",
    )
    (repo / "tests" / "test_url.py").write_text(
        "from pkg.url import is_valid_port\n\ndef test_standard_port() -> None:\n    assert is_valid_port('http://localhost:8080')\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "Initial commit"], cwd=repo, check=True)

    # Bug-fix PR commit (fixes single-digit ports and adds unit test)
    (repo / "pkg" / "url.py").write_text(
        "import re\n\ndef is_valid_port(url: str) -> bool:\n    return bool(re.search(r':\\d{1,5}$', url))\n",
        encoding="utf-8",
    )
    (repo / "tests" / "test_url.py").write_text(
        "from pkg.url import is_valid_port\n\ndef test_standard_port() -> None:\n    assert is_valid_port('http://localhost:8080')\n\ndef test_single_digit_port() -> None:\n    assert is_valid_port('http://localhost:9')\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "fix: accept single-digit ports in is_valid_port (#42)"], cwd=repo, check=True)

    mined = mine_repository(repo, repo_name="acme/sample-repo", since="2020-01-01", limit=5)
    assert len(mined) == 1
    c = mined[0]
    assert c.pr_number == 42
    assert c.src_files == ["pkg/url.py"]
    assert c.test_files == ["tests/test_url.py"]

    contract = extract_test_contract_from_diff(c.test_patch)
    assert "test_single_digit_port" in contract["test_functions"]
    assert "is_valid_port" in contract["symbols"]

    instr = synthesize_instruction_md(c)
    assert "is_valid_port" in instr
    assert "\\d{1,5}" not in instr  # No implementation spoiler!

    out_ds = tmp_path / "dataset"
    task_dir = emit_harbor_task(c, out_ds)
    assert (task_dir / "task.toml").is_file()
    assert (task_dir / "instruction.md").is_file()
    assert (task_dir / "environment" / "workspace.tar.gz").is_file()

    val = validate_harbor_task(task_dir)
    assert val.valid, f"Validation failed: {val}"
    assert val.nop_pass_rate < 1.0
    assert val.oracle_pass_rate == 1.0

