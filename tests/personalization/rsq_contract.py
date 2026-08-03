"""The frozen contract between the RSQ questionnaire and the RSQ scorer.

`docs/execution-plan.md` D4:

    RSQ item cut: the eight safe items only (4, 11, 13, 18, 20, 21, 23, 29).
    Keep 7, 14, 17, 26, 27, 30 — they are the raw material for D3. **Never
    renumber surviving items**; the IDs are the join key to stored responses.

That last clause is the whole reason this file exists. `rsq_responses` is a
`JSONField` keyed by item ID (`{"1": 4, "2": 3, ...}` — see
`onboarding_viewmodel.dart:144`). There is no foreign key, no schema, and no
validation. The number `17` in a blob written last month means "People are
never there when you need them" only because everyone agrees it does.

Renumber the surviving items to 1..22 and nothing breaks, nothing errors, no
migration fails. Every stored response silently starts meaning a different
sentence, and every attachment score computed from them is quietly wrong — in
a report we are about to charge $39 for and hand to clinicians.

This module freezes the agreement so a violation is loud.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VIEWS_PY = REPO_ROOT / "backend-django" / "apps" / "personalization" / "views.py"
TASKS_PY = REPO_ROOT / "backend-django" / "apps" / "personalization" / "tasks.py"
MIGRATIONS_DIR = REPO_ROOT / "backend-django" / "apps" / "personalization" / "migrations"

# D4: the eight items being deleted.
ITEMS_TO_DELETE = frozenset({4, 11, 13, 18, 20, 21, 23, 29})

# D4: the six model-of-other items that must survive the cut. D3's fix scores
# these; they are the entire reason the cut is eight items and not fourteen.
MODEL_OF_OTHER_ITEMS = frozenset({7, 14, 17, 26, 27, 30})

# The 22 items that must still be served after the cut, with the exact text
# each ID must keep. Captured from `QuestionnaireView` on 2026-08-03, before
# the cut. An ID whose text changes has been renumbered, whatever the diff
# says it was doing.
SURVIVING_ITEMS: dict[int, str] = {
    1: "I find it difficult to depend on other people.",
    2: "It is very important to me to feel independent.",
    3: "I find it easy to get emotionally close to others.",
    5: "I worry that I will be hurt if I allow myself to become too close to others.",
    6: "I am comfortable without close emotional relationships.",
    7: "I am not sure that I can always depend on others to be there when I need them.",
    8: "I want to be completely emotionally intimate with others.",
    9: "I worry about being alone.",
    10: "I am comfortable depending on other people.",
    12: "I find it difficult to trust others completely.",
    14: "I want emotionally close relationships.",
    15: "I am comfortable having other people depend on me.",
    16: "I worry that others don't value me as much as I value them.",
    17: "People are never there when you need them.",
    19: "It is very important to me to feel self-sufficient.",
    22: "I prefer not to have other people depend on me.",
    24: "I am somewhat uncomfortable being close to others.",
    25: "I find that others are reluctant to get as close as I would like.",
    26: "I prefer not to depend on others.",
    27: "I know that others will be there when I need them.",
    28: "I worry about having others not accept me.",
    30: "I find it relatively easy to get close to others.",
}

# Items the scorer reads after the P0.1 fix (commit 09f8feb): the four Griffin
# & Bartholomew prototype scales, with item 26 restored to Dismissing.
SCORED_AFTER_P0_1 = frozenset({1, 2, 3, 5, 6, 8, 9, 10, 12, 15, 16, 19, 22, 24, 25, 26, 28})

# Served but feeding no prototype score, as of P0.1.
UNSCORED_AFTER_P0_1 = frozenset({4, 7, 11, 13, 14, 17, 18, 20, 21, 23, 27, 29, 30})

# Of those, the ones that survive D4's cut.
#
# `docs/engineering/rsq-scoring.md` argues these are not an error: the RSQ
# embeds Collins & Read AAS material (depend / close / anxiety) which this
# product does not compute, so ~18 of 30 items feeding the four prototypes is
# the instrument working as designed.
#
# That argument is credible and it makes D4's stated rationale stale. D4 keeps
# 7, 14, 17, 26, 27, 30 as "the raw material for D3" — but 26 is now scored as
# a Dismissing item, and the other five feed nothing and, on this analysis,
# correctly feed nothing. Which means the cut leaves five questions in an
# onboarding flow that P1 is trying to shorten, earning nothing.
#
# That is a product decision, not a QA one. Flagged to the PM 2026-08-03.
AAS_REMAINDER_KEPT_BY_D4 = frozenset({7, 14, 17, 27, 30})

VALID_STYLES = frozenset(
    {"secure", "dismissive-avoidant", "anxious-preoccupied", "fearful-avoidant"}
)


# ---------------------------------------------------------------------------
# Reading the questionnaire and the scorer without importing or running them
#
# Parsed rather than called, so these checks need no database, no Django
# settings, no authenticated request and no running stack. A contract test
# that needs infrastructure to run is a contract test that stops being run.
# ---------------------------------------------------------------------------


def served_items() -> dict[int, str]:
    """The RSQ items `QuestionnaireView` hands the client, as {id: text}."""
    tree = ast.parse(VIEWS_PY.read_text(encoding="utf-8"), filename=str(VIEWS_PY))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "rsq_questions" for t in node.targets
        ):
            items = ast.literal_eval(node.value)
            return {int(d["id"]): d["text"] for d in items}
    raise AssertionError(
        f"No `rsq_questions` list literal found in {VIEWS_PY}. The questionnaire "
        "moved or is now built dynamically. Until this helper is updated, every "
        "RSQ item-contract test is inspecting nothing."
    )


def scored_items() -> set[int]:
    """The item IDs the scorer actually reads.

    Two sources, unioned, because the scorer has already been written both
    ways in one day. It used to inline `r[3] + (6 - r[9]) + ...` in the
    function body; as of P0.1 it declares a `_PROTOTYPES` table of
    `{style: (plain_items, reversed_items)}`. Reading both means this helper
    survives the next restructure too, and `test_the_contract_is_reading_a_
    real_questionnaire` catches it if it ever stops finding anything.
    """
    tree = ast.parse(TASKS_PY.read_text(encoding="utf-8"), filename=str(TASKS_PY))
    found: set[int] = set()

    # Form 1: a module-level prototype key table.
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id.lstrip("_").upper().startswith("PROTOTYPE")
            for t in node.targets
        ):
            found |= _flatten_ints(ast.literal_eval(node.value))

    # Form 2: `r[N]` subscripts inside the scorer.
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "calculate_rsq_attachment_style":
            found |= {
                sub.slice.value
                for sub in ast.walk(node)
                if isinstance(sub, ast.Subscript)
                and isinstance(sub.value, ast.Name)
                and sub.value.id == "r"
                and isinstance(sub.slice, ast.Constant)
                and isinstance(sub.slice.value, int)
                # The neutral-default backfill loop indexes with a variable
                # (`r[i]`), not a constant, so it does not match here.
            }
            break
    else:
        raise AssertionError(
            f"No `calculate_rsq_attachment_style` function found in {TASKS_PY}. If "
            "the scorer was renamed or moved, update this helper — the join-key "
            "tests are inspecting nothing until you do."
        )

    return found


def _flatten_ints(value) -> set[int]:
    if isinstance(value, bool):
        return set()
    if isinstance(value, int):
        return {value}
    if isinstance(value, dict):
        return set().union(*(_flatten_ints(v) for v in value.values())) if value else set()
    if isinstance(value, (list, tuple, set)):
        return set().union(*(_flatten_ints(v) for v in value)) if value else set()
    return set()




def cut_has_happened() -> bool:
    """True once D4's eight items stop being served."""
    return not (ITEMS_TO_DELETE & set(served_items()))


def legacy_blob_30_items() -> dict[str, int]:
    """A response blob in the shape stored before the cut.

    Values are arbitrary but fixed: what matters is that all thirty keys are
    present, as strings, exactly as `onboarding_viewmodel.dart` writes them.
    Rows like this already exist in `personalization_profiles.rsq_responses`
    and D4 says they must stay readable with no migration.
    """
    return {str(i): (i % 5) + 1 for i in range(1, 31)}
