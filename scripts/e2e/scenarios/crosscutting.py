"""§3.6 — cross-cutting.

The two that need everything else to have happened first.

S17 is `tests_boundary.py`'s assertion made against a real server after real
accumulation. One check on an empty thread proves very little; the interesting
question is whether A's profile leaks after twenty turns of A behaving
distinctively, which is when there is finally something to leak.

S18 is the regression cover for the blind spot transcription closed. Voice was
not merely unreadable to Bliss before it — it was invisible, because the
context builder skips messages with an empty body, and voice is exactly where
the loaded messages go.
"""

import subprocess
import time

import requests

from .runner import (
    DJANGO,
    Scenario,
    bad_night,
    check,
    leak_offenders,
    shell,
    shell_json,
)

# ── S17 — The boundary under load ───────────────────────────────────────────

S17 = Scenario(
    "S17",
    "The boundary under load",
    note="every tendency saturated on A, then sweep everything B can reach",
)

SPOKEN_SHARP = (
    "I am so sick of this. You never listen to me and I am done "
    "talking about it tonight."
)


def _saturate(couple):
    """Give A every tendency the vocabulary has, through the product.

    Withdrawal and repair come from real sends. Escalation and rephrase-
    acceptance come from the two endpoints that record them. Pursuit is the one
    A must *not* have — the boundary test needs A's profile full, and
    `tendencies_for` drops the weaker of withdraw/pursue when both are present,
    which would quietly leave one fewer thing to leak.
    """
    for index in range(5):
        bad_night(couple, index, weeks_ago=5 - index)

    for _ in range(5):
        couple.send("a", kind="sticker", sticker="repair.sorry")

    # A caution that fires records ESCALATES; taking the suggestion records
    # ACCEPTS_HELP. Both through the endpoints a client actually calls.
    couple.check_draft("a", "you are pathetic and this is typical you")
    for _ in range(5):
        couple.caution_outcome("a", "used_suggestion")

    shell(
        "from apps.personalization import behaviour;"
        f"u={couple.user_expr('a')};"
        "[behaviour.observe(u, behaviour.ESCALATES) for _ in range(5)];"
        "print('ok')"
    )
    return couple.tendencies("a")


def _s17(couple):
    """A's profile is as full as it can get. B must still learn nothing."""
    observed = _saturate(couple)
    check(
        "S17: A's profile is genuinely saturated first",
        len(observed) >= 4,
        f"{observed} — a leak test against an empty profile proves nothing",
    )

    # The guidance derived from A's profile is real and non-empty, so there is
    # something with words in it that could escape.
    guidance = shell_json(
        "import json;"
        "from apps.personalization import boundary;"
        f"print(json.dumps(boundary.phrasing_guidance_for({couple.user_expr('a')}.id)))"
    )
    check(
        "S17: and there is real guidance derived from it",
        len(guidance) >= 4,
        f"{len(guidance)} directives",
    )

    # Now everything B can reach, including the side-effecting ones.
    surfaces = couple.surfaces("b")
    offenders = leak_offenders(couple, "b", surfaces)
    check(
        "S17: no signal name appears on any surface B can read",
        not offenders,
        str(offenders),
    )

    # The guidance sentences themselves, not just the signal keys. A serializer
    # that rendered `guidance_for` into a nudge payload would pass the keyword
    # check and fail this one.
    leaked_guidance = {}
    for name, response in surfaces.items():
        for directive in guidance:
            fragment = directive.split("—")[0].strip()[:40]
            if fragment and fragment in response.text:
                leaked_guidance.setdefault(name, []).append(fragment)
    check(
        "S17: nor does any of the guidance text",
        not leaked_guidance,
        str(leaked_guidance),
    )

    # And the sentences meant for A reading about themselves, which are the
    # most damaging form because they are already written as prose.
    self_description = shell_json(
        "import json;"
        "from apps.personalization import boundary;"
        f"print(json.dumps(boundary.self_description_for({couple.user_expr('a')}.id)))"
    )
    leaked_self = {}
    for name, response in surfaces.items():
        for sentence in self_description:
            fragment = sentence.split(",")[-1].strip().rstrip(".")
            if fragment and fragment in response.text:
                leaked_self.setdefault(name, []).append(fragment)
    check(
        "S17: nor the sentences written for A to read about themselves",
        not leaked_self,
        str(leaked_self),
    )

    # B's own behaviour endpoint returns B's profile, which is nearly empty.
    # There is deliberately no id parameter; assert that guessing one does not
    # turn it into a lookup, because "there is no such parameter" and "the
    # parameter is ignored" are the same thing right up until somebody adds a
    # filter that reads request.query_params.
    a_id = couple.user_id("a")
    for parameter in ("user", "user_id", "id", "partner", "for"):
        probed = requests.get(
            f"{DJANGO}/api/v1/personalization/behaviour",
            params={parameter: a_id},
            headers=couple.headers("b"),
            timeout=30,
        )
        check(
            f"S17: ?{parameter}= does not turn the endpoint into a lookup",
            not leak_offenders(couple, "b", {"probe": probed}),
            probed.text[:90],
        )

    check(
        "S17: and B's own view of themselves is still their own",
        "withdraws_after_conflict" not in couple.tendencies("b"),
        str(couple.tendencies("b")),
    )


S17.body = _s17


# ── S18 — Voice carries ─────────────────────────────────────────────────────

S18 = Scenario(
    "S18",
    "Voice carries",
    note="a spoken message reaches Bliss as text, and is treated like a typed one",
)


