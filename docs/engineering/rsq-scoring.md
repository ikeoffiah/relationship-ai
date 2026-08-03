# The RSQ scorer: what is actually wrong with it

Engineering note, 2026-08-03. Written because three sessions are making
decisions on my earlier analysis of this file and **part of that analysis was
wrong**. This supersedes what I said in the cross-session discussion.

## The correction

I previously said the scorer used "ad-hoc subscales, not the published
scoring", and that it "discards the entire model-of-other dimension". Both
claims were too strong, and `docs/execution-plan.md` D3 was promoted to P0 partly
on the strength of them.

Comparing the shipped formulas to the Griffin & Bartholomew (1994) RSQ prototype
key, three of the four matched **exactly**:

| Subscale | Shipped | Published key |
|---|---|---|
| Secure | 3, 9R, 10, 15, 28R | 3, 9R, 10, 15, 28R — **match** |
| Fearful | 1, 5, 12, 24 | 1, 5, 12, 24 — **match** |
| Preoccupied | 6R, 8, 16, 25 | 6R, 8, 16, 25 — **match** |
| Dismissing | 2, 6, 19, 22, **28R** | 2, 6, 19, 22, **26** — **differs** |

This is the published instrument with **one item wrong**, not an invention. That
is a much better position than I reported.

It also explains the anomaly the product session found. Item 28 appearing twice
with the same sign is not a deliberate 2×2 shared-self-model design and not a
double-count — it is almost certainly a transcription slip, `26` typed as `28`,
with the reverse-keying copied from the secure line above it. Item 26 ("I prefer
not to depend on others") is a canonical dismissing item. Item 28 ("I worry
about having others not accept me") is a self-model anxiety item with no place
in the dismissing scale at all.

**On "unused items".** I wrote that 14 of 30 items feed nothing and framed it
as the instrument being broken. Both halves were wrong, and the count is now
also stale: since item 26 was restored to the dismissing scale the scorer reads
**17** items, not 16, so **13** are unused rather than 14. Withdrawn per D3.37,
and it should not be cited as an argument about validation — the verdict on
that stands on the absence of norming, which is a separate and better ground.

Unused is normal. The RSQ embeds items from several
sources; only ~18 feed the four prototype scores, and the remainder belong to
the Collins & Read AAS subscales (depend / close / anxiety) which this product
does not compute. Unused ≠ discarded-in-error.

## What is genuinely defective

1. **Dismissing uses item 28 where the published key uses item 26.** One line.
2. **A blank or tied submission returns `secure`.** All four scores land on 3.0
   and `max()` returns the first key. Anyone who skips is labelled securely
   attached — shipping-blocking the moment the onboarding gate is removed.

That is the whole list. Both are fixed here.

## What a scorer change does *not* fix

Using the published key is not the same as having norms. A facilitator will ask
two questions and the second one still has no good answer:

- *"What is your scoring key?"* — answerable now, and citable.
- *"Normed against what?"* — nothing. There is no comparison sample, so a
  percentile or a "you scored higher than X% of couples" claim is unsupportable.

**The report may state a prototype and describe it. It must not imply external
validation, norming, or clinical interpretation.** That constraint belongs in
the artefact spec, not in this file, but it is the real channel risk and no
amount of scorer work removes it.

## Consequence for the plan

D3's severity was overstated by me. The fix is a day and worth doing before the
report ships — a wrong dismissing item is a real error and professionals may
recognise the key. But "not survivable in that channel" was my language and it
was too strong; the norming gap is the thing that actually needs handling, and
it is a copy decision rather than an engineering one.

D4's item cut stays safe for *this product's* scoring. Note only that the eight
cut items include AAS material, so cutting forecloses ever computing those
subscales without re-adding them.

## Verification note

The published key above is stated from knowledge of the instrument, not from a
copy of the source paper in this repository. Before any external claim is made
about the scoring, someone should check it against Griffin, D. W., &
Bartholomew, K. (1994), *Models of the self and other*, JPSP 67(3). If it
differs, this file and `calculate_rsq_attachment_style` are the only two places
that need to change.

---

## Does the corrected scorer compute model-of-other? **No.**

Asked repeatedly and answered here so it stops depending on message timing.

The fix resolved **two things only**: the item-28→26 index error, and the
tie-break that returned "secure". It computes four prototype means. There is no
axis computation — `grep -c "model_of_self\|model_of_other\|axis\|dimension"`
over `tasks.py` returns **0**.

My earlier claim that items 7/14/17/27/30 were "precisely what a corrected
scorer would need" was wrong, and QA is right to have flagged the contradiction.

**But the axes do not need those items.** In Bartholomew's model they are linear
combinations of the four prototype scores already computed:

    model of self  ≈ (secure + dismissing) − (preoccupied + fearful)
    model of other ≈ (secure + preoccupied) − (dismissing + fearful)

Definitional, not empirical. About an hour to add, and it gives the report a
genuine 2×2 rather than a label comparison.

**Consequence for the item cut.** Only item 26 needed keeping, and it is now
scored. Items 7, 14, 17, 27, 30 feed nothing and never will, so the P1 cut can
be **13 items rather than 8** — a 43% shorter questionnaire with no scoring
change.

**On the distribution.** The axes will exist; a distribution to calibrate them
against will not. One profile has RSQ data. Set the `differing` threshold from
the scale midpoint and record it as chosen, not measured.
