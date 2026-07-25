"""Seed more couple-game packs. All use the scored guess-your-partner mechanic
the existing client already handles (Know Your Partner + Would You Rather).
Idempotent. The spicy pack is gated by age-verification + per-couple opt-in in
the API, not here."""

from django.db import migrations

# (key, title, description, game_type, category, order, [(prompt, [options]), ...])
PACKS = [
    (
        "kyp-faith-values",
        "Faith & Values",
        "How well do you know what grounds each other?",
        "know_your_partner",
        "spiritual",
        1,
        [
            ("What grounds me most spiritually is…", ["Prayer", "Nature", "Community", "Quiet reflection"]),
            ("My idea of living my values is…", ["Helping others", "Honesty always", "Daily gratitude", "Personal growth"]),
            ("On faith, I'd say I'm…", ["Devout", "Seeking", "Private about it", "Spiritual, not religious"]),
            ("A value I most want us to share is…", ["Kindness", "Loyalty", "Generosity", "Forgiveness"]),
            ("When life gets hard, I lean on…", ["My faith", "My people", "Myself", "Time"]),
            ("I feel most at peace when…", ["In worship", "In nature", "With family", "Alone with my thoughts"]),
        ],
    ),
    (
        "kyp-money-future",
        "Money & Future",
        "Do you know how your partner thinks about money?",
        "know_your_partner",
        "financial",
        2,
        [
            ("With money, I'm more of a…", ["Saver", "Spender", "Planner", "Go-with-the-flow"]),
            ("Our top financial priority should be…", ["A home", "Travel & experiences", "Paying off debt", "Security"]),
            ("A dream purchase for us is…", ["A home", "A big trip", "A car", "An experience"]),
            ("When it comes to budgeting, I…", ["Track everything", "Wing it", "Split it up", "Avoid it"]),
            ("In 5 years I hope we've…", ["Bought a home", "Traveled a lot", "Grown savings", "Started a family"]),
            ("Financial stress hits me hardest around…", ["Unexpected bills", "Big purchases", "Everyday spending", "The future"]),
        ],
    ),
    (
        "kyp-just-for-fun",
        "Just for Fun",
        "The lighthearted round — how well do you really know each other?",
        "know_your_partner",
        "fun",
        3,
        [
            ("My perfect weekend is…", ["Adventure", "Total relaxation", "Seeing friends", "A home project"]),
            ("My ideal vacation is…", ["Beach", "Mountains", "City", "Road trip"]),
            ("My guilty pleasure is…", ["Reality TV", "Junk food", "Online shopping", "Sleeping in"]),
            ("At a party I'm usually…", ["The life of it", "In one deep chat", "Helping the host", "Leaving early"]),
            ("My comfort watch is…", ["A comedy", "A thriller", "A documentary", "Something cozy"]),
            ("If we won the lottery I'd first…", ["Travel", "Buy a home", "Save it", "Treat everyone"]),
        ],
    ),
    (
        "would-you-rather-1",
        "Would You Rather",
        "Pick yours, then guess what your partner would choose.",
        "would_you_rather",
        "relationship",
        4,
        [
            ("Would you rather…", ["A cozy night in", "A night out"]),
            ("Would you rather…", ["Breakfast in bed", "A sunset walk"]),
            ("Would you rather…", ["Somewhere new", "A favorite spot"]),
            ("Would you rather…", ["A big group hangout", "Just the two of us"]),
            ("Would you rather…", ["A surprise date", "Plan it together"]),
            ("Would you rather…", ["A deep talk", "Silly fun"]),
        ],
    ),
    (
        "kyp-after-dark",
        "After Dark",
        "A little more intimate — for couples who've turned this on together.",
        "know_your_partner",
        "spicy",
        5,
        [
            ("My favorite kind of affection is…", ["Cuddling", "Kissing", "Hand-holding", "A surprise touch"]),
            ("I feel most desired when you…", ["Compliment me", "Make time for me", "Flirt with me", "Plan a surprise"]),
            ("My ideal romantic evening is…", ["A candlelit dinner", "Dancing at home", "A long bath together", "A getaway"]),
            ("The best way to set the mood is…", ["Music", "Low lights", "A good meal", "A back rub"]),
            ("I'd love for us to be more…", ["Playful", "Adventurous", "Affectionate", "Spontaneous"]),
            ("A little romance to me looks like…", ["Love notes", "Slow dances", "Weekend escapes", "Surprise dates"]),
        ],
    ),
]


def seed(apps, schema_editor):
    GamePack = apps.get_model("engagement", "GamePack")
    GameQuestion = apps.get_model("engagement", "GameQuestion")
    for key, title, desc, gtype, category, order, questions in PACKS:
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
            continue
        for i, (prompt, options) in enumerate(questions):
            GameQuestion.objects.create(pack=pack, prompt=prompt, options=options, order=i)


def unseed(apps, schema_editor):
    GamePack = apps.get_model("engagement", "GamePack")
    GamePack.objects.filter(key__in=[p[0] for p in PACKS]).delete()


class Migration(migrations.Migration):
    dependencies = [("engagement", "0006_gameconsent")]
    operations = [migrations.RunPython(seed, unseed)]
