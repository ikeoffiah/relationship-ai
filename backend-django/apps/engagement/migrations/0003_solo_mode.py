"""Solo mode: let the daily features work for a single user before a partner
joins. Relationship FKs become nullable, per-day uniqueness is keyed on the
user, and the streak becomes per-user.

The engagement_streaks table is recreated (drop + create) because its primary
key moves from relationship to user. This is safe: the table is brand-new and
empty in every environment.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("relationships", "0001_initial"),
        ("engagement", "0002_seed_content"),
    ]

    operations = [
        # ── Nullable relationship FKs ───────────────────────────────────
        migrations.AlterField(
            model_name="dailyquestionresponse",
            name="relationship",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="daily_responses",
                to="relationships.relationship",
            ),
        ),
        migrations.AlterField(
            model_name="relationshipcheckin",
            name="relationship",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="check_ins",
                to="relationships.relationship",
            ),
        ),
        migrations.AlterField(
            model_name="sharedgoal",
            name="relationship",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="shared_goals",
                to="relationships.relationship",
            ),
        ),
        migrations.AlterField(
            model_name="gratitudemoment",
            name="relationship",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="gratitude_moments",
                to="relationships.relationship",
            ),
        ),
        # ── Re-key per-day uniqueness on the user ───────────────────────
        migrations.RemoveConstraint(
            model_name="dailyquestionresponse",
            name="uniq_daily_response_per_user_day",
        ),
        migrations.AddConstraint(
            model_name="dailyquestionresponse",
            constraint=models.UniqueConstraint(
                fields=["user", "date_key"],
                name="uniq_daily_response_per_user_day",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="relationshipcheckin",
            name="uniq_check_in_per_user_day",
        ),
        migrations.AddConstraint(
            model_name="relationshipcheckin",
            constraint=models.UniqueConstraint(
                fields=["user", "date_key"],
                name="uniq_check_in_per_user_day",
            ),
        ),
        # ── Per-user streak (drop + recreate; table is empty) ───────────
        migrations.DeleteModel(name="EngagementStreak"),
        migrations.CreateModel(
            name="EngagementStreak",
            fields=[
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="engagement_streak",
                        serialize=False,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("current_streak", models.PositiveIntegerField(default=0)),
                ("longest_streak", models.PositiveIntegerField(default=0)),
                ("last_activity_date", models.CharField(blank=True, default="", max_length=10)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "engagement_streaks"},
        ),
    ]
