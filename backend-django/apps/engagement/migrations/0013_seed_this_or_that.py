"""Seed a 'This or That' pack — rapid either/or picks where the fun is seeing
how aligned (or not) you are. Uses the agreement reveal, not guessing.
Idempotent."""

from django.db import migrations

PACK = (
    "tot-us",
    "This or That: Us",
    "Quick either/or picks — see how in sync you really are.",
    "this_or_that",
    "fun",
    0,
    [
        ("Night in or night out?", ["Night in", "Night out"]),
        ("Beach or mountains?", ["Beach", "Mountains"]),
        ("Plan everything or go with the flow?", ["Plan it", "Go with the flow"]),
        ("Early bird or night owl?", ["Early bird", "Night owl"]),
        ("Save it or spend it?", ["Save it", "Spend it"]),
        ("Big party or small gathering?", ["Big party", "Small gathering"]),
        ("Sweet or savoury?", ["Sweet", "Savoury"]),
        ("Text or call?", ["Text", "Call"]),
        ("Adventure trip or relaxing getaway?", ["Adventure", "Relax"]),
        ("Movie at home or out for dinner?", ["Movie at home", "Out for dinner"]),
    ],
)


def seed(apps, schema_editor):
    GamePack = apps.get_model("engagement", "GamePack")
    GameQuestion = apps.get_model("engagement", "GameQuestion")
    key, title, desc, gtype, category, order, questions = PACK
    pack, _ = GamePack.objects.get_or_create(
        key=key,
        defaults={
            "title": title,
            "description": desc,
            "game_type": gtype,
            "category": category,
            "order": order,
        },
    )
    if pack.questions.exists():
        return
    for i, (prompt, options) in enumerate(questions):
        GameQuestion.objects.create(pack=pack, prompt=prompt, options=options, order=i)


def unseed(apps, schema_editor):
    GamePack = apps.get_model("engagement", "GamePack")
    GamePack.objects.filter(key=PACK[0]).delete()


class Migration(migrations.Migration):
    dependencies = [("engagement", "0012_blissitem_reminded_at")]
    operations = [migrations.RunPython(seed, unseed)]
