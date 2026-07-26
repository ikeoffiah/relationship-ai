"""
Deterministic natural-language parser for the @bliss assistant.

Turns a chat message like "@bliss remind us to book the anniversary dinner next
Friday at 7pm" into a structured draft the client can confirm before saving:

    {"kind": "reminder", "title": "book the anniversary dinner",
     "due_at": <datetime>, "has_time": True}

It is intentionally rule-based, not an LLM: it needs no keys, runs in-process,
is fully testable, and never invents an event the user didn't ask for. A model-
backed parser can be layered on later behind the same shape; this is the floor.

``now`` is injected everywhere so behaviour is deterministic under test.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Optional

from django.utils import timezone

_TAG = re.compile(r"@bliss\b", re.IGNORECASE)

# Leading verb phrases we strip to get to the actual task text.
_LEAD = re.compile(
    r"^\s*(please\s+)?"
    r"(remind (me|us|them)(\s+to)?|"
    r"set (a |an )?(reminder|alarm)(\s+to)?|"
    r"add( an?)?( event)?|schedule|create (a |an )?(reminder|event)|"
    r"put .* (on|in) (the |our )?calendar|book)\b[:,]?\s*",
    re.IGNORECASE,
)

_WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
    "mon": 0, "tue": 1, "tues": 1, "wed": 2, "thu": 3, "thur": 3,
    "thurs": 3, "fri": 4, "sat": 5, "sun": 6,
}

# Words that, if present, lean the item toward a calendar event rather than a
# bare reminder ("dinner", "appointment", …). Reminder is the default.
_EVENT_WORDS = re.compile(
    r"\b(dinner|lunch|breakfast|brunch|date|appointment|meeting|party|trip|"
    r"anniversary|birthday|reservation|movie|concert|flight|vacation|wedding)\b",
    re.IGNORECASE,
)


@dataclass
class BlissDraft:
    kind: str            # "reminder" | "event"
    title: str
    due_at: Optional[datetime]
    has_time: bool       # False => due_at is a date at a default hour

    def as_dict(self) -> dict:
        return {
            "kind": self.kind,
            "title": self.title,
            "due_at": self.due_at.isoformat() if self.due_at else None,
            "has_time": self.has_time,
        }


def is_bliss_command(text: str) -> bool:
    return bool(text and _TAG.search(text))


def parse_bliss_command(text: str, now: Optional[datetime] = None) -> Optional[BlissDraft]:
    """Parse a raw chat message into a :class:`BlissDraft`, or ``None`` if the
    message doesn't tag @bliss or has no discernible task."""
    if not text or not _TAG.search(text):
        return None
    now = now or timezone.now()

    # Drop the tag and any leading verb phrase.
    body = _TAG.sub("", text, count=1).strip(" \t:,-")
    body = _LEAD.sub("", body).strip()

    due_at, has_time, body = _extract_datetime(body, now)
    title = _clean_title(body)
    if not title:
        return None

    # An event is something on the shared calendar (dinner, appointment…); a bare
    # timed task stays a reminder even with a clock time.
    kind = "event" if _EVENT_WORDS.search(title) else "reminder"
    return BlissDraft(kind=kind, title=title, due_at=due_at, has_time=has_time)


# ── datetime extraction ──────────────────────────────────────────────────

_DEFAULT_HOUR = 9  # undated-time reminders default to 9am local

_TIME_RE = re.compile(
    r"\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b|"
    r"\b(\d{1,2}):(\d{2})\s*(am|pm)?\b|"
    r"\b(\d{1,2})\s*(am|pm)\b",
    re.IGNORECASE,
)


