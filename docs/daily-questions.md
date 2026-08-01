# Generated daily questions

A spec, not an implementation report. Written before building so the arguments
are visible and can be disagreed with.

---

## 1. What exists

`DailyQuestion` is a catalog of 14 rows. `services.todays_question()` picks
`questions[date_ordinal % 14]`. That is the whole mechanism.

Three consequences:

- **Every couple on the platform gets the same question on the same day.** The
  product's central claim is that it knows this relationship; the daily
  question knows nothing about anybody.
- **It repeats every fortnight.** A couple in their third month has answered
  each question six times. There is no dedupe — they will be asked again what
  they are looking forward to this week, and their earlier answer is sitting
  in the database unread.
- **The model has no user, no relationship, and no generation.** Fields are
  `prompt_text, category, is_active, order`.

Worth noting the codebase already knows how to do better one function below:
`todays_micro_action()` matches on attachment style and is deterministic per
`(user, day)`. The daily question just does not use any of it.

## 2. Batch, not on read

Generate ahead into a table the endpoint reads. **Not** on the API call.

Four reasons, in the order they bite:

1. **Latency on the opening path.** `GET /daily-question` is on the app's first
   screen. A model call there is a spinner the user feels every morning, and
   the failure mode when the provider is slow is a home screen that does not
   load.
2. **Both partners must get the same question.** That is the entire two-sided
   reveal mechanic. Generating on read means whoever opens first defines it,
   and two partners opening within the same second is a race that produces two
   different questions and a broken reveal.
3. **Anything generated has to be moderated before it is shown.** A question
   grounded in a couple's own thread is exactly the thing that must not go out
   unchecked — and moderation is a second call, which doubles the latency
   problem if it happens on read.
4. **Cost.** One generation per couple per week against one per open, per
   partner, per day.

There is already a precedent in the repo to copy rather than invent:
`ThreadSummary` is written by a background task and never generated inline,
"so this adds no latency to a send". Same shape, same reason.

**Cadence:** a weekly job generating the next 7 days per active couple. Weekly
rather than nightly because generation is the expensive part and 7 questions in
one call costs barely more than 1 — and because a week of lead time means a
failed job is invisible rather than a blank home screen.

## 3. Shape

```
CoupleDailyQuestion
    relationship  FK
    date_key      char(10)      # the day it is for
    prompt_text   text          # encrypted, like every other couple-derived text
    category      char          # reuses DailyQuestion.CATEGORY_CHOICES
    source        char          # "generated" | "catalog"
    generated_at  datetime
    unique_together: (relationship, date_key)
```

`todays_question(user)` becomes: look for a `CoupleDailyQuestion` for this
couple and today; if there is none, fall back to the existing catalog rotation.
**The catalog stays.** It is the floor — for new couples with no history, for
solo users with no relationship, and for every day the generator failed or was
never run. Deleting it would trade a dull question for a blank screen.

`DailyQuestionResponse.question` is a `PROTECT` FK to `DailyQuestion`, so it
needs a nullable `couple_question` FK alongside rather than a type change. Both
paths write a response; only one of the two FKs is set.

## 4. What it is generated from

Only things both partners could see, and only through the boundary.

**In:** the rolling `ThreadSummary` (which already exists and is already a
précis rather than a transcript), the couple's `category` history — what they
have been asked recently, so it does not ask the same shape five times — and
the season of the relationship (how long paired, whether they are in a rough
patch by the connection score's own reading).

**Out, and this is the load-bearing part:** anything from
`personalization/behaviour.py`. Not a tendency, not a signal name, not guidance
derived from one. The question is read by *both* partners, so it is the one
place where a leak would be a leak to the person it is about *and* their
partner simultaneously. It must go through `boundary.py` or not go at all —
and the honest answer is that nothing in behaviour.py has any business here, so
the generator simply does not import it.

Nor the private check-in values, for the same arithmetic reason the connection
score refuses them: a question shaped by "one of you said you feel distant"
tells the other one exactly that.

## 5. Safety

Two gates, both before storage, neither on the read path:

1. **Moderation**, through the same `omni-moderation` call `apps/chat` already
   uses for media. A generated intimate question is a plausible way to produce
   something the couple did not ask for.
2. **A rough-patch rule.** If the couple is inside a rupture — the connection
   score reads `quiet`, or there has been a sharp exchange in the window — the
   generator asks for repair-shaped and appreciation-shaped questions, and is
   forbidden the `intimacy` category. "What is your favourite thing about our
   sex life" on the morning after a fight is the single worst thing this
   feature could produce, and it is entirely reachable without this rule.

Anything failing either gate falls back to the catalog for that day. Silent,
logged, no user-visible failure.

## 6. Rollout

`GENERATED_DAILY_QUESTIONS` off by default. On for internal couples first,
because the failure mode is not an exception — it is a question that is subtly
wrong about someone's relationship, and that is only visible by reading them.

**Do not ship without a way to read what it produced.** A generated question is
sent to two people who did not ask for it and cannot un-see it. The minimum is
a way to list a week of generated questions across couples before they are
shown, and a kill switch that reverts to the catalog for everyone at once.

## 7. Testing

- Unit: fallback when nothing is generated, when the job failed, when
  moderation refuses; the same question for both partners; the intimacy rule
  during a rough patch; nothing from behaviour.py in the prompt.
- Scenario (S20): a couple with history gets a generated question, both
  partners see the *same* one, it is not a catalog string, and the leak sweep
  is clean on both partners' surfaces.
- Simulation: assert questions do not repeat across the four weeks — the thing
  the current implementation gets wrong and no test noticed.

## 8. What this does not solve

The question is still one per day for the couple as a unit. If the two of them
are in very different places, a single question that suits both is sometimes
not available, and the honest answer then is a duller one rather than a
question that fits one of them and lands badly on the other.
