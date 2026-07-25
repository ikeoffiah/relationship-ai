"""Seed a starter catalog of daily questions and micro-actions so the daily
features have content on day one. Idempotent: skips rows that already exist."""

from django.db import migrations

DAILY_QUESTIONS = [
    ("What's one small thing your partner did recently that you appreciated?", "appreciation"),
    ("What made you feel most connected to each other this week?", "connection"),
    ("What's something you're looking forward to doing together?", "fun"),
    ("When did you last feel really understood by your partner?", "connection"),
    ("What's one thing you'd love more of in your relationship?", "growth"),
    ("What's a value you both share that guides your decisions?", "values"),
    ("What's a memory of the two of you that always makes you smile?", "fun"),
    ("What's something hard you're carrying that your partner could help with?", "growth"),
    ("How do you most like to be comforted after a rough day?", "intimacy"),
    ("What's one way your partner has grown that you admire?", "appreciation"),
    ("What does a perfect ordinary day together look like to you?", "fun"),
    ("What's a worry about 'us' you haven't said out loud yet?", "growth"),
    ("What's something you're proud of that you two built together?", "connection"),
    ("What helps you feel safe bringing up something difficult?", "values"),
]

MICRO_ACTIONS = [
    ("Send your partner a text telling them one thing you appreciate about them.", "appreciation", ""),
    ("Ask your partner how their day was — and put your phone down while they answer.", "presence", ""),
    ("Do one small chore your partner usually handles, without being asked.", "service", ""),
    ("Give your partner a 20-second hug today (long hugs release oxytocin).", "affection", ""),
    ("Reassure your partner you're glad you're together — say it out loud.", "affection", "anxious"),
    ("Give your partner some unhurried space today, and let them know it's from care.", "presence", "avoidant"),
    ("Name one feeling you had today out loud, instead of keeping it in.", "openness", "avoidant"),
    ("Ask your partner one question about something they care about, and just listen.", "presence", ""),
]


def seed(apps, schema_editor):
    DailyQuestion = apps.get_model("engagement", "DailyQuestion")
    MicroActionTemplate = apps.get_model("engagement", "MicroActionTemplate")

    for order, (text, category) in enumerate(DAILY_QUESTIONS):
        DailyQuestion.objects.get_or_create(
            prompt_text=text, defaults={"category": category, "order": order}
        )
    for text, category, style in MICRO_ACTIONS:
        MicroActionTemplate.objects.get_or_create(
            text=text, defaults={"category": category, "target_attachment_style": style}
        )


def unseed(apps, schema_editor):
    DailyQuestion = apps.get_model("engagement", "DailyQuestion")
    MicroActionTemplate = apps.get_model("engagement", "MicroActionTemplate")
    DailyQuestion.objects.filter(prompt_text__in=[q[0] for q in DAILY_QUESTIONS]).delete()
    MicroActionTemplate.objects.filter(text__in=[m[0] for m in MICRO_ACTIONS]).delete()


class Migration(migrations.Migration):
    dependencies = [("engagement", "0001_initial")]
    operations = [migrations.RunPython(seed, unseed)]
