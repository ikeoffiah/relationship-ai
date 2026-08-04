# Documentation rot — two detectors

Owner: QA. Written 2026-08-03, implementing `docs/specs/README.md` §6 (rule
D3.34) and marketing's recurrence sweep.

```bash
pytest tests/docs/ -v          # both detectors; stdlib only, no DB, no keys
./tests/run_qa_gates.sh        # with the rest of the QA gates
```

Two failures, same family, one invisible to the other.

| | Catches | Detector |
|---|---|---|
| **Cross-reference** | A pointer that no longer resolves | `tests/docs/doc_reference_scan.py` |
| **Recurrence** | A pointer that resolves fine, resting on a pricing model that was replaced | `tests/docs/recurrence_lint.py` |

Both fail in both directions. Both are enforced by an allowlist that carries a
reason per entry, because in both cases the thing worth enforcing is not "this
text is forbidden" but "somebody read this and said why it is fine."

---

## 1. Why this class needs a machine

The rule, from `docs/specs/README.md` §6:

> when a document's subject changes, the documents that *frame* it go stale
> even though nothing in them was edited

Nothing errors. The citation still parses. The file still exists. Git blame
shows no recent change to the citing document, because there wasn't one — the
document it points at moved.

It has now happened **seven times in a week** in this repo. Every catch before
these detectors was a person happening to re-read something.

The worst instance was `facilitator-session-guide.md`, whose entire stated
justification was "Promised in the Cohort License §5.6" — a section deleted by
the one-SKU pricing decision. The document's reason for existing had been
removed underneath it, and it was queued to be handed to an engineer as
authoritative.

---

## 2. The cross-reference checker

Three assertions, per §6:

1. Every `` `<file>.md` `` resolves to a file that exists.
2. Every `` `<file>.md` §N `` resolves to a section that exists in it.
3. Every spec in `docs/specs/` appears in README §3, and every spec named in
   README §1 or §3 exists.

Assertion 2 is the one that matters. A dead **file** reference is loud — the
link is obviously broken. A dead **section** reference is silent: the file
opens, the reader scrolls, finds nothing at §5.6, and either assumes they
misread or quietly reasons from whatever is nearby.

### What a section is, here

Not just headings. Acceptance criteria in this repo live in **table rows** and
are cited as §7.1 and "criterion 7.5" interchangeably, so the index reads four
shapes: numbered headings, `Part N` headings (`product-assessment.md` numbers
its top level that way and `execution-plan.md` cites it as §3), numbered table
rows, and numbered list items.

Getting this wrong in either direction breaks the gate:

- Heading-only parsing reported `support-icon-coverage.md` §7.1 and
  `accessibility.md` §6.4 as dead. Both are real, findable rows. A false
  positive on a live spec is the fastest way to get a docs gate turned off.
- Too permissive and the gate goes blind. `go-to-market.md` contains `$35.64`
  and `25.6%`; if either indexed as a section, §5.6 would resolve and the
  checker would no longer see the defect it was built for.

`test_section_indexing_is_neither_blind_nor_indiscriminate` pins both ends.

### Historical citations

§6 allows them — an audit entry recording a finding that a later decision
resolved should keep its reference — provided they are past tense and marked.

**Only the marker is enforced.** Detecting past tense mechanically is
unreliable in both directions, and a checker that guesses at grammar gets
argued with rather than fixed. The marker is also the part that actually serves
the reader: it is what lets someone hitting a dead §-number know whether they
have found a bug or a deliberate record.

Recognised markers: `(historical)`, "for the record", "original finding",
"superseded", "since removed", "no longer exists", and a few near variants —
see `HISTORICAL_MARKERS`. Scope is the **paragraph**, deliberately: if a marker
covered the whole file, one audit note would launder every stale reference in
it.

The reverse is checked too. A marker on a reference that still resolves is a
document describing something as dead when it is alive, and it makes a reader
distrust every other marker.

> **Do not add a marker to a citation that is merely wrong.** The marker means
> "this is deliberate". Using it to silence the check converts a caught defect
> into a permanent lie.

### The self-reference problem

§6 of the specs README documents this checker, using literal backticked
filenames, and cites `go-to-market.md` §5.6 as its worked example — a section
since removed, and the exact reference it exists to catch. The scan blanks that
section before reading (line numbering preserved, so reported lines stay
correct). A checker that fails on the paragraph describing it is a checker that
gets deleted on its first run.

---

## 3. The recurrence lint

The cross-reference checker structurally cannot see a **valid citation resting
on a dead assumption**: the reference resolves, the sentence parses, the
arithmetic is internally consistent, and only the pricing model underneath has
been replaced.

