#!/usr/bin/env bash
set -euo pipefail
cd /workspace
git apply --whitespace=nowarn /solution/gold.patch || patch -p1 < /solution/gold.patch
