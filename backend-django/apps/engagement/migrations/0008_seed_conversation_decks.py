"""Seed Conversation Deck packs — unscored open prompts to talk through
together (no guessing, no score). Idempotent."""

from django.db import migrations

# (key, title, description, category, order, [prompt, ...])
DECKS = [
    (
        "deck-deeper",
        "Deeper Conversations",
        "Open questions to explore together — no scores, just talk.",
        "relationship",
        10,
        [
            "What's a moment you felt closest to me recently?",
            "What's something you've always wanted to try together?",
            "When do you feel most understood by me?",
            "What does a great day for us look like a year from now?",
            "What's a fear you don't say out loud very often?",
            "What made you fall for me?",
            "What's one way I could support you better right now?",
            "What are you most grateful for about us?",
        ],
    ),
    (
        "deck-faith",
        "Faith & Meaning Talks",
        "Gentle prompts about beliefs, values, and what matters most.",
        "spiritual",
        11,
        [
            "What gives your life the most meaning right now?",
            "How did your upbringing shape what you believe?",
            "What does a life well-lived look like to you?",
            "When do you feel most at peace?",
            "What value do you most want us to build our life around?",
            "Is there a tradition you'd love for us to keep or start?",
        ],
    ),
]


def seed(apps, schema_editor):
    GamePack = apps.get_model("engagement", "GamePack")
    GameQuestion = apps.get_model("engagement", "GameQuestion")
    for key, title, desc, category, order, prompts in DECKS:
        pack, _ = GamePack.objects.get_or_create(
            key=key,
            defaults={
                "title": title,
                "description": desc,
                "game_type": "conversation_deck",
                "category": category,
                "order": order,
            },
        )
        if pack.questions.exists():
            continue
        for i, prompt in enumerate(prompts):
            GameQuestion.objects.create(pack=pack, prompt=prompt, options=[], order=i)


def unseed(apps, schema_editor):
    GamePack = apps.get_model("engagement", "GamePack")
    GamePack.objects.filter(key__in=[d[0] for d in DECKS]).delete()


class Migration(migrations.Migration):
    dependencies = [("engagement", "0007_seed_more_games")]
    operations = [migrations.RunPython(seed, unseed)]
