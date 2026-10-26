"""Contract-aware task prompt synthesizer for repo2bench.

Generates a clean, self-contained `instruction.md` from a mined commit's PR/Issue
description and unit test expectations (`test_patch`), ensuring the coding agent
knows the exact public function/class/attribute names asserted by the hidden unit
tests without leaking the developer's source code fix (`src_patch`).
"""

from __future__ import annotations

import ast
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .git_miner import MinedCommit


def extract_test_contract_from_diff(test_patch: str) -> dict[str, list[str]]:
    """Extract added test function names, asserted expressions, and public symbols from test_patch."""
    added_lines: list[str] = []
    test_funcs: list[str] = []
    assert_snippets: list[str] = []
    symbols: set[str] = set()

    for line in test_patch.splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        code_line = line[1:]
        added_lines.append(code_line)

        m_fn = re.match(r"^\s*(?:async\s+)?def\s+(test_[A-Za-z0-9_]+)\s*\(", code_line)
        if m_fn:
            test_funcs.append(m_fn.group(1))

        stripped = code_line.strip()
        if stripped.startswith(("assert ", "with pytest.raises(")):
            if len(stripped) <= 140 and stripped not in assert_snippets:
                assert_snippets.append(stripped)

    # Parse added lines with AST where possible, and fallback to regex identifier extraction
    joined = "\n".join(added_lines)
    try:
        tree = ast.parse(joined)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    symbols.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    symbols.add(node.func.attr)
            elif isinstance(node, ast.Attribute):
                symbols.add(node.attr)
    except SyntaxError:
        for m in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?)\s*\(", joined):
            sym = m.group(1)
            if not sym.startswith("test_") and sym not in {"assert", "pytest", "len", "str", "int", "dict", "list"}:
                symbols.add(sym)

    # Filter out generic test helpers
    ignore_syms = {
        "pytest", "raises", "mark", "parametrize", "approx", "monkeypatch",
        "isinstance", "len", "str", "int", "float", "list", "dict", "set", "tuple",
        "append", "extend", "get", "items", "keys", "values", "strip", "split",
    }
    clean_symbols = sorted(s for s in symbols if s not in ignore_syms and not s.startswith("test_"))[:15]

    return {
        "test_functions": test_funcs[:8],
        "assertions": assert_snippets[:8],
        "symbols": clean_symbols,
    }


def despoil_commit_to_goal(text: str, src_files: list[str] | tuple[str, ...] = ()) -> str:
    """Rewrite a post-hoc commit message into a pre-commit, goal-oriented prompt without leaking file paths or how-to diffs."""
    out = re.sub(r"\s*\(#\d+\)\s*$", "", text).strip()
    # Strip explicit source file paths so the agent must search the repository itself
    for sf in src_files:
        out = out.replace(f"`{sf}`", "the codebase").replace(sf, "the codebase")
    out = re.sub(r"`?[A-Za-z0-9_./-]+\.(?:py|ts|tsx|js|rs|go)`?", "the relevant module", out)
    # Strip post-hoc 'by <implementation detail>' clauses from commit titles/lines
    out = re.sub(
        r"\s+by\s+(?:adding|removing|deleting|changing|updating|replacing|passing|setting|calling|using)\b[^.\n]*",
        "",
        out,
        flags=re.IGNORECASE,
    )
    return out.strip()


def _test_name_to_goal_bullet(fn_name: str) -> str:
    """Convert `test_single_digit_port_accepted` into a human-readable scenario requirement."""
    clean = re.sub(r"^test_?", "", fn_name).replace("_", " ").strip()
    return clean[:1].upper() + clean[1:] if clean else fn_name


def synthesize_instruction_md(
    commit: MinedCommit,
    custom_prompt: str | None = None,
    *,
    black_box: bool = True,
) -> str:
    """Build a self-contained, pre-commit goal-oriented Harbor `instruction.md` for a mined commit.

    When `black_box=True` (default), strips target file paths, commit-message implementation
    spoilers, and raw test assertion code so the agent receives a realistic user-facing goal
    as if written BEFORE the commit existed.
    """
    if custom_prompt and custom_prompt.strip():
        return custom_prompt.strip() + "\n"

    contract = extract_test_contract_from_diff(commit.test_patch)
    raw_title = re.sub(r"\s*\(#\d+\)\s*$", "", commit.subject).strip()
    goal_title = despoil_commit_to_goal(raw_title, commit.src_files) if black_box else raw_title

    # Clean commit body (strip Co-authored-by / Signed-off-by footers)
    body_lines = [
        ln
        for ln in commit.body.splitlines()
        if not re.match(r"^(Co-authored-by|Signed-off-by|Reviewed-by):", ln, re.I)
    ]
    raw_body = "\n".join(body_lines).strip()
    clean_body = despoil_commit_to_goal(raw_body, commit.src_files) if (black_box and raw_body) else raw_body

    sections: list[str] = [
        f"# Goal: {goal_title}",
        "",
        f"**Repository:** `{commit.repo_name}`",
        "",
        "## Context & Goal",
    ]

    if clean_body:
        sections.append(clean_body)
    else:
        sections.append(
            f"Resolve the issue or support the capability described by: **{goal_title}** in `{commit.repo_name}`."
        )

    if not black_box:
        sections.extend(
            [
                "",
                "## Target Files & Module Scope",
                "Inspect and update the relevant implementation in:",
            ]
        )
        for sf in commit.src_files:
            sections.append(f"- `{sf}`")

    if contract["test_functions"] or contract["symbols"]:
        sections.extend(
            [
                "",
                "## Acceptance Criteria",
                "Ensure your solution satisfies the following behavioral goals and public interface expectations:",
            ]
        )
        if contract["test_functions"]:
            sections.append("- **Behavioral scenarios that must succeed:**")
            for fn in contract["test_functions"][:6]:
                sections.append(f"  - {_test_name_to_goal_bullet(fn)}")
        if contract["symbols"]:
            syms_str = ", ".join(f"`{s}`" for s in contract["symbols"][:8])
            sections.append(f"- **Public symbols / entrypoints involved:** {syms_str}")
        if not black_box and contract["assertions"]:
            sections.append("- **Key expectations checked by the test suite:**")
            for a in contract["assertions"][:5]:
                sections.append(f"  - `{a}`")

    sections.extend(
        [
            "",
            "## Workflow",
            "1. Search `/workspace` to identify the relevant module(s) and root cause.",
            "2. Implement a clean, minimal solution that satisfies the acceptance criteria without introducing regressions.",
            "3. Verify your changes against relevant unit tests before finishing.",
            "",
        ]
    )

    return "\n".join(sections)

