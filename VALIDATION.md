# Validation harness

How we validate RelationshipAI before shipping. Two layers:

1. **Automated** — runs with no external keys, gates CI: linters, all test
   suites, and a safety-classifier evaluation.
2. **Live end-to-end** — a manual checklist that needs real keys/infra
   (OpenAI, LiveKit, Postgres/Redis) to exercise the AI, video, and DB paths
   that stubs can't cover.

## Quick start

```bash
make validate      # lint + safety eval + Flutter/Django/FastAPI test suites
make safety-eval   # just the safety evaluation report
make test          # just the test suites
make lint          # just the linters
```

`make validate` is the single command to run before merging. In CI the same
suites run per service (`django-ci`, `fastapi-ci`, `flutter-ci`).

## Safety classifier evaluation

`backend-fastapi/tests/validation/` holds a **labeled message set**
(`safety_dataset.py`) and a **scorer** (`test_safety_eval.py`). It runs each
message through the real pre-screen pipeline (`SafetyPreScreener`) and reports:

- **Clear-crisis recall** — crises the Layer-1 rules / keyword floor must catch.
  **Gated: must be ≥ 90%.**
- **False positives on safe** — safe messages (incl. traps like "my back is
  killing me", "I want to dye my hair"). **Gated: must be 0.**
- **Paraphrase-crisis recall** — obliquely-phrased crises. **Reported, not
  gated** — these need the embedding (Layer 2) and LLM (Layer 3) layers, which
  only run when keys are set. This number is the calibration target.

Run the report directly:

```bash
make safety-eval
# or: cd backend-fastapi && ./venv/bin/python -m tests.validation.test_safety_eval
```

**Calibration workflow:** grow `safety_dataset.py` with real, de-identified
examples, then tune the Layer-2 threshold / exemplars and the Layer-3 prompt
against the report. See `docs/safety/classifier-upgrade.md`. The dataset is
deliberately small and first-pass; treat its thresholds as provisional.

### Note on the two safety modes

- **Without keys (CI, local default):** Layers 2/3 fall back to keyword
  heuristics. The eval measures this floor — clear crises caught, zero false
  positives, paraphrases largely missed.
- **With keys (`OPENAI_API_KEY`, `SAFETY_CLASSIFIER_MODEL`):** Layer 2 does
  embedding similarity and Layer 3 does contextual LLM classification, closing
  the paraphrase gap. Re-run the eval in a keyed environment to measure the
  real production recall.

## Live end-to-end checklist (manual, needs real infra)

The automated suites stub external services. Before a release, exercise these
against a real stack (`OPENAI_API_KEY`, LiveKit keys, Postgres+Redis, a built
mobile app):

- [ ] **AI counseling** — send a chat turn; confirm a real, personalized reply
      streams back (set `LLM_PROVIDER`/`OPENAI_API_KEY`). Confirm a crisis
      message triggers the safety modal and (if configured) crisis resources.
- [ ] **Counseling memory** — after a session, confirm the extractor writes
      memories and a later session's reply reflects them (needs embeddings +
      the `memory_vectors` table).
- [ ] **Safety, keyed** — run `make safety-eval` in the keyed env; confirm
      paraphrase recall climbs vs. the floor.
- [ ] **Onboarding → portrait → invite** — finish onboarding, see the portrait,
      send a partner invite, accept on a second account.
- [ ] **Daily engagement** — daily question two-sided reveal, check-in, a shared
      goal, points/streak increment.
- [ ] **Games** — play Know Your Partner on both accounts, see the scored
      reveal; a Conversation Deck; the spicy toggle (both age-verified + both
      opted in).
- [ ] **Video** — start a joint session on two devices, confirm two-way video
      (needs `LIVEKIT_URL` + key/secret).

## Known gaps (tracked)

- Safety thresholds/exemplars are first-pass — calibrate with real data.
- Layer 2/3 recall is only measured on the keyword floor in CI; the keyed path
  needs a periodic keyed eval run.
- Counseling memory uses the private namespace only (shared-context memories
  are a follow-up).
