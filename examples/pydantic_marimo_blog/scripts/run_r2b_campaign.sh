#!/usr/bin/env bash
# Evaluate the 8 baseline Gemini coding agent configurations on the 20 Held-Out Test PRs
# (`antigravity` & `pi` x `gemini-4-argon` & `gemini-3.8-flash` x `medium` & `high`)
# via `repo2bench eval` (powered by Harbor Docker sandboxes).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EXAMPLE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DATASET_DIR="${DATASET_DIR:-$EXAMPLE_DIR/datasets/repo2bench-v2.0-test}"
OUTPUT_DIR="${OUTPUT_DIR:-$EXAMPLE_DIR/results/r2b_v2}"
CONCURRENCY="${CONCURRENCY:-4}"

echo "[repo2bench] Running 8-agent matrix evaluation on $DATASET_DIR -> $OUTPUT_DIR"
repo2bench eval \
  --dataset "$DATASET_DIR" \
  --agents antigravity,pi \
  --models gemini-4-argon,gemini-3.8-flash \
  --thinking medium,high \
  --concurrency "$CONCURRENCY" \
  --output "$OUTPUT_DIR" "$@"
