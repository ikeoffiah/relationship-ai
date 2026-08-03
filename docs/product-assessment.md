# Product assessment: Bliss

An outside read of the product through four lenses — Cagan's *Inspired*, Eyal's
*Hooked*, Krug's *Don't Make Me Think*, and Torres's *Continuous Discovery
Habits*. Based on a full pass over the code (32k lines Flutter, 17k lines
Django, 54 screens) and a live walkthrough on an iPhone 17 Pro Max simulator
against the local stack.

Written 2026-08-02.

---

## The one-paragraph version

The *thinking* in this product is well above average — genuinely so. The
reasoning in `connection.py`, `boundary.py`, `assist.py`, `insights_card.dart`
and `docs/outcome-loop.md` is the kind of work Cagan describes when he
distinguishes product teams from feature teams: someone has repeatedly asked
"what does this do to the couple?" and changed the design because of the
answer. That is rare and it is the asset here.

The *execution* has drifted into exactly what Cagan warns about. Twenty-one
feature areas exist, most of them shallow; the daily habit runs on 14 rotating
questions; there is no analytics of any kind, so nobody can know which of the
twenty-one matter; there is no business model in the codebase at all; and the
path from install to first value is 40+ taps of clinical questionnaire followed
by a modal privacy wall and a blank screen. The product is well-reasoned
locally and unvalidated globally.

Three things would change more than everything else combined: **instrument it**,
**cut the onboarding gate**, and **fix the daily question content pool**.

---

## Part 1 — What is genuinely good

### 1.1 The ethical reasoning is a real differentiator (Cagan: product vision)

This is the strongest thing in the codebase and it is not a soft point — it is
the defensible moat.

`personalization/connection.py` reasons through why a couple score must be
built from behaviour rather than from averaging two private check-ins: the
average leaks one partner's answer to the other by arithmetic. It then commits
to five properties — mutual not busy, able to fall, conflict subtracted rather
than penalised, slow, and quiet when low. That last one matters most: the score
hides itself on a bad week, because "the morning after a fight, someone opening
the app for help should be met with something useful, not a low number."

`personalization/boundary.py` promotes "one partner's profile is never shown to
the other" from a convention to a single enforced function with an adversarial
test. The reasoning is stated plainly in `docs/outcome-loop.md`: an inferred
model of one partner surfaced to the other "is a manipulation manual… in a
separation it is discoverable." Very few teams building in this space would
have written that sentence, let alone built the boundary.

`insights_card.dart` renders *nothing* when there is nothing to say — no "no
insights yet" placeholder — because a weekly card announcing that we looked and
found nothing "would turn an honest silence into a weekly reminder of being
assessed."