def _extract_datetime(body: str, now: datetime):
    """Return (due_at | None, has_time, remaining_body)."""
    day: Optional[date] = None
    has_time = False
    hour = _DEFAULT_HOUR
    minute = 0

    # --- relative offsets: "in 2 hours", "in 30 minutes", "in 3 days" ---
    m = re.search(r"\bin\s+(\d+)\s*(min(?:ute)?s?|hours?|hrs?|days?|weeks?)\b", body, re.IGNORECASE)
    if m:
        n = int(m.group(1))
        unit = m.group(2).lower()
        delta = (
            timedelta(minutes=n) if unit.startswith("min")
            else timedelta(hours=n) if unit.startswith(("hour", "hr"))
            else timedelta(weeks=n) if unit.startswith("week")
            else timedelta(days=n)
        )
        body = body[: m.start()] + body[m.end():]
        return now + delta, True, body.strip()

    # --- day anchors ---
    lower = body.lower()
    if "tomorrow" in lower:
        day = (now + timedelta(days=1)).date()
        body = re.sub(r"\btomorrow\b", "", body, flags=re.IGNORECASE)
    elif "today" in lower or "tonight" in lower:
        day = now.date()
        if "tonight" in lower:
            hour, has_time = 19, True
        body = re.sub(r"\b(today|tonight)\b", "", body, flags=re.IGNORECASE)
    else:
        wd = re.search(r"\b(next\s+)?(" + "|".join(_WEEKDAYS) + r")\b", body, re.IGNORECASE)
        if wd:
            target = _WEEKDAYS[wd.group(2).lower()]
            day = _next_weekday(now.date(), target, force_next_week=bool(wd.group(1)))
            body = body[: wd.start()] + body[wd.end():]

    # --- explicit clock time ---
    tm = _TIME_RE.search(body)
    if tm:
        h, mi, ap = _time_groups(tm)
        if h is not None:
            hour, minute, has_time = h, mi, True
            body = body[: tm.start()] + body[tm.end():]

    if day is None and not has_time:
        return None, False, body.strip()
    if day is None:
        # A time but no day -> today if still ahead, else tomorrow.
        candidate = datetime.combine(now.date(), time(hour, minute), tzinfo=now.tzinfo)
        if candidate <= now:
            candidate = candidate + timedelta(days=1)
        return candidate, has_time, body.strip()

    due = datetime.combine(day, time(hour, minute), tzinfo=now.tzinfo)
    return due, has_time, body.strip()


def _time_groups(m: re.Match):
    """Normalise whichever alternative in _TIME_RE matched to (hour, minute, ampm)."""
    if m.group(1):  # "at 7", "at 7:30 pm"
        h, mi, ap = int(m.group(1)), int(m.group(2) or 0), m.group(3)
    elif m.group(4):  # "7:30pm"
        h, mi, ap = int(m.group(4)), int(m.group(5)), m.group(6)
    elif m.group(7):  # "7pm"
        h, mi, ap = int(m.group(7)), 0, m.group(8)
    else:
        return None, None, None
    ap = (ap or "").lower()
    if ap == "pm" and h < 12:
        h += 12
    elif ap == "am" and h == 12:
        h = 0
    if not (0 <= h <= 23 and 0 <= mi <= 59):
        return None, None, None
    return h, mi, ap


def _next_weekday(from_date: date, target: int, force_next_week: bool) -> date:
    """The next date whose weekday is ``target``. 'next friday' (force_next_week)
    always jumps at least 7 days out; a bare 'friday' picks the nearest upcoming
    one (today counts as already passed)."""
    ahead = (target - from_date.weekday()) % 7
    if ahead == 0:
        ahead = 7  # a bare weekday name never means "today"
    if force_next_week and ahead < 7:
        ahead += 7
    return from_date + timedelta(days=ahead)


def _clean_title(body: str) -> str:
    body = re.sub(r"\s+", " ", body).strip(" \t:,-.")
    # Trim dangling connectors left behind after removing time phrases.
    body = re.sub(r"\b(on|at|for|to)\s*$", "", body, flags=re.IGNORECASE).strip()
    body = re.sub(r"^(on|at|for|to)\s+", "", body, flags=re.IGNORECASE).strip()
    return body[:200]
