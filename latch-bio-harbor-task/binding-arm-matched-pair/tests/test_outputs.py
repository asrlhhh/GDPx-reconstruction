"""Verifier for the binding-arm matched-pair task.

The agent must write /workspace/analysis_output.json containing exactly
    {"matched_pair": ["<construct id>", "<construct id>"]}
Grading is order-insensitive: the pair must equal the expected one-arm / two-arm pair.
"""
import json
from pathlib import Path

OUTPUT = Path("/workspace/analysis_output.json")

# Expected answer (one single-arm construct and one two-arm construct). See solution/solve.py for the
# derivation; order does not matter.
EXPECTED_PAIR = frozenset({"construct_05", "construct_10"})

VALID_IDS = {f"construct_{i:02d}" for i in range(1, 13)}


def _load():
    assert OUTPUT.exists(), f"{OUTPUT} was not written"
    text = OUTPUT.read_text()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:  # pragma: no cover - reported as failure
        raise AssertionError(f"analysis_output.json is not valid JSON: {exc}") from exc
    assert isinstance(data, dict), "top-level JSON value must be an object"
    return data


def test_output_schema():
    data = _load()
    assert "matched_pair" in data, "missing key 'matched_pair'"
    pair = data["matched_pair"]
    assert isinstance(pair, list), "'matched_pair' must be a list"
    assert len(pair) == 2, "'matched_pair' must carry exactly two construct identifiers"
    assert all(isinstance(x, str) for x in pair), "construct identifiers must be strings"
    assert len(set(pair)) == 2, "the two construct identifiers must differ"
    unknown = [x for x in pair if x not in VALID_IDS]
    assert not unknown, f"identifiers not found in the data (must match exactly): {unknown}"


def test_matched_pair():
    pair = _load()["matched_pair"]
    assert frozenset(pair) == EXPECTED_PAIR, f"matched_pair {sorted(pair)} is not the matched pair"
