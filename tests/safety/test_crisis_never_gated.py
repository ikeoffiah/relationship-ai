"""D7: nothing that reaches crisis resources is ever gated.

`docs/execution-plan.md` D7:

    No paywall, no trial wall, no entitlement check on the support icon, the
    safety path, or anything downstream of them. This is a hard test QA owns,
    not a convention.

This file is that test. `docs/qa/crisis-gating.md` explains what it checks and
why each check is shaped the way it is; read that before changing anything
here.

Three things this test is built to survive:

* **Code that does not exist yet.** The paywall is P0.2 and unwritten. The
  assertions therefore describe the *shape* of a gate rather than any specific
  entitlement API, and the map discovers crisis surfaces rather than listing
  them, so a screen added in March is covered without anyone remembering.
* **Going vacuously green.** The most likely way a static gate fails is by
  quietly matching nothing after a rename. `test_the_map_still_describes_the_
  product` fails if the map stops finding the anchors it is supposed to find.
* **Being outrun by the feature it guards.** Static analysis cannot prove a
  runtime path is ungated. `test_runtime_gate_test_exists_once_billing_lands`
  fails the moment billing code appears without the runtime test beside it, so
  the coverage arrives with the risk instead of after it.

Run: `pytest tests/safety/ -v` (stdlib only — no DB, no keys, no services).
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import crisis_surface_map as cmap  # noqa: E402


# ---------------------------------------------------------------------------
# 0. The map must keep describing the product
# ---------------------------------------------------------------------------


def test_the_map_still_describes_the_product():
    """A static gate's most likely failure is silence.

    Rename `features/safety/`, move the support icon, restructure the graph,
    and every assertion below starts scanning an empty set and passing. This
    test is the smoke alarm's test button: it fails when the map has stopped
    finding the things it exists to find.
    """
    tier1 = {cmap.rel(p) for p in cmap.tier1_closure()}
    discovered = {cmap.rel(p) for p in cmap.discover_crisis_files()}

    must_be_tier1 = {
        "mobile/lib/shared/widgets/support_action.dart",
        "mobile/lib/features/safety/safety_resources_screen.dart",
        "mobile/lib/features/safety/safety_resources_data.dart",
        "mobile/lib/features/chat/widgets/safety_protocol_modal.dart",
        "backend-fastapi/app/safety/layer1_rules.py",
        "backend-fastapi/app/orchestration/graph.py",
    }
    missing = sorted(must_be_tier1 - tier1)
    assert not missing, (
        "The crisis-path map no longer covers surfaces it is supposed to "
        f"cover: {missing}\n\n"
        "Either these files moved (update CRISIS_DIRS / TIER1_ANCHORS in "
        "tests/safety/crisis_surface_map.py) or the crisis path was "
        "restructured. Until the map is fixed, every D7 assertion below is "
        "scanning the wrong files and passing for the wrong reason."
    )

    # Discovery-by-symbol is the half that covers code nobody remembered to
    # register. If it stops finding the support icon's mount points, new
    # screens will silently fall outside the gate.
    mount_points = [f for f in discovered if f.endswith(".dart")]
    assert len(mount_points) >= 10, (
        f"Symbol discovery found only {len(mount_points)} Dart crisis surfaces. "
        "It should be finding every screen that mounts SupportAction. Check "
        "CRISIS_SYMBOLS_DART against how the support icon is now referenced."
    )


def test_reviewed_exceptions_have_not_gone_stale():
    """An allowlist nobody prunes becomes a list of things nobody checks."""
    stale = []
    for rel_path, reason in cmap.REVIEWED_EXCEPTIONS.items():
        path = cmap.REPO_ROOT / rel_path
        if not path.exists():
            stale.append(f"{rel_path}: file no longer exists")
            continue
        if not cmap.find_gates(cmap.read(path), strict=True):
            stale.append(f"{rel_path}: no longer contains any gate — drop the exception")
        if not reason.strip():
            stale.append(f"{rel_path}: exception has no stated reason")

    assert not stale, (
        "REVIEWED_EXCEPTIONS in tests/safety/crisis_surface_map.py is out of "
        "date:\n  " + "\n  ".join(stale) + "\n\nRemove the entries that no "
        "longer apply. Every line in that dict is a standing decision to let "
        "an entitlement concept sit near a crisis path; it should only be "
        "there while it is still true."
    )


# ---------------------------------------------------------------------------
# 1. Tier 1 — the crisis path proper. Zero tolerance.
# ---------------------------------------------------------------------------


def test_no_entitlement_concept_anywhere_on_the_crisis_path():
    """Nothing downstream of the support icon may so much as name a gate.

    This is the transitive closure: not just the support screen, but
    everything it imports, and everything those import. A gate does not have
    to be written in the file you are looking at to gate it.
    """
    violations = []
    for path in sorted(cmap.tier1_closure()):
        rel_path = cmap.rel(path)
        if rel_path in cmap.REVIEWED_EXCEPTIONS:
            continue
        for line_no, rule, matched in cmap.find_gates(cmap.read(path), strict=True):
            violations.append(f"{rel_path}:{line_no}  [{rule}]  {matched!r}")

    assert not violations, _tier1_message(violations)


def _tier1_message(violations: list[str]) -> str:
    return (
        "D7 violation — an entitlement concept appears on the crisis path.\n\n"
        + "\n".join(violations)
        + "\n\n"
        "`docs/execution-plan.md` D7: nothing that reaches crisis resources is "
        "ever gated — not the support icon, not the safety path, not anything "
        "downstream of them.\n\n"
        "These files are Tier 1: their job is getting a person in crisis to a "
        "hotline. They are held to a stricter word list than the rest of the "
        "product (see STRICT_EXTRA_PATTERNS), because prose about billing has "
        "no business here and the cost of a miss is not recoverable.\n\n"
        "If the match is genuinely benign — a comment saying 'no entitlement "
        "check here, see D7' — add it to REVIEWED_EXCEPTIONS with a reason, a "
        "reviewer and a date. Do not widen the pattern list to make this pass."
    )


# ---------------------------------------------------------------------------
# 2. Tier 2 — mount points and callers. Nothing may sit near the crisis call.
# ---------------------------------------------------------------------------


def test_no_entitlement_check_sits_next_to_a_crisis_reference():
    """A screen may gate its own premium feature. It may not gate the icon.

    Tier 2 files are ordinary product surfaces that happen to carry a crisis
    reference — `home_screen.dart` mounts the support icon and also renders
    the rest of the home screen. Banning the word `entitlement` from them
    outright would be unworkable. So the rule is proximity: a gate may exist in
    the file, but not within PROXIMITY_LINES of the crisis reference.

    Proximity is a proxy for "guards it", and a deliberately crude one. See
    the note on PROXIMITY_LINES for why the crudeness is the right trade.
    """
    violations = []
    for path in sorted(cmap.tier2_files()):
        rel_path = cmap.rel(path)
        if rel_path in cmap.REVIEWED_EXCEPTIONS:
            continue
        text = cmap.read(path)
        for gate_line, rule, gate, crisis_line, crisis in cmap.gates_near_crisis(
            text, path.suffix
        ):
            violations.append(
                f"{rel_path}:{gate_line} [{rule}] {gate!r} "
                f"sits {abs(gate_line - crisis_line)} lines from "
                f"the crisis reference {crisis!r} at line {crisis_line}"
            )

    assert not violations, (
        "D7 violation — an entitlement check sits next to a crisis reference.\n\n"
        + "\n".join(violations)
        + "\n\n"
        "Move the gate away from the crisis path, or if the two are genuinely "
        "unrelated and merely adjacent, add the file to REVIEWED_EXCEPTIONS "
        "with a reason.\n\n"
        "Read the code before adding the exception. This check exists because "
        "the cheapest way to gate a crisis path by accident is to wrap a whole "
        "build method in an entitlement branch and not notice the support icon "
        "was inside it."
    )


# ---------------------------------------------------------------------------
# 3. The route and the icon must be unconditional
# ---------------------------------------------------------------------------


def test_safety_route_is_registered_unconditionally():
    """Every SupportAction in the app pushes `/safety`. If that route stops
    being registered unconditionally, all of them become dead taps."""
    main_dart = cmap.MOBILE_LIB / "main.dart"
    assert main_dart.exists(), "mobile/lib/main.dart is missing"
    text = cmap.read(main_dart)

    assert "'/safety': (context) =>" in text, (
        "`/safety` is no longer a plain entry in the `routes:` map in "
        "mobile/lib/main.dart.\n\n"
        "D7 requires the crisis destination to be reachable with no condition "
        "attached. If it moved to onGenerateRoute, or behind any guard, that "
        "guard is now the thing standing between a person in crisis and a "
        "hotline number — even if today it only checks something harmless."
    )

    route_line = next(
        i for i, line in enumerate(text.splitlines(), 1) if "'/safety': (context) =>" in line
    )
    for line_no, rule, matched in cmap.find_gates(text):
        assert abs(line_no - route_line) > cmap.PROXIMITY_LINES, (
            f"An entitlement token [{rule}] {matched!r} appears at "
            f"main.dart:{line_no}, next to the `/safety` route registration at "
            f"line {route_line}."
        )


def test_support_icon_always_navigates():
    """The support icon's tap handler must be unconditional.

    Not `onPressed: entitled ? ... : null`, not a disabled state, not a
    "learn more" upsell. One tap, one destination, always.
    """
    support = cmap.MOBILE_LIB / "shared" / "widgets" / "support_action.dart"
    assert support.exists(), (
        "mobile/lib/shared/widgets/support_action.dart is gone. If the support "
        "icon was renamed or moved, update TIER1_ANCHORS and this test — but "
        "the invariant does not move with it."
    )
    text = cmap.read(support)

    assert "Navigator.of(context).pushNamed('/safety')" in text, (
        "The support icon no longer navigates directly to '/safety'.\n\n"
        "Whatever it does now sits between a person in crisis and the hotline "
        "list. If the navigation was legitimately refactored, this test needs "
        "to be rewritten against the new call — deliberately, not by deleting "
        "the assertion."
    )

    forbidden = [
        ("if (", "a conditional in the support widget"),
        ("Visibility(", "conditional visibility"),
        ("Offstage(", "conditional visibility"),
        ("SizedBox.shrink()", "a render-nothing branch"),
        ("onPressed: null", "a disabled state"),
    ]
    found = [why for token, why in forbidden if token in text]
    assert not found, (
        f"support_action.dart now contains {found}. The support icon is the "
        "one thing in this product that is never conditional on anything — "
        "not entitlement, not connection state, not onboarding progress. "
        "Anything that can hide or disable it is a D7 risk regardless of what "
        "it currently checks."
    )


def test_support_icon_mount_points_have_not_shrunk():
    """D7 protects reach, not just the destination.

    A paywall that never touches `support_action.dart` can still violate D7 by
    quietly dropping the icon from the screens a paying-vs-not user sees. This
    is the coverage-erosion check: the icon may be added anywhere, but a screen
    losing it has to be a decision somebody made on purpose.
    """
    present = {
        cmap.rel(p)
        for p in cmap.all_dart_files()
        if "SupportAction()" in cmap.read(p)
    }
    lost = sorted(
        f for f in SUPPORT_ICON_BASELINE if f not in present and (cmap.REPO_ROOT / f).exists()
    )
    assert not lost, (
        "These screens used to carry the support icon and no longer do:\n  "
        + "\n  ".join(lost)
        + "\n\n'One quiet icon, same destination, one tap from anywhere' is the "
        "arrangement `support_action.dart` documents and D7 depends on. "
        "Removing it from a screen shrinks how far crisis help reaches.\n\n"
        "If a removal is intended, delete the entry from SUPPORT_ICON_BASELINE "
        "in this file and say why in the commit message."
    )


# Screens carrying the support icon as of the D7 baseline (2026-08-03,
# verified against `grep -rn SupportAction mobile/lib`). `hub_scaffold.dart`
# covers every hub screen at once.
SUPPORT_ICON_BASELINE = {
    "mobile/lib/features/bliss/views/calendar_screen.dart",
    "mobile/lib/features/chat/chat_screen.dart",
    "mobile/lib/features/consent/consent_dashboard_screen.dart",
    "mobile/lib/features/couple_chat/views/couple_chat_screen.dart",
    "mobile/lib/features/history/session_detail_screen.dart",
    "mobile/lib/features/history/session_history_screen.dart",
    "mobile/lib/features/home/views/home_screen.dart",
    "mobile/lib/features/hubs/hub_scaffold.dart",
    "mobile/lib/features/notifications/notification_center_screen.dart",
    "mobile/lib/features/settings/about_screen.dart",
    "mobile/lib/features/settings/security_settings_screen.dart",
    "mobile/lib/features/settings/settings_screen.dart",
}


# ---------------------------------------------------------------------------
# 4. Backend contracts — parsed, not imported, so this runs anywhere
# ---------------------------------------------------------------------------


def _parse(path: Path) -> ast.Module:
    return ast.parse(cmap.read(path), filename=str(path))


def _find_function(tree: ast.Module, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


def test_crisis_resources_takes_no_caller_supplied_arguments():
    """`crisis_resources()` reads config and nothing else.

    The natural way to gate hotlines is to make this function personalised —
    `crisis_resources(user)` — and then, one refactor later, to filter by
    entitlement inside it. Keeping the signature empty makes that change
    impossible to land quietly: it cannot happen without this test going red.
    """
    router = cmap.FASTAPI_APP / "api" / "chat_router.py"
    assert router.exists(), "backend-fastapi/app/api/chat_router.py is missing"

    fn = _find_function(_parse(router), "crisis_resources")
    assert fn is not None, (
        "`crisis_resources` is gone from chat_router.py. It is the function "
        "that puts hotline numbers in front of someone the classifier has "
        "flagged. If it moved, this test must move with it."
    )

    args = fn.args
    total = (
        len(args.posonlyargs)
        + len(args.args)
        + len(args.kwonlyargs)
        + (1 if args.vararg else 0)
        + (1 if args.kwarg else 0)
    )
    assert total == 0, (
        "`crisis_resources()` has grown parameters: "
        f"{[a.arg for a in args.posonlyargs + args.args + args.kwonlyargs]}.\n\n"
        "It is deliberately caller-independent. The moment it takes a user, a "
        "session or a request, it becomes possible for the resource list to "
        "differ between two people — and the only reason it ever would is a "
        "check D7 forbids. If there is a real need to regionalise, do it from "
        "configuration, not from the caller."
    )


def test_safety_prescreen_is_the_first_thing_that_runs():
    """Nothing may be inserted ahead of the safety screen.

    A paywall node added at the top of the counseling graph would gate the
    crisis classifier itself: an unpaid user's message would never be screened,
    so a crisis in it would never be detected. That is the worst available
    version of a D7 violation, and it is one line of graph wiring away.
    """
    graph_py = cmap.FASTAPI_APP / "orchestration" / "graph.py"
    assert graph_py.exists(), "backend-fastapi/app/orchestration/graph.py is missing"
    tree = _parse(graph_py)

    entry_points = [
        node.args[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "set_entry_point"
        and node.args
        and isinstance(node.args[0], ast.Constant)
    ]

    assert entry_points == ["node_1_safety_prescreen"], (
        f"The counseling graph's entry point is {entry_points}, not "
        "['node_1_safety_prescreen'].\n\n"
        "Safety pre-screening runs first, before consent, memory, strategy or "
        "the model. Anything placed ahead of it decides whether a message gets "
        "screened for crisis at all."
    )


def test_escalation_reaches_the_safety_protocol_directly():
    """The prescreen's escalation branch goes straight to SAFETY_PROTOCOL."""
    graph_py = cmap.FASTAPI_APP / "orchestration" / "graph.py"
    tree = _parse(graph_py)

    targets: list[str] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_conditional_edges"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value == "node_1_safety_prescreen"
        ):
            for arg in node.args[1:]:
                if isinstance(arg, ast.Dict):
                    targets = [
                        v.value for v in arg.values if isinstance(v, ast.Constant)
                    ]

    assert "SAFETY_PROTOCOL" in targets, (
        f"The safety prescreen's conditional edges go to {targets}, which does "
        "not include SAFETY_PROTOCOL.\n\n"
        "An escalated message must be able to leave the graph through the "
        "safety exit without passing through any other node. Every node added "
        "in between is a node that could fail, stall, or check something."
    )


