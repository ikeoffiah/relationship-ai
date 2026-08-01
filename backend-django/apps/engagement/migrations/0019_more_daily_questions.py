"""Enough daily questions that a couple does not meet the same one twice.

There were fourteen, rotated by the date's ordinal. Every couple on the
platform got the same question on the same day, and it came round again a
fortnight later — so a couple in their third month had answered each of them
six times. That repetition is what makes a feature feel mechanical, and it is
the thing that gets fixed by having more questions rather than by having a
model write them.

Categories are the ones already on the model. The balance is deliberate:
`intimacy` is the smallest group, because it is the one that lands worst at the
wrong moment, and `appreciation` and `connection` are the largest, because they
are the two that are safe on any day of a relationship.
"""

from django.db import migrations

QUESTIONS = [
    # ── appreciation ────────────────────────────────────────────────────
    ("What's something they did this week that you never thanked them for?", "appreciation"),
    ("What do they do that makes an ordinary day easier?", "appreciation"),
    ("When did they last make you laugh without trying?", "appreciation"),
    ("What would you miss first if they went away for a month?", "appreciation"),
    ("What's a small kindness of theirs you've come to rely on?", "appreciation"),
    ("What do they do better than you, and are you glad about it?", "appreciation"),
    ("When did they last give you something you didn't ask for?", "appreciation"),
    ("What's a thing they do that you'd never think to do yourself?", "appreciation"),
    ("What have they got better at since you met?", "appreciation"),
    ("What do other people not know about how kind they are?", "appreciation"),
    ("What's the last thing they did that surprised you?", "appreciation"),
    ("When did you last feel proud of them?", "appreciation"),
    ("What's a way they've changed your mind about something?", "appreciation"),
    ("What do you thank them for silently and never out loud?", "appreciation"),
    ("What's the smallest thing they do that means the most?", "appreciation"),
    ("When did they last put you first without mentioning it?", "appreciation"),
    ("What would you tell a friend about them if they weren't listening?", "appreciation"),
    ("What have they carried for you lately without being asked?", "appreciation"),
    ("What's something about them you took for granted this week?", "appreciation"),
    ("When did they last make a hard day shorter?", "appreciation"),
    # ── connection ──────────────────────────────────────────────────────
    ("When did you last feel properly listened to?", "connection"),
    ("What's something you've been meaning to tell them and haven't?", "connection"),
    ("What's on your mind today that you haven't said out loud?", "connection"),
    ("When did you last feel like a team?", "connection"),
    ("What's a conversation you'd like to have but keep putting off?", "connection"),
    ("What do you need more of this week?", "connection"),
    ("When did you last feel far away from each other, and what closed it?", "connection"),
    ("What's something you're worried about that they don't know?", "connection"),
    ("What would you like them to ask you about?", "connection"),
    ("When did you last feel completely yourself with them?", "connection"),
    ("What's a moment from this week you'd like to go back to?", "connection"),
    ("What's the hardest thing about this week for you?", "connection"),
    ("When do you feel closest to them — what's actually happening?", "connection"),
    ("What's something you've changed your mind about lately?", "connection"),
    ("What do you wish they understood without you explaining?", "connection"),
    ("What have you been carrying on your own?", "connection"),
    ("When did you last feel really at ease together?", "connection"),
    ("What's a small thing that's been bothering you?", "connection"),
    ("What would make this week feel less heavy?", "connection"),
    ("What's something you're proud of that you haven't mentioned?", "connection"),
    ("When did you last surprise yourself?", "connection"),
    ("What do you need from them tonight — practically, not romantically?", "connection"),
    ("What's a question you'd like them to stop asking?", "connection"),
    ("What are you looking forward to that has nothing to do with them?", "connection"),
    ("When did you last feel unsure about something and not say?", "connection"),
    # ── fun ─────────────────────────────────────────────────────────────
    ("What's the most ridiculous argument you two have ever had?", "fun"),
    ("If you had a free weekend and no money, what would you do together?", "fun"),
    ("What's a habit of theirs you find funny?", "fun"),
    ("What would your song be, and would they agree?", "fun"),
    ("What's the worst holiday you could plan for each other?", "fun"),
    ("Who would win in an argument about directions, honestly?", "fun"),
    ("What's a skill you'd both be terrible at?", "fun"),
    ("What's the best meal you've ever had together?", "fun"),
    ("If you swapped jobs for a week, who would struggle more?", "fun"),
    ("What's the daftest thing you've done to make them laugh?", "fun"),
    ("What film could you both watch again tonight?", "fun"),
    ("What's something you've both got weirdly strong opinions about?", "fun"),
    ("What would the title of a documentary about your household be?", "fun"),
    ("What's the last thing that made you both laugh at the same time?", "fun"),
    ("If you had to teach a class together, what would it be?", "fun"),
    ("What's a small tradition you two have that nobody else would get?", "fun"),
    ("What's the most useless thing you own together?", "fun"),
    ("Where would you go tomorrow if the day were free?", "fun"),
    ("What's a nickname that never stuck?", "fun"),
    ("What's something you disagree about that doesn't matter at all?", "fun"),
    # ── growth ──────────────────────────────────────────────────────────
    ("What's one thing you'd like to be better at in this relationship?", "growth"),
    ("What do you do when you're upset that doesn't help?", "growth"),
    ("What's a pattern you'd like to break together?", "growth"),
    ("How do you know when you've stopped listening?", "growth"),
    ("What's something you've apologised for and not changed?", "growth"),
    ("What do you find hardest to say?", "growth"),
    ("What would you like to handle differently next time you disagree?", "growth"),
    ("What's a way you've grown that they might not have noticed?", "growth"),
    ("What do you need when you're overwhelmed, and do they know?", "growth"),
    ("What's a fear you have about the two of you?", "growth"),
    ("When you go quiet, what's usually happening?", "growth"),
    ("What's something you'd like to stop apologising for?", "growth"),
    ("What do you avoid talking about, and why?", "growth"),
    ("What's a habit of yours that makes things harder?", "growth"),
    ("How do you want to be treated when you get something wrong?", "growth"),
    ("What's a way you've been unfair recently?", "growth"),
    ("What would you like more patience with?", "growth"),
    ("What's a thing you've learned about yourself this year?", "growth"),
    # ── values ──────────────────────────────────────────────────────────
    ("What does a good life look like to you in five years?", "values"),
    ("What's something you'd never compromise on?", "values"),
    ("What did your family get right that you want to keep?", "values"),
    ("What did your family get wrong that you want to leave behind?", "values"),
    ("What does home mean to you?", "values"),
    ("What are you working towards that matters most?", "values"),
    ("How do you want to be remembered by the people close to you?", "values"),
    ("What's a promise you've made to yourself?", "values"),
    ("What do you think you owe each other?", "values"),
    ("What does fairness look like in a household?", "values"),
    ("What would you want to be true of you both in twenty years?", "values"),
    ("What's something you believe that most people you know don't?", "values"),
    ("What do you want money to do for you?", "values"),
    ("What's a decision you're glad you made together?", "values"),
    ("What do you want your ordinary weeks to feel like?", "values"),
    ("What would you protect above everything else?", "values"),
    # ── intimacy ────────────────────────────────────────────────────────
    # The smallest group on purpose. These land worst at the wrong moment, and
    # `services._allowed_categories` holds them back after a rupture.
    ("When do you feel most wanted?", "intimacy"),
    ("What kind of touch do you miss when it's been a while?", "intimacy"),
    ("What makes you feel close after a hard day?", "intimacy"),
    ("What's something you'd like more of that you find hard to ask for?", "intimacy"),
    ("When did you last feel really desired?", "intimacy"),
    ("What helps you relax enough to be close?", "intimacy"),
    ("What's a small gesture that means more than it looks?", "intimacy"),
    ("How do you like to be comforted?", "intimacy"),
]


def seed(apps, schema_editor):
    DailyQuestion = apps.get_model("engagement", "DailyQuestion")
    start = DailyQuestion.objects.count()
    for offset, (text, category) in enumerate(QUESTIONS):
        DailyQuestion.objects.get_or_create(
            prompt_text=text,
            defaults={"category": category, "order": start + offset},
        )


def unseed(apps, schema_editor):
    DailyQuestion = apps.get_model("engagement", "DailyQuestion")
    DailyQuestion.objects.filter(
        prompt_text__in=[text for text, _ in QUESTIONS]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("engagement", "0018_blissitem_partner_invite")]
    operations = [migrations.RunPython(seed, unseed)]
