"""Parse cross-references between the markdown documents.

`docs/specs/README.md` §6 (rule D3.34): when a document's subject changes, the
documents that *frame* it go stale even though nothing in them was edited. The
citation still parses, the file still exists, and the section it points at is
gone — so nothing errors and nobody notices until a person happens to re-read
it. That has now happened five times in this repo in a week, and every catch was
somebody's luck.

This module extracts what the documents claim about each other. The assertions
live in `test_cross_references_resolve.py`.

Three reference kinds are recognised:

* **File** — a backticked ``  `name.md`  `` anywhere in prose.
* **Section** — a file reference immediately followed by ``§N``, ``§N.M``,
  ``§§N and M``, ``§§N–M``, ``§N / §M``, ``§N or §M``.
* **Spec registry** — the tables in §1 and §3 of `docs/specs/README.md`.

Stdlib only. Parses text; imports nothing it is checking.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS = REPO_ROOT / "docs"
SPECS = DOCS / "specs"
SPEC_README = SPECS / "README.md"

# Markdown outside `docs/` that documents legitimately cite.
ROOT_DOCS = ["README.md", "VALIDATION.md"]


# ---------------------------------------------------------------------------
# Historical citations
# ---------------------------------------------------------------------------

# §6: "Historical citations are allowed — an audit entry recording a finding
# that a later decision resolved should keep the reference — but must be in the
# past tense and marked as such, so the reader can tell a stale pointer from a
# deliberate one."
#
# Only the marker is enforced. Detecting past tense mechanically is unreliable
# in both directions, and a checker that guesses at grammar gets argued with
# instead of fixed. The marker is the part that actually serves the reader: it
# is what lets someone hitting a dead §-number know whether they have found a
# bug or a deliberate record.
#
# These are the phrasings already in use in the corpus, plus one canonical
# form. Keep the list short — every addition makes it easier to silence the
# check without meaning to.
HISTORICAL_MARKERS = [
    r"\(historical\)",
    r"\[historical\]",
    r"for the record",
    r"original finding",
    r"as (?:it |they )?(?:was|were) written",
    r"superseded",
    r"since (?:removed|deleted|renumbered|cut)",
    r"now (?:removed|deleted|renumbered|gone|cut)",
    r"no longer exists?",
    r"which no longer",
    r"before (?:it|this) was (?:removed|cut|renumbered)",
]

_HISTORICAL = re.compile("|".join(HISTORICAL_MARKERS), re.IGNORECASE)


# ---------------------------------------------------------------------------
# Text preparation
# ---------------------------------------------------------------------------

_FENCE = re.compile(r"^\s*(```|~~~)")


def strip_code_fences(text: str) -> str:
    """Blank out fenced code blocks, preserving line numbering.

    A filename inside a code sample is an illustration, not a citation — the
    allowlist snippet in `money-path.md` names modules that deliberately do not
    exist yet. Lines are replaced rather than removed so reported line numbers
    still point at the right place.
    """
    out, in_fence = [], False
    for line in text.splitlines():
        if _FENCE.match(line):
            in_fence = not in_fence
            out.append("")
            continue
        out.append("" if in_fence else line)
    return "\n".join(out)


def strip_section(text: str, heading_number: str) -> str:
    """Blank out one numbered top-level section, preserving line numbering.

    Needed for exactly one thing: §6 of `docs/specs/README.md` documents this
    checker, using literal backticked filenames and citing `go-to-market.md`
    §5.6 as its worked example — the very reference it exists to catch. A
    checker that fails on the paragraph describing it is a checker that gets
    deleted on its first run.
    """
    lines = text.splitlines()
    out, inside = [], False
    for line in lines:
        m = re.match(r"^(#{1,6})\s+(\d+(?:\.\d+)*)\.?\s", line)
        if m:
            level, number = len(m.group(1)), m.group(2)
            if number == heading_number:
                inside = True
                out.append("")
                continue
            # Any heading at the same or higher level ends the section.
            if inside and level <= 2 and not number.startswith(f"{heading_number}."):
                inside = False
        out.append("" if inside else line)
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------


@dataclass
class Document:
    path: Path
    rel: str
    text: str
    sections: set[str] = field(default_factory=set)


_HEADING = re.compile(r"^#{1,6}\s+(\d+(?:\.\d+)*)\.?(?:\s|$)", re.MULTILINE)


def _section_ids(text: str) -> set[str]:
    """Numbered headings, e.g. `## 5. Pricing` -> "5", `### 3.3.1 X` -> "3.3.1".

    A parent is implied by any child: a document with `### 5.1` answers a
    reference to §5 even when it has no bare `## 5` heading.
    """
    ids: set[str] = set()
    for number in _HEADING.findall(text):
        ids.add(number)
        parts = number.split(".")
        for i in range(1, len(parts)):
            ids.add(".".join(parts[:i]))
    return ids


def load_documents() -> dict[str, Document]:
    """Every markdown document, keyed by repo-relative POSIX path."""
    paths = sorted(DOCS.rglob("*.md"))
    paths += [REPO_ROOT / name for name in ROOT_DOCS if (REPO_ROOT / name).exists()]

    docs: dict[str, Document] = {}
    for path in paths:
        rel = path.resolve().relative_to(REPO_ROOT).as_posix()
        raw = path.read_text(encoding="utf-8", errors="replace")
        body = strip_code_fences(raw)
        if rel == SPEC_README.relative_to(REPO_ROOT).as_posix():
            body = strip_section(body, "6")
        docs[rel] = Document(path=path, rel=rel, text=body, sections=_section_ids(raw))
    return docs


def basename_index(docs: dict[str, Document]) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for rel in docs:
        index.setdefault(rel.rsplit("/", 1)[-1], []).append(rel)
    return index


# ---------------------------------------------------------------------------
# Reference extraction
# ---------------------------------------------------------------------------

# A backticked markdown filename, then — bound tightly, because a `§` further
# down the sentence usually belongs to a different subject — an optional run of
# section numbers.
_FILE_REF = re.compile(r"`([A-Za-z0-9._\-/]+\.md)`(?P<tail>[ ,(]{0,3}§{1,2}[^\n]{0,60})?")

_SECTION_RUN = re.compile(
    r"^[ ,(]{0,3}§{1,2}\s*"
    r"(?P<body>\d+(?:\.\d+)*"
    r"(?:\s*(?:,|/|&|and|or|to|[–—-])\s*(?:§{1,2}\s*)?\d+(?:\.\d+)*)*)"
)

_RANGE_SEP = re.compile(r"\s*[–—-]\s*")


@dataclass(frozen=True)
class Reference:
    source: str
    line: int
    target: str
    section: str | None
    historical: bool


def _paragraph_around(text: str, line_no: int) -> str:
    """The contiguous non-blank lines containing `line_no` (1-based)."""
    lines = text.splitlines()
    i = line_no - 1
    if i < 0 or i >= len(lines):
        return ""
    start = i
    while start > 0 and lines[start - 1].strip():
        start -= 1
    end = i
    while end + 1 < len(lines) and lines[end + 1].strip():
        end += 1
    return "\n".join(lines[start : end + 1])


def _parse_sections(tail: str) -> list[str]:
    """Section numbers from a tail like " §§12 and 13.4" or " §3.2 / §3.3"."""
    m = _SECTION_RUN.match(tail)
    if not m:
        return []
    body = m.group("body")
    parts = re.split(r"\s*(?:,|/|&|\band\b|\bor\b|\bto\b)\s*", body)

    out: list[str] = []
    for part in parts:
        part = part.replace("§", "").strip()
        if not part:
            continue
        # "2–4" expands only for single-level integers; "3.1–3.4" is left
        # as its endpoints, since the intermediate numbering is not knowable.
        if _RANGE_SEP.search(part):
            ends = [x.strip() for x in _RANGE_SEP.split(part, maxsplit=1)]
            lo, hi = (ends + ["", ""])[:2]
            if lo.isdigit() and hi.isdigit() and int(hi) >= int(lo) and int(hi) - int(lo) < 30:
                out.extend(str(n) for n in range(int(lo), int(hi) + 1))
                continue
            out.extend(x for x in (lo, hi) if x)
            continue
        out.append(part)
    return [p for p in out if re.fullmatch(r"\d+(?:\.\d+)*", p)]


def extract_references(doc: Document) -> list[Reference]:
    refs: list[Reference] = []
    for m in _FILE_REF.finditer(doc.text):
        line_no = doc.text.count("\n", 0, m.start()) + 1
        historical = bool(_HISTORICAL.search(_paragraph_around(doc.text, line_no)))
        sections = _parse_sections(m.group("tail") or "")
        if not sections:
            refs.append(Reference(doc.rel, line_no, m.group(1), None, historical))
        else:
            for section in sections:
                refs.append(Reference(doc.rel, line_no, m.group(1), section, historical))
    return refs


def all_references(docs: dict[str, Document]) -> list[Reference]:
    return [ref for doc in docs.values() for ref in extract_references(doc)]


# ---------------------------------------------------------------------------
# The spec registry in README §1 and §3
# ---------------------------------------------------------------------------


def specs_on_disk() -> set[str]:
    return {p.name for p in SPECS.glob("*.md") if p.name != "README.md"}


def _readme_section_text(number: str) -> str:
    """One numbered section of the specs README, code fences stripped."""
    text = strip_code_fences(SPEC_README.read_text(encoding="utf-8", errors="replace"))
    lines = text.splitlines()
    out, inside = [], False
    for line in lines:
        m = re.match(r"^(#{1,6})\s+(\d+(?:\.\d+)*)\.?\s", line)
        if m:
            if m.group(2) == number:
                inside = True
                continue
            if inside and len(m.group(1)) <= 2:
                break
        if inside:
            out.append(line)
    return "\n".join(out)


def specs_named_in(section: str) -> set[str]:
    """Spec filenames cited in a given README section."""
    return set(re.findall(r"`([A-Za-z0-9._\-]+\.md)`", _readme_section_text(section)))


def resolve(target: str, index: dict[str, list[str]], docs: dict[str, Document]) -> list[str]:
    """Candidate documents a reference could mean. Empty means unresolvable."""
    if target in docs:
        return [target]
    return index.get(target.rsplit("/", 1)[-1], [])
