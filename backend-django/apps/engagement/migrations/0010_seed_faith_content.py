"""Seed the opt-in faith feature: a shared checklist of daily practices and a
small rotating set of readings.

Content policy for this seed:
  * Practices are universal (blank tradition) so every opted-in user sees them.
  * Readings are either non-sectarian "universal" reflections or public-domain
    (KJV) scripture for the Christian set. Richer, curated per-tradition content
    (Qur'an, Torah, Dhammapada, etc.) is deliberately left to content ops rather
    than shipped here — the universal set is the safe fallback in the meantime.
Idempotent: re-running seeds nothing new.
"""

from django.db import migrations

# (key, label, icon, order)
PRACTICES = [
    ("morning-prayer", "Morning prayer / intention", "🌅", 1),
    ("scripture", "Read today's passage together", "📖", 2),
    ("gratitude", "Name one thing you're grateful for", "🙏", 3),
    ("act-of-service", "One small act of service", "🤲", 4),
    ("evening-reflection", "Evening reflection / examen", "🌙", 5),
    ("fasting", "Keep today's fast / abstinence", "🕊️", 6),
]

# (tradition, title, reference, body, reflection_prompt, order)
READINGS = [
    (
        "universal",
        "Begin with gratitude",
        "",
        "Before anything is asked of the day, pause and notice one good thing "
        "already present between you — a kindness, a comfort, a shared quiet.",
        "What is one thing about your partner you were grateful for this week, "
        "but haven't said out loud?",
        1,
    ),
    (
        "universal",
        "Patience with each other",
        "",
        "Love is not a feeling that arrives fully formed; it is a practice of "
        "returning, gently, to the same person again and again.",
        "Where could you offer your partner a little more patience this week?",
        2,
    ),
    (
        "universal",
        "Repair over being right",
        "",
        "A relationship is not kept whole by never disagreeing, but by the "
        "willingness to reach back across the distance a disagreement creates.",
        "Is there a small rupture between you that is still waiting for a repair?",
        3,
    ),
    (
        "universal",
        "Presence",
        "",
        "To be fully with another person — unhurried, undistracted — is one of "
        "the most generous things we can give.",
        "When did you last feel truly present with your partner? How could you "
        "make more room for that?",
        4,
    ),
    (
        "christian",
        "Dwelling together",
        "Psalm 133:1 (KJV)",
        "Behold, how good and how pleasant it is for brethren to dwell together "
        "in unity.",
        "What helps the two of you 'dwell together in unity' — and what tends to "
        "get in the way?",
        1,
    ),
    (
        "christian",
        "What love is",
        "1 Corinthians 13:4-7 (KJV)",
        "Charity suffereth long, and is kind; charity envieth not; charity "
        "vaunteth not itself, is not puffed up... beareth all things, believeth "
        "all things, hopeth all things, endureth all things.",
        "Which quality of love here would your relationship most like to grow in "
        "this season?",
        2,
    ),
    (
        "christian",
        "Bear with one another",
        "Colossians 3:13 (KJV)",
        "Forbearing one another, and forgiving one another, if any man have a "
        "quarrel against any: even as Christ forgave you, so also do ye.",
        "Is there something you're holding onto that you're being invited to "
        "forgive — in your partner, or in yourself?",
        3,
    ),
    (
        "christian",
        "A cord of three strands",
        "Ecclesiastes 4:9-12 (KJV)",
        "Two are better than one... for if they fall, the one will lift up his "
        "fellow: but woe to him that is alone when he falleth. And a threefold "
        "cord is not quickly broken.",
        "How do you 'lift each other up' when one of you falls? Where could you "
        "lean on each other more?",
        4,
    ),
]


def seed(apps, schema_editor):
    FaithPractice = apps.get_model("engagement", "FaithPractice")
    DailyReading = apps.get_model("engagement", "DailyReading")

    for key, label, icon, order in PRACTICES:
        FaithPractice.objects.get_or_create(
            key=key,
            defaults={"label": label, "icon": icon, "tradition": "", "order": order},
        )

    for tradition, title, reference, body, prompt, order in READINGS:
        DailyReading.objects.get_or_create(
            tradition=tradition,
            title=title,
            defaults={
                "reference": reference,
                "body": body,
                "reflection_prompt": prompt,
                "order": order,
            },
        )


def unseed(apps, schema_editor):
    FaithPractice = apps.get_model("engagement", "FaithPractice")
    DailyReading = apps.get_model("engagement", "DailyReading")
    FaithPractice.objects.filter(key__in=[p[0] for p in PRACTICES]).delete()
    DailyReading.objects.filter(title__in=[r[1] for r in READINGS]).delete()


class Migration(migrations.Migration):
    dependencies = [("engagement", "0009_faith_models")]
    operations = [migrations.RunPython(seed, unseed)]