def _real_m4a(text: str) -> bytes | None:
    """Actual speech, not a container header with zeros in it.

    The existing `m4a_bytes` fixture is enough to pass the server's sniff and
    nothing else — a transcription model would return nothing from it, so a
    test built on it would prove the upload path and quietly skip the thing
    S18 exists to check. macOS `say` produces a real AAC file; where it is not
    available the scenario says so rather than passing on a fake.
    """
    path = "/tmp/e2e-s18.m4a"
    try:
        subprocess.run(
            ["say", "-o", path, "--data-format=aac", text],
            check=True, capture_output=True, timeout=60,
        )
        with open(path, "rb") as handle:
            return handle.read()
    except Exception:
        return None


def _upload_voice(couple, audio):
    return requests.post(
        f"{couple.base}/media",
        headers=couple.headers("a"),
        files={"file": ("note.m4a", audio, "audio/mp4")},
        data={"kind": "voice", "duration_ms": 6000},
        timeout=120,
    )


def _celery_workers() -> int:
    """How many workers answer a ping. Zero means the queue goes nowhere."""
    try:
        return int(
            shell(
                "from config.celery import app;"
                "print(len(app.control.ping(timeout=3.0) or []))"
            )
        )
    except Exception:
        return 0


def _await_transcript(couple, media_id, timeout=90.0):
    """Poll the meta endpoint the client polls. Returns the transcript or ''."""
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        meta = requests.get(
            f"{DJANGO}/api/v1/chat/media/{media_id}/meta",
            headers=couple.headers("a"),
            timeout=30,
        ).json()
        if meta.get("transcript"):
            return meta["transcript"]
        time.sleep(2.0)
    return ""


def _s18(couple):
    """A sharp *spoken* message must reach the machinery a typed one reaches.

    Two halves, and the second is the one that matters. Getting the text out of
    the audio is only useful if the text then goes where text goes: the context
    Bliss reads, and the sharpness check the repair nudge is gated on. Before
    transcription the harshest thing anyone said in the relationship could be
    the one thing every coaching mechanism in the product could not see.
    """
    # Transcription is queued, not inline, so a dead worker looks exactly like
    # a working system with quiet audio: the note uploads, plays, and is simply
    # never readable by Bliss. Say so plainly rather than letting the transcript
    # assertion time out and read as a model failure.
    #
    # Worth its own check because this is not hypothetical. The worker on this
    # branch crashed on boot — `apps/insights/tasks.py` imported a model that
    # had been renamed — so every background task in the product was silently
    # doing nothing, and nothing anywhere said so.
    workers = _celery_workers()
    check(
        "S18: a celery worker is alive to run the transcription",
        workers > 0,
        "no workers answered — background tasks are not running at all"
        if not workers
        else f"{workers} answering",
    )
    if not workers:
        return

    couple.send("a", "can we talk about last night")
    couple.send("b", "not now")

    audio = _real_m4a(SPOKEN_SHARP)
    if audio is None:
        check(
            "S18: a real audio fixture is available",
            False,
            "`say` is unavailable — refusing to run this on a synthetic header",
        )
        return

    # One retry on a 5xx. The upload goes through a real vendor, and a
    # transient there is a fact about the afternoon rather than about the
    # code — a suite that goes red on it teaches people to rerun it without
    # reading it. A 4xx is never retried: that would be the server saying no.
    upload = _upload_voice(couple, audio)
    if upload.status_code >= 500:
        time.sleep(3.0)
        upload = _upload_voice(couple, audio)
    check(
        "S18: the voice note uploads",
        upload.status_code == 201,
        f"{upload.status_code} {upload.text[:70]}",
    )
    if upload.status_code != 201:
        return
    media = upload.json()

    sent = couple.send("a", kind="voice", media=media["id"])
    check("S18: and sends as a message", bool(sent.get("id")), str(sent)[:90])

    transcript = _await_transcript(couple, media["id"])
    check(
        "S18: it transcribes",
        bool(transcript),
        transcript[:90] or "no transcript after 90s",
    )
    if not transcript:
        return

    # Assert properties, not the words. Speech recognition is not stable enough
    # to pin, and it does not need to be: what matters is that the sharp part
    # survived, because the sharp part is what every downstream mechanism reads.
    lowered = transcript.lower()
    check(
        "S18: and the sharp content survives the trip",
        "never listen" in lowered or "sick of" in lowered or "done talking" in lowered,
        transcript[:90],
    )

    # The half that was actually broken. `_thread_context` builds Bliss's whole
    # view out of message bodies and skips empty ones; a voice note's text
    # lives on its media row.
    context = shell(
        "from apps.chat import assist;"
        "from apps.relationships.models import Relationship;"
        f"c=assist._thread_context(Relationship.objects.get(id='{couple.rel}'));"
        "print(repr(c))"
    )
    check(
        "S18: the transcript appears in the context Bliss reads",
        any(word in context.lower() for word in ("never listen", "sick of", "done talking")),
        context[-120:],
    )

    # And it reaches the nudge machinery, which gates the repair opening on a
    # keyword scan of message *bodies*. A spoken "I'm done talking about it"
    # has to count as the sharp exchange a typed one would.
    sharp = shell(
        "from apps.chat import assist;"
        "from apps.relationships.models import Relationship;"
        f"print(assist._had_sharp_exchange(Relationship.objects.get(id='{couple.rel}')))"
    )
    check(
        "S18: a sharp spoken message counts as a sharp exchange",
        sharp == "True",
        f"_had_sharp_exchange={sharp}",
    )

    offered = couple.nudge("b")
    check(
        "S18: so the repair nudge fires on a spoken rupture",
        (offered or {}).get("kind") == "repair",
        f"got {(offered or {}).get('kind') or 'none'}",
    )


S18.body = _s18


SCENARIOS = [S17, S18]
