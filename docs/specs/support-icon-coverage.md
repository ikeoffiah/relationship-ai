# Support icon coverage — the fix list

Owner: product/design (`local_81faf803`). Execution-plan **D3.17**, inside P0.10.
Engineering-blocking. Built by: engineer.

Makes true a claim that is currently false in two places of live copy —
*"support resources are one tap from every screen"* (`marketing-copy.md` §1
description and §7 landing page). See `capability-claims-audit.md` §1.3.

It is also the cheapest safety improvement available in the product: one line per
app bar.

---

## 1. Current state — verified, and one trap in the raw data

**14 of 53 screens are covered.** 11 carry `SupportAction` directly; the three
hub tabs inherit it from `HubScaffold`.

> **Trap for whoever automates this:** `talk_screen.dart`, `us_screen.dart` and
> `you_screen.dart` do **not** contain the string `SupportAction` and are
> nonetheless covered — `HubScaffold` supplies their app bar. A naive grep marks
> them missing. Likewise `main_navigation_screen.dart` is a container: its
> children own their app bars, and it needs no icon of its own.

---

## 2. Group A — app bar already has `actions:`

Append `const SupportAction()` to the existing list. Seven files.

| File | Note |
|---|---|
| `onboarding/onboarding_flow_screen.dart` | **Do this one first.** See §5. |
| `engagement/views/shared_goals_screen.dart` | |
| `games/views/games_list_screen.dart` | Sits beside the spicy-games action |
| `relationship/dissolve_relationship_screen.dart` | |
| `relationship/our_story_screen.dart` | |
| `settings/profile_edit_screen.dart` | |
| `auth/views/age_verification_screen.dart` | |

## 3. Group B — app bar present, no `actions:`

Add `actions: const [SupportAction()]`. Eighteen files.

**Product surfaces (P0):**

| File |
|---|
| `engagement/views/daily_ritual_screen.dart` |
| `faith/views/faith_screen.dart` |
| `focus/views/focus_screen.dart` |
| `commitments/views/commitments_screen.dart` |
| `two_truths/views/two_truths_screen.dart` |
| `games/views/game_play_screen.dart` |
| `bliss/views/bliss_plan_screen.dart` |
| `relay/relay_compose_screen.dart` |
| `relay/relay_inbox_screen.dart` |
| `relationship/invite_partner_screen.dart` |
| `onboarding/screens/relationship_portrait_screen.dart` |
| `sessions/joint_session_entry_screen.dart` |

**Admin and auth surfaces (P1):**

| File |
|---|
| `settings/change_password_screen.dart` |
| `settings/email_change_screen.dart` |
| `settings/legal_document_screen.dart` |
| `auth/views/email_verification_screen.dart` |
| `auth/views/forgot_password_screen.dart` |
| `auth/views/new_password_screen.dart` |

## 4. Group C — no app bar. Needs a decision, not a one-liner.

| File | Ruling |
|---|---|
| `sessions/joint_video_call_screen.dart` | **Needs real design.** A live joint session is precisely where an exchange can escalate, and there is no app bar to hang an icon on. Add a small persistent overlay control in a corner, consistent with the call's other controls. **The only non-trivial item in this document.** Joint video is Tier 3 frozen (`feature-kill-list.md`) — if it stays frozen through P0, defer this and note it, but do not silently skip it. |
| `onboarding/screens/onboarding_complete_screen.dart` | Add a minimal `AppBar` carrying only `SupportAction`. It is the end of the 40-tap stretch and it currently has no chrome at all. |
| `relationship/accept_invite_screen.dart` | Same treatment. This is partner B's first screen. |
| `auth/views/login_screen.dart`, `signup_screen.dart`, `welcome_screen.dart` | P1. Add a minimal app bar or a footer text link. Lower priority — a person in crisis is not typically sitting at a signup form — but they are cheap and they make the claim literally true. |
| `home/views/main_navigation_screen.dart` | **No change.** Container; children own their app bars. |
| `hubs/talk_screen.dart`, `us_screen.dart`, `you_screen.dart` | **No change.** Covered by `HubScaffold`. |
| `onboarding/screens/{rsq,relationship_context,cultural_context,communication_quiz}_screen.dart` | **No change.** Covered by §5. |
| `auth/views/splash_screen.dart`, `auth_landing_screen.dart` | **Deliberate exception.** Transient, sub-two-second, no interaction. |
| `safety/safety_resources_screen.dart` | **Deliberate exception.** It is the destination. |

---

## 5. The single most valuable line in this document

`onboarding/onboarding_flow_screen.dart` already renders the app bar for **all
four questionnaire steps** — `RsqScreen`, `RelationshipContextScreen`,
`CulturalContextScreen` and `CommunicationQuizScreen` are `PageView` children
under its `Scaffold`, and their own `Scaffold`s carry no `appBar`.

So **one line covers the entire questionnaire.**

That stretch is 40+ taps, the longest continuous span anyone spends in this app,
and the RSQ items being answered include:

> *"I worry about being abandoned."* (23)
> *"I often worry that romantic partners won't want to stay with me."* (21)
> *"I worry about being alone."* (9)
> *"I worry about having others not accept me."* (28)

Thirty items in that register, with no visible route to help anywhere on screen.
Whatever the marketing copy says, that is the gap worth closing first, and it is
one line.

---

## 6. Keeping it true

A coverage fix that is not enforced regresses the first time someone adds a
screen. Same construction as the entitlement allowlist
(`money-path-acceptance.md` §3.3.1) and the boundary import test.

**Static test:** every file under `features/**` declaring a `Scaffold` with an
`appBar:` must reference `SupportAction`, except an explicit allowlist:

```
SUPPORT_ICON_EXEMPT = {
    "features/safety/safety_resources_screen.dart",   # is the destination
    "features/auth/views/splash_screen.dart",         # transient
    "features/auth/views/auth_landing_screen.dart",   # transient
}
```

Fails in both directions: an unlisted screen without the icon fails, and an
exemption for a screen that no longer needs one fails. Adding a screen without
support becomes a visible decision in a diff rather than an omission.

**Also add** (`marketing-copy.md` is marketing's file, so this is a request, not
an edit): once §2–§4 land, §1 and §7 copy becomes true as written and needs no
softening. Until then it is false and should not go live — the audit's suggested
interim wording is *"support resources are always reachable."*

---

## 7. Acceptance criteria

| # | Criterion |
|---|---|
| 7.1 | Every screen in Groups A and B renders `SupportAction` in its app bar. |
| 7.2 | Every Group C screen is either fixed or listed in `SUPPORT_ICON_EXEMPT` with a reason. |
| 7.3 | The static test in §6 passes and fails in both directions. |
| 7.4 | `SupportAction` reaches `/safety` from every screen with **no entitlement check on the path** — this intersects D7 and money-path criteria 4.1–4.7. Re-run those after this change. |
| 7.5 | Tapping support from the middle of onboarding and returning does not lose questionnaire answers. Intersects D3.1 (onboarding persistence) — **if persistence is not yet shipped, this route currently discards forty answers.** |
| 7.6 | The icon renders correctly against every app bar background in the fix list, including transparent ones. |

**7.5 is the one to watch.** Adding a support route into onboarding before
answers persist creates a new way to lose them — someone in distress taps for
help, comes back, and their work is gone. **Ship D3.1 first, or ship both
together.** Do not ship this one alone.
