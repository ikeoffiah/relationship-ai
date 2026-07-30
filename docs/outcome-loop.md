# The outcome loop

How the app gets better at helping a specific couple, without getting more
confident about who they are.

Status: proposed. First slice of the larger personalisation work; deliberately
scoped so it produces value before any of the modelling behind it is built.

---

## 1. What this is instead of

The obvious way to make a relationship app "learn" is to infer more: feed
everything a couple does into a model and let it build a picture of each
person. That makes the system more *confident*, not more correct, and it fails
in three specific ways:

- **Confirmation drift.** Once it decides someone is avoidant, every silence
  confirms it. There is no path for counter-evidence.
- **Inference on inference.** Derived traits become inputs to further
  derivation, and the error compounds with no ground truth to arrest it.
- **Self-fulfilling labels.** Telling someone they are anxiously attached
  changes how they behave, and then the change is read as confirmation.

So this learns something else. **The unit of learning is the
intervention → outcome pair, not the personality trait.** Not "who is this
person", but "does this kind of help, in this kind of moment, work for these
two". That is supervised, per-couple, measurable, and cannot drift into a
diagnosis because it never makes one.

`apps/personalization/behaviour.py` already holds the line on the trait side —
tendencies not diagnoses, decay, never overriding self-report, never shown to
the partner. Nothing here changes that. This adds the loop it has been missing:
a way to find out whether any of it is helping.

---

## 2. The boundary, promoted from convention to invariant

`behaviour.py` rule 4 says a person's profile is never shown to their partner.
That is the single most important property in this whole system and it is
currently a convention held up by careful authors.

**Make it a function.** `apps/personalization/boundary.py`, one entry point,
and every path that carries anything derived from A toward B goes through it.

```python
def phrasing_guidance_for(recipient_id) -> list[str]:
    """Style directives for text being written *to* `recipient`.

    The only thing permitted to cross between partners. Returns instructions
    about tone — "lead with reassurance", "keep it short and concrete" — and
    never a signal name, a score, an observation, or anything that could be
    read back as a claim about the person.
    """
```

Two rules, tested the way an auth boundary is tested:

- Anything returned by this function may only be injected into a prompt whose
  output goes **to the person it describes**. It may never be returned to their
  partner as content.
- Nothing else about a person crosses. No trait, no score, no tendency, no
  observation, in any form, ever.

The test that matters is adversarial: assert that no `behaviour.SIGNALS` name,
no numeric score, and no phrase from `SELF_DESCRIPTION` appears in any response
body reachable by the other partner. That test is the product promise.

Why this is worth being absolute about: an inferred model of one partner,
surfaced to the other, is a manipulation manual. In the minority of couples
with a controlling dynamic it is a weapon, and in a separation it is
discoverable. There is no version of the feature that is worth that.

---

## 3. What counts as an intervention

Anything the system does that is meant to change what happens next:

| kind | fired from | already exists |
|---|---|---|
| `caution` | `assist.check_before_send` returning caution | yes |
| `rephrase` | a suggestion offered and shown | yes |
| `nudge_repair` / `nudge_night` / `nudge_opportunity` | `assist.nudge_for` | yes |
| `read_coach` | `assist.coach_response` | yes |
| `daily_question` | engagement question selection | yes |
| `game` | game pack selection | yes |

Every one of these is already computed. This adds a row when it fires, and a
row when the person responds to it. No new model calls, no added latency — the
same constraint `behaviour.py` set for itself, and for the same reason: a
learning layer that made every send slower or dearer would be paid for by the
couple in the one place they notice.

---

## 4. What counts as an outcome, and the honest problem with that

Two tiers, and they are not equally trustworthy.

**Immediate** (seconds to minutes) — attributable, because the person is
responding to the thing itself:

- caution → sent anyway / sent the suggestion / edited / abandoned
- rephrase → accepted / ignored
- nudge → acted / dismissed (already recorded on `AssistNudge`)
- question → answered / skipped

**Downstream** (hours to days) — valuable but *not attributable*:

- did the exchange de-escalate rather than continue sharply
- was there a repair attempt within 24h
- did either partner's `RelationshipCheckIn.connection_score` move

The problem is the counterfactual. If a couple's connection score rises the day
after a repair nudge, that is not evidence the nudge did it. Couples have good
days. Pretending otherwise is how a system convinces itself it is working.

Two mitigations, and the second one has an ethical edge worth naming:

1. **Weight immediate signals heavily and downstream ones as a slow prior.**
   Immediate outcomes decide policy; downstream ones only nudge it.
2. **Hold-outs, but narrowly.** Occasionally withhold a *marginal, low-stakes*
   intervention and compare. Never a safety escalation, never a repair nudge to
   a couple in visible distress. Withholding help to improve a metric is a
   thing this product does not get to do, so the hold-out set is restricted to
   interventions the system was ambivalent about anyway.

---

## 5. Schema

Three tables. All per-couple; none stores message content.

### `InterventionEvent`

```python
id            = UUIDField(pk)
relationship  = FK(Relationship)
user          = FK(User)            # the recipient
kind          = CharField(choices)  # the table in §3
context       = JSONField()         # see below — a fingerprint, not a message
offered_at    = DateTimeField()
response      = CharField(blank)    # accepted | modified | declined | ignored
responded_at  = DateTimeField(null)
held_out      = BooleanField(default=False)
```

`context` is the part to get right. It is a **fingerprint of the situation**,
never the situation itself:

```json
{"hour": 23, "tendencies": ["withdraws_after_conflict"],
 "sharp_recently": true, "days_since_conflict": 1, "thread_active": true}
```

No message text, no draft, no transcript. This table must never become a log of
what two people said to each other — that is a much larger promise than the
feature is worth, and it is the same reasoning that made `BehaviourProfile` one
row per person rather than a table of observations.

### `InterventionOutcome`

One optional row per event, written by a batch job from data already recorded:

```python
event            = OneToOneField(InterventionEvent)
de_escalated     = BooleanField(null)
repair_within_24h = BooleanField(null)
check_in_delta   = FloatField(null)
computed_at      = DateTimeField()
```

### `CouplePolicy`

What has been learned. One row per relationship, same shape and same discipline
as `BehaviourProfile`: a JSON blob of running scores, decayed on read and
write, never a log.

```python
relationship = OneToOneField(Relationship)
weights      = JSONField(default=dict)   # "nudge_night@hour=23": {score, count, updated_at}
updated_at   = DateTimeField(auto_now=True)
```

Decay matters here for the same reason it does for tendencies: a couple who
ignored every nudge during a hard fortnight should not be written off for good.
Reuse `behaviour.HALF_LIFE_DAYS` rather than inventing a second constant.

---

## 6. What actually changes because of it

A loop that learns and changes nothing is a telemetry pipeline. Three concrete
behaviours, in order of value:

**Suppression.** If this couple has dismissed the night nudge at 11pm four
times running, stop firing it at 11pm. This alone probably justifies the build:
an unwanted nudge is worse than no nudge, because it teaches people to ignore
the thing that will one day matter.

**Calibration.** If someone accepts almost every rephrase, offer more freely.
If they send anyway every time, raise the threshold — a caution that is always
overridden is not a caution, it is friction with a moral tone.

**Selection.** Prefer questions and games whose *kind* has landed before, among
those that would most reduce what the system does not yet know. That is active
learning, and it compounds honestly: every answer reduces uncertainty, which
changes the next question.

Each of these reads `CouplePolicy` and nothing else. If the policy is empty —
a new couple — everything falls back to today's behaviour exactly.

---

## 7. Known limits, stated rather than designed around

- **Cold start.** Per-couple learning has nothing to go on for a new couple.
  Deliberate: they get the current, sensible defaults. Pooling priors across
  couples would fix it and is the obvious step two, but it needs an aggregation
  story that cannot leak one couple's patterns into another's experience, and
  that is a bigger piece of work than this.
- **No causality.** §4. The system will know what correlates with acceptance,
  which is genuinely useful and is not the same as knowing what helps.
- **Response is not benefit.** A nudge someone acts on is not necessarily a
  nudge that helped them. Optimising purely for acceptance would drift toward
  telling people what they want to hear, which for this product is a failure
  mode rather than a win. The downstream tier exists as a slow counterweight,
  which is exactly why it is kept even though it is not attributable.

---

## 8. Deletion and retention

- Intervention events reference no message content, so a deleted message leaves
  nothing orphaned. But they die with the relationship and with account
  erasure, through the same path the media work uses.
- `context` fingerprints must not be reversible into content. No free text.
- `CouplePolicy` decays on its own; nothing here needs a sweep.

---

## 9. Sequencing

1. **`boundary.py` and its adversarial test.** First, before anything writes a
   row. The invariant is easier to hold from the start than to retrofit.
2. **`InterventionEvent` and the write hooks.** Nudges first — the feedback
   endpoint already exists and only needs to write a second row. Then caution
   and rephrase, which need the client to report which branch of the caution
   sheet was taken.
3. **`CouplePolicy` and suppression.** The smallest useful behaviour change.
4. **Outcomes and calibration.** Once there is enough data to be worth reading.
5. **Selection.** Last, because it is the one that benefits from everything
   else already being in place.

Steps 1–3 are a week or so and produce a real improvement — no more nudges at
an hour this couple has repeatedly told you they do not want them. Everything
after that is worth deciding on the evidence steps 1–3 produce, rather than
now.
