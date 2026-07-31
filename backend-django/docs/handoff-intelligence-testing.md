
---

## 8. Per-couple calibration of what counts as sharp

Sharpness is couple-relative. "You're the worst 😂" between two people who talk
that way is affection; the same words elsewhere are contempt. One global
threshold cannot be right for both, and the couple it is wrong for turns the
feature off.

The loop that learns this already existed — `outcomes.py`, per-couple, decayed,
one-directional — it just ran at a single level per couple, so overriding the
caution on banter also quietened it for genuine contempt. It now splits by
**register**.

**How.** `assist.register_of(draft)` returns `playful` or `plain`, locally and
free: emoji or laughter markers make it playful, *unless* the draft contains
name-calling, a threat, or an absolute aimed at the partner. Those
disqualifiers are the point — an emoji after "you always do this" does not make
it a joke, and letting it would hand couples a way to calibrate away the exact
patterns the check exists for. The most a couple can teach this is to stop
commenting on their banter.

`/assist/caution-outcome` takes an optional `draft`, derives the register from
it, and records under `caution@playful` / `caution@plain`. Only the register is
kept — the draft is not stored, logged or forwarded, and `CouplePolicy` still
records that a kind of help was offered in a kind of moment, never what was
said.

**Why the sender rather than the receiver.** The obvious design is to ask the
partner who received a borderline message whether they minded. Two reasons not
to. It tells the receiver that the system had doubts about their partner's
message, which is a leading question that manufactures injury where there was
none — the inverse of the S7 property. And it is biased in the worst possible
direction: in a couple with a controlling dynamic, the partner being asked will
say it was fine, so the feature would learn to go quiet exactly where it should
stay loud. Any feedback channel routed through the person with less power in
the relationship has this property. The sender's own override is supervised,
already collected, and comes from the person who knows what they meant.

If receiver input is wanted later, the safe shape is a *preference* asked once
in settings ("when you two are joking, should Bliss stay out of it?"), never a
verdict on a specific message.

**Both keys are read.** `_caution_is_wanted` checks the register bucket *and*
the bare `caution` key. Reading only the register key would have been the
write-here/read-there bug that took this loop out once already — silently, for
every couple who had taught it something before today.

**S19** covers it: banter cautions, five overrides, banter goes quiet including
a joke never sent before, and contempt still cautions for that same couple.
Plus unit tests in `tests_assist.py` for the disqualifiers.

**The catch, and it is a big one.** *Mobile never calls
`/assist/caution-outcome` at all.* Nothing in `couple_chat_viewmodel.dart`
reports which way a caution went, so the entire outcome loop — this
calibration, the suppression in S11, the tendency observed when a rewrite is
accepted — receives nothing from real users and is exercised only by this
suite. Wiring the caution sheet's three buttons to that endpoint, with the
draft, is what turns all of it on. It is a small change and it is the highest
-value one left in this area.
