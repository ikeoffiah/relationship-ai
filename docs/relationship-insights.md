# Relationship insights

A spec, not an implementation report. The feature is unbuilt; what exists is a
model, a migration, an unattached manager, and a job that could never run.

Written before building because the central question is not technical.

---

## 1. What it is for

Each partner talks to Bliss privately. Nobody else reads those sessions — not
the partner, and until now not the product either.

The idea is that a system holding both sides can see things neither partner can
see alone, in the way a couples therapist who has been seeing each of you
separately can. Five detectors were named:

| type | what it notices |
|---|---|
| `perception_gap` | the two of you remember the same event differently |
| `recurring_theme` | the same argument returning in different clothes |
| `needs_gap` | one partner naming a need the other never registers |
| `progress` | something that used to hurt and has stopped |
| `flourishing_pattern` | what is working, so it can be protected |

The therapist analogy is the reason this is worth building and the reason it is
dangerous. A therapist holds each partner's confidence and *chooses what to
name in the room*. That choosing is the whole skill, and it is the part the
current design leaves to a boolean.

## 2. What exists

Nothing that runs.

- `RelationshipInsight` — real schema, migrated, **0 rows ever**.
- `InsightQuerySet` with consent filters — **never attached to the model**, so
  `RelationshipInsight.objects.public(user)` raises `AttributeError`.
- `insight_synthesis_job` — imported `apps.insights.jobs.*` and
  `apps.core.vector`, neither of which has ever existed. It is not a task, and
  taking down Celery during autodiscovery was its only effect on the product.
- No views, no urls, no serializers, no caller, not in beat.
- Mobile has an "Insight detected" notification toggle for a notification that
  cannot fire, and one invite-screen sentence about "shared insights".

## 3. The rule everything else follows from

The existing design has three consent booleans and one queryset. That queryset
says:

> `for_joint_prompt()` — "No per-user consent check is required because the
> joint session is a shared context."

This conflates the **session** being shared with the **evidence** being shared.
It would place an insight derived from one partner's private solo session into
a prompt both partners see, with no check, by design. It is unreachable today
only because the manager was never attached.

`boundary.py` already states the principle this violates:

> an inferred model of one partner, surfaced to the other, is a manipulation
> manual. In the minority of couples with a controlling dynamic it is a weapon.
> In a separation it is discoverable.

So the rule, and it is not negotiable by a flag:

> **Nothing derived from one partner's private sessions may reach the other
> partner in a form that reveals what they said, felt, or were assessed as.**

That does not kill the feature. It reshapes it.

## 4. What survives the rule: shape, not content

The insight worth surfacing is usually the *shape* of a gap, which is symmetric
and reveals nothing:

- ✅ "You two are remembering last weekend differently. Worth comparing notes?"
- ❌ "Grace felt dismissed when you cancelled on Saturday."

The first is true of both partners, discloses no content, and is *the actually
useful thing* — it is the opening a couple cannot find on their own. The second
is Grace's private session read aloud.

So each insight splits in three:

```
shape        symmetric, contentless, safe for both. The only thing that
             crosses by default.
mine         what this means for me, built from my sessions, shown only to me.
             This is where the value is for the individual.
synthesis    the therapist's version, naming both sides. Requires *both*
             partners to opt in, per insight, after seeing what it says.
```

`a_narrative_summary` and `b_narrative_summary` become strictly self-facing.
`synthesis` becomes double-gated. `shared_with_a`/`shared_with_b` stop meaning
"an admin flipped this" and start meaning "this partner consented to their own
side being named".

## 5. Consent, concretely

- Insights are computed **unshared**. Default is nothing crosses.
- The `shape` may be shown to both without consent, because it contains
  nothing about either of them beyond the fact of a difference.
- `synthesis` requires the subject of each half to approve their own half —
  shown to them first, verbatim, with a decline that costs nothing and is not
  reported to the partner.
- `approved_for_joint` is derived, never set directly: it is true only when
  both partners have approved and neither has since withdrawn.
- Withdrawal is retroactive: it removes the insight from future joint prompts
  and deletes the synthesis text.

**Attach the manager**, and make `public()` the only read path. An unattached
consent filter is worse than none, because the next person assumes it enforces
something.

## 6. Confidence, and what to do with a weak one

`confidence` exists on the model with no stated meaning. It needs one, because
an insight is a claim about somebody's relationship:

- Below a floor, an insight is stored but never surfaced in any form. It is
  evidence for the next run, not a finding.
- The `shape` needs less confidence than the `synthesis`, because it claims
  less.
- Confidence must come from *evidence count and agreement across sessions*, not
  from the model's self-report. A model asked how sure it is will say "0.85".

**Measured, and worse than the spec assumed.** Three genuinely unrelated
arguments — a back door left unlocked, a brother who was rude at lunch, an
untaxed car — produced "responsibility for shared tasks" at **0.8**, against
**0.9** for a real theme. So the self-report does not merely skew high; it
barely separates a finding from an invention, and no floor placed between 0.8
and 0.9 would be anything but luck. The prompt already forbade this in as many
words and the words did not bind.

What works is asking a question whose answer can be checked. The detector must
name *which* arguments the subject appears in, by number, and fewer than three
citations is not a theme. On the same noise case the model still proposes the
same vacuous subject and can only cite two of the three, so it is dropped. This
is the pattern to reach for whenever a model's own certainty is the only thing
standing between a couple and a claim about their relationship: replace "how
sure are you" with "show me what you are looking at".

