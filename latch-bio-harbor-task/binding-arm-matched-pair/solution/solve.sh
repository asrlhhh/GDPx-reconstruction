#!/usr/bin/env bash
# Oracle solution: runs the reference analysis with the task image's analysis venv and writes
# /workspace/analysis_output.json.
set -euo pipefail
SOLUTION_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
/root/.venv/bin/python "${SOLUTION_DIR}/solve.py"
cat /workspace/analysis_output.json
echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT
