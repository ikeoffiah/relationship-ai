# Transcribing calls

What to do with the audio of a couple's video session, and — more importantly —
what not to keep.

Status: proposed. Depends on nothing in the chat media work except the
principles; it reaches a different conclusion about retention, on purpose.

---

## 1. The decision this rests on

**Transcribe, derive, discard.** The audio is never stored. The verbatim
transcript is never stored. What persists is derived insight: talk-time
balance, interruption counts, where the Four Horsemen appeared, whether either
partner reached for repair, emotional temperature over the call.

This is the opposite of the choice made for voice notes, and the asymmetry is
deliberate:

- A **voice note** is a message one person composed *for* the other. Keeping it
  is keeping their message, which is what a thread is.
- A **call** is shared, unrehearsed and emotionally loaded. A word-for-word
  record of a couple's worst argument is a liability: discoverable in a
  separation, and re-readable by a partner who wants to re-litigate "you said
  *exactly* this". Nobody's relationship has ever been improved by a transcript
  of the fight.

The derived insight is also simply the more useful artefact. What improves
communication is "you interrupted eleven times in the first ten minutes and
none of it landed" — not a paragraph of what was said.

A useful side effect: with no audio and no verbatim retained, there is no
second bucket to erase. The deletion story built for chat media does not
acquire a new hole.

---

## 2. Why not realtime

Live coaching during a call is worse on every axis:

- **Product.** Interrupting two people mid-argument with an AI suggestion is the
  wrong intervention at the wrong moment. The value is in what they take away,
  not in being corrected while their partner watches.
- **Cost.** Realtime transcription is an order of magnitude dearer than batch.
- **Engineering.** Sub-second latency, partial-transcript handling, and a whole
  class of failure that a post-call job simply does not have.

So: the call ends, a job runs, and the insight appears afterwards — in the
thread, as something to talk about.

---

## 3. How the audio gets out

LiveKit **Track egress** exports individual tracks without transcoding, and
streaming audio to a captioning service over WebSocket is a documented use of
it. Two consequences worth having:

- **One track per participant means speaker labels for free.** No diarisation,
  no diarisation errors, no paying a model to guess who was talking. For a
  two-person call this is the whole problem solved by configuration.
- **Silence is cheap to remove.** Run VAD over each track before sending it
  anywhere. In a real conversation each person is silent most of the time, and
  trimming typically halves the billable minutes.

Pipeline: call ends → track egress per participant → VAD trim → STT per track →
merge into a speaker-labelled timeline in memory → derive → **discard the
timeline** → persist the insight.

The merged timeline exists only inside the worker process. It is never written
to disk, never logged, and never returned by an endpoint.

---

## 4. Cost

Verified against OpenAI's pricing page (July 2026): `gpt-4o-mini-transcribe` is
$0.003/min, `gpt-4o-transcribe` and `whisper-1` $0.006/min. Note the
`gpt-4o*-transcribe` figures are OpenAI's *estimates* — those models bill by
audio input token, so real spend moves with speech density.

A 45-minute call, two tracks, roughly half silence after VAD ≈ 45 billable
minutes ≈ **14¢**. Weekly sessions come to about $1/couple/month.

Cost is not the constraint here. It is worth saying plainly because it is the
usual reason this feature gets deferred, and it should not be.

---

## 5. Consent, which is the actual hard part

Recording a call moves audio off the peer-to-peer path. That changes the
privacy posture of calls entirely, and it is not something to slip into a
release note.

**All parties must consent, in-app, before egress starts.** Several US states
require it, and both partners are on the call. More importantly for this
product: coercive control is a real dynamic, so one partner must never be able
to enable recording for the other.

Three rules, none of them negotiable:

1. **If either declines, it is off.** Not "off for them" — off. There is no
   per-participant version of this that is honest.
2. **A non-dismissible indicator for the entire call.** If someone forgets they
   are being transcribed, consent has expired in every sense that matters.
3. **Either partner can stop it mid-call, and stopping is immediate.** The
   control has to be equally reachable by both, and stopping discards what has
   been captured so far rather than processing it.

Consent is per-call. A couple who agreed last week has not agreed today —
standing consent for recording conversations is how this becomes something
people feel they did not sign up for.

---

## 6. What gets derived

Feed the speaker-labelled timeline through what already exists rather than
inventing a second analysis stack:

- **The contempt vocabulary** in `apps/chat/assist.py` already encodes what
  this product means by a sharp exchange. Run it over the transcript.
- **`apps/personalization/behaviour.py`** already models tendencies with decay
  and a "tendencies, not diagnoses" rule. A call is a rich source of exactly
  the signals it already tracks — withdrawal, pursuit, escalation, repair.
- **`apps/insights/RelationshipInsight`** already has per-partner narratives
  with separate consent flags, which is the right shape for a call summary.

Plus what only a call can give you, and what chat cannot:

| measure | why it matters |
|---|---|
| talk-time balance | the most legible imbalance in any conversation |
| interruptions, by direction | who is not letting whom finish |
| repair attempts, and whether they landed | Gottman's strongest single predictor |
| emotional temperature over time | where it turned, not just that it did |

These are also exactly the *dyadic patterns* the outcome-loop spec identifies as
the missing layer — a call is the densest source of them the product will ever
have.

---

## 7. What is shown, and to whom

The same boundary as everything else: **nothing derived from one partner is
surfaced to the other as a claim about them.**

- Talk-time balance and interruption counts are properties of *the
  conversation*, not of a person, and can be shown jointly.
- Anything that reads as a characterisation of one partner goes only to that
  partner.
- The default output is a prompt for the two of them to talk about, not a
  report the app hands down. "You both got quieter around the money bit — worth
  picking that up?" beats a scorecard.

Route it through the boundary function in `docs/outcome-loop.md` §2 rather than
writing a second set of rules here.

---

## 8. Sequencing

1. **Consent UI and the indicator.** First. Nothing captures audio until both
   the agreement and the visible reminder exist, because retrofitting consent
   onto a working pipeline is how it ends up perfunctory.
2. **Egress + VAD + STT, ending in a discarded timeline.** Prove the pipeline
   with nothing persisted but a log line saying how many minutes it processed.
3. **Derivation**, reusing the contempt vocabulary and `behaviour.py`.
4. **Presentation** as a thread prompt.

Step 2 producing nothing is the point: it is the version that can be run
against real calls to check cost and quality before a single derived claim is
stored about anybody.

---

## 9. Open questions

- **Which STT.** Speech with two speakers on separate tracks is the easy case;
  the choice should be made on accented and code-switched speech, which is what
  these couples will actually bring. Worth a bake-off on real recordings before
  committing.
- **Retention of the derived insight.** It should decay like everything else,
  but "how long is a call worth remembering" is a product question rather than
  an engineering one.
- **Calls that are not sessions.** A casual video call is not a counselling
  session, and transcribing every call would be a much larger promise. The
  default should probably be that only structured sessions are offered
  transcription at all.

Sources: [LiveKit egress overview](https://docs.livekit.io/home/egress/overview/),
[LiveKit text and transcriptions](https://docs.livekit.io/agents/multimodality/text/),
[OpenAI API pricing](https://developers.openai.com/api/docs/pricing).
