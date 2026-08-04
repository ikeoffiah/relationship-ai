"""A ratchet on silently-swallowed failures.

The history bug — `persist_turn()` catching everything and returning, so a
feature was non-functional with zero rows and nothing anywhere reporting it —
is not one bug. It is a habit with 26 instances, catalogued in
`docs/qa/silent-failures.md`.

Fixing all 26 at once is not the plan and should not be: several are correct,
and the P0 money path outranks the rest. So this is a ratchet rather than a
gate. The inventory below is what exists today. It may shrink freely. It may
not grow.

That way the sweep does not decay into a document nobody re-runs, and the
class of defect stops expanding while the individual instances are worked
through in priority order.

Stdlib only. Run: `pytest tests/observability/ -v`
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import silent_failure_scan as scan  # noqa: E402


# Every broad exception handler that discards without logging, counting or
# re-raising, as of 2026-08-03. Keyed by (file, function, exception) so the
# baseline does not churn when unrelated edits move line numbers.
#
# Ranked write-up, with the reasoning behind each severity, is in
# docs/qa/silent-failures.md. The short version of the ranking axis: how long
# could a *total* failure of this run before anyone noticed, and what breaks
# while it does.
KNOWN_SILENT_HANDLERS: set[tuple[str, str, str]] = {
    # --- Tier A: safety, consent, money, audit -----------------------------
    # The counselling stack degrades to a keyword floor / canned reply on the
    # same root cause, and the degraded state is indistinguishable from the
    # healthy one at every observation point we have. See silent-failures.md §2.
    ("backend-fastapi/app/safety/layer2_semantic.py", "screen_layer2", "Exception"),
    ("backend-fastapi/app/safety/layer3_contextual.py", "screen_layer3", "Exception"),
    ("backend-fastapi/app/orchestration/llm_provider.py", "generate_reply", "Exception"),
    # Silently restarts the audit hash chain at "genesis". The weekly verifier
    # does catch the resulting fork, so this is detection-delayed rather than
    # undetectable — but the cause is unattributable when it fires.
    ("backend-django/apps/audit/logger.py", "_get_last_hash", "Exception"),
    # --- Tier B: the product quietly becomes a worse version of itself -----
    ("backend-fastapi/app/api/chat_router.py", "persist_turn", "Exception"),
    ("backend-fastapi/app/api/chat_router.py", "fetch_personalization", "Exception"),
    ("backend-fastapi/app/api/chat_router.py", "fetch_shared_context", "Exception"),
    ("backend-fastapi/app/api/chat_router.py", "fetch_memories", "Exception"),
    ("backend-fastapi/app/api/chat_router.py", "get_optional_pool", "Exception"),
    ("backend-fastapi/app/counseling/broker.py", "send_to_user", "Exception"),
    ("backend-fastapi/app/counseling/broker.py", "_listen_to_redis", "Exception"),
    ("backend-fastapi/app/counseling/broker.py", "is_online", "Exception"),
    ("backend-fastapi/app/memory/extractor.py", "extract", "Exception"),
    ("backend-fastapi/app/api/relationships.py", "decrypt_context", "Exception"),
    ("backend-django/apps/chat/assist.py", "_partner_notes", "Exception"),
    ("backend-django/apps/chat/assist.py", "_caution_is_wanted", "Exception"),
    ("backend-django/apps/chat/assist.py", "_count_call", "Exception"),
    ("backend-django/apps/chat/assist.py", "model_calls", "Exception"),
    ("backend-django/apps/engagement/services.py", "_allowed_categories", "Exception"),
    ("backend-django/apps/personalization/behaviour.py", "tendencies_for", "Exception"),
    ("backend-django/apps/chat/media.py", "has_metadata", "Exception"),
    # --- Tier C: defensible as written -------------------------------------
    ("backend-django/apps/accounts/middleware.py", "process_request", "Exception"),
    ("backend-fastapi/app/api/websockets.py", "handle_websocket_session", "Exception"),
    ("backend-fastapi/app/api/websockets.py", "couple_thread_websocket", "Exception"),
}


def test_no_new_silently_swallowed_failures():
    """The inventory may shrink. It may not grow."""
    current = {h.key for h in scan.broad_silent_handlers()}
    added = sorted(current - KNOWN_SILENT_HANDLERS)

    assert not added, (
        "New broad exception handlers discard a failure without logging, "
        "counting or re-raising:\n\n  "
        + "\n  ".join(f"{f} :: {fn}() :: except {exc}" for f, fn, exc in added)
        + "\n\n"
        "This is the shape behind the history bug: `persist_turn()` caught "
        "everything and returned, so the feature was non-functional with zero "
        "rows and nothing anywhere reporting it.\n\n"
        "Failing *open* is usually right — a convenience must not interrupt "
        "counseling. Failing *silently* is the defect. Record the failure and "
        "continue:\n\n"
        "    with degraded('persist_turn', fallback='history row not written',\n"
        "                  session_id=session_id):\n"
        "        await conn.execute(...)\n\n"
        "See docs/qa/silent-failures.md §5 for the helper's contract. If the "
        "handler is genuinely control flow (`DoesNotExist`, a documented "
        "`IntegrityError` race), catch that type specifically rather than "
        "`Exception` and this check will not see it."
    )


def test_the_known_inventory_has_not_gone_stale():
    """Entries that no longer exist must be removed, so the list stays real.

    A baseline nobody prunes stops describing the code and starts describing
    the day it was written. Fixing one of these should be a two-line diff — the
    fix, and its removal from here.
    """
    current = {h.key for h in scan.broad_silent_handlers()}
    resolved = sorted(KNOWN_SILENT_HANDLERS - current)

    assert not resolved, (
        "These handlers are in KNOWN_SILENT_HANDLERS but the scanner no longer "
        "finds them:\n\n  "
        + "\n  ".join(f"{f} :: {fn}() :: except {exc}" for f, fn, exc in resolved)
        + "\n\nIf they were fixed: delete these lines, and strike the entry "
        "from the table in docs/qa/silent-failures.md. If they were renamed or "
        "moved, update the key.\n\n"
        "Either way this is good news — the ratchet turned."
    )


def test_the_scanner_still_finds_something():
    """Guard against the scan going vacuously green.

    If `_records()` starts matching everything, or SCAN_ROOTS stops resolving,
    this file passes forever while checking nothing.
    """
    handlers = scan.scan()
    assert len(handlers) > 20, (
        f"The scanner found only {len(handlers)} exception handlers across both "
        "backends. It should be finding dozens. Check SCAN_ROOTS and the "
        "RECORDING_CALLS heuristic before trusting any result above."
    )
    assert any(h.guards_write for h in handlers), (
        "No scanned handler was classified as guarding a write. The WRITE_HINTS "
        "heuristic has stopped matching."
    )
