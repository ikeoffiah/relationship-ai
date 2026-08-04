# Position: the `spicy` games category

Owner: product/design (`local_81faf803`). Written 2026-08-03 at the PM's request
— a written position rather than an improvisation, ahead of couples therapists
becoming the primary channel.

**Short version: keep the content, change the framing, hide the entry point.**
The content is clinically unremarkable. The packaging is the problem, and it is
the packaging a clinician would decline to explain to a client.

---

## 1. What it actually is

Checked rather than assumed:

- **One pack**, `After Dark`, out of nine. The others are relationship (3), fun
  (2), spiritual (2), financial (1).
- **The prompts are mild.** *"My favourite kind of affection is…"*, *"I feel most
  desired when you…"*, *"My ideal romantic evening is…"*, *"The best way to set
  the mood is…"*
- **The gate is genuinely good** and enforced server-side in `_visible_packs`:
  both partners age-verified **and** both individually opted in. Asymmetric
  unlock is impossible by construction.
- **Never exercised.** `GameConsent`: 0 rows. `age_verified`: **0 of 1,416
  users.**

That last line matters: the feature is currently fail-closed, but **by accident
of nobody having verified rather than by design**. Nothing has tested the open
path.

---

## 2. The position

### 2.1 Keep the content. Removing it would weaken us in the primary channel.

Desire, affection and sexual connection are standard couples-therapy territory —
Gottman, EFT and sensate-focus work all address them directly. A couples product
that cannot mention desire is conspicuously avoiding something every clinician
in the channel handles routinely, and the avoidance is more noticeable than the
content.

At this level of explicitness, *"I feel most desired when you…"* is closer to a
Love Maps exercise than to an adult game. **A clinician will not blink at the
prompts.**

### 2.2 Change the framing. "Spicy" and 🌶️ are the entire problem.

The gap between the content and its packaging is the whole issue. A therapist
recommending this to clients has to explain a chilli pepper — and having to
explain it is the reason they will not recommend it.

**Rename the category to `intimacy`.** Drop the emoji. That single change makes
the same content recommendable without a conversation.

This costs nothing. `category` is an internal field on `GamePack`, the title
`After Dark` is fine as a pack name, and no user has ever seen either.

### 2.3 Hide the entry point — it is the actual defect

`games_list_screen.dart` puts a 🌶️ `IconButton` in the Games app bar
**unconditionally**, tooltip *"Spicy games"*, before any opt-in and regardless of
whether the couple will ever opt in.

So the gating is correct server-side and the *affordance* is ungated. Every
user sees a chilli pepper in their app chrome — including couples who will never
enable it, and including anyone glancing at the phone.

**Move the opt-in out of chrome.** It belongs as a row inside preferences or the
Us hub, found deliberately by someone looking for it, not offered in the app bar
to everyone. This is the same error the codebase already diagnosed and fixed
elsewhere: *"a navigation menu disguised as chrome."*

### 2.4 Keep the double opt-in, and write down the real reason

The code comment says *"a symmetric, consensual gate rather than one partner
enabling adult content for the other."* Correct, and understated.

**The stronger reason is coercion.** In a couple, one partner asking the other to
opt in to sexual content is a pressure point, and it lands hardest in exactly the
relationships this product is most careful about elsewhere. The symmetric gate
does not remove that pressure — nothing in software can — but it ensures **the
app is never the mechanism**: there is no path where one person switches
something on for both.

That belongs beside the boundary reasoning in `outcome-loop.md` §2 rather than in
a passing comment, because it is the same class of decision.

**One addition:** opting *out* must be unilateral, silent, and immediate. Either
partner revokes, the packs disappear, and the other is not told who did it. A
gate that requires both to enable and both to disable would be worse than no
gate — it would make withdrawal a negotiation.

---

## 3. Why this is right for the therapist channel specifically

The founder's instinct about conservative institutions was right, and the
channel change does not reverse this position — it strengthens it.

A secular clinician will not object to the content. What they need is to know
what is in the product before they recommend it, and the honest description is a
**selling point** in the refusals-as-proof shape:

> Intimacy prompts are opt-in by both partners, age-gated, and never shown
> otherwise. Either of you can switch them off on your own, at any time, and the
> other is not told.

That sentence is true, it is enforced server-side, and it is the kind of thing a
clinician checks. It reads as care rather than as prudishness — which is exactly
what "Spicy 🌶️" cannot do.

**For the secondary premarital channel**, the same mechanics with the neutral
name are survivable in a way the current framing is not. A parish coordinator
who sees a chilli pepper stops evaluating.

---

## 4. What to do

| # | Change | Cost |
|---|---|---|
| 4.1 | Rename category `spicy` → `intimacy`; drop 🌶️ everywhere | One migration, a few strings |
| 4.2 | Remove the unconditional app-bar button; move opt-in into preferences | Small |
| 4.3 | Verify opt-out is unilateral, silent and immediate | Check + test |
| 4.4 | Test the **open** path — both verified, both opted in. It has never run. | Test |
| 4.5 | Add the §3 sentence to therapist-facing material | Marketing |

**Do not** gate this behind the paywall. It is Loop 1 content and D3.11 keeps the
free tier intact.

**Do not** make it more explicit to justify the label. The label is what changes.

## 5. Open question for the PM

**App Store age rating.** This content at this mildness probably does not force
17+, but a visible "Spicy" label and a chilli emoji are what draw a reviewer's
attention to the question in the first place. 4.1 reduces review risk as a side
effect rather than as its purpose — worth knowing, not worth doing for that
reason alone.
