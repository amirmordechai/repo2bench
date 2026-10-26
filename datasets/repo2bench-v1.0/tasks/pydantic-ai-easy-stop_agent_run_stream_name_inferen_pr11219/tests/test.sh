#!/usr/bin/env bash
set -uo pipefail

cd /workspace
mkdir -p /logs/verifier

# Capture agent's source diff before applying held-out tests
git add -N . >/dev/null 2>&1 || true
BASE_SHA=$(git rev-list --max-parents=0 HEAD 2>/dev/null || echo HEAD)
git diff "$BASE_SHA" -- . ":!GEMINI.md" ":!AGENTS.md" ":!.agents" ":!scripts/verify_diff.py" > /logs/verifier/agent.patch 2>/dev/null || true

# Apply held-out unit test diff from the PR
git apply --whitespace=nowarn /tests/test_patch.diff >/dev/null 2>&1 || \
  patch -p1 --forward --batch < /tests/test_patch.diff >/dev/null 2>&1 || true

# Run pytest and generate JUnit XML
PYTHONPATH="/workspace:/workspace/pydantic_ai_slim:/workspace/pydantic_graph:/workspace/src/pydantic_ai_harness:/workspace/src/pydantic_clai2:${PYTHONPATH:-}" python3 -m pytest /tests/test_pr_regression.py \
  --junitxml=/logs/verifier/results.xml -q > /logs/verifier/test_output.txt 2>&1
PYTEST_RC=$?

python3 /tests/scorer.py \
  --agent-patch /logs/verifier/agent.patch \
  --gold-patch /tests/gold.patch \
  --junit-xml /logs/verifier/results.xml \
  --output-score /logs/verifier/score.json \
  --output-reward /logs/verifier/reward.json

exit 0
