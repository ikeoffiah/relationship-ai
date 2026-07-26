"""
State and reveal logic for Two Truths & a Lie.

Kept out of the views so the commit-before-reveal rule is unit-testable without
HTTP. The lie is disclosed only once BOTH partners have authored their three
statements AND both have submitted a guess — so nobody can peek at the answer
before committing to their own.
"""

from typing import Optional


def build_state(mine, theirs) -> dict:
    """The caller's view of the round.

    ``mine``/``theirs`` are ``TwoTruthsPlay`` instances or ``None``. The
    partner's ``lie_index`` is never included until the round is revealed; their
    statements are shown as soon as they've authored, so the caller can guess.
    """
    authored = mine is not None
    partner_authored = theirs is not None
    i_guessed = mine is not None and mine.guess_index is not None
    partner_guessed = theirs is not None and theirs.guess_index is not None
    revealed = authored and partner_authored and i_guessed and partner_guessed

    state = {
        "authored": authored,
        "partner_authored": partner_authored,
        "i_guessed": i_guessed,
        "partner_guessed": partner_guessed,
        "revealed": revealed,
        # My own content — I already know my lie.
        "my_statements": mine.statements if mine else None,
        "my_lie_index": mine.lie_index if mine else None,
        "my_guess": mine.guess_index if mine else None,
        # The partner's statements to guess against — WITHOUT their lie index.
        "partner_statements": theirs.statements if theirs else None,
    }
    if revealed:
        state["reveal"] = {
            "partner_lie_index": theirs.lie_index,
            "i_caught_them": mine.guess_index == theirs.lie_index,
            "partner_guess": theirs.guess_index,
            "they_caught_me": theirs.guess_index == mine.lie_index,
            "my_lie_index": mine.lie_index,
        }
    return state


def validate_statements(raw) -> tuple[Optional[str], Optional[list]]:
    """Coerce/validate the three authored statements."""
    if not isinstance(raw, list) or len(raw) != 3:
        return "Provide exactly three statements.", None
    cleaned = [str(s).strip() for s in raw]
    if any(not s for s in cleaned):
        return "Statements can't be empty.", None
    if any(len(s) > 200 for s in cleaned):
        return "Each statement must be under 200 characters.", None
    return None, cleaned


def validate_index(raw) -> tuple[Optional[str], Optional[int]]:
    """Coerce/validate a 0–2 index (form-encoded values arrive as strings)."""
    try:
        i = int(raw)
    except (TypeError, ValueError):
        return "Index must be 0, 1, or 2.", None
    if not (0 <= i <= 2):
        return "Index must be 0, 1, or 2.", None
    return None, i
