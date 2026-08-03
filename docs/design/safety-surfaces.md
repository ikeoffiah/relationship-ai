# Two surfaces where monetisation and safety touch

Owner: design (`local_81faf803`). Built by: engineer. Written 2026-08-03.

Two designs in one document because they share a single constraint: **both are
seen by someone who may be having the worst evening of their year, and in both
the wrong treatment reads as betrayal rather than as a product decision.**

1. **The counsellor paywall** (P0.2). Copy and behaviour are fixed by
   `docs/specs/counsellor-paywall-copy.md`. Treatment is here.
2. **The support control on the joint video call** (P0.10, D3.17). Ruling is
   fixed by `docs/specs/support-icon-coverage.md` §4, which calls it *"the only
   non-trivial item in this document."* Design is here.

Neither spec is reopened. Where this document appears to disagree with either,
the other spec wins and I have made a mistake.

---

# Part 1 — The counsellor paywall

## 1.1 The moment being designed for

The behaviour, from the copy spec: the session opens freely, the person writes
their message, the safety classifier reads it, and only if it finds no crisis
signal does the sheet appear — with the draft preserved.

So the person on the other side of this sheet has, seconds ago, typed out the
thing they were dreading. They are at their most open. **That is the whole
design problem: at maximum vulnerability we are asking for money, and every
persuasion technique that works here is one we must not use.**

The treatment has one job. Not conversion. Not clarity, though it needs that.
Its job is that **someone who declines does not feel they were tricked into
opening up.** If they close this sheet feeling they were harvested, we have lost
them, their partner, and — if they came from a cohort — the facilitator's next
three classes. Restraint here is not ethics tax; it is the only version that
survives contact with the person it happens to.

## 1.2 The single most important decision: their words stay on screen

**A partial-height bottom sheet. Never a full-screen takeover, never a dialog.**

- `showModalBottomSheet`, `isScrollControlled: true`, **`maxHeight: 58%` of the
  viewport.**
- The composer, with their draft in it, **remains visible above the sheet.**
- Scrim at **12% `AppColors.onBrand`**, not the Material default of 32% black.

The 58% is doing real work and is not a round number chosen for looks. It is the
largest sheet that leaves the composer's first two lines visible on a 5.4"
device. A heavy scrim and a full-height sheet say *what you were doing is gone
now.* A light scrim over a visible draft says *this is a thing on top of what
you were doing, and what you were doing is still there.* We are about to tell
them in copy that their draft is kept; showing it is worth more than saying it,
which is why the copy spec deliberately does **not** say it (a promise not to
delete something introduces the idea that it might be deleted).

Nothing may be layered over the composer. If the keyboard is open when the
classifier returns, **dismiss the keyboard first, then present the sheet** —
otherwise the sheet lands on top of the keyboard and the draft is hidden by
accident, which is the one failure mode this whole decision exists to prevent.

## 1.3 Layout

```
 ╭──────────────────────────────────────────────────╮  radius 24 top
 │                    ────                          │  drag handle, borderStrong
 │                                                  │  32
 │  Keep going with Bliss                           │  headlineLarge 22/600
 │                                                  │  12
 │  You've written something worth thinking         │  bodyLarge 16, softCharcoal
 │  through. Bliss can help you work it out —       │
 │  and help you say it, when you're ready.         │
 │                                                  │  20
 │  Bliss is $39. One payment, both of you,         │  bodyLarge 16/600
 │  no subscription.                                │
 │  Everything else you're already using            │  bodyMedium 14, mutedInk
 │  stays free.                                     │
 │                                                  │  24
 │  ┌────────────────────────────────────────────┐  │
 │  │            Continue — $39                  │  │  coral, onBrand ink, 52pt
 │  └────────────────────────────────────────────┘  │
 │                                                  │  12
 │  ┌────────────────────────────────────────────┐  │
 │  │                Not now                     │  │  outlined, 52pt
 │  └────────────────────────────────────────────┘  │
 │                                                  │  24
 ├──────────────────────────────────────────────────┤  1px hairline, full bleed
 │  ╭────────────────────────────────────────────╮  │
 │  │  If you need help right now, you don't     │  │  bodyLarge 16/600
 │  │  need to pay for it.                       │  │
 │  │  Crisis lines and support services are     │  │  bodyMedium 14, softCharcoal
 │  │  always free here, and always available    │  │
 │  │  — whether or not you ever buy anything.   │  │
 │  │  ┌──────────────────────────────────────┐  │  │
 │  │  │  ♥  Get support                      │  │  │  outlined, 48pt
 │  │  └──────────────────────────────────────┘  │  │
 │  ╰────────────────────────────────────────────╯  │  calmSurface, radius 20
 ╰──────────────────────────────────────────────────╯
```

