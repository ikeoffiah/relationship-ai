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
