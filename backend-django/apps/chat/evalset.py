"""Labelled drafts for measuring the pre-send check.

Accuracy here is asymmetric, and the labels reflect that. A false negative is a
missed opportunity to soften something. A **false positive is much worse**: it
tells someone their ordinary, honest message is unkind, and the fastest way to
make a couple stop talking in the app is to moralise at them for being upset.

So the "benign" half is deliberately loaded with messages that are blunt, sad,
frustrated, or in the middle of a disagreement — all of which must pass
untouched. Only contempt, name-calling, sweeping character attacks and threats
should flag.
"""

# (draft, should_flag)
EVAL_DRAFTS: list[tuple[str, bool]] = [
    # ── Plainly benign: logistics and warmth ────────────────────────────────
    ("ok see you at 7", False),
    ("can you grab milk on the way home?", False),
    ("just landed, calling you in a bit", False),
    ("miss you today", False),
    ("that was such a good dinner, thank you", False),
    ("running 15 late, sorry!", False),
    ("do you want to watch something tonight?", False),
    ("I booked the table for friday", False),
    # ── Benign but negative: upset, sad, blunt. MUST NOT FLAG. ──────────────
    ("I'm really tired and I don't have it in me tonight", False),
    ("I felt hurt when you left without saying anything", False),
    ("I don't agree with you on this at all", False),
    ("that annoyed me, honestly", False),
    ("I need some space this evening, not upset with you", False),
    ("I've been dreading this conversation", False),
    ("I'm frustrated and I want to talk about it properly", False),
    ("no, I don't want to go. I told you that already", False),
    ("this is the third time and it's wearing me down", False),
    ("I'm angry about what happened yesterday", False),
    ("can we not do this right now, I'm exhausted", False),
    ("I think you were wrong to say that", False),
    # ── Should flag: contempt, name-calling, sweeping attack, threat ────────
    ("you never listen to me and you always put your friends first", True),
    ("you're so selfish, it's actually pathetic", True),
    ("wow. classic you. grow up", True),
    ("you always ruin everything, every single time", True),
    ("honestly you're just lazy and everyone sees it", True),
    ("if you do that again I'm gone, watch me", True),
    ("you're an idiot for thinking that", True),
    ("nobody else would put up with you", True),
    ("you never cared about me, not once", True),
    ("shut up. I'm done talking to you", True),

    # ── Contempt the original word list missed entirely ─────────────────────
    ("oh please, spare me the drama queen act", True),
    ("here we go again, why am I not surprised", True),
    ("you're just like your mother and you'll never change", True),
    ("wow just wow. cry me a river", True),
    ("that never happened, you're imagining things again", True),
    ("fuck you, I'm not doing this", True),
    ("you're being hysterical, calm down", True),
    ("what a joke. absolutely pathetic", True),
    ("don't talk to me, leave me alone", True),
    ("maybe we should break up then", True),

    # ── Benign uses of words that appear in the vocabulary ───────────────────
    # These may still escalate — that costs one cheap call the model clears —
    # but they must never be *flagged*, so they belong in the set.
    ("that show was ridiculous, I laughed so hard", False),
    ("relax, I've got the tickets sorted", False),
    ("this traffic is absolutely disgusting", False),
    ("never mind, I found my keys", False),
    ("I always look forward to fridays with you", False),
    ("my boss is being a nightmare, not you", False),
]


def counts() -> tuple[int, int]:
    flagged = sum(1 for _, should in EVAL_DRAFTS if should)
    return len(EVAL_DRAFTS) - flagged, flagged


# ── Rupture detection ───────────────────────────────────────────────────────
#
# A different question from the one above, with a different asymmetry, so it
# needs its own labels.
#
# The pre-send check asks "will this wound the person reading it" and is
# generous, because escalating costs one cheap call. Rupture detection asks
# "were these two fighting", and its answers feed the connection score and the
# repair nudge. A false positive there is the product telling a couple their
# relationship went badly on the strength of a string match; a false negative
# is a fight nobody counted, which costs nothing because everything downstream
# fails toward "no rupture" and "already repaired".
#
# Three classes rather than two, because the single most useful thing a
# detector can say about most sharp-sounding messages is "on its own, this
# means nothing":
#
#   None          ordinary, however blunt or negative.
#   "dismissive"  stonewalling, sweeping, shutting down. Real when it recurs,
#                 meaningless alone — half these phrasings are also how people
#                 agree to things ("whatever's easiest", "I don't care, you
#                 pick"). Needs corroboration.
#   "hostile"     contempt, name-calling, threats. A rupture on its own.
#
# (text, class)
EVAL_SHARP: list[tuple[str, str | None]] = [
    # ── Ordinary, including the phrasings the old detector fired on ─────────
    ("I don't care what we watch tonight", None),
    ("whatever you want is fine", None),
    ("whatever's easiest for you", None),
    ("do whatever works for your schedule", None),
    ("I don't care either way, you pick", None),
    ("forget it, I already grabbed one", None),
    ("I'm done with dinner, are you ready?", None),
    ("running 10 late", None),
    ("can you grab milk on the way home", None),
    ("night x", None),
    # ── Blunt, upset, disagreeing. Not a rupture. ───────────────────────────
    ("I'm frustrated and I want to talk about it properly", None),
    ("I felt hurt when you left without saying anything", None),
    ("I don't agree with you on this at all", None),
    ("that annoyed me, honestly", None),
    ("this is the third time and it's wearing me down", None),
    ("I need some space this evening, not upset with you", None),
    ("I think you were wrong to say that", None),
    ("can we not do this right now, I'm exhausted", None),
    # ── Playful. Emphatically not a rupture. ────────────────────────────────
    ("you're the worst 😂", None),
    ("I hate you so much right now 😂😂", None),
    ("stop it 😭", None),
    # ── Dismissive: real when it recurs, nothing on its own ─────────────────
    ("whatever.", "dismissive"),
    ("whatever, fine", "dismissive"),
    ("forget it", "dismissive"),
    ("forget it then", "dismissive"),
    ("I'm done", "dismissive"),
    ("I'm done talking about this", "dismissive"),
    ("don't talk to me", "dismissive"),
    ("leave me alone", "dismissive"),
    ("I'm not doing this", "dismissive"),
    ("you always do this", "dismissive"),
    ("you never listen to me", "dismissive"),
    ("I don't care anymore", "dismissive"),
    ("I don't care what you do", "dismissive"),
    # ── Hostile: a rupture on its own ───────────────────────────────────────
    ("you're pathetic and I don't know why I bother", "hostile"),
    ("you are so selfish it is unbelievable", "hostile"),
    ("grow up", "hostile"),
    ("oh please, spare me", "hostile"),
    ("this is why nobody can talk to you", "hostile"),
    ("fuck you", "hostile"),
    ("shut up", "hostile"),
    ("stop being so dramatic", "hostile"),
    ("you're overreacting as usual", "hostile"),
    ("I want a divorce", "hostile"),
    ("you're a complete idiot", "hostile"),
    ("that's just typical you", "hostile"),
    ("why am I not surprised", "hostile"),
    ("you'll never change", "hostile"),
    ("here we go again", "hostile"),
    ("calm down", "hostile"),
]
