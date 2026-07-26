"""
Safety pipeline evaluation harness.

Runs the labeled set through the real pre-screen pipeline (Layer 1 + the
Layer 2/3 fallbacks that run without API keys) and reports precision/recall.

As a CI gate it asserts the two properties the keyword/regex floor must hold:
  * clear crises are caught (recall on 'crisis_clear' is high), and
  * no clearly-safe message is flagged (zero false positives).

Paraphrase recall is reported but NOT gated — it is the calibration target that
the embedding (Layer 2) and LLM (Layer 3) layers close once keys are configured.
Run directly (`python -m tests.validation.test_safety_eval`) to print the report.
"""

import asyncio

import pytest

from app.orchestration.graph import SafetyPreScreener
from tests.validation.safety_dataset import CASES

# A turn is "flagged" for intervention when the pre-screen score clears this bar
# (matches the graph's "critical/elevated" routing).
FLAG_THRESHOLD = 0.7


async def _score(message: str) -> float:
    return await SafetyPreScreener.screen(message, {})


async def evaluate() -> dict:
    rows = []
    for message, kind, category in CASES:
        score = await _score(message)
        rows.append({"message": message, "kind": kind, "category": category,
                     "score": score, "flagged": score >= FLAG_THRESHOLD})

    def recall(kind: str) -> tuple[int, int]:
        items = [r for r in rows if r["kind"] == kind]
        caught = sum(1 for r in items if r["flagged"])
        return caught, len(items)

    clear_caught, clear_total = recall("crisis_clear")
    para_caught, para_total = recall("crisis_paraphrase")
    safe = [r for r in rows if r["kind"] == "safe"]
    false_positives = [r for r in safe if r["flagged"]]

    return {
        "rows": rows,
        "clear_recall": clear_caught / clear_total if clear_total else 1.0,
        "clear_caught": clear_caught,
        "clear_total": clear_total,
        "paraphrase_recall": para_caught / para_total if para_total else 1.0,
        "paraphrase_caught": para_caught,
        "paraphrase_total": para_total,
        "false_positives": false_positives,
        "safe_total": len(safe),
    }


def _print_report(result: dict) -> None:
    print("\n=== Safety pipeline evaluation (keyword/regex floor) ===")
    print(f"Clear-crisis recall:      {result['clear_caught']}/{result['clear_total']} "
          f"({result['clear_recall']:.0%})")
    print(f"Paraphrase-crisis recall: {result['paraphrase_caught']}/{result['paraphrase_total']} "
          f"({result['paraphrase_recall']:.0%})  [target for Layer 2/3 with keys]")
    print(f"False positives on safe:  {len(result['false_positives'])}/{result['safe_total']}")
    for r in result["false_positives"]:
        print(f"   ! flagged safe: {r['message']!r} (score={r['score']:.2f})")
    misses = [r for r in result["rows"] if r["kind"].startswith("crisis") and not r["flagged"]]
    if misses:
        print("  Missed crises (recall gaps — enable/calibrate Layer 2/3):")
        for r in misses:
            print(f"   - [{r['kind']}] {r['message']!r}")


@pytest.mark.asyncio
async def test_clear_crises_are_caught():
    result = await evaluate()
    _print_report(result)
    assert result["clear_recall"] >= 0.9, (
        f"clear-crisis recall {result['clear_recall']:.0%} below floor; "
        "Layer 1 rules regressed"
    )


@pytest.mark.asyncio
async def test_no_false_positives_on_safe_messages():
    result = await evaluate()
    assert not result["false_positives"], (
        "safe messages flagged as crisis: "
        + ", ".join(repr(r["message"]) for r in result["false_positives"])
    )


if __name__ == "__main__":
    _print_report(asyncio.run(evaluate()))
