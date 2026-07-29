"""URL configuration for the daily-engagement API (mounted at /api/v1/engagement/)."""

from django.urls import path

from apps.engagement import (
    bliss_views,
    commitment_views,
    faith_views,
    focus_views,
    game_views,
    two_truths_views,
    views,
)

urlpatterns = [
    # Focus Mode (consensual, mutual)
    path("focus", focus_views.current, name="engagement-focus"),
    path("focus/propose", focus_views.propose, name="engagement-focus-propose"),
    path("focus/accept", focus_views.accept, name="engagement-focus-accept"),
    path("focus/decline", focus_views.decline, name="engagement-focus-decline"),
    path("focus/end", focus_views.end, name="engagement-focus-end"),
    # Partner commitments (for / with)
    path("commitments", commitment_views.commitments, name="engagement-commitments"),
    path(
        "commitments/<uuid:item_id>/done",
        commitment_views.complete_commitment,
        name="engagement-commitment-done",
    ),
    path(
        "commitments/<uuid:item_id>/cancel",
        commitment_views.cancel_commitment,
        name="engagement-commitment-cancel",
    ),
    # Two Truths & a Lie
    path("two-truths", two_truths_views.state, name="engagement-two-truths"),
    path("two-truths/author", two_truths_views.author, name="engagement-two-truths-author"),
    path("two-truths/guess", two_truths_views.guess, name="engagement-two-truths-guess"),
    path("two-truths/reset", two_truths_views.reset, name="engagement-two-truths-reset"),
    # Bliss assistant (taggable @bliss reminders / events)
    path("bliss/interpret", bliss_views.interpret, name="engagement-bliss-interpret"),
    path("bliss/items", bliss_views.items, name="engagement-bliss-items"),
    path("bliss/items/<uuid:item_id>/done", bliss_views.complete_item, name="engagement-bliss-done"),
    path("bliss/items/<uuid:item_id>/cancel", bliss_views.cancel_item, name="engagement-bliss-cancel"),
    path(
        "bliss/items/<uuid:item_id>/respond",
        bliss_views.respond_to_invite,
        name="engagement-bliss-respond",
    ),
    # The in-app calendar: dated items in a window, grouped by day.
    path("bliss/calendar", bliss_views.calendar, name="engagement-bliss-calendar"),
    # Faith / spirituality (opt-in)
    path("faith/today", faith_views.faith_today, name="engagement-faith-today"),
    path(
        "faith/practices/complete",
        faith_views.complete_practice,
        name="engagement-faith-practice-complete",
    ),
    path("faith/reflect", faith_views.reflect, name="engagement-faith-reflect"),
    # Couple games
    path("games", game_views.game_list, name="engagement-games"),
    path("games/spicy-consent", game_views.spicy_consent, name="engagement-spicy-consent"),
    path("games/<slug:key>", game_views.game_detail, name="engagement-game-detail"),
    path("games/<slug:key>/answer", game_views.game_answer, name="engagement-game-answer"),
    # Daily question
    path("daily-question", views.daily_question, name="engagement-daily-question"),
    path(
        "daily-question/answer",
        views.answer_daily_question,
        name="engagement-answer-question",
    ),
    # Check-in
    path("check-in", views.submit_check_in, name="engagement-check-in"),
    path("check-in/history", views.check_in_history, name="engagement-check-in-history"),
    # Shared goals
    path("goals", views.goals, name="engagement-goals"),
    path("goals/<uuid:goal_id>/progress", views.log_goal_progress, name="engagement-goal-progress"),
    path("goals/<uuid:goal_id>", views.update_goal, name="engagement-goal-update"),
    # Micro-action
    path("micro-action", views.micro_action, name="engagement-micro-action"),
    path(
        "micro-action/complete",
        views.complete_micro_action,
        name="engagement-micro-action-complete",
    ),
    # Gratitude / repair
    path("gratitude", views.gratitude, name="engagement-gratitude"),
    # Summary
    path("summary", views.summary, name="engagement-summary"),
]
