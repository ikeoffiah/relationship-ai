"""Mutation tests for the cross-reference gate.

`test_cross_references_resolve.py` is currently red on a real defect, which is
the strongest evidence a checker can have. The other assertions are green and
therefore unproven — a regex that matches nothing passes most confidently of
all. These plant each failure and assert the parser sees it.

Everything runs against synthetic text, so nothing here touches the corpus.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import doc_reference_scan as scan  # noqa: E402


def _doc(rel: str, text: str) -> scan.Document:
    body = scan.strip_code_fences(text)
    return scan.Document(path=Path(rel), rel=rel, text=body, sections=scan._section_ids(text))


def _refs(text: str, rel: str = "docs/a.md") -> list[scan.Reference]:
    return scan.extract_references(_doc(rel, text))


# --- reference extraction ---------------------------------------------------


def test_finds_a_plain_file_reference():
    refs = _refs("See `go-to-market.md` for the pricing.")
    assert [(r.target, r.section) for r in refs] == [("go-to-market.md", None)]


@pytest.mark.parametrize(
    "text,expected",
    [
        ("`a.md` §5", ["5"]),
        ("`a.md` §5.6", ["5.6"]),
        ("`a.md` §3.3.1 is the tripwire", ["3.3.1"]),
        ("`a.md` §§12 and 13.4 are the call script", ["12", "13.4"]),
        ("`a.md` §3.2 / §3.3", ["3.2", "3.3"]),
        ("`a.md` §1 or §3", ["1", "3"]),
        ("`a.md` §§2–4 land", ["2", "3", "4"]),
        ("`a.md` (§4.1)", ["4.1"]),
    ],
)
def test_parses_the_section_shapes_the_corpus_actually_uses(text, expected):
    assert [r.section for r in _refs(text)] == expected


def test_does_not_bind_a_section_from_further_down_the_sentence():
    """`go-to-market.md` §3.1's estimate — but §7 says` must not attach §7 to
    the file. Over-binding invents references and then fails on them."""
    refs = _refs("`a.md` mentions the estimate — but §7 of something else says otherwise.")
    assert [r.section for r in refs] == [None]


def test_ignores_camelcase_identifiers_that_end_in_md():
    """`AppIconSize.md` is a Dart size token, not a document."""
    assert _refs("Icon is `AppIconSize.md` (20), white") == []


def test_ignores_references_inside_code_fences():
    text = "Real: `a.md`\n\n```\nENTITLEMENT = {'<report module>', 'b.md'}\n```\n"
    assert [r.target for r in _refs(text)] == ["a.md"]


# --- section indexing -------------------------------------------------------


@pytest.mark.parametrize(
    "text,present",
    [
        ("## 5. Pricing", "5"),
        ("### 3.3.1 The tripwire", "3.3.1"),
        ("### 3.3.1 The tripwire", "3"),  # parent implied by child
        ("## Part 3 — What I would do", "3"),
        ("| # | Criterion |\n|---|---|\n| 7.1 | Every screen renders it. |", "7.1"),
        ("- 6.4 — labelText on all 24 fields", "6.4"),
    ],
)
def test_indexes_every_shape_a_section_number_takes(text, present):
    assert present in scan._section_ids(text)


def test_does_not_index_numbers_that_merely_appear_in_prose():
    """The gate's blind-spot risk. `$35.64` and `25.6%` both live in
    go-to-market.md; if either indexed as a section, §5.6 would resolve and the
    checker would be blind to the defect it exists for."""
    text = "- Revenue per download is **$35.64** and trial→paid ~25.6%.\n"
    ids = scan._section_ids(text)
    assert "35.64" not in ids
    assert "25.6" not in ids
    assert "5.6" not in ids


# --- the three assertions ---------------------------------------------------


def test_catches_a_section_that_was_deleted_underneath_a_citation():
    """The D3.34 case: nobody edited the citing document."""
    target = _doc("docs/gtm.md", "## 5. Pricing\n### 5.5 Gifting\n")
    citing = _doc("docs/plan.md", "Priced in `gtm.md` §5.6, on the observation that...")
    docs = {d.rel: d for d in (target, citing)}
    index = scan.basename_index(docs)

    ref = scan.extract_references(citing)[0]
    assert ref.section == "5.6"
    assert not ref.historical
    candidates = scan.resolve(ref.target, index, docs, citing.rel)
    assert candidates and ref.section not in docs[candidates[0]].sections


def test_a_marked_historical_citation_is_allowed_to_be_dead():
    citing = _doc(
        "docs/audit.md",
        "*Original finding, for the record:* `gtm.md` §5.6 defined a Cohort\n"
        "License ladder that the one-SKU decision removed.",
    )
    assert scan.extract_references(citing)[0].historical is True


def test_a_marker_in_a_different_paragraph_does_not_launder_a_live_citation():
    """Marker scope is the paragraph. If it leaked to the whole document, one
    audit note would silence every stale reference in the file."""
    citing = _doc(
        "docs/audit.md",
        "*Original finding, for the record:* the ladder was removed.\n"
        "\n"
        "The checkout knows one price, see `gtm.md` §5.6.\n",
    )
    refs = scan.extract_references(citing)
    assert [r.historical for r in refs] == [False]


def test_catches_a_reference_to_a_file_that_does_not_exist():
    docs = {"docs/a.md": _doc("docs/a.md", "See `deleted-spec.md` for the rule.")}
    index = scan.basename_index(docs)
    ref = scan.extract_references(docs["docs/a.md"])[0]
    assert not scan.resolve(ref.target, index, docs, "docs/a.md")
    assert not scan.exists_outside_corpus(ref.target)


def test_a_path_qualified_reference_outside_docs_still_resolves():
    """`infra/README.md` is a real document that this scan does not cover.
    Reporting it as broken would be a false positive on a correct citation."""
    assert scan.exists_outside_corpus("infra/README.md") == (
        (scan.REPO_ROOT / "infra" / "README.md").is_file()
    )
    assert not scan.exists_outside_corpus("infra/does-not-exist.md")


# --- the self-reference problem --------------------------------------------


def test_the_section_that_documents_the_checker_is_skipped():
    """§6 of the specs README describes this checker using literal backticked
    filenames and cites `go-to-market.md` §5.6 as its worked example — the very
    reference it exists to catch. Without the skip, the gate fails on the
    paragraph explaining it, on its first run, and gets deleted."""
    raw = scan.SPEC_README.read_text(encoding="utf-8")
    assert "§5.6" in raw, "The README's worked example changed; update this test."

    stripped = scan.strip_section(scan.strip_code_fences(raw), "6")
    assert "§5.6" not in stripped, (
        "strip_section no longer removes §6 of the specs README. The gate will "
        "now fail on the section that documents it."
    )
    assert stripped.count("\n") == raw.count("\n"), (
        "strip_section changed the line count, so every reported line number in "
        "that file is now wrong."
    )


def test_stripping_a_section_leaves_its_neighbours_intact():
    text = "## 5. Five\nkeep-five\n\n## 6. Six\ndrop-six\n\n## 7. Seven\nkeep-seven\n"
    out = scan.strip_section(text, "6")
    assert "keep-five" in out
    assert "drop-six" not in out
    assert "keep-seven" in out