Horizontal padding `AppSpacing.xxl` (24) throughout.

## 1.4 The rules the treatment has to encode

The copy spec forbids specific words. These are the visual equivalents, and each
maps to a named pattern in the FTC's *Bringing Dark Patterns to Light* taxonomy
or the EDPB's *deceptive design patterns* guidance. Naming them makes the rule
checkable rather than tasteful.

| Forbidden | Pattern it would be |
|---|---|
| A lock icon, a padlock, a key, a "premium" badge, a crown, a star | **Misdirection / trick wording** in visual form. The copy spec bans the words; a glyph says them louder. |
| Any countdown, timer, "today only", or animated urgency | **Urgency** (FTC §2). |
| "X couples joined this week", avatars, testimonials, star ratings | **Social proof** (FTC §6). |
| A struck-through price, a "was $79" | **Sneaking / hidden costs** inverted; also simply untrue. |
| "Not now" as a text link, in grey, smaller, or below the fold | **Misdirection** (FTC §4) and visual interference. The decline must be a real button, same width, same 48pt+ target, differing **only** in fill. |
| Confirmshaming of any kind — "No thanks, I'll struggle alone" | **Confirmshaming** (Mathur et al.). Catastrophic here specifically. |
| Any illustration, mascot, hero image, or celebratory motion | Not a named pattern; simply wrong. This is not a moment for delight. |
| Auto-selecting or pre-highlighting the pay button | **Forced action** (FTC §7). Neither button is focused on present. |
| A second prompt later in the session | Copy spec §4. Once. |

**The support block is not stylable away.** Three structural guarantees, not
style guidance:

1. It renders in **every** state of this sheet, including when the paywall's own
   network call fails — so it is built from constants, never from a payload.
2. **If the sheet ever has to scroll**, at large text sizes or on a small
   device, the support block is **pinned outside the scroll area, at the
   bottom**. The purchase copy scrolls; the route to help never does. This is
   the concrete meaning of the copy spec's *"above the fold."*
3. Its body text is `bodyMedium` at 14 — the same size as the price sub-line
   above it. Never 12, never `mutedInk`, never centred-and-italic. The moment it
   is styled like a legal footer, it is one.

**Get support** carries `Icons.volunteer_activism_outlined` — the exact glyph
from `SupportAction`, which this user has seen in the app bar of every screen for
however long they have had the app. Recognition beats novelty at a bad moment,
and this is the only place in the product where I would insist on an icon inside
a button.

Tapping it dismisses the paywall entirely and routes to `/safety`. Nobody comes
back from the crisis screen to a card form.

## 1.5 Motion

- In: `AppMotion.settle` (360ms), `AppMotion.enter`. Slide from the bottom edge,
  scrim fading in over the same duration.
- Out: `AppMotion.quick` (220ms), `AppMotion.exit`.
- Under reduced motion: cross-fade, no travel, per `AppMotion.duration`.
- **No entrance stagger, no scale-up, no spring, no haptic.** A haptic on a
  paywall is a nudge, and `Curves.elasticOut` here would be grotesque.
- **No delay before the sheet appears.** If the classifier takes 900ms, that is
  900ms of the person watching their message sit there — show a normal sending
  indicator during it, exactly as an ungated send would look, because at that
  moment we do not yet know whether this is gated.

## 1.6 On decline

Sheet dismisses. Composer regains focus, draft intact, cursor at the end.

**No toast. No "we saved your draft". No banner.** Their words are still there;
pointing at that fact is how you make someone wonder whether it was in doubt.

**No visible price, lock, or upsell anywhere in the session afterwards.** Not a
banner, not a greyed send button, not a badge on the composer. They declined
once; the product's job now is to be exactly what it was before it asked.

## 1.7 Accessibility

- Sheet: `Semantics(container: true, namesRoute: true, label: 'Bliss is $39')`.
- **Focus lands on the sheet's heading, not on a button.** A screen-reader user
  should hear what this is before they are anywhere near either action.
