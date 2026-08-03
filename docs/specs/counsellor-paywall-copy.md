# The counsellor paywall — copy and behaviour

Owner: product/design (`local_81faf803`). Execution-plan **D3.11** constraint 2.
Built by: engineer, with **P0.2**.

The gate is on the counsellor. The door to help is never closed, and the paywall
has to say so. This is the one place where monetisation and safety posture touch,
so the behaviour matters more than the words and is specified first.

---

## 1. The problem with gating at the door

A paywall on the private session fires **before the user has typed anything**.
So at the moment it appears we do not know — and cannot know — whether this
person opened the app to browse or because something happened tonight.

`go-to-market.md` §5.2 names the failure: *"a product that gates help behind a
card at the moment someone needs it is a scandal waiting to happen."* A card form
in front of someone at 1am after a fight is that scandal, and no amount of
careful wording fixes a gate placed at the wrong moment.

## 2. The fix: gate the reply, not the door

**Let them in. Let them type. Run safety. Then decide.**

```
open private session
   └─ session opens normally. No gate, no card, no price.
      └─ user writes and sends their first message
         └─ safety pre-screen runs (already runs on every turn)
            ├─ crisis signal  → full safety path. NO paywall, now or later
            │                   in this session. The session continues, free.
            └─ no signal      → paywall sheet, with the message preserved
                                 ├─ pays     → message sends, reply streams
                                 └─ declines → message KEPT as a draft
```

Why this is right on every axis:

- **Nobody in distress meets a card form.** The classifier reads the message
  before we ask for money, so the one case we must never get wrong is decided by
  evidence rather than by timing.
- **It costs nothing we weren't already spending.** The pre-screen runs on every
  turn already. The expensive counsellor call is what stays gated — so COGS is
  still bounded, which was the point of D3.11.
- **It converts better.** A written message is the strongest intent signal in the
  product. Someone who has typed out the thing they are dreading is far closer to
  paying than someone looking at an empty screen — this is §5.2's own
  "moment-of-need" argument, applied one step later.
- **A decline costs the user nothing.** The draft is kept. They wrote something
  hard; we do not throw it away because they didn't pay.

**The crisis exemption is per session, not per message.** Once a session has
tripped the classifier, that session is free for its whole length. Someone in
crisis must never hit a gate on turn four because turn three read calmer.

Fail-open, matching `assist.py`: **if the classifier errors or times out, no
paywall.** Let the message through. Trapping a message behind a broken
classifier is the worse failure, and here it would also be trapping it behind a
payment.

---

## 3. The sheet

Shown once per session, dismissible, and it must never be the first thing on the
screen (§2).

> ### Keep going with Bliss
>
> You've written something worth thinking through. Bliss can help you work it
> out — and help you say it, when you're ready.
>
> **Bliss is $39. One payment, both of you, no subscription.**
> Everything else you're already using stays free.
>
> **[ Continue — $39 ]**
> **[ Not now ]**
>
> ---
>
> **If you need help right now, you don't need to pay for it.**
> Crisis lines and support services are always free here, and always available —
> whether or not you ever buy anything.
> **[ Get support ]**

### Rules on the words

- **"Not now", never "No thanks" or "Maybe later".** They are declining a
  purchase, not declining help, and the label should not imply they turned
  something down.
- **Never** "Unlock", "Upgrade", "Premium", "Pro", or a lock icon. This is not a
  treasure chest. Someone reached for help and we are asking them to pay — the
  register is plain, not gamified.
- **No urgency of any kind.** No countdown, no "limited", no strikethrough
  price, no "X couples joined this week". Manufactured urgency at a moment of
  real distress is the worst thing in this document.
- **No loss framing.** Not "don't lose your progress", not "your conversation
  will be deleted". Their draft is kept, and the copy says so implicitly by not
  threatening it.
- **State what stays free, in the sheet.** "Everything else you're already using
  stays free" prevents the reading that we have taken the whole app away.
- **The support block is not a footnote.** Same type size as the body, above the
  fold, visually separated. It is not fine print and must not be styled as fine
  print.

### The support block is not optional and not stylable away

- It appears on **every** rendering of this sheet, in every state.
- **[ Get support ]** routes to `/safety`, the same destination as the support
  icon, with no entitlement check anywhere on that path (D7, and money-path
  acceptance criteria 4.1–4.7).
- Tapping it dismisses the paywall entirely. Nobody returns from the crisis
  screen to a card form.
- It renders even if the paywall's own network call fails.

---

## 4. What must never happen

| Never | Why |
|---|---|
| A paywall on `/safety`, the support icon, or anything downstream | D7. Release blocker, not a bug. |
| A paywall shown before the first message is written | §1. It is the whole design. |
| A paywall in a session that tripped the crisis classifier | Per session, not per message. |
| A paywall inside `couple_chat` | Loop 1 is free and partner B must never meet a paywall (D3.11). The couple's own thread is not the counsellor. |
| A paywall during onboarding | They are completing the assessment they may already have paid for. |
| Price or upsell text on any safety surface | Acceptance criterion 4.6. |
| Discarding the user's draft on decline | They wrote something hard. |
| A second prompt in the same session after a decline | Once. Asking twice makes it nagging at exactly the wrong moment. |

---

## 5. The tone coach and "say it better"

Both live in `couple_chat`, both call the same LLM, and both are metered — so
D3.11's COGS logic applies to them too.

**Recommend leaving them free**, and this is a judgement the PM should confirm:

- They are per-message and short. `assist.py` runs them on a small model
  (`gpt-4.1-mini`) with a 2.5s budget and explicit tiering in `_needs_model` to
  keep call volume down. They are an order of magnitude cheaper than a counselling
  turn.
- They are inside the couple's thread, which is Loop 1. A paywall there breaks
  the "partner B never meets a paywall" rule.
- **They are the strongest free-tier hook in the product.** Someone who has
  watched Bliss rewrite a sharp message into one that landed has experienced the
  thing the counsellor does, in miniature, for pennies.

If cost becomes a problem, cap by volume rather than gating by payment — a
per-day ceiling degrades gracefully and never presents a price at a bad moment.

---

## 6. Acceptance criteria

Add to `money-path-acceptance.md` §4.

| # | Criterion |
|---|---|
| 4.8 | A private session opens with no paywall, no price, and no lock icon visible. |
| 4.9 | The paywall appears only **after** a first message is composed and safety-screened. |
| 4.10 | A message tripping the crisis classifier produces the safety path and **no** paywall — and no paywall for the remainder of that session, on any later turn. |
| 4.11 | A classifier error or timeout results in **no** paywall. Fail open. |
| 4.12 | The support block renders on every paywall state, including when the paywall's own network call fails. |
| 4.13 | **[ Get support ]** reaches `/safety` with no entitlement check on the path, and dismisses the paywall. |
| 4.14 | Declining preserves the drafted message. |
| 4.15 | The paywall is shown at most once per session. |
| 4.16 | No paywall renders in `couple_chat` or in onboarding, in any state. |
| 4.17 | Copy contains no countdown, scarcity, strikethrough price, or social-proof count. Reviewed manually, and re-reviewed on any copy change. |

**4.10 and 4.13 are release blockers.** They are the two that turn a pricing
decision into a headline.
