"""Mutation tests for the D7 gate: prove it goes red when it should.

`test_crisis_never_gated.py` passes today. That is not evidence it works — a
test that asserts nothing passes too, and a regex that matches nothing passes
most confidently of all. D7 is the one guarantee in this product where "we have
a test for it" needs to mean something, so the gate gets its own tests.

Each case below plants a violation of the kind the engineer is about to have
the opportunity to write, and asserts the detector finds it. They run against a
synthetic mini-repo in a tmp dir, so nothing here touches product code.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import crisis_surface_map as cmap  # noqa: E402


@pytest.fixture
def fake_repo(tmp_path, monkeypatch):
    """A miniature product with the same crisis shape as the real one."""
    mobile_lib = tmp_path / "mobile" / "lib"
    fastapi_app = tmp_path / "backend-fastapi" / "app"
    django_apps = tmp_path / "backend-django" / "apps"

    (mobile_lib / "features" / "safety").mkdir(parents=True)
    (mobile_lib / "shared" / "widgets").mkdir(parents=True)
    (mobile_lib / "features" / "home").mkdir(parents=True)
    (fastapi_app / "safety").mkdir(parents=True)
    (fastapi_app / "orchestration").mkdir(parents=True)
    django_apps.mkdir(parents=True)

    (mobile_lib / "shared" / "widgets" / "support_action.dart").write_text(
        "import 'package:mobile/features/safety/helpers.dart';\n"
        "class SupportAction extends StatelessWidget {\n"
        "  Widget build(BuildContext context) => IconButton(\n"
        "    onPressed: () => Navigator.of(context).pushNamed('/safety'),\n"
        "  );\n"
        "}\n"
    )
    (mobile_lib / "features" / "safety" / "helpers.dart").write_text(
        "String hotline() => '988';\n"
    )
    (mobile_lib / "features" / "safety" / "safety_resources_screen.dart").write_text(
        "class SafetyResourcesScreen extends StatelessWidget {}\n"
    )
    (mobile_lib / "features" / "home" / "home_screen.dart").write_text(
        "class HomeScreen extends StatelessWidget {\n"
        "  Widget build(c) => Scaffold(actions: const [SupportAction()]);\n"
        "}\n"
    )

    monkeypatch.setattr(cmap, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(cmap, "MOBILE_LIB", mobile_lib)
    monkeypatch.setattr(cmap, "FASTAPI_APP", fastapi_app)
    monkeypatch.setattr(cmap, "DJANGO_APPS", django_apps)
    monkeypatch.setattr(
        cmap,
        "CRISIS_DIRS",
        [mobile_lib / "features" / "safety", fastapi_app / "safety", django_apps / "safety"],
    )
    monkeypatch.setattr(
        cmap,
        "TIER1_ANCHORS",
        [mobile_lib / "shared" / "widgets" / "support_action.dart"],
    )
    monkeypatch.setattr(cmap, "TIER2_ANCHORS", [])
    return tmp_path


def _tier1_violations() -> list[str]:
    out = []
    for path in sorted(cmap.tier1_closure()):
        for line_no, rule, matched in cmap.find_gates(cmap.read(path), strict=True):
            out.append(f"{cmap.rel(path)}:{line_no} [{rule}] {matched}")
    return out


def test_baseline_fake_repo_is_clean(fake_repo):
    """The fixture itself must start green, or the cases below prove nothing."""
    assert _tier1_violations() == []


def test_catches_a_gate_written_into_the_support_icon(fake_repo):
    """The obvious one: wrap the icon in an entitlement check."""
    icon = fake_repo / "mobile" / "lib" / "shared" / "widgets" / "support_action.dart"
    icon.write_text(
        icon.read_text().replace(
            "onPressed: () =>",
            "onPressed: entitlement.isActive ? () =>",
        )
    )
    assert any("entitlement" in v for v in _tier1_violations())


def test_catches_a_gate_hidden_one_import_away(fake_repo):
    """The one a reviewer misses: the support screen is clean, but something
    it imports is not. This is why Tier 1 is a transitive closure and not a
    list of files."""
    (fake_repo / "mobile" / "lib" / "features" / "safety" / "helpers.dart").write_text(
        "bool get hasPaid => billing.isPaid;\n" "String hotline() => hasPaid ? '988' : '';\n"
    )
    assert _tier1_violations(), (
        "A gate imported into the crisis path went undetected. The Tier 1 "
        "closure is not following imports."
    )


def test_catches_a_gate_planted_next_to_a_mount_point(fake_repo):
    """Tier 2: the screen carrying the support icon gates the whole app bar."""
    home = fake_repo / "mobile" / "lib" / "features" / "home" / "home_screen.dart"
    home.write_text(
        "class HomeScreen extends StatelessWidget {\n"
        "  Widget build(c) {\n"
        "    if (!user.hasEntitlement) return const Paywall();\n"
        "    return Scaffold(actions: const [SupportAction()]);\n"
        "  }\n"
        "}\n"
    )
    findings = cmap.gates_near_crisis(home.read_text(), ".dart")
    assert findings, "A paywall wrapping a support-icon mount point went undetected."


def test_distant_gate_in_a_tier2_file_is_allowed(fake_repo):
    """The other half of the proximity rule: a screen may still gate its own
    premium feature far from the crisis reference. If this fails, the gate is
    too noisy to survive contact with the engineer."""
    home = fake_repo / "mobile" / "lib" / "features" / "home" / "home_screen.dart"
    home.write_text(
        "class HomeScreen extends StatelessWidget {\n"
        "  Widget build(c) => Scaffold(actions: const [SupportAction()]);\n"
        + "  // filler\n" * (cmap.PROXIMITY_LINES + 5)
        + "  Widget report(c) => user.hasEntitlement ? Report() : Upsell();\n"
        "}\n"
    )
    assert cmap.gates_near_crisis(home.read_text(), ".dart") == []


# --- the AST contracts ------------------------------------------------------


def _crisis_resources_arity(src: str) -> int:
    tree = ast.parse(src)
    fn = next(
        n
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        and n.name == "crisis_resources"
    )
    a = fn.args
    return (
        len(a.posonlyargs)
        + len(a.args)
        + len(a.kwonlyargs)
        + (1 if a.vararg else 0)
        + (1 if a.kwarg else 0)
    )


def test_catches_crisis_resources_growing_a_user_argument():
    """The subtle one. Nobody writes `if not paid: return []`. They write
    `crisis_resources(user)` for a good reason, and the filter arrives later."""
    assert _crisis_resources_arity("def crisis_resources():\n    return []\n") == 0
    assert _crisis_resources_arity("def crisis_resources(user):\n    return []\n") == 1
    assert _crisis_resources_arity("def crisis_resources(*, req):\n    return []\n") == 1


def _entry_points(src: str) -> list[str]:
    return [
        n.args[0].value
        for n in ast.walk(ast.parse(src))
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "set_entry_point"
        and n.args
        and isinstance(n.args[0], ast.Constant)
    ]


def test_catches_a_node_inserted_ahead_of_the_safety_screen():
    """The worst available D7 violation: an entitlement node in front of the
    classifier means an unpaid user's crisis is never detected at all."""
    assert _entry_points('g.set_entry_point("node_1_safety_prescreen")') == [
        "node_1_safety_prescreen"
    ]
    assert _entry_points('g.set_entry_point("node_0_entitlement_check")') != [
        "node_1_safety_prescreen"
    ]


def test_tripwire_fires_when_payment_code_appears(fake_repo):
    """The tripwire must notice billing arriving, or the runtime test never
    gets written."""
    assert cmap.paywall_exists_in_product() is False
    (fake_repo / "backend-fastapi" / "app" / "billing.py").write_text(
        "STRIPE_KEY = 'sk_test'\n"
    )
    assert cmap.paywall_exists_in_product() is True
