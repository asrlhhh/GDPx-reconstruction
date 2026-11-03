#!/usr/bin/env bash
# Harbor verifier entry point: writes 1 (pass) or 0 (fail) to /logs/verifier/reward.txt.
# Uses the interpreter that ships with the task image (no network needed).
set -uo pipefail

mkdir -p /logs/verifier
PY=/root/.venv/bin/python
if [ ! -x "$PY" ]; then PY=python3; fi

if "$PY" -c "import pytest" >/dev/null 2>&1; then
  "$PY" -m pytest -q -rA /tests/test_outputs.py
  status=$?
else
  # Fallback runner when pytest is not installed in the image.
  "$PY" - <<'PY'
import importlib.util, sys, traceback
spec = importlib.util.spec_from_file_location("t", "/tests/test_outputs.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
failed = 0
for name in sorted(n for n in dir(mod) if n.startswith("test_")):
    try:
        getattr(mod, name)()
        print(f"PASSED {name}")
    except Exception:
        failed += 1
        print(f"FAILED {name}")
        traceback.print_exc()
sys.exit(1 if failed else 0)
PY
  status=$?
fi

if [ "$status" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
exit 0
