"""Documents must not cite things that no longer exist.

Implements `docs/specs/README.md` §6 (rule D3.34): when a document's subject
changes, the documents that *frame* it go stale even though nothing in them was
edited. The citation still parses, the file still exists, the section it points
at is gone — nothing errors, and nobody finds out until a person happens to
re-read it.

That has happened five times in this repo in a week. Every catch was luck. The
worst instance was `facilitator-session-guide.md`, whose entire stated
justification was "Promised in the Cohort License §5.6" — a section deleted by
the one-SKU pricing decision. The document's reason for existing had been
removed underneath it and it was still queued to be handed to an engineer as
authoritative.

Three assertions, each failing in both directions:

1. Every ``  `filename.md`  `` resolves to a file that exists.
2. Every ``  `filename.md` §N  `` resolves to a section that exists in it.
3. Every spec in `docs/specs/` appears in README §3, and every spec named in
   README §1 or §3 exists.

Historical citations stay legal — an audit entry recording a finding that a
later decision resolved should keep its reference — but must carry a marker, so
a reader hitting a dead §-number can tell a stale pointer from a deliberate
record. See `HISTORICAL_MARKERS` in `doc_reference_scan.py`.

Stdlib only. Run: `pytest tests/docs/ -v`
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import doc_reference_scan as scan  # noqa: E402

DOCS = scan.load_documents()
INDEX = scan.basename_index(DOCS)
REFERENCES = scan.all_references(DOCS)


# ---------------------------------------------------------------------------
# 0. The scan must keep describing the corpus
# ---------------------------------------------------------------------------


def test_the_scan_still_finds_the_documents_and_their_sections():
    """A docs checker's most likely failure is finding nothing and passing.

    If the corpus moves, or the reference regex stops matching, every assertion
    below iterates an empty list and reports success.
    """
    assert len(DOCS) >= 40, (
        f"Only {len(DOCS)} markdown documents found. Expected 40+ under docs/ "
        "plus the root README and VALIDATION. Check DOCS / ROOT_DOCS."
    )
    assert len(REFERENCES) >= 150, (
        f"Only {len(REFERENCES)} cross-references parsed; expected 200+. The "
        "reference regex has probably stopped matching, which would make every "
        "check below vacuous."
    )

    with_sections = [r for r in REFERENCES if r.section]
    assert len(with_sections) >= 60, (
        f"Only {len(with_sections)} references carry a section number. Section "
        "binding has broken; assertion 2 is checking almost nothing."
    )


def test_section_indexing_is_neither_blind_nor_indiscriminate():
    """Calibration, in both directions, against two known facts.

    Section numbers come from headings, `Part N` headings, numbered table rows
    and numbered list items — four sources, because acceptance criteria in this
    repo live in table rows and are cited as §7.1. Widening the net that far
    risks the opposite failure: an index so permissive that every reference
    resolves and the gate never fires.
    """
    gtm = DOCS["docs/go-to-market.md"]
    assert "5.5" in gtm.sections, (
        "go-to-market.md §5.5 ('Gifting') is not indexed. Section parsing is "
        "missing real headings, which produces false failures."
    )
    assert "5.6" not in gtm.sections, (
        "go-to-market.md §5.6 resolved. It should not: section 5 runs 5.0–5.5 "
        "since the one-SKU decision killed the tiered Cohort License. If this "
        "passes, the index is matching stray numbers — '$35.64' and '25.6%' "
        "both appear in that file — and the gate is now blind to the exact "
        "defect it was built for."
    )

    sic = DOCS["docs/specs/support-icon-coverage.md"]
    assert "7.1" in sic.sections, (
        "support-icon-coverage.md §7.1 is not indexed. It is a table row, not a "
        "heading — acceptance criteria in this repo are numbered that way and "
        "cited as §N.M. Heading-only parsing reports live specs as dead."
    )


# ---------------------------------------------------------------------------
# 1. Files
# ---------------------------------------------------------------------------


def test_every_referenced_document_exists():
    broken = []
    for ref in REFERENCES:
        if scan.resolve(ref.target, INDEX, DOCS, ref.source):
            continue
        if scan.exists_outside_corpus(ref.target):
            continue
        broken.append(f"{ref.source}:{ref.line}  ->  `{ref.target}`")

    assert not broken, (
        "Documents cite files that do not exist:\n\n  "
        + "\n  ".join(sorted(set(broken)))
        + "\n\nEither the file was renamed and the citing document was not "
        "updated, or the reference was wrong when written."
    )


# ---------------------------------------------------------------------------
# 2. Sections — the assertion that catches D3.34
# ---------------------------------------------------------------------------


def test_every_referenced_section_exists():
    """The one that matters.

    A dead *file* reference is loud — the link is obviously broken. A dead
    *section* reference is silent: the file opens, the reader scrolls, finds
    nothing at §5.6, and either assumes they misread or quietly reasons from
    whatever is nearby.
    """
    broken = []
    for ref in REFERENCES:
        if ref.section is None or ref.historical:
            continue
        candidates = scan.resolve(ref.target, INDEX, DOCS, ref.source)
        if not candidates:
            continue  # assertion 1's problem
        if any(ref.section in DOCS[rel].sections for rel in candidates):
            continue
        where = candidates[0]
        broken.append(
            f"{ref.source}:{ref.line}  ->  `{ref.target}` §{ref.section}  "
            f"(no such section in {where})"
        )

    assert not broken, (
        "Documents cite sections that no longer exist:\n\n  "
        + "\n  ".join(sorted(set(broken)))
        + "\n\n"
        "This is rule D3.34 (`docs/specs/README.md` §6): nobody edited the "
        "citing document. The document it points at changed.\n\n"
        "Two ways to fix, and the choice matters to the reader:\n\n"
        "  * If the pointer is simply wrong now — repoint it, or drop it.\n"
        "  * If it is a deliberate record of something that *was* true — an "
        "audit finding resolved by a later decision — keep it, put it in the "
        "past tense, and mark it so a reader can tell. Markers currently "
        "recognised: (historical), 'for the record', 'original finding', "
        "'superseded', 'since removed', 'no longer exists'. The marker must "
        "appear in the same paragraph.\n\n"
        "Do not add a marker to a citation that is merely wrong. The marker "
        "means 'this is deliberate', and using it to silence the check "
        "converts a caught defect into a permanent lie."
    )


def test_historical_citations_are_marked_and_not_merely_absent():
    """Assertion 2's other direction.

    A marker on a reference that still resolves is a document describing
    something as dead when it is alive — the same class of error pointing the
    other way, and the one that makes a reader distrust every other marker.
    """
    mislabelled = []
    for ref in REFERENCES:
        if ref.section is None or not ref.historical:
            continue
        candidates = scan.resolve(ref.target, INDEX, DOCS, ref.source)
        if not candidates:
            continue
        if any(ref.section in DOCS[rel].sections for rel in candidates):
            mislabelled.append(
                f"{ref.source}:{ref.line}  ->  `{ref.target}` §{ref.section} "
                "(marked historical, but the section still exists)"
            )

    assert not mislabelled, (
        "These citations are marked as historical but still resolve:\n\n  "
        + "\n  ".join(sorted(set(mislabelled)))
        + "\n\nIf the section came back, or was never removed, drop the marker "
        "— a reader who checks and finds it alive stops believing the next "
        "marker too.\n\n"
        "If the paragraph is historical for an unrelated reason and the marker "
        "was picked up by accident, split the sentence so the marker does not "
        "sit in the same paragraph as a live reference."
    )


# ---------------------------------------------------------------------------
# 3. The spec registry
# ---------------------------------------------------------------------------


def test_every_spec_on_disk_is_listed_in_the_readme():
    on_disk = scan.specs_on_disk()
    listed = scan.specs_named_in("3")

    unlisted = sorted(on_disk - listed)
    assert not unlisted, (
        "Specs exist in docs/specs/ but are absent from §3 of the README:\n\n  "
        + "\n  ".join(unlisted)
        + "\n\n§3 is the index a reader uses to find out what exists. A spec "
        "missing from it is a spec nobody is told about — and, per §1, "
        "possibly one with build-order dependencies nobody will read in time."
    )


def test_every_spec_named_in_the_readme_exists():
    """The other direction: §1's dependency table and §3's index.

    §1 is the more dangerous of the two. It is the build-order table — the one
    the README exists to make people read first — and every row names a spec.
    A row pointing at a deleted document is a dependency nobody can check.
    """
    on_disk = scan.specs_on_disk()
    missing = []
    for section in ("1", "3"):
        for name in sorted(scan.specs_named_in(section)):
            if name in on_disk or name in DOCS:
                continue
            if scan.resolve(name, INDEX, DOCS, "docs/specs/README.md"):
                continue
            missing.append(f"README §{section} names `{name}`, which does not exist")

    assert not missing, (
        "The README names specs that do not exist:\n\n  "
        + "\n  ".join(sorted(set(missing)))
        + "\n\nIf the spec was renamed, update the README. If it was dropped, "
        "remove the row — including from §1, where a stale row is a build-order "
        "dependency that cannot be satisfied."
    )
