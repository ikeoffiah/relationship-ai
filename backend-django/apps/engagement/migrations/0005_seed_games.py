"""Seed the first couple game: a Know Your Partner pack. Idempotent."""

from django.db import migrations

PACK = {
    "key": "know-your-partner-1",
    "title": "How Well Do You Know Me?",
    "description": "Answer about yourself, then guess your partner. See how well you match.",
    "game_type": "know_your_partner",
    "category": "relationship",
    "order": 0,
}

QUESTIONS = [
    ("My ideal Friday night is…", ["Cozy night in", "Out with friends", "A quiet dinner for two", "Something spontaneous"]),
    ("My go-to comfort food is…", ["Pizza", "Ice cream", "Something home-cooked", "Chocolate"]),
    ("When I'm stressed, what helps me most is…", ["Space to myself", "A good talk", "A hug", "Getting active"]),
    ("My love language leans toward…", ["Words of affirmation", "Quality time", "Physical touch", "Acts of service"]),
    ("On a day off, I'd rather…", ["Sleep in and relax", "Get outdoors", "Tackle a project", "See people"]),
    ("The little thing that makes my day is…", ["A kind text", "A good coffee", "A tidy space", "A shared laugh"]),
    ("My dream trip is…", ["A beach escape", "A city adventure", "A nature retreat", "A food tour"]),
]


def seed(apps, schema_editor):
    GamePack = apps.get_model("engagement", "GamePack")
    GameQuestion = apps.get_model("engagement", "GameQuestion")

    pack, _ = GamePack.objects.get_or_create(key=PACK["key"], defaults=PACK)
    if pack.questions.exists():
        return
    for order, (prompt, options) in enumerate(QUESTIONS):
        GameQuestion.objects.create(pack=pack, prompt=prompt, options=options, order=order)


def unseed(apps, schema_editor):
    GamePack = apps.get_model("engagement", "GamePack")
    GamePack.objects.filter(key=PACK["key"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("engagement", "0004_gamepack_alter_pointsledger_reason_gamequestion_and_more"),
    ]
    operations = [migrations.RunPython(seed, unseed)]