- Traversal: heading → body → price → Continue → Not now → support block. The
  support block is last in reading order and that is correct, because it is
  the destination someone arrives at deliberately rather than the first thing
  read; it is *visually* prominent and *structurally* terminal.
- `SemanticsService.announce` nothing. The sheet's arrival is announced by the
  route change; adding an announcement to a payment prompt is a nudge.
- Every target ≥48pt; the two primary buttons at 52.
- Full text at 310% must not push the support block off-screen — §1.4 item 2 is
  the test.

## 1.8 Acceptance criteria

Adds to the copy spec's §6.

| # | Criterion |
|---|---|
| D1 | The user's draft is visible on screen while the sheet is shown, on the smallest supported device with the keyboard dismissed. |
| D2 | Scrim opacity ≤15%; the conversation behind remains legible. |
| D3 | "Not now" has the same width and the same touch target as "Continue — $39". |
| D4 | No lock, padlock, key, crown, star, badge, timer, count or strikethrough renders anywhere in this sheet, in any state. Asserted against the widget tree, not reviewed by eye. |
| D5 | At 310% text scale the support block is fully visible without scrolling; if the sheet scrolls, the support block does not. |
| D6 | With the paywall's network call failed, the support block still renders and **Get support** still reaches `/safety`. |
| D7 | Declining returns focus to the composer with the draft unchanged and shows no toast, banner or price for the remainder of the session. |
| D8 | With Reduce Motion on, the sheet cross-fades and does not travel. |

---

# Part 2 — The support control on the joint video call

`sessions/joint_video_call_screen.dart`. No app bar, a live two-way video call
between partners, and per the coverage spec the screen where an exchange can
escalate in real time.

## 2.1 The three constraints, and what each rules out

**It must be findable by someone who is upset.** Which rules out an
auto-hiding control. Video UIs conventionally fade their chrome after a few
seconds; the call controls here may do that if the engineer wants. **The support
control never fades, never dims, and never requires a tap-to-reveal.** An
affordance that has to be summoned is not "one tap from every screen", it is two
taps and a piece of knowledge.

**It must not read as "hang up" or "report my partner".** Which rules out the
bottom control row. That row is `[mic] [end call, red] [cam]`, and anything
placed in or beside it inherits the semantics of call control — it becomes a
fourth thing you do *to the call*. Adjacency to a red end-call button is the
worst available context for an affordance whose meaning is "there is help
elsewhere". It also rules out any red, any triangle, any shield, any flag, and
any word in the family of *report*, *flag*, *alert*, *emergency*.

**It must not imply we are monitoring the call.** Which rules out a badge, a
recording-style dot, anything that appears *conditionally*, and above all
anything that appears **in response to what is being said**. A control that
materialises when the conversation gets heated tells both people that something
was listening. It is always there, from the first second, and it never changes.

## 2.2 Placement

**Top-left, inside the `SafeArea`, 16pt from both edges.**

Reasoning, including the option I rejected:

- **Not bottom** — §2.1, the destructive neighbourhood.
- **Not top-right** — occupied by the self-view picture-in-picture at 110×160.
  Top-right is where this user's muscle memory lives, because `SupportAction` is
  appended to `actions:` on every app bar in the app, and I considered moving
  the PiP to the left to reclaim it. **I am not proposing that.** Joint video is
  otherwise frozen; a layout change to the self-view is a second change to a
  frozen screen, and the recovered muscle memory is worth less than it sounds —
  a person reaching for help on a full-bleed video screen is not navigating from
  memory of an app bar that is not present.
- **Top-left** is the only remaining corner, and it is the right one for a
  different reason: it is the conventional "get out of here" position, it is
  furthest from the thumb's resting arc so it will not be hit by accident during
  a call, and it is diagonally opposite the destructive control.

## 2.3 Treatment

**A pill, not a bare icon.**

```
╭─────────────────────╮
│  ♥   Support        │   height 44, radius pill
╰─────────────────────╯   ~112 wide
```

