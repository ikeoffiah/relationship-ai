# The 21 feature areas, ranked

Owner: product/design (`local_81faf803`). Execution-plan follow-on to **D8**.

Not a deletion order. This is the answer to *"what are we deliberately not
finishing during the freeze"*, so that the freeze is a decision rather than a
backlog nobody looks at.

---

## 0. First, a warning about the evidence

I pulled row counts for every model in the database intending to rank on usage.
**Do not use them, and do not let anyone else.**

```
users: 1313
domains: [('test.local', 1301), ('example.com', 6), ('t.local', 4),
          ('bliss.local', 1), ('gmail.com', 1)]
```

**1301 of 1313 accounts are synthetic** — e2e fixtures and the scenario-testing
harness. There is exactly one real account. `Relationship: 649` and
`CoupleMessage: 6947` are simulation output, not behaviour.

So this ranking is built on **strategic dependency, not evidence**, and it is
labelled as such throughout. Execution-plan §1 already says downloads are 0;
this is the same fact from the other end. Nothing here should be treated as
"users don't want X" — nobody has had the chance to want anything yet.

**One thing the counts do legitimately show:** which features have never been
exercised *even by a comprehensive simulation harness*. That is weak evidence
about reachability and completeness, not about demand, and it is used only that
way below.

**When this document should be rewritten:** after the first two cohorts, on real
data. That is the first moment any of this is answerable.

---

## 1. The ranking criteria

In priority order:

1. **Does the $39 SKU depend on it?** — the only thing generating revenue.
2. **Is it legally or ethically load-bearing?** — safety, consent, auth. Never
   cut, never "finished later", regardless of use.
3. **Does the afterlife depend on it?** — the daily loop is what produces the
   facilitator's testimonial, which sells the next cohort (see the pricing
   discussion: report carries the purchase, curriculum carries the eight weeks,
   daily loop carries the afterlife).
4. **What does carrying it cost?** — surface area, dependencies, QA, support,
   and the review risk it adds to a store listing.
5. **Does something else already do its job better?** — the strongest kill
   signal available without usage data.

---

## 2. Tier 0 — Load-bearing. Not touchable.

| Area | Why |
|---|---|
| `auth` | Everything. |
| `consent` | Legal, and the credibility surface a facilitator reads. |
| `safety` | D7. Never gated, never deferred, never cut. |
| `onboarding` | **This is the product we sell.** The $39 buys the assessment; onboarding *is* the assessment. It has the most P0 work of anything in the app (D3.1 persistence, P0.1 scorer, P1 item cut). |
| `home` / `hubs` | The shell. |
| `relationship` | Pairing. Without it there is no couple, no report, no revenue. |
| `settings` | Account, security, and the notification controls that P2 owes. |

## 3. Tier 1 — Sells the $39. Finish these.

| Area | Why | State |
|---|---|---|
| `engagement` | Holds the daily question, check-in, micro-actions, gratitude — and it is the spine the eight-session curriculum will be sequenced over. The single most load-bearing feature area after onboarding. | 121 questions, no delivery trigger |
| `notifications` | Under a one-off, a couple who goes quiet in week two is a facilitator with no story. The daily-question beat job lives here, and it is the mechanism that sells cohort 31. | 19 types, 4 user controls, no daily trigger |

## 4. Tier 2 — The afterlife. Keep, don't expand.

| Area | Why | Note |
|---|---|---|
| `couple_chat` | The surface a couple opens daily, and where the tone coach lives. The most complete feature in the app. | Finished. Leave it alone. |
| `chat` (AI sessions) | The differentiator versus Prepare/Enrich — "an app you keep" only means something if the app does something a workbook can't. | Needs the P0.10 credibility pass: four chrome bars, blank first-run, the "Validation" chip |
| `games` | Real content (9 packs, 61 questions), genuinely two-sided, and natural curriculum material. | Fine as is |
| `bliss` (calendar / @bliss) | Quietly the most strategically valuable thing in Tier 2: **it is the only scheduled-delivery mechanism in the product.** Given that the core loop has no trigger, the reminder infrastructure here is worth more than the calendar UI it was built for. | Beat jobs work |

## 5. Tier 3 — Freeze. Do not finish during P0–P2.

Ordered by how confident I am that not finishing them costs nothing.

| Area | Reasoning |
|---|---|
| `sessions` (joint video / LiveKit) | **Highest carrying cost in the app, lowest evidence of need.** Pulls `livekit_client` + `flutter_webrtc` — both flagged in every build as lacking Swift Package Manager support — plus LiveKit keys and per-minute infrastructure cost. Never exercised even by the harness. A premarital couple sitting in the same room does not need a video bridge. If anything is cut outright after the freeze, this is first. |
| `relay` ("Say it better") | **Something else already does its job better.** The tone coach in `couple_chat` rewrites a message inline, in the thread, at the moment of sending. `relay` is a separate screen, a separate inbox, a separate mental model, for the same intent — and it is the one surface whose internal name leaked into the UI. Zero rows even in simulation. Strongest *conceptual* kill candidate in the product: not a bad feature, a second, worse copy of one we already have. |
| `two_truths` | Overlaps `games` almost entirely and sits alone as a feature area for one mechanic. Fold into `games` after the freeze rather than maintaining separately. |
| `focus` | Requires both partners present and coordinating in real time — the hardest coordination in the product, for the smallest payoff. Untouched even in simulation. |
| `history` | **Currently a promise the app does not keep** — see §7. Either fix it in P0.10 or remove the entry from the You tab. What it must not do is keep offering "everything you have talked through before" over an empty table. |
| `commitments` | The *concept* is strong premarital material ("little promises") and should be curriculum content. The standalone feature area should not be finished. |

