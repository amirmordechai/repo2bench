#!/usr/bin/env bash
# Autonomous 9-Candidate Evaluation on repo2bench-v1.0 (20 tasks x 9 = 180 trials)
# Includes:
# - 8 Gemini configurations (antigravity & pi x gemini-3.8-flash & gemini-4-argon x medium & high)
# - 1 Harness² optimized Antigravity substrate configuration (agy-harness-gemini-3.8-flash-medium-r2b)
set -uo pipefail

REPO_ROOT="/opt/wb-eval/workbuddy-bench"
VERTEX_LOG_DIR="/opt/wb-eval/logs/vertex_turns_r2b"
REPORTS_DIR="/opt/wb-eval/reports/r2b"
export PATH="$REPO_ROOT/.venv/bin:/usr/local/bin:$HOME/.local/bin:$PATH"
export WB_HARNESS_WS="/opt/wb-eval/agy_optimized_ws"

mkdir -p "$VERTEX_LOG_DIR" "$REPORTS_DIR" "/opt/wb-eval/logs/r2b"

# Heartbeat loop to keep /tmp/wb_active_lock fresh while campaign runs
(
  while true; do
    touch /tmp/wb_active_lock
    sleep 60
  done
) &
HEARTBEAT_PID=$!

cleanup() {
  kill "$HEARTBEAT_PID" 2>/dev/null || true
  rm -f /tmp/wb_active_lock
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] r2b campaign script exiting."
}
trap cleanup EXIT

cd "$REPO_ROOT"

# Cross-model pairs (Flash on :3456 + Argon on :3470) so parallel jobs never share model quota
JOBS_PAIRED=(
  "antigravity-gemini-3.8-flash-medium-r2b"
  "antigravity-gemini-4-argon-medium-r2b"
  "pi-gemini-3.8-flash-medium-r2b"
  "pi-gemini-4-argon-medium-r2b"
  "antigravity-gemini-3.8-flash-high-r2b"
  "antigravity-gemini-4-argon-high-r2b"
  "pi-gemini-3.8-flash-high-r2b"
  "pi-gemini-4-argon-high-r2b"
)

run_one_job() {
  local job="$1"
  local port="${2:-3456}"
  if [ -d "$REPO_ROOT/results_r2b/$job" ]; then
    local done_count
    done_count=$(find "$REPO_ROOT/results_r2b/$job" -name "reward.json" 2>/dev/null | wc -l)
    if [ "$done_count" -ge 20 ]; then
      echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] === Skipping job=$job (already has $done_count/20 completed trials)"
      return 0
    fi
    export RESUME_JOB="results_r2b/$job"
  else
    unset RESUME_JOB || true
  fi
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] >>> Starting job=$job (proxy_port=$port)"
  PROXY_PORT="$port" ./scripts/run.sh --job "$job" \
    > "/opt/wb-eval/logs/r2b/${job}.log" 2>&1
  local rc=$?
  local final_count
  final_count=$(find "$REPO_ROOT/results_r2b/$job" -name "reward.json" 2>/dev/null | wc -l)
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] <<< Finished job=$job (rc=$rc, completed=$final_count/20)"
  return $rc
}

echo "=================================================================="
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] STARTING REPO2BENCH-V1.0 CAMPAIGN (8 CANDIDATES + HARNESS2 AGY)"
echo "=================================================================="

for (( i=0; i<${#JOBS_PAIRED[@]}; i+=2 )); do
  j1="${JOBS_PAIRED[$i]}"
  j2="${JOBS_PAIRED[$((i+1))]:-}"
  run_one_job "$j1" 3456 &
  p1=$!
  if [ -n "$j2" ]; then
    sleep 5
    run_one_job "$j2" 3470 &
    p2=$!
    wait "$p1" "$p2"
  else
    wait "$p1"
  fi
done

echo "=================================================================="
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] RUNNING HARNESS2 OPTIMIZED ANTIGRAVITY SUBSTRATE"
echo "=================================================================="
run_one_job "agy-harness-gemini-3.8-flash-medium-r2b" 3456

touch "$REPORTS_DIR/R2B_CAMPAIGN_DONE"
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] ALL 9 JOBS (180 TRIALS) COMPLETE!"

