#!/usr/bin/env python3
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
    s = re.sub(r"\s+", " ", s).replace("'", '"')
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
        path_obj.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(score_obj, indent=2))


if __name__ == "__main__":
    main()