# ---------------------------------------------------------------------------
# 5. The tripwire
# ---------------------------------------------------------------------------

RUNTIME_TEST = Path(__file__).parent / "test_crisis_runtime_ungated.py"


def test_runtime_gate_test_exists_once_billing_lands():
    """Static analysis cannot prove a runtime path is ungated.

    Everything above reads source. None of it can prove that an unpaid account
    actually receives `safety_triggered` with resources attached, because
    proving that needs a request, an account, and an entitlement to withhold —
    none of which exist yet.

    So this test watches for the day they do. The moment payment code appears
    anywhere in the product, the runtime test must exist beside it. That way
    the coverage lands with the risk rather than in a follow-up ticket that
    competes with launch.

    `docs/qa/crisis-gating.md` §4 is the spec for what that test must assert.
    """
    if not cmap.paywall_exists_in_product():
        pytest.skip("No billing code in the product yet (P0.2 unstarted).")

    assert RUNTIME_TEST.exists(), (
        "Payment code now exists in the product, but "
        f"{RUNTIME_TEST.relative_to(cmap.REPO_ROOT)} does not.\n\n"
        "Every assertion in this file is static: it reads source and reasons "
        "about words. That was enough while there was nothing to gate with. "
        "Now there is, and D7 needs proof that an account holding no "
        "entitlement still reaches crisis resources at runtime — not proof "
        "that nobody typed the word 'entitlement' near the code.\n\n"
        "Write the runtime test to the spec in docs/qa/crisis-gating.md §4. "
        "It is four assertions and it is the difference between D7 being "
        "tested and D7 being asserted."
    )