## 6. Tier 3, with a deliberate exception — `faith`

`faith` has zero rows in every table, including in simulation. On the mechanical
criteria it belongs at the bottom of Tier 3.

**Keep it, and do not cut it.**

*Re-read against D3.0 (global SaaS, not Nigeria-targeted) on 2026-08-03. The
protection stands, and the global case is stronger than the one I originally
wrote.*

The go-to-market channel is churches and premarital programmes. **Faith-based
premarital preparation is the dominant global form of premarital counselling**,
not a regional variant — Catholic Pre-Cana, Anglican marriage preparation, US
evangelical premarital counselling, and their equivalents across Africa, Latin
America and the Philippines. Prepare/Enrich's faith-based edition is a large
part of why it owns this channel.

A faith tab is therefore not a peripheral feature here. It is the single
strongest signal to a facilitator that this product was built for their couples
rather than retrofitted at them. Under D3.0 that argument **widens** — the
addressable set of faith-based programmes globally is far larger than the
Nigerian subset I originally cited.

This is the one place where "no evidence of use" and "strategic value" point in
opposite directions, and strategy wins **because there is no real usage evidence
either way**. Cutting it would be reading synthetic zeros as demand signal.

It stays frozen — no new work — but it is not a kill candidate, and it should be
visible in the facilitator pitch.

## 7. Not a feature area, but on this list

**Session history is silently non-functional.** `sessions.Session`
(`langgraph_sessions`) has **0 rows**, including after I ran a real AI session
against the local stack this afternoon. The writer is `persist_turn()` in
`chat_router.py`, and its exception handler is:

```python
except Exception:
    # History is a convenience; never let it interrupt counseling.
    return
```

Failing open is the right instinct for the send path. The consequence is that
this feature can be completely broken and *nothing anywhere reports it*.

That makes `product-assessment.md` §2.11 worse than a copy contradiction. It is
not just that the consent sheet says sessions are deleted while the You tab
promises "everything you have talked through before" — it is that the second
screen is currently offering a feature that stores nothing, and is built so the
failure is invisible.

**For P0.10:** decide which promise is true, make both screens say it, and give
`persist_turn` a log line and a metric so a silent failure stops being silent.

### 7.1 The therapist portal — frozen, and the reason matters

*Updated 2026-08-03 for D3.35: v1 ships with no humans in the loop — no
clinicians, no coaches, no therapist supply.*

`product-assessment.md` §2.7 asked whether the therapist portal was a real
B2B2C wedge or dead code. **The answer is neither, for v1.** It is built, it is
inert, and it stays inert deliberately. Recording that as answered rather than
leaving it open.

**Frozen, not cut — and not because it might be a wedge later.** That was the
old justification and it was weak, because "we might want it" keeps everything.
The durable reason is that **removal touches consent**:

```
apps/consent/  → models.py · constants.py · access_policy.py · gate.py · serializers.py
apps/safety/   → models.py · admin.py
+ two consent migrations
```

`access_policy.py` and `gate.py` are the enforcement layer. Deleting ~425 lines
of `apps/therapist` means surgery on the most sensitive code in the product — in
the exact area where a consent control was found that is read by nothing
(`session-retention-wording.md` §1.1). Freezing costs nothing. Deleting costs
risky work in the consent layer with no revenue attached to it.

**This is a better class of reason to keep something**, and worth generalising:
"might be useful" keeps everything forever; "removal is riskier than retention,
here is the coupling" is checkable and expires when the coupling does.

### 7.2 But the *surface* should go, and it is separable

The backend freeze does not require showing it to users. Two live surfaces
reference a therapist nobody can have:

- `consent_dashboard_screen.dart:197` — a **"Therapist access"** row, rendered
  unconditionally, reading *"Your therapist cannot see your sessions."*
- The in-session consent sheet — the same row, on the sheet that blocks every
  session. Observed on device, 2026-08-03.

The sentence is not false — there is no therapist, so no therapist can see
anything. But it is a **control implying a capability that does not exist in
v1**, which is the D3.16 shape appearing in the product rather than in copy. Two
concrete costs: a user reading "your therapist" may reasonably wonder whether we
have connected one, and a facilitator vetting us will ask about the clinician
network we do not have — on a sales call, about a screen we chose to show them.

**Recommendation: hide the row when the user has no therapist connection.**
Conditional rendering only; no model change, no migration, no consent surgery.
Line 70 of the same file already does exactly this for the "What your therapist
can see" section, so the pattern is there. **Freeze the backend as ruled, hide
the surface** — they are separable and only one of them is risky.

---

## 8. Summary

| Tier | Areas | Action |
|---|---|---|
| 0 — Load-bearing | auth, consent, safety, onboarding, home/hubs, relationship, settings | Never cut |
| 1 — Sells the $39 | engagement, notifications | Finish |
| 2 — The afterlife | couple_chat, chat, games, bliss | Keep, don't expand |
| 3 — Frozen | sessions/video, relay, two_truths, focus, history, commitments | Don't finish |
| 3ᵉ — Frozen, protected | faith | Don't finish, don't cut |

**Nothing is deleted today.** D8 freezes; this ranks the freeze.

**After the first two cohorts**, three decisions come up with real evidence:
fold `two_truths` into `games`; cut `relay` in favour of the tone coach; and cut
joint video unless a facilitator has actually asked for it. All three are
reversible-by-not-doing-them, which is why they can wait.

**One thing I would not wait on:** `history` is making a promise the product does
not keep, on a screen a facilitator will read while deciding whether to trust us
with their couples. That belongs in P0.10 with the rest of the credibility pass.
