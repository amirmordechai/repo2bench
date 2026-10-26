"""Git history miner & signal filter for repo2bench.

Scans a Git repository's commits / merged PRs, separates source code diffs from
unit test diffs, filters out noisy commits (reverts, docs-only, lockfiles, giant
refactors), and classifies task difficulty (easy / medium / hard).
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

NOISE_SUBJECT_RE = re.compile(
    r"\b(revert|chore\(release\)|bump version|release v?\d|merge branch|typo|docs?:|ci:|style:)\b",
    re.IGNORECASE,
)

PR_NUM_RE = re.compile(r"\(#(\d+)\)")


@dataclass
class MinedCommit:
    """A candidate commit mined from a Git repository that modifies both src and tests."""

    repo_name: str
    repo_path: Path
    commit_sha: str
    parent_sha: str
    committed_date: str
    subject: str
    body: str
    pr_number: int | None
    src_files: list[str] = field(default_factory=list)
    test_files: list[str] = field(default_factory=list)
    src_patch: str = ""
    test_patch: str = ""
    src_lines_changed: int = 0
    test_lines_changed: int = 0
    difficulty: str = "medium"

    @property
    def task_id(self) -> str:
        """Deterministic Harbor task slug: <repo_short>-<difficulty>-<slug>_<short_sha>."""
        repo_short = self.repo_name.split("/")[-1].lower().replace("_", "-")
        clean_subj = PR_NUM_RE.sub("", self.subject).strip()
        clean_subj = re.sub(r"^(fix|feat|refactor|bug|enh|perf)(\([^)]+\))?:\s*", "", clean_subj, flags=re.I)
        slug = re.sub(r"[^a-z0-9]+", "_", clean_subj.lower()).strip("_")[:34].rstrip("_")
        if not slug:
            slug = f"commit_{self.commit_sha[:7]}"
        pr_part = f"pr{self.pr_number}" if self.pr_number else self.commit_sha[:7]
        return f"{repo_short}-{self.difficulty}-{slug}_{pr_part}"


def is_test_path(path: str) -> bool:
    """Return True if path is a Python unit test file."""
    if not path.endswith(".py"):
        return False
    parts = path.replace("\\", "/").split("/")
    fname = parts[-1]
    if any(p in ("tests", "test", "__tests__") for p in parts[:-1]):
        return fname.startswith("test_") or fname.endswith("_test.py") or fname == "conftest.py"
    return fname.startswith("test_") or fname.endswith("_test.py")


def is_src_path(path: str) -> bool:
    """Return True if path is a production Python source file (not docs/tests/examples/ci)."""
    if not path.endswith(".py"):
        return False
    if is_test_path(path):
        return False
    parts = path.replace("\\", "/").split("/")
    excluded_roots = {"docs", "doc", "examples", "benchmarks", "scripts", ".github", "site"}
    if parts[0] in excluded_roots:
        return False
    return True


def is_ignored_noise_path(path: str) -> bool:
    """Return True for snapshots, cassettes, lockfiles, or docs that shouldn't disqualify a commit."""
    p = path.lower()
    return (
        p.endswith((".md", ".rst", ".txt", ".lock", ".yaml", ".yml", ".json", ".toml", ".snap"))
        or "/cassettes/" in p
        or "/__snapshots__/" in p
    )


def split_unified_diff_by_file(diff_text: str) -> dict[str, str]:
    """Split a `git diff` unified patch into a mapping of {file_path: file_diff_block}."""
    by_file: dict[str, str] = {}
    current_path: str | None = None
    current_lines: list[str] = []

    for line in diff_text.splitlines(keepends=True):
        if line.startswith("diff --git "):
            if current_path is not None and current_lines:
                by_file[current_path] = "".join(current_lines)
            m = re.match(r"^diff --git a/(.*?) b/(.*?)\s*$", line)
            current_path = m.group(2) if m else None
            current_lines = [line]
        else:
            if current_path is not None:
                current_lines.append(line)

    if current_path is not None and current_lines:
        by_file[current_path] = "".join(current_lines)

    return by_file


def count_changed_lines(patch_text: str) -> int:
    """Count added + removed lines in a unified diff (excluding +++ / --- headers)."""
    count = 0
    for line in patch_text.splitlines():
        if (line.startswith("+") and not line.startswith("+++")) or (
            line.startswith("-") and not line.startswith("---")
        ):
            count += 1
    return count