| Property | Value |
|---|---|
| Fill | `AppColors.overlayScrim` (`#B3000000`) — 70% black, so it is legible over any frame content including a bright window behind someone's head |
| Icon | `Icons.volunteer_activism_outlined`, `AppIconSize.md` (20), white |
| Label | "Support", `labelSmall` (11/500/+0.5), white, `AppSpacing.sm` after the icon |
| Padding | 14 leading, 16 trailing, vertically centred |
| Border | none |
| Shadow | none — the scrim already separates it |
| Touch target | 48×48 minimum via `IconButton.styleFrom(minimumSize:)` or an explicit `SizedBox`; the visual pill is 44 tall inside it |

**The label is why this is a pill and not an icon.** Everywhere else in the app
this affordance is an icon alone, and that is fine because it sits in an app bar
among other icons, in a screen with a title, in a calm moment. Here it sits over
a moving image of someone's face, alone, with no context, possibly at a moment
when the person looking at it is not reading carefully. One word removes every
ambiguity — including, decisively, the ambiguity between "help" and "hang up".

**White on 70% black is ≥9:1** over any underlying frame, which is why the scrim
is that dark. This is the one place in the product where a heavy scrim is
correct: the background is arbitrary and uncontrollable, so contrast has to be
manufactured rather than assumed.

**Never coral, never crisis red, never teal.** Neutral by construction. A
coloured support control on a call screen is an opinion about the call.

## 2.4 Behaviour on tap

This is where it would be easy to do harm, so it is specified precisely.

1. Route to `/safety` as a full-screen route pushed over the call. **Same
   destination as every other `SupportAction` in the app** — no variant, no
   in-call mini-sheet. One destination, always, is the property D7 protects.
2. **Do not change any call state.** Do not mute the mic, do not disable the
   camera, do not pause the video, do not notify the partner. Every one of those
   is a change to a two-way conversation that the user did not ask for, and the
   partner experiences a silent mute as being hung up on mid-sentence — during
   what may already be a difficult exchange.
3. **A persistent 36pt bar at the top of the safety screen:** *"Your call is
   still connected."* with a **Return** text button. `AppColors.calmSurface`
   fill, `softCharcoal` text, `hairline` bottom border. It tells the truth about
   a state the user can no longer see, which is the whole reason it exists.
4. Ending the call from there uses the existing hang-up path, reached by
   returning. **Do not add a second end-call control to the safety screen** —
   `safety_resources_screen.dart` is the destination and must not grow call
   semantics.
5. **No entitlement check anywhere on this path.** D7, and this is the same
   route the money-path acceptance criteria 4.1–4.7 already cover; re-run them
   after this change per coverage-spec §7.4.

## 2.5 Accessibility

- `Semantics(button: true, label: 'Support', hint: 'Opens support resources. Your call stays connected.')`
  — the hint answers the question that would otherwise stop someone from tapping
  it, and it is the one place in the app where the hint is load-bearing rather
  than decorative.
- **First in traversal order on this screen**, before the self-view and before
  the call controls. A screen-reader user should reach it without swiping past a
  hang-up button.
- 48×48 minimum target.
- Never announced, never focus-stolen, never a live region. It is always there
  and it never changes, so it has nothing to announce.

## 2.6 If joint video stays frozen

Per the coverage spec, joint video is Tier 3 frozen and the ruling is *"if it
stays frozen through P0, defer this and note it, but do not silently skip it."*

If it is deferred, it must be recorded in `SUPPORT_ICON_EXEMPT` with the reason
`# frozen feature, control designed in docs/design/safety-surfaces.md §2, not built`
— so the static test in coverage-spec §6 keeps failing in the useful direction
the moment the screen is unfrozen. An exemption with a design already written
against it is a scheduled task. An exemption with a blank reason is a hole.

## 2.7 Acceptance criteria

| # | Criterion |
|---|---|
| V1 | The support pill is visible from the first frame of the call and never fades, dims, or auto-hides — including while the call controls do. |
| V2 | It is visually distinct from the call controls in position, shape and colour, and contains no red. |
| V3 | Tapping it changes no call state: mic, camera, connection and partner notification are all unchanged. Asserted, not eyeballed. |
| V4 | The "Your call is still connected" bar renders on `/safety` when arrived at from a call, and not otherwise. |
| V5 | It reaches `/safety` with no entitlement check on the path. |
| V6 | White-on-scrim measures ≥4.5:1 against a full-white video frame. |
| V7 | It is the first focusable element in the screen's semantics traversal order. |
| V8 | It never appears, changes, or animates in response to call content. |