`go-to-market.md` §3.1 and §5.2 contradicted each other for days. As it was
written, §3.1 asserted "gross margin at $14.99/month is 92–96%" — a monthly
margin against a monthly price, neither of which has existed since D2 — while
§5.2 correctly modelled $39-once. Each was plausible in isolation, so neither
read as wrong, and there was no link between them to break.

The detector is blunt by construction: **since D2 we sell one thing, once, so
any sentence carrying a per-period unit is suspect.** A grep for that found
five live contradictions in about a minute, including an anti-paid-install
argument sized on $90–150 first-year ARPU against a real figure of $39 once —
2–4× wrong in the direction that made paid installs look *better* than they are.

### A hit is a question, not a defect

This changes what the tests assert. They do not claim per-period language is
wrong. Competitor pricing genuinely is "/month", vendor bills genuinely are
per-month, and `crisis-gating.md` names the trial wall precisely in order to
forbid it. What is asserted is that **every occurrence has been read by
someone who wrote down why**. `REVIEWED_USES` is the record of that reading,
and the reason field is the deliverable — an allowlist of bare paths records
that someone silenced the check; a reason records that someone read it.

### Why counts are part of the key

Allowlisting `("go-to-market.md", "price-per-period")` once would silence that
file forever — and it is both the most actively edited document in the repo and
the one that held all five contradictions. Storing the expected count means a
*new* per-period sentence moves the number and asks its question, while the
reviewed ones stay quiet. Updating a count is a one-character edit that
requires having read the line that moved it, which is the whole mechanism.

### `retention` is deliberately not a term

It was on the founding list and it is by a wide margin the noisiest word in
this corpus — 60+ hits across 12 files, essentially all of them one of two
senses with nothing to do with recurring revenue:

- **Data retention.** `session-retention-wording.md` is entirely about what we
  keep from a session.
- **Week-4 couple retention.** One of the five numbers in the plan, and a
  perfectly good metric for a one-off business.

Keeping it would have meant allowlisting a dozen files on day one, and an
allowlist that large on day one is a gate nobody reads. Bare `subscription`,
`monthly` and `trial` were narrowed for the same reason: most of their
occurrences are documents correctly describing the subscription we *stopped*
selling.

Calibration is pinned in both directions against the manual sweep's two known
signals — `go-to-market.md` held all five, `marketing-copy.md` came back clean —
plus fixtures for each of the five real sentences and for five legitimate ones.

---

## 4. Open findings

Both are in documents QA does not own, so they are reported rather than fixed.

### R1 — `execution-plan.md:260` cites a section that no longer exists

D2.1 reads: *"Marketing priced a four-step licence ladder (Cohort 10/25/50/
Annual) in `go-to-market.md` §5.6…"* — a section which no longer exists.

Section 5 now runs 5.0–5.5; §5.6 died with the one-SKU decision. The sentence
is already past tense and is a legitimate historical citation — it is recording
what marketing did before D2 — but it carries no marker, so a reader following
it lands on nothing and has no way to know that is intended.

**Fix: two words.** For the record, `capability-claims-audit.md` handles the
identical citation correctly with "*Original finding, for the record:*". Something like "in what
was then `go-to-market.md` §5.6 (since removed)" clears it.

### R2 — `intimacy-content-position.md` is not in README §3

A spec landed in `docs/specs/` and is absent from the §3 index. §3 is how a
reader finds out what exists; a spec missing from it is a spec nobody is told
about, and possibly one with build-order dependencies in §1 that nobody will
read in time.

This one is worth noting for a second reason: the gate caught it **within
minutes of the file landing**, which is the drift class working exactly as
described — nobody edited the README, a new document simply appeared beside it.

---

## 5. Known limits

- **The recurrence lint only reads prose.** A dead pricing assumption expressed
  as a mechanic rather than a sentence is invisible to it. The live example:
  the couple-code referral comps a referred couple "30 days free", which is a
  subscription that no longer exists. No per-period *word* need appear in the
  code that implements it.
- **Neither detector reads code.** Both scan `docs/**`. An event schema
  emitting `trial_start` is caught in the taxonomy document and missed in the
  Dart constant.
- **Cross-reference resolution is basename-first.** `facilitator-report.md`
  names both a design document and a spec; candidates are ranked (same
  directory, then `docs/specs/`) and a section is accepted if it exists in any
  of them. Guessing harder than the reader can would invent failures.
- **Neither knows whether a claim is true**, only whether it is reachable and
  whether its units match the business model. `capability-claims-audit.md` is
  the human process for the rest.
