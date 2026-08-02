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

### The residual inference, stated rather than left implicit

"Symmetric and reveals nothing" is very slightly too strong for
`perception_gap`, and it is better to write this down than to discover it in a
complaint. A partner who rated the fortnight a 5 every day, and is then told
the two of them have been seeing it differently, can conclude their partner
rated it lower. The shape does not say so; arithmetic does.

Three reasons this is accepted rather than designed away:

1. It is inherent to the concept. Any true statement that a gap exists is
   subtractable by someone who knows their own half. The only way to remove the
   inference entirely is not to have the feature.
2. What leaks is one bit — *lower* — not a number, not a note, not a day. The
   thing that would actually hurt, and that the detector refuses to emit, is
   the direction stated **as a finding** and the magnitude attached to it.
   "Your partner has been finding this much harder than you" is a different
   object from a couple working out that they disagree.
3. It only fires on a sustained, consistent gap — six-plus paired days, a full
   point apart, holding its direction. That is a fact about the relationship
   the couple would benefit from discussing, not a stray bad Tuesday.

What follows from accepting it: the wording must never *confirm* the inference.
That is why the phrase is fixed rather than generated, and why S23 asserts no
direction word and no digit survives into what crossed.

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
2. ~~**`perception_gap`, shape-only.**~~ **Done**, and not from the source this
   document assumed. See below.
3. **The consent flow**, before anything reads private *session text* at all.
   Still owed, and still the gate on `synthesis` and the narrative halves.
4. **The remaining detectors**, one at a time, each with a written argument for
   why its output may cross.

### Where `perception_gap` reads from, and the mistake that delayed it

It was deferred twice on the same reasoning: it needs both partners' private
accounts of the same event, and `counselor_sessions` **has never held a row**.
The table is still empty. The reasoning was wrong anyway, because it was a
claim about one table dressed up as a claim about the feature.

Two partners already give private accounts of the same period every day, in
`RelationshipCheckIn` — one row each, one 1–5 score each, keyed to the same day
by a unique constraint, so A and B align with no join ambiguity. That model's
own docstring had said so the whole time: *"The per-partner score series is the
raw material for the perception-gap insight."*

Reading check-ins instead of transcripts changes the detector's character
entirely, and for the better:

- **It is deterministic.** No model call, so there is no prompt to bind and
  nothing to invent — which matters given that the other detector had to be
  rebuilt around citations after it produced a confident theme for three
  unrelated arguments.
- **Confidence finally means what §6 asked for.** It is computed from paired-day
  count and how consistently the gap holds its direction, not from asking
  something how sure it feels.
- **It never decrypts anything.** The private `note` on a check-in is free text
  somebody wrote for themselves; only the integer column is read, and a test
  fails if `decrypt_field_value` is so much as called.

It fires on six or more paired days inside four weeks, an average of **1.5**
points apart, with the gap holding its direction at least 70% of the days they
differed. Two of those bars are worth the ink:

- **1.5, not 1.0.** A full point was the first choice and it is too low. Five
  points is a coarse scale, so a couple sitting steadily on 5 and 4 are not
  seeing the fortnight differently — they are agreeing and rounding
  differently, and saying otherwise manufactures a problem out of the
  granularity of the widget.
- **Direction has to hold.** Two partners whose scores cross back and forth are
  not experiencing the weeks differently, they are having different Tuesdays.
  Agreement is measured only over days they actually differed: days they
  matched are not evidence *against* a direction, and counting them as dissent
  would make a couple who agree most of the time and diverge hard look like
  noise.

The counselling-transcript form of this detector is still the richer one and
still waits — for data, and for the consent flow at step 3.

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
- **Scenario S23** — two check-in series a point apart over eight paired days,
  reaching both partners as the same shape, with no direction word and no digit
  surviving into what crossed, and confidence inside the band the arithmetic
  allows.

The direction-free property is asserted three times over, deliberately, because
it is the one thing that cannot be allowed to regress: as a symmetry test in the
detector's unit tests (flip the two series, get an identical result), as a
vocabulary check in the live scenario, and again in the Flutter widget test that
renders the card — the surface is perfectly capable of reintroducing a direction
the server carefully withheld.

Still owed: the simulation should report insights alongside tendencies, so what
the system believes about a couple is readable in one place.

## 9a. On the phone

The backend was live, scheduled and tested for a while with **no client at
all** — worth recording, because a feature that exists only in the database is
indistinguishable from one that was never built, and the test suite is happy
either way.

`GET /api/v1/insights/` is fetched alongside the connection score in
`EngagementViewModel.loadRitual`, and rendered by `InsightsCard` under the
score on the home screen. Three decisions worth keeping:

- **Empty renders nothing.** No "no insights yet", no empty state, no
  placeholder. Empty is the ordinary answer and the detectors are built to give
  it; a weekly card announcing that we looked and found nothing would turn an
  honest silence into a standing reminder of being assessed. Same reasoning as
  `hidden` on the score card.
- **The client re-decides nothing.** Consent, expiry, the abuse hold and the
  confidence floor are all settled by `objects.public(user)`. Re-checking any
  of it on the phone would mean two implementations of one safety rule, and the
  stale one would be the one already installed on somebody's handset.
- **The card is capped at two.** There are only two detectors today. A home
  screen that can grow an unbounded list of things we have noticed about you is
  a different and worse product.

The framing sentence around each shape lives in the widget, not the server,
because it is presentation — but it is deliberately flat, carries no severity,
no count and no suggested action. Naming what to do about it is a therapist's
job and this is not one.

## 10. What I would not build

The vector pipeline (`apps.core.vector`, `update_relationship_vectors`). It
appears in the job with no stated purpose, pgvector is in the stack but unused
by any model, and "embed the relationship" is a solution looking for a
question. If retrieval is needed later, it can be added when there is something
to retrieve.
