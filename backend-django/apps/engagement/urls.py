"""URL configuration for the daily-engagement API (mounted at /api/v1/engagement/)."""

from django.urls import path

from apps.engagement import game_views, views

urlpatterns = [
    # Couple games
    path("games", game_views.game_list, name="engagement-games"),
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
