"""The map of every surface that reaches crisis resources.

Decision D7 (`docs/execution-plan.md`) says nothing that reaches crisis
resources is ever gated — no paywall, no trial wall, no entitlement check on
the support icon, the safety path, or anything downstream of them.

To test that, something has to know what "the safety path" *is*. This module is
that something. It is deliberately separate from the test so that the map can
be reviewed as a map: if this file does not describe the product, the test
below it is measuring the wrong thing, and no amount of green tells you
otherwise.

Two ways a surface gets into the map:

1. **Discovered.** Anything under a safety/crisis directory, or any file that
   references a crisis entry point, is pulled in automatically. New files land
   in the map without anyone remembering to add them.
2. **Named.** A short list of anchors that are load-bearing but would not be
   discovered by name — `support_action.dart` is called "support", not
   "safety"; `graph.py` holds the escalation route.

Discovery is the important half. A map that only contains what someone
remembered to write down decays into a list of the files that were interesting
in August.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

MOBILE_LIB = REPO_ROOT / "mobile" / "lib"
FASTAPI_APP = REPO_ROOT / "backend-fastapi" / "app"
DJANGO_APPS = REPO_ROOT / "backend-django" / "apps"


# ---------------------------------------------------------------------------
# What counts as "reaches crisis resources"
# ---------------------------------------------------------------------------

# Symbols that mean this file is on the crisis path. A file mentioning any of
# these is either a crisis surface or a caller of one, and either way an
# entitlement check next to it is a defect.
CRISIS_SYMBOLS_DART = [
    r"SupportAction",              # the quiet support icon, mounted app-wide
    r"'/safety'",                  # the route it pushes
    r'"/safety"',
    r"SafetyResourcesScreen",      # the hotline screen itself
    r"safetyResources\b",          # the hotline data
    r"SafetyProtocolModal",        # the blocking crisis interruption
    r"safetyOverlayLevel",         # the state that raises it
    r"safetyOverlayResources",
    r"safety_triggered",           # the SSE frame that carries resources
]

CRISIS_SYMBOLS_PY = [
    r"\bcrisis_resources\b",       # the resource list sent to the client
    r"\bsafety_triggered\b",       # the SSE frame carrying it
    r"\bSAFETY_PROTOCOL\b",        # the graph's escalation exit
    r"\bSafetyPreScreener\b",
    r"\bSafetyPostScreener\b",
    r"\bnode_1_safety_prescreen\b",
    r"\broute_after_prescreen\b",
    r"\bscreen_layer[1-4]\b",
    r"\bSafetyIncident\b",
    r"\bSensitiveDisclosureDetector\b",
]

# The map has two tiers, because two different things are true of them.
#
# TIER 1 — the crisis path proper. Files whose job *is* reaching crisis
# resources. Nothing in here, or in anything it imports, may name an
# entitlement concept at all. Zero tolerance, whole-file, transitive.
#
# TIER 2 — mount points and callers. Screens that carry the support icon,
# routers that emit the safety frame. These are ordinary product surfaces that
# happen to also touch the crisis path, and they may legitimately gate
# *something else* on the same screen. The rule for them is narrower: the gate
# must not be anywhere near the crisis reference.
#
# Getting this split right is what stops the test from being either useless or
# unbearable. `main.dart` imports every screen in the app; closing over it
# would make Tier 1 mean "the whole product" and the first legitimate paywall
# anywhere would turn the D7 gate red. A gate that cries wolf gets deleted, and
# then D7 is protected by nothing.

# Directories whose entire contents are Tier 1 by construction.
CRISIS_DIRS = [
    MOBILE_LIB / "features" / "safety",
    FASTAPI_APP / "safety",
    DJANGO_APPS / "safety",
]

# Tier 1 anchors that discovery-by-name would miss, because they are on the
# path to crisis resources under a name that does not say "safety".
TIER1_ANCHORS = [
    # The support icon. Called "support", lives in shared/widgets, mounted on
    # a dozen screens. This is the single most important file in the map: it is
    # the one tap from anywhere that D7 exists to protect.
    MOBILE_LIB / "shared" / "widgets" / "support_action.dart",
    # The blocking crisis interruption.
    MOBILE_LIB / "features" / "chat" / "widgets" / "safety_protocol_modal.dart",
    # The escalation route: prescreen -> SAFETY_PROTOCOL.
    FASTAPI_APP / "orchestration" / "graph.py",
]

# Tier 2 anchors: multi-purpose files that carry a crisis reference.
TIER2_ANCHORS = [
    # Route registration. If `/safety` stops being an unconditional route,
    # every SupportAction in the app becomes a dead tap.
    MOBILE_LIB / "main.dart",
    # Raises the modal, shows the "see support" snackbar.
    MOBILE_LIB / "features" / "chat" / "chat_screen.dart",
    # Emits the `safety_triggered` SSE frame carrying `crisis_resources()`.
    FASTAPI_APP / "api" / "chat_router.py",
]


# ---------------------------------------------------------------------------
# What counts as a gate
# ---------------------------------------------------------------------------

# D2 leaves exactly one entitlement concept in the product: a single permanent
# flag set by a single $39 payment. There is no tier matrix to reason about, so
# any of these appearing on a crisis surface is unambiguous.
#
# Two lists, at two precisions, because the two tiers can afford different
# false-positive rates.
#
# PAYMENT_PATTERNS is high precision. It runs over the whole product, so every
# false positive is a stranger's file turning red for no reason. It matches the
# shapes a gate actually takes in code — identifiers, not English. `entitled`
# is not here because `apps/chat/views.py` says "entitled to" about a person's
# data, and `can_access` is not here because the *consent* system legitimately
# owns that phrase and consent is not payment.
#
# STRICT_EXTRA_PATTERNS is high recall, and only ever runs over Tier 1 — files
# whose entire job is crisis handling. Prose about billing has no business
# there, so the broad words are safe to ban outright, and the recall is worth
# having on precisely the files where a miss is worst.
PAYMENT_PATTERNS = [
    ("entitlement", r"entitlement|is[_]?entitled|has[_]?entitlement"),
    ("paywall", r"pay[_\-]?wall"),
    # No trailing \b: `_` is a word character, so `\bstripe\b` does not match
    # STRIPE_SECRET_KEY — which is exactly how a processor key gets written.
    # The mutation test in test_crisis_gate_catches_violations.py found this.
    ("processor", r"\bstripe(?!s\b|d\b)|\bpaystack|revenue[_]?cat"),
    ("checkout", r"checkout[_]?(session|url|id|link)|price[_]?id|\bsku\b"),
    (
        "purchase",
        r"purchase[_]?(id|token|state|status|verified|record)"
        r"|has[_]?purchased|is[_]?purchased|is[_]?paid\b|has[_]?paid\b",
    ),
    ("redemption-code", r"redemption[_]?code|redeem[_]?code|redemptioncode"),
    ("premium", r"\bpremium\b"),
    (
        "subscription",
        r"subscription[_]?(status|plan|tier|id|state)|is[_]?subscribed",
    ),
    ("trial-wall", r"trial[_]?(wall|expired|ends|active|remaining|started)"),
    ("upgrade-prompt", r"upgrade[_]?(prompt|sheet|screen|dialog|flow|cta)"),
    (
        "feature-gate",
        r"feature[_]?gate|gated[_]?by|paid[_]?only"
        r"|require[_]?(entitlement|purchase|payment|payment)",
    ),
]

# Tier 1 only. Broad on purpose.
STRICT_EXTRA_PATTERNS = [
    ("billing-word", r"\bbilling\b|\bcheckout\b|\binvoice\b"),
    ("trial-word", r"\btrial\b"),
    ("tier-word", r"\btier\b|\bis[_]?pro\b|\bpro[_]?tier\b"),
    ("purchase-word", r"\bpurchases?\b|\bpurchased\b"),
    ("access-check", r"has[_]?access|can[_]?access"),
    ("subscription-word", r"(?<!Stream)(?<!Event)(?<!stream)\bsubscriptions?\b"),
    ("entitled-word", r"\bentitled\b"),
    ("locked-behind", r"locked[_]?behind|is[_]?locked[_]?feature"),
]

COMPILED_PAYMENT = [
    (name, re.compile(pattern, re.IGNORECASE)) for name, pattern in PAYMENT_PATTERNS
]
COMPILED_STRICT = COMPILED_PAYMENT + [
    (name, re.compile(pattern, re.IGNORECASE)) for name, pattern in STRICT_EXTRA_PATTERNS
]


# ---------------------------------------------------------------------------
# Reviewed exceptions
# ---------------------------------------------------------------------------

# A crisis surface may name an entitlement concept only to *refuse* it — for
# example a comment saying "no entitlement check here, see D7", or a test
# asserting the absence. Those go here, with a reason, a reviewer and a date.
#
# This is the escape hatch and it is meant to be uncomfortable to use. Adding a
# line here is a decision to let an entitlement word sit on a crisis path; it
# should be argued for in review, not typed to make a red build go away.
#
# Keys are repo-relative POSIX paths.
REVIEWED_EXCEPTIONS: dict[str, str] = {}


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def _iter_source_files(root: Path, suffix: str) -> list[Path]:
    if not root.exists():
        return []
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d
            for d in dirnames
            if d not in {"__pycache__", ".pytest_cache", "venv", "node_modules", ".git"}
        ]
        for name in filenames:
            if name.endswith(suffix):
                out.append(Path(dirpath) / name)
    return sorted(out)


def all_dart_files() -> list[Path]:
    return _iter_source_files(MOBILE_LIB, ".dart")


def all_python_files() -> list[Path]:
    return _iter_source_files(FASTAPI_APP, ".py") + _iter_source_files(DJANGO_APPS, ".py")


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _matches_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text) for p in patterns)


def tier1_seeds() -> set[Path]:
    """Files whose job is reaching crisis resources."""
    found: set[Path] = set()
    for directory in CRISIS_DIRS:
        found.update(_iter_source_files(directory, ".dart"))
        found.update(_iter_source_files(directory, ".py"))
    for anchor in TIER1_ANCHORS:
        if anchor.exists():
            found.add(anchor)
    return {p.resolve() for p in found}


def discover_crisis_files() -> set[Path]:
    """Every file that is on, or calls into, the crisis path.

    Union of: Tier 1, the named Tier 2 anchors, and — the part that matters —
    every file anywhere in the app that references a crisis symbol. That last
    clause is why a screen added next March that mounts `SupportAction` is
    covered without anybody editing this file.
    """
    found: set[Path] = set(tier1_seeds())

    for anchor in TIER2_ANCHORS:
        if anchor.exists():
            found.add(anchor.resolve())

    for path in all_dart_files():
        if _matches_any(read(path), CRISIS_SYMBOLS_DART):
            found.add(path.resolve())

    for path in all_python_files():
        if _matches_any(read(path), CRISIS_SYMBOLS_PY):
            found.add(path.resolve())

    return found


def tier2_files() -> set[Path]:
    """Crisis callers and mount points — everything discovered that is not
    Tier 1 or downstream of it."""
    return discover_crisis_files() - tier1_closure()


# ---------------------------------------------------------------------------
# Import-closure walking
#
# A gate does not have to be written *in* the support screen to gate it. It can
# sit in anything the support screen imports. So the map is closed over imports
# from every crisis file, transitively, within first-party code.
# ---------------------------------------------------------------------------

_DART_IMPORT = re.compile(r"""^\s*(?:import|export)\s+['"]([^'"]+)['"]""", re.MULTILINE)


def _resolve_dart_import(spec: str, importer: Path) -> Path | None:
    if spec.startswith("package:mobile/"):
        return MOBILE_LIB / spec[len("package:mobile/") :]
    if spec.startswith(("package:", "dart:")):
        return None  # third-party / SDK; not ours to police
    return (importer.parent / spec).resolve()


_PY_IMPORT_FROM = re.compile(r"^\s*from\s+((?:app|apps)(?:\.[A-Za-z0-9_]+)*)\s+import", re.MULTILINE)
_PY_IMPORT = re.compile(r"^\s*import\s+((?:app|apps)(?:\.[A-Za-z0-9_]+)*)", re.MULTILINE)


def _resolve_py_module(module: str) -> list[Path]:
    root = FASTAPI_APP.parent if module.startswith("app.") or module == "app" else DJANGO_APPS.parent
    parts = module.split(".")
    base = root.joinpath(*parts)
    candidates = [base.with_suffix(".py"), base / "__init__.py"]
    # `from app.safety.layer1_rules import screen_layer1` resolves to the
    # module; `from app.safety import x` resolves to the package. Also try the
    # parent, for `from app.x.y import z` where y is a symbol not a module.
    parent = root.joinpath(*parts[:-1])
    candidates += [parent.with_suffix(".py"), parent / "__init__.py"]
    return [c for c in candidates if c.exists() and c.is_file()]


def close_over_imports(seeds: set[Path]) -> set[Path]:
    """Transitive first-party import closure of `seeds`."""
    seen: set[Path] = set()
    queue = list(seeds)

    while queue:
        path = queue.pop()
        path = path.resolve()
        if path in seen or not path.exists() or not path.is_file():
            continue
        seen.add(path)
        text = read(path)

        if path.suffix == ".dart":
            for spec in _DART_IMPORT.findall(text):
                target = _resolve_dart_import(spec, path)
                if target is not None and target.exists():
                    queue.append(target)
        elif path.suffix == ".py":
            for module in _PY_IMPORT_FROM.findall(text) + _PY_IMPORT.findall(text):
                queue.extend(_resolve_py_module(module))

    return seen


def tier1_closure() -> set[Path]:
    """Every file a tap on the support icon, or a crisis escalation, can
    execute code from — transitively."""
    return close_over_imports(tier1_seeds())


def find_gates(text: str, strict: bool = False) -> list[tuple[int, str, str]]:
    """Every entitlement-shaped token in `text`, as (line_no, rule, match)."""
    hits = []
    for name, pattern in COMPILED_STRICT if strict else COMPILED_PAYMENT:
        for match in pattern.finditer(text):
            line_no = text.count("\n", 0, match.start()) + 1
            hits.append((line_no, name, match.group(0)))
    return sorted(hits)


def find_crisis_references(text: str, suffix: str) -> list[tuple[int, str]]:
    """Every crisis-symbol reference in `text`, as (line_no, matched_text)."""
    symbols = CRISIS_SYMBOLS_DART if suffix == ".dart" else CRISIS_SYMBOLS_PY
    hits = []
    for pattern in symbols:
        for match in re.finditer(pattern, text):
            line_no = text.count("\n", 0, match.start()) + 1
            hits.append((line_no, match.group(0)))
    return sorted(hits)


# How close an entitlement token may sit to a crisis reference in a Tier 2
# file before a human has to look at it.
#
# This is a blunt instrument and it is chosen deliberately. Deciding properly
# whether a crisis reference sits inside an entitlement-guarded branch needs a
# Dart parser and a Python one, and both would then need to stay correct
# through every refactor. The cost of a false positive here is that somebody
# reads twenty lines of a diff and adds one line to REVIEWED_EXCEPTIONS. The
# cost of a false negative is a person in crisis hitting a paywall. Those are
# not the same cost, so the instrument is tuned to over-report.
PROXIMITY_LINES = 25


def gates_near_crisis(text: str, suffix: str) -> list[tuple[int, str, str, int, str]]:
    """Entitlement tokens sitting within PROXIMITY_LINES of a crisis reference.

    Returns (gate_line, rule, gate_text, crisis_line, crisis_text).
    """
    gates = find_gates(text)
    if not gates:
        return []
    crisis = find_crisis_references(text, suffix)
    if not crisis:
        return []

    findings = []
    for gate_line, rule, gate_text in gates:
        for crisis_line, crisis_text in crisis:
            if abs(gate_line - crisis_line) <= PROXIMITY_LINES:
                findings.append((gate_line, rule, gate_text, crisis_line, crisis_text))
                break
    return findings


def paywall_exists_in_product() -> bool:
    """Has P0.2 landed? Used to escalate the tripwire tests.

    True once entitlement-shaped code appears anywhere in the app outside the
    QA tests themselves.
    """
    for path in all_dart_files() + all_python_files():
        if find_gates(read(path)):
            return True
    return False