## 7. Safety

- **The rough-patch rule, as with the daily question.** An insight naming a
  recurring conflict theme, delivered the morning after a fight, is a
  prosecution. Hold surfacing while `is_rupture` sees an open rupture.
- **Abuse signals stop anything *crossing*, for ninety days, resetting on every
  new signal.** A perception-gap insight in a coercive relationship is a tool
  for the controlling partner — it tells them what their partner said
  privately, which is exactly what they are trying to find out. Consent does
  not help, because consent under coercion is not consent.

  Three details, each of which was got wrong in an earlier draft:

  **The self-facing half stays on.** The first version disabled the feature
  entirely, which punishes the person it is trying to protect: "what this means
  for me", built from my own sessions and shown only to me, reveals nothing to
  a partner and is arguably worth *more* to somebody in that situation than to
  anybody else. Only `shape` and `synthesis` are held.

  **Ninety days, not for ever.** Permanence was out of character for a product
  where behaviour halves every three weeks and policy suppression decays back
  in about ninety days. It also meant one hit on a keyword list — the same
  class of detector this codebase has twice found close to inverted —
  permanently removed a feature with no route back and no explanation.

  **Elapsed time only. Never a behavioural condition.** The obvious refinement
  is to re-enable on evidence of significant repair, and it is a trap. Repair
  signals — stickers, gratitude, warm re-engagement — are all things the
  controlling partner can perform and can pressure the other into performing,
  so "demonstrate repair to restore access" is a set of instructions for
  looking repaired, handed to the person we are protecting against. Any gate
  whose input can be produced under pressure by the party with more power is
  not a gate. A behavioural condition would also make the safety response
  legible — a couple could work out that the feature vanished because of
  something one of them said, and telling an abuser the system noticed is its
  own harm. Nobody can perform elapsed time. Repair may never shorten the
  clock; a new signal restarts it, which is what distinguishes one bad night
  nine months ago from something still happening.

  **A signal retracts, it does not only block.** Found by writing S22 rather
  than by thinking about it, which is the argument for writing S22. The gate
  was implemented in the nightly task alone, so a signal stopped the *next*
  insight while one written the previous week went on crossing for the rest of
  its thirty-day life. "Nothing crosses" has to mean the rows already written,
  so a signal now unshares them — from the sweep, and immediately from the
  read-coach referral, because a night is a long time to leave "here is the
  pattern in your arguments" on the screen of a couple who just tripped this.
  The read path deliberately does *not* check: it would mean a ninety-day
  message scan on every home screen load, and the retraction already leaves the
  stored rows in the correct state.

  Note the asymmetry with the rough-patch rule above. An open rupture only
  *waits* — a theme they were already shown is not made harmful by this week's
  argument, and pulling it off the screen would itself be a message. A signal
  retracts. The two rules look alike and are not.
- **Nothing derived from `behaviour.py`.** Tendencies are the system's opinion,
  not events. They already have a boundary and it is not this one.
- Moderation on every generated narrative before storage, as with media.

## 8. What I would build first

Not the detectors. In order:

1. ~~**The safety work now**: delete `tasks.py`, attach the manager, remove
   `for_joint_prompt`, keep the model.~~ **Done.** Seven tests cover the read
   path, where there were none.
2. **`perception_gap`, shape-only.** "You two are remembering last weekend
   differently. Worth comparing notes?" — no content from either side, so it
   needs no consent flow and discloses nothing.
3. **The consent flow**, before anything reads private sessions at all.
4. **The remaining detectors**, one at a time, each with a written argument for
   why its output may cross.

An earlier draft put `perception_gap` **last**, on the grounds that it is the
only one that cannot exist without reading both private sides. That sequenced
by risk and ignored value: it is also the headline, the reason the feature
exists, and building it last means possibly spending the whole budget on four
detectors nobody asked for and never learning whether the core idea works. It
would also have meant designing the consent flow around the easy cases and then
discovering it does not fit the one it exists for.

Shape-only resolves it. The headline gets validated first and cheaply, and the
consent machinery is deferred until there is evidence it is worth building —
which is the same argument that stopped the daily question being generated.

## 9. Testing

Built, and all of it passing.

- **Unit** — 31 tests in `apps/insights/tests.py`: `public()` returns nothing
  without consent; one partner's consent does not reveal it to the other;
  below-floor confidence never surfaces; a theme the model cannot cite is
  dropped; a signal retracts what was already stored while an open rupture does
  not; the abuse check fails *closed*.
- **Scenario S21** — a real theme, produced from a real thread by a real model
  call, reaching both partners as the same insight in words that quote neither
  of them. The leak sweep runs on both sides. Rather than extending the sweep
  only here, `/api/v1/insights/` was added to `passive_surfaces` in the runner,
  so **every** scenario now sweeps it — insights are the newest thing that
  crosses between two people and therefore the likeliest place for a leak.
- **Scenario S22** — an insight, then an abuse signal, then nothing crossing to
  either partner; their own thread, behaviour and score still answering 200;
  five repair stickers not buying it back; and the stored row retracted rather
  than quietly rewritten.

Still owed: the simulation should report insights alongside tendencies, so what
the system believes about a couple is readable in one place.

## 10. What I would not build

The vector pipeline (`apps.core.vector`, `update_relationship_vectors`). It
appears in the job with no stated purpose, pgvector is in the stack but unused
by any model, and "embed the relationship" is a solution looking for a
question. If retrieval is needed later, it can be added when there is something
to retrieve.