def classify_difficulty(num_src_files: int, src_lines_changed: int) -> str:
    """Classify a mined commit into easy / medium / hard."""
    if num_src_files == 1 and src_lines_changed <= 30:
        return "easy"
    if num_src_files <= 2 and src_lines_changed <= 100:
        return "medium"
    return "hard"


def _git(repo_path: Path, args: list[str], timeout: int = 60) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo_path), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=True,
    )
    return proc.stdout


def mine_repository(
    repo_path: Path,
    repo_name: str | None = None,
    *,
    since: str = "2025-06-01",
    max_commits_scan: int = 500,
    limit: int = 20,
    min_src_lines: int = 2,
    max_src_lines: int = 350,
) -> list[MinedCommit]:
    """Scan a Git repository and return verified candidate commits with separated src/test patches."""
    repo_path = repo_path.resolve()
    if not repo_name:
        try:
            remote_url = _git(repo_path, ["config", "--get", "remote.origin.url"]).strip()
            m = re.search(r"github\.com[:/](.+?)(?:\.git)?$", remote_url)
            repo_name = m.group(1) if m else repo_path.name
        except Exception:
            repo_name = repo_path.name

    log_fmt = "%H%x1f%P%x1f%cI%x1f%s%x1f%b%x1e"
    cmd = ["log", f"--max-count={max_commits_scan}", f"--since={since}", f"--format={log_fmt}"]
    raw_log = _git(repo_path, cmd, timeout=120)

    candidates: list[MinedCommit] = []
    for rec in raw_log.split("\x1e"):
        rec = rec.strip()
        if not rec:
            continue
        parts = rec.split("\x1f")
        if len(parts) < 4:
            continue
        sha = parts[0].strip()
        parents = parts[1].strip().split()
        if not parents:
            continue
        parent_sha = parents[0]
        cdate = parts[2].strip()
        subject = parts[3].strip()
        body = parts[4].strip() if len(parts) > 4 else ""

        if NOISE_SUBJECT_RE.search(subject):
            continue

        # Fast path: check changed file names first before fetching full diff blobs
        try:
            names_out = _git(repo_path, ["diff-tree", "--no-commit-id", "--name-only", "-r", sha])
        except Exception:
            continue
        changed_files = [f.strip() for f in names_out.splitlines() if f.strip()]
        if not changed_files or len(changed_files) > 18:
            continue

        src_files = [f for f in changed_files if is_src_path(f)]
        test_files = [f for f in changed_files if is_test_path(f) and not f.endswith("conftest.py")]
        if not src_files or not test_files:
            continue

        # Reject commits that also modify non-Python build/frontend files (.ts, .tsx, .rs, .go)
        unknown_files = [
            f
            for f in changed_files
            if f not in src_files
            and f not in test_files
            and not is_ignored_noise_path(f)
            and not f.endswith("conftest.py")
        ]
        if unknown_files:
            continue

        # Fetch full unified diff for src_files and test_files
        try:
            full_diff = _git(
                repo_path,
                ["diff", parent_sha, sha, "--", *src_files, *test_files],
                timeout=60,
            )
        except Exception:
            continue

        by_file = split_unified_diff_by_file(full_diff)
        src_patch = "".join(by_file[f] for f in src_files if f in by_file)
        test_patch = "".join(by_file[f] for f in test_files if f in by_file)

        if not src_patch.strip() or not test_patch.strip():
            continue

        # Require real test assertions or test functions added in test_patch
        if not re.search(r"^\+\s*(async\s+)?def test_|^\+\s*assert\b", test_patch, re.MULTILINE):
            continue

        src_lines = count_changed_lines(src_patch)
        test_lines = count_changed_lines(test_patch)
        if src_lines < min_src_lines or src_lines > max_src_lines:
            continue

        pr_match = PR_NUM_RE.search(subject)
        pr_num = int(pr_match.group(1)) if pr_match else None
        diff_tier = classify_difficulty(len(src_files), src_lines)

        candidates.append(
            MinedCommit(
                repo_name=repo_name,
                repo_path=repo_path,
                commit_sha=sha,
                parent_sha=parent_sha,
                committed_date=cdate,
                subject=subject,
                body=body,
                pr_number=pr_num,
                src_files=src_files,
                test_files=test_files,
                src_patch=src_patch,
                test_patch=test_patch,
                src_lines_changed=src_lines,
                test_lines_changed=test_lines,
                difficulty=diff_tier,
            )
        )
        if len(candidates) >= limit:
            break

    return candidates
