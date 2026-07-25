"""
Couple-games engine logic: scoring and the two-sided reveal.

A guessing game (Know Your Partner, Would You Rather, This or That) reveals both
partners' answers only once *both* have completed the pack — the same reveal
mechanic as the daily question, so the pull to finish is built in. Misses are
framed as conversation starters, never failure: that framing lives in the
client, but the API returns the mismatches plainly so it can.
"""

from apps.engagement.models import GamePlay, GameQuestion


def pack_progress(pack, relationship, user, partner):
    """How far each partner is through a pack, and whether it's revealable."""
    total = pack.questions.count()
    my_done = GamePlay.objects.filter(pack=pack, user=user).count()
    partner_done = (
        GamePlay.objects.filter(pack=pack, user=partner).count() if partner else 0
    )
    i_complete = total > 0 and my_done >= total
    partner_complete = total > 0 and partner is not None and partner_done >= total
    return {
        "total": total,
        "my_answered": my_done,
        "partner_answered": partner_done,
        "i_complete": i_complete,
        "partner_complete": partner_complete,
        "revealed": i_complete and partner_complete,
    }


def build_reveal(pack, user, partner):
    """Per-question reveal for a scored game once both partners are done.

    Returns each question with both self-answers, both guesses, whether each
    guessed the other correctly, and the two scores.
    """
    questions = list(pack.questions.all())
    mine = {p.question_id: p for p in GamePlay.objects.filter(pack=pack, user=user)}
    theirs = {p.question_id: p for p in GamePlay.objects.filter(pack=pack, user=partner)}

    items = []
    my_score = 0
    partner_score = 0
    for q in questions:
        m = mine.get(q.id)
        t = theirs.get(q.id)
        # I guessed my partner correctly if my guess == their self-answer.
        i_got_them = (
            m is not None and t is not None and m.guess_answer == t.self_answer
        )
        they_got_me = (
            m is not None and t is not None and t.guess_answer == m.self_answer
        )
        if i_got_them:
            my_score += 1
        if they_got_me:
            partner_score += 1
        items.append(
            {
                "question_id": str(q.id),
                "prompt": q.prompt,
                "options": q.options,
                "my_answer": m.self_answer if m else None,
                "partner_answer": t.self_answer if t else None,
                "my_guess": m.guess_answer if m else None,
                "partner_guess": t.guess_answer if t else None,
                "i_guessed_them": i_got_them,
                "they_guessed_me": they_got_me,
                # A "surprise" — a mismatch worth talking about — from my side.
                "surprise": (m is not None and t is not None and not i_got_them),
            }
        )
    return {
        "questions": items,
        "my_score": my_score,
        "partner_score": partner_score,
        "out_of": len(questions),
    }


def validate_answer(question: GameQuestion, self_answer, guess_answer, is_scored: bool):
    """Coerce and bound-check the submitted option indices.

    Returns ``(error, self_idx, guess_idx)`` — ``error`` is a message string when
    invalid (indices then ``None``), else ``None`` with the parsed integers.
    """
    n = len(question.options or [])

    def _idx(v):
        if v is None or v == "":
            return None, True
        try:
            return int(v), True
        except (ValueError, TypeError):
            return None, False

    self_idx, self_ok = _idx(self_answer)
    guess_idx, guess_ok = _idx(guess_answer)
    if not self_ok or not guess_ok:
        return "answers must be option indices", None, None
    if is_scored and (self_idx is None or not (0 <= self_idx < n)):
        return "self_answer must be a valid option index", None, None
    if guess_idx is not None and not (0 <= guess_idx < n):
        return "guess_answer must be a valid option index", None, None
    return None, self_idx, guess_idx