`chat/assist.py` sets two rules for AI in the couple's thread: **fail open**
(a broken classifier must never trap someone's message) and **stay rare** ("an
assistant that comments constantly stops being an assistant and becomes a
chaperone, and people stop typing honestly in front of it").

**This is your positioning.** It is not currently expressed anywhere a user or
an investor can see it — see §2.7.

### 1.2 Anti-dark-pattern instincts (Hooked, read correctly)

Eyal's book is routinely misread as a manual for compulsion loops. This team
read it the other way and it shows:

- The streak was deliberately removed. `daily_ritual_screen.dart` explains why:
  a consecutive-day counter "turns how often two people tap a phone into a
  proxy for how they are doing, and it hands them a number saying they broke
  something on a week one of them was ill." It was replaced with "Together 12
  of the last 30 days" — a count a bad week cannot take away.
- The safety button was de-escalated. A `#B71C1C` "Get Help Now 🆘" bar used to
  sit on nine screens with a second red floating button on top of it on three
  tabs, tied to no risk signal. It is now one quiet icon, same destination, one
  tap from anywhere, with emergency red retained only where it means something.
- The connection score is designed to be *able to fall*, which is the opposite
  of what an engagement-optimised metric does.

For a relationship product this restraint is correct and it is hard-won.

### 1.3 The two-sided reveal is a strong core mechanic

The daily question — both partners answer privately, answers unlock only when
both are in — is the best mechanic in the product. It creates a genuine variable
reward (Hooked's third phase), it is inherently two-sided, and `TodayHero`
resolves the home screen to exactly one state (`reveal` / `unanswered` /
`waiting` / `done`) with the action inline rather than one screen away. The
ordering is deliberate and correct: the reveal outranks everything, and
"waiting on your partner" never stands alone because a dead end is the fastest
way to stop opening an app.

This is the thing to build the product around. It is currently starved of
content (§2.3).

### 1.4 Safety engineering is real

Three-layer classifier (rules → embeddings → LLM), a labelled evaluation set,
and CI gates at ≥90% clear-crisis recall with **zero** tolerated false
positives on safe messages — including deliberate traps like "my back is
killing me." `VALIDATION.md` is honest about what the gates do and don't cover
(paraphrase recall is reported, not gated, because it needs keys CI doesn't
have). Support resources are one tap from every screen. This is the part of the
product most likely to matter legally and it is the part treated most rigorously.

### 1.5 Honest specs

Five documents in `docs/` are marked "spec, not an implementation report" or
"Status: proposed" and are candid about what does not work. `relationship-insights.md`
opens by stating the feature is unbuilt and that the shipped manager "raises
`AttributeError`." `daily-questions.md` states plainly that "the product's
central claim is that it knows this relationship; the daily question knows
nothing about anybody." Writing that down before building is exactly Torres's
discipline of making assumptions visible so they can be argued with.

### 1.6 The navigation refactor was the right call

Eleven features were previously reachable only through icon buttons inside
another feature's app bar — "a navigation menu disguised as chrome." Two Truths
sat a level below that; the @bliss plan was reachable only via a snackbar that
appeared once, *after* you had already used it. Collapsing Home/History/Privacy/
Settings into Today/Us/Talk/You freed three of four nav slots for product
rather than admin. Correct diagnosis, correct fix.

### 1.7 Latency reasoning tied to user experience

`assist.py` documents a model comparison (gpt-4.1-nano 5/6 at 714ms vs
gpt-4.1-mini 6/6 at 782ms) and chooses the slower model because 68ms inside a
2.5s budget is worth "the one false positive that makes a couple turn the
feature off." Separately, the read-coach timeout was raised from 2.5s to 6s
after noticing that "under load the hardest message a partner can send got no
coaching at all, because the call timed out and a timeout is indistinguishable
from *nothing needed*." That is engineering reasoning about product outcomes.

---

## Part 2 — What is bad

Ordered by how much damage each does.

### 2.1 There is no analytics. At all. (Cagan + Torres — critical)

```
grep -rl "analytics|amplitude|mixpanel|posthog|track(" mobile/lib backend-*
→ two false positives (audio "tracking" in a voice recorder)
```

Sentry captures crashes. **Nothing captures behaviour.** There is no event for
onboarding started, onboarding abandoned, question answered, invite sent,
invite accepted, session started, message sent, feature opened, or day-2 return.

Everything below follows from this:

- You cannot compute activation, retention, or the invite-acceptance rate — the
  three numbers that decide whether this product lives.
- You cannot tell which of twenty-one feature areas is used. Some of them are
  almost certainly dead weight, and there is no way to know which.
- Torres's opportunity-solution tree needs an outcome at the root. There isn't
  one, so discovery has nothing to point at.
- `docs/outcome-loop.md` contains the line **"A loop that learns and changes
  nothing is a telemetry pipeline."** The product currently has neither. The
  per-couple `CouplePolicy` learning loop was built — good — but the
  product-level equivalent for the team was not.

The irony is sharp: a product that carefully instruments *the couple's*
relationship has no instrumentation of *its own* health.

**This is the single highest-leverage fix in the document.** A privacy-respecting
event schema — action names and timestamps, no content, honouring the existing
consent model — is roughly a week and unblocks every other decision.

### 2.2 Time-to-value is brutal (Krug + Hooked — critical)

Measured end to end from the live run:

| Step | Cost |
|---|---|
| Sign up + verify email + verify age | ~4 screens |
| **RSQ: 30 Likert items, all mandatory** | 30 taps |
| Relationship context | multi-field |
| Cultural context | multi-select |
| Communication quiz | 5 questions |
| **Total before seeing the product** | **40+ deliberate taps** |

There is no skip. `auth_landing_screen.dart` hard-routes any user with
`onboarding_completed == false` into the flow, and `rsq_screen.dart` disables
Continue until `isRsqComplete` — every one of 30 items answered.

Three compounding problems:

**The scale has no anchors.** The 30 items render as bare chips labelled
`1 2 3 4 5`. There is no "Strongly disagree / Strongly agree" legend anywhere
in `features/onboarding/` — I grepped for it and it does not exist. So a user
answers 30 psychometric items without being told which end is which. This is not
just a usability defect; it silently corrupts the attachment-style scores that
feed prompt modifiers, micro-action selection, and the portrait. **Fix this
today — it is a two-line change and it is poisoning your personalization data.**

**The framing is clinical.** Step headers read "Attachment Style," "Cultural
Context," "Communication Style." Item 4 is "I want to merge completely with
another person." Item 18 is "My desire to merge completely sometimes scares
people away." This is a validated research instrument administered verbatim, and
it reads like intake paperwork, not like a product.

**The payoff is thin.** After 40 taps the reveal is two cards: "Attachment
Style: Fearful Avoidant" and "Communication Style: Analytical." Two labels for
forty answers. Krug's core rule — every question you ask must earn itself — is
violated 28 times over.

What Cagan would say: the questionnaire exists because the *system* wants
prompt modifiers, not because the *user* wants anything. Value risk is being
paid for by the user, up front, before they have any reason to trust you.

**Recommendation:** cut to 8–10 items (short-form RSQ variants exist and are
psychometrically defensible), label the scale ends, make the rest optional and
progressive, and let people into the product first. Add the anchors regardless
of whether you shorten it.

### 2.3 The daily habit runs on 14 questions

`todays_question()` selects from `DailyQuestion.objects.filter(is_active=True)`.
Migration `0002_seed_content.py` seeds **14 rows**. That is the entire content
pool for the product's central daily loop.

Recent work added per-couple ordering (`_couple_order`) and category filtering
by circumstance (`_allowed_categories`) — both good — but a shuffled 14 is still
14. A couple in month three has answered every question roughly six times. There
is no dedupe against prior answers, so someone will be asked what they are
looking forward to this week while their previous six answers to that exact
question sit unread in the database.

`docs/daily-questions.md` diagnoses this precisely, prescribes batch generation
ahead of time (correctly rejecting generate-on-read for four stated reasons),
and remains unbuilt.

For Hooked's variable-reward phase, a 14-item loop that repeats fortnightly is
not variable — it is a rerun. This is the highest-value *content* gap in the
product and the fix is already specified.

### 2.4 There is no external trigger for the core loop (Hooked)

The celery beat schedule contains six jobs. None of them is "tell the couple
today's question is ready."

Of the 19 notification types, the daily-ritual-related ones are all *reactive*:
`DAILY_QUESTION_READY` fires only when the **second** partner answers, and
`PARTNER_CHECKED_IN` only after a partner acts. The reminders that do fire on
schedule (`BLISS_REMINDER`, `COMMITMENT_REMINDER`) are ones the user explicitly
created for themselves.

So if neither partner opens the app, nothing ever prompts them, and the loop
silently dies. In Eyal's terms, the product has an internal trigger (loneliness,
post-argument tension) and no external trigger to bootstrap the habit before
that internal trigger forms. Habits do not form without one.

The counter-argument — "we removed the streak because we don't want to nag" —
is right about streaks and wrong about triggers. A single well-timed daily
prompt is not a compulsion loop. And you already have the machinery to do it
respectfully: `CouplePolicy` suppression exists specifically so a nudge a couple
keeps dismissing stops firing.

### 2.5 Notification control covers 4 of 19 types

`settings_screen.dart` exposes exactly four toggles: session reminders, partner
joined, relay received, insight detected.

The other fifteen — daily question ready, partner checked in, goal progress,
game ready, bliss reminder, bliss created, bliss invite, commitment reminder,
commitment created, focus proposed, focus started, focus ended, safety followup,
therapist connected, system — **have no user control at all.**

For a product whose stated posture is user agency and consent, and which
carefully lets people control what data is shared, having no way to turn off
two-thirds of its own push notifications is inconsistent with its own values.
It is also the fastest route to a system-level "turn off all notifications from
Bliss," which kills §2.4 permanently.

### 2.6 The invite is email-only, and everything depends on it

`invite_partner_screen.dart` offers one input: a text field for the partner's
email address. There is no share sheet, no copyable link, no SMS, no WhatsApp,
no QR code — despite `bliss://accept-invite?token=…` already being implemented
and working in `main.dart`.

The path for partner B is: receive an email → find it (not in Promotions) → tap
→ install → sign up → verify email → verify age → 30 Likert items → four more
onboarding screens → finally connected.

Every partner-dependent feature is behind that: the two-sided reveal, all games,
Two Truths, Focus, Commitments, Shared goals, couple chat, Say-it-better, joint
sessions. That is most of the product.

Two things make it worse:

**The Us tab does not gate on partner status.** `talk_screen.dart` correctly
branches on `connected` and shows "Connect with your partner" when solo.
`us_screen.dart` does not — it renders all eight destinations unconditionally.
So a solo user taps "Games — answer about yourself, then guess each other" and
the backend replies `"Games need an active partner connection."` Same product,
two different answers to the same question, one screen apart.

**The invite screen speaks our language, not theirs.** "Journey Together."
"Invite your partner to share this therapeutic space." Krug: a user should never
have to translate. Say what happens — "They'll get a link. Once they're in, you
can see each other's answers."

**Recommendation:** add a share sheet with a link as the primary action, keep
email as secondary, and let partner B see *something* (the question their
partner answered, blurred) before being asked to complete onboarding.

### 2.7 There is no business model in the codebase

No subscription, no paywall, no entitlement check, no RevenueCat, no Stripe, no
billing, no tier gating, no trial. `legal_documents.dart` mentions subscriptions
in boilerplate; nothing implements them.

Cagan's four risks are value, usability, feasibility, and **viability**. The
first three have been worked on. The fourth has not been started, and it is the
one that determines whether any of this survives. It also shapes the product:
a per-couple subscription, a freemium split, and a therapist-referral model
imply three very different feature sets, and you are currently building for
none of them specifically.

Related: the therapist portal exists in `apps/therapist/` with no visible
product story around it. That is either a real B2B2C wedge — plausibly the
strongest monetization path for this category — or dead code. Decide which.

### 2.8 Twenty-one feature areas, no evidence for any of them

Feature areas in `mobile/lib/features/`: auth, bliss, chat, commitments, consent,
couple_chat, engagement, faith, focus, games, history, home, hubs, notifications,
onboarding, relationship, relay, safety, sessions, settings, two_truths.

Commit velocity: 169 commits in July 2026 alone, out of 285 total since April.
That is a four-month-old codebase with a mature-product surface area.

Cagan's feature-factory test is not "are these features good?" — several are
thoughtfully built. It is "can you say what outcome each one moved?" Without
§2.1, the answer is no for all twenty-one. Torres would add: none of these
appear to trace back to a validated opportunity from customer contact.

The concrete cost shows up in the hubs. `HubScaffold` defines an optional
`badge` field for exactly this purpose — "2 waiting," "Sam's turn." **No hub
passes one.** All three tabs are static lists that look identical every time you
open them. The code comment on `TodayHero` diagnoses this exactly, about the old
home screen: five static cards that "could not answer the only question a
dashboard exists to answer: *is there anything here for me today?*" That fix was
applied to Home and then not applied to the three tabs that replaced it.

### 2.9 The AI session is buried under four chrome bars and opens blank

From the live run, opening a private session shows, top to bottom:

1. App bar — "Private session" + support icon + "Consent" pill
2. Pink bar — "Private session · Nothing shared  **Change**"
3. White bar — 🔒 "Your private session"
4. Grey bar — "You are talking to an AI, not a licensed therapist. **What that means**"
5. ~1100pt of empty cream
6. "Type a message…"

"Private session" appears three times on one screen. Four bars of disclosure and
zero product. `message_list.dart` has no empty-state branch and `SuggestionStrip`
renders nothing when empty, so a new session is a void.

Krug's rule is that a page should be self-evident. This one is self-evidently
*about its own legal posture*. A first-time user's most likely reaction is
hesitation, which is the opposite of what a counselling product needs in that
moment.

**Recommendation:** collapse bars 2–4 into one persistent line, and open with a
short greeting from Bliss plus 3–4 starter prompts ("Something that happened
this week," "A conversation I'm dreading," "Something I want to appreciate").

### 2.10 A modal consent wall on every single session

`chat_screen.dart` calls `ConsentSummarySheet.show()` in `initState`, on every
entry. It presents a 90%-height modal titled "Before we begin" listing four
settings with four "Edit" links plus "View full privacy settings," and dismissal
without tapping "Start session" drops the user into `_SessionBlockedState`.

`isFirstSession` is never passed as `true` from `ChatScreen`, so the sheet is
dismissible after a two-second lockout — meaning the flow gets the friction of a
hard gate with none of the informed-consent benefit of one.

Two further observations from the live run: the sheet's `FractionallySizedBox(0.9)`
leaves a large dead area between the four rows and the button, and the
"Start session" button renders as pale, low-contrast text that reads as disabled.
I hesitated before tapping it.

Informed consent should be strong once and then quiet. Show the full sheet on
first session; after that the persistent "Consent" pill already in the app bar
is sufficient.

### 2.11 The privacy promise contradicts itself

The consent sheet says: **"Session storage — Your session conversations are
deleted when the session ends."**

The You tab says: **"Past sessions — Everything you have talked through before."**

Both shipped, one screen apart. Whichever is true, a user reading both learns
they cannot rely on either. For a product whose core differentiator is
trustworthiness about data, this is a more serious defect than its size suggests.

### 2.12 Internal machinery is shown to the user

The AI's reply in the live run was preceded by a purple chip reading
**"Validation."** That is `_StrategyChip` in `assistant_message_bubble.dart`
rendering `message.strategy` — the model's internal therapeutic technique.

Telling someone "I am now validating you" immediately before validating them
undermines the validation. It reframes a warm reply as the output of a
technique-selection algorithm. Nobody asked to see it and it helps no one.

Two secondary problems on the same widget: the chip uses raw
`Colors.purple.shade50/700`, off-palette in an otherwise disciplined
coral/cream/teal system; and the assistant's reply renders as bare text with no
bubble and no avatar while the user's message gets a solid coral bubble — so the
one message that needs attribution has none.

**Remove the chip.**

### 2.13 Visual and copy defects seen live

- **The AI disclosure banner is clipped by the Dynamic Island on every tab.**
  `MainNavigationScreen` puts `_buildAIDisclosureBanner()` in a `Column` outside
  any `SafeArea`; the child screens have their own `SafeArea` but the banner
  sits above it. It renders as "You are talking to a[…]l therapist." on Today,
  Us, Talk and You. This is the most-seen pixel in the app and it is broken.
  One-line fix.
- **Redundant disclosure.** The same banner sits permanently on all four tabs
  *and* again inside every chat. A permanent warning stops being read within a
  day (Krug's banner blindness) while still costing vertical space on every
  screen — and the one place it genuinely matters, the chat, already has its own.
- **"Good day," with no name.** Home rendered the greeting followed by blank
  space. `authVM.user?.name.split(' ').first ?? 'User'` doesn't cover an empty
  name string.
- **The suggestion strip clips mid-word** — "…and I want us to find a way" runs
  off the right edge with no wrap and no visible scroll affordance.
- **The joint session is titled "Private session."** `chat_screen.dart`
  hardcodes the title regardless of `isJointSession`. On the screen where
  knowing whether your partner can see this matters most, the label is wrong.
- **Joint sessions use placeholder identity** — `partnerInitial: 'P'`,
  `partnerFirstName: 'Partner'`, hardcoded.
- **Stub in a shipped path** — `_handleStepOut()` carries
  `// In a real app, this would call the API` and only pops the route.
- **Accessibility is essentially absent.** Three `Semantics`/`semanticLabel`
  usages across 54 screens. The check-in is five bare emoji (😞😕😐🙂😍) with no
  labels; the RSQ is 30 sets of unlabelled numeric chips. Flutter gives some of
  this for free, but not these.

### 2.14 No continuous discovery (Torres)

There is no evidence in the repository of any customer contact: no interview
notes, no research directory, no opportunity mapping, no assumption tests, no
usability sessions. `VALIDATION.md` is thorough — and it validates that the
*system* works, not that the *product* is wanted. Every checkbox is a technical
path exercise.

Torres's minimum bar is a weekly touchpoint with a customer feeding a
continuously-updated opportunity-solution tree. The current process appears to
be: identify a problem by reasoning about it (often very well), write a careful
spec, build it, ship it, never find out. The reasoning quality is high enough
that this has produced good decisions anyway — but it does not scale, and it
cannot tell you which of your twenty-one feature areas to kill.

`infra/README.md` mentions a **20-user pilot**. Twenty couples is a discovery
goldmine and there is no sign in the repo of anything being learned from them.

---

## Part 3 — What I would do, in order

**Week 1 — stop flying blind**

1. Add the Likert scale anchors. Two lines. It is corrupting your data now.
2. Wrap the disclosure banner in `SafeArea`. One line.
3. Remove the `_StrategyChip`. Delete.
4. Fix the joint-session title, and resolve the storage/history contradiction
   (§2.11) — decide which is true and make both screens say it.
5. Ship a privacy-respecting event schema: onboarding start/step/abandon/complete,
   invite sent/opened/accepted, question shown/answered/revealed, session
   started/first-message, feature opened, day-N return. Names and timestamps, no
   content, consent-aware.

**Weeks 2–4 — fix activation**

6. Cut onboarding to 8–10 items, make the rest progressive, drop the hard gate.
7. Add a share-sheet invite with a link; keep email secondary.
8. Gate the Us tab on partner status the way Talk already does.
9. Give the chat an opening greeting and starter prompts; collapse the four
   chrome bars to one; show the consent sheet on first session only.

**Weeks 4–8 — fix the loop**

10. Build the generated daily questions per `docs/daily-questions.md`. This is
    the core loop's fuel and the spec is already written.
11. Add one scheduled daily-question trigger, routed through `CouplePolicy`
    suppression so it backs off when ignored.
12. Expose notification controls for all 19 types, grouped.
13. Wire hub badges — `HubScaffold` already takes them.

**Ongoing — discovery and viability**

14. Interview two couples a week from the pilot. Every week. Write it down.
15. Decide the business model, and decide whether the therapist portal is the
    wedge or dead code.
16. Once §5 has two months of data, rank the twenty-one feature areas by usage
    and kill the bottom third. Cagan: the goal is not more features, it is fewer
    features that work.

---

## Closing

The gap in this product is not care and it is not craft — both are visibly
present, and in the ethical reasoning they are exceptional. The gap is
**feedback**. Every serious problem above is a case of a good decision made in
isolation and never checked against a real couple: a questionnaire designed for
what the model needs, an invite designed for the schema, a hub designed as a
menu, a consent flow designed for the lawyer, twenty-one features designed for
the roadmap.

You have a 20-user pilot and a live product. The cheapest thing you can do this
month is start listening to it.
