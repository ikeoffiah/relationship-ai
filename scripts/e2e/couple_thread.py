"""End-to-end exercise of the couple thread against the running stack.

Not a unit test. This drives real HTTP against Django on :8000 and a real
WebSocket against FastAPI on :8001, with two separate authenticated users, to
check the things unit tests structurally cannot: that the receipt written by
one process reaches the other one's socket, that presence survives the trip
through Redis, and how long any of it takes.

Every assertion prints PASS/FAIL and the script exits non-zero if any failed,
so it is usable as a smoke check rather than something to read carefully.

    docker compose up -d
    backend-django/venv/bin/python scripts/e2e/couple_thread.py

It has already earned its keep twice. It found that Django and FastAPI were
signing and verifying JWTs with different SECRET_KEYs, so every couple-thread
socket was rejected with a bare 403 that looked like a permissions problem; and
it found a varchar(10) column rejecting an 11-character value, which the unit
suite missed because it runs on SQLite and SQLite ignores varchar limits.
Neither is reachable from a unit test, because both live in the gap between two
processes.
"""

import asyncio
import json
import pathlib
import sys
import time
import uuid

import requests
import websockets

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

# The plumbing this shares with the scenario suite: making users, keeping
# score, and reaching into the container for the setup a public API correctly
# refuses to provide. Two copies of "did this pass" would drift.
from harness import (  # noqa: E402
    DJANGO,
    REPO,
    WS,
    auth,
    check,
    has_exif,
    jpeg_with_gps,
    latencies,
    m4a_bytes,
    ms,
    pair,
    register,
    report,
    shell,
    wait_for,
)

_ = REPO  # re-exported for anyone importing this module rather than running it


async def run():
    stamp = uuid.uuid4().hex[:8]
    print("\n== setup ==")
    a_token = register(f"e2e-a-{stamp}@test.local")
    b_token = register(f"e2e-b-{stamp}@test.local")
    check("two users registered", True)

    # Pair them directly. The invite flow only ever emails the raw token —
    # correctly, since a token returned in an API response would be a token an
    # attacker could enumerate — so pairing is done as setup rather than as
    # part of what is under test here.
    rel = pair(f"e2e-a-{stamp}@test.local", f"e2e-b-{stamp}@test.local")
    check("relationship formed", bool(rel), rel)

    base = f"{DJANGO}/api/v1/chat/{rel}"

    # ---- sockets -------------------------------------------------------
    print("\n== presence ==")
    a_events, b_events = [], []

    async def pump(sock, sink):
        try:
            async for frame in sock:
                sink.append(json.loads(frame))
        except Exception:
            pass

    a_ws = await websockets.connect(f"{WS}/ws/couple/{rel}?token={a_token}")
    a_task = asyncio.create_task(pump(a_ws, a_events))
    await asyncio.sleep(0.4)

    ready = [e for e in a_events if e.get("type") == "thread_ready"]
    check(
        "A gets thread_ready with partner_online=false",
        bool(ready) and ready[0].get("partner_online") is False,
        json.dumps(ready[0]) if ready else "no thread_ready",
    )

    t0 = time.perf_counter()
    b_ws = await websockets.connect(f"{WS}/ws/couple/{rel}?token={b_token}")
    b_task = asyncio.create_task(pump(b_ws, b_events))
    event, took = await wait_for(
        a_events, lambda e: e.get("type") == "presence" and e.get("online")
    )
    check("A is told B came online", event is not None, f"{took:.0f}ms")
    latencies["presence online"] = took
    b_ready = [e for e in b_events if e.get("type") == "thread_ready"]
    check(
        "B's thread_ready reports A already online",
        bool(b_ready) and b_ready[0].get("partner_online") is True,
        json.dumps(b_ready[0]) if b_ready else "none",
    )

    # ---- send + ticks --------------------------------------------------
    print("\n== delivery receipts ==")
    b_events.clear()
    t0 = time.perf_counter()
    r = requests.post(
        f"{base}/messages/send",
        headers=auth(a_token),
        json={"body": "are we still on for tomorrow?", "client_id": uuid.uuid4().hex},
        timeout=20,
    )
    send_ms = ms(t0)
    msg = r.json()
    check("A's send returns status=sent", msg.get("status") == "sent", f"{send_ms}, got {msg.get('status')}")

    pushed_event, took = await wait_for(
        b_events, lambda e: e.get("type") == "couple_message"
    )
    check("B's socket receives the message", pushed_event is not None, f"{took:.0f}ms")
    latencies["message fanout"] = took
    pushed = [e for e in b_events if e.get("type") == "couple_message"]
    check(
        "the pushed copy carries no tick state",
        bool(pushed) and pushed[0]["message"].get("status") is None,
        "status must belong to the sender only",
    )

    a_events.clear()
    t0 = time.perf_counter()
    requests.post(f"{base}/delivered", headers=auth(b_token), timeout=20)
    receipt_event, took = await wait_for(
        a_events, lambda e: e.get("type") == "couple_receipt"
    )
    check("A's socket receives the delivery receipt", receipt_event is not None, f"{took:.0f}ms")
    latencies["receipt fanout"] = took
    receipts = [e for e in a_events if e.get("type") == "couple_receipt"]
    check(
        "the receipt reports delivered but not read",
        bool(receipts)
        and receipts[0].get("last_delivered_at")
        and receipts[0].get("last_read_at") is None,
        json.dumps(receipts[0]) if receipts else "",
    )

    def status_of(mid, token):
        page = requests.get(f"{base}/messages", headers=auth(token), timeout=20).json()
        for row in page["results"]:
            if row["id"] == mid:
                return row["status"]
        return "<missing>"

    check("A now sees delivered", status_of(msg["id"], a_token) == "delivered")
    check(
        "B sees no status on A's message",
        status_of(msg["id"], b_token) is None,
        "ticks are the sender's, not the recipient's",
    )
    check(
        "delivery did not clear B's unread count",
        requests.get(f"{base}/unread", headers=auth(b_token), timeout=20).json()["unread"] == 1,
        "receiving is not reading",
    )

    a_events.clear()
    requests.post(f"{base}/read", headers=auth(b_token), timeout=20)
    await wait_for(a_events, lambda e: e.get("type") == "couple_receipt")
    check("A now sees seen", status_of(msg["id"], a_token) == "seen")
    check(
        "B's unread is cleared by reading",
        requests.get(f"{base}/unread", headers=auth(b_token), timeout=20).json()["unread"] == 0,
    )

    # A message sent after they read must not inherit the blue tick.
    later = requests.post(
        f"{base}/messages/send",
        headers=auth(a_token),
        json={"body": "one more thing", "client_id": uuid.uuid4().hex},
        timeout=20,
    ).json()
    check("a message sent after they read stays on one tick", status_of(later["id"], a_token) == "sent")

    # ---- stickers ------------------------------------------------------
    print("\n== stickers ==")
    b_events.clear()
    sticker = requests.post(
        f"{base}/messages/send",
        headers=auth(a_token),
        json={"kind": "sticker", "sticker": "repair.sorry", "client_id": uuid.uuid4().hex},
        timeout=20,
    ).json()
    check("a sticker persists as kind=sticker", sticker.get("kind") == "sticker" and sticker.get("sticker") == "repair.sorry")
    await wait_for(
        b_events,
        lambda e: e.get("type") == "couple_message"
        and e["message"].get("sticker") == "repair.sorry",
    )
    check(
        "the sticker reaches B's socket intact",
        any(
            e.get("type") == "couple_message" and e["message"].get("sticker") == "repair.sorry"
            for e in b_events
        ),
    )

    # ---- @bliss --------------------------------------------------------
    print("\n== @bliss in the thread ==")
    b_events.clear()
    interp = requests.post(
        f"{DJANGO}/api/v1/engagement/bliss/interpret",
        headers=auth(a_token),
        json={"text": "@bliss remind us to call the venue tomorrow at 5pm"},
        timeout=20,
    ).json()
    draft = interp.get("draft") or interp
    check("the tag parses to a draft", bool(draft.get("title")), json.dumps(draft)[:160])

    created = requests.post(
        f"{DJANGO}/api/v1/engagement/bliss/items",
        headers=auth(a_token),
        json={
            "kind": draft.get("kind", "reminder"),
            "title": draft.get("title", "call the venue"),
            "due_at": draft.get("due_at"),
            "source": "couple_chat",
        },
        timeout=20,
    )
    check("the item is created", created.status_code == 201, str(created.status_code))

    page = requests.get(f"{base}/messages", headers=auth(b_token), timeout=20).json()
    system = [m for m in page["results"] if m["kind"] == "system"]
    check("a system line appears in the thread", bool(system), system[0]["body"] if system else "none")
    check(
        "the system line is authored by nobody",
        bool(system) and system[0]["sender_id"] is None,
    )
    await wait_for(
        b_events,
        lambda e: e.get("type") == "couple_message"
        and e["message"].get("kind") == "system",
    )
    check(
        "the system line is pushed live to B",
        any(
            e.get("type") == "couple_message" and e["message"].get("kind") == "system"
            for e in b_events
        ),
    )

    # An item from anywhere else must stay out of the shared thread.
    before = len([m for m in page["results"] if m["kind"] == "system"])
    requests.post(
        f"{DJANGO}/api/v1/engagement/bliss/items",
        headers=auth(a_token),
        json={"kind": "reminder", "title": "private thing", "source": "bliss"},
        timeout=20,
    )
    page2 = requests.get(f"{base}/messages", headers=auth(b_token), timeout=20).json()
    after = len([m for m in page2["results"] if m["kind"] == "system"])
    check(
        "an item raised elsewhere does NOT post to the thread",
        after == before,
        "otherwise a private counseling session leaks to the partner",
    )

    # ---- calendar invites -----------------------------------------------
    print("\n== calendar invites ==")
    from_ = "2026-01-01T00:00:00+00:00"
    to_ = "2030-01-01T00:00:00+00:00"
    cal = f"{DJANGO}/api/v1/engagement/bliss"

    invited = requests.post(
        f"{cal}/items",
        headers=auth(a_token),
        json={
            "kind": "event",
            "title": "dinner out",
            "due_at": "2026-09-04T19:30:00+00:00",
            "invite_partner": True,
        },
        timeout=20,
    ).json()
    check("tagging the partner leaves it pending", invited.get("partner_invite") == "pending")

    def cal_items(token):
        return requests.get(
            f"{cal}/calendar", headers=auth(token), params={"from": from_, "to": to_}, timeout=20
        ).json()

    mine = cal_items(a_token)
    theirs = cal_items(b_token)
    row_a = next((r for r in mine["items"] if r["id"] == invited["id"]), None)
    row_b = next((r for r in theirs["items"] if r["id"] == invited["id"]), None)
    check("it appears on both calendars", row_a is not None and row_b is not None)
    check(
        "only the person asked is prompted to answer",
        row_a is not None and row_b is not None
        and row_a["awaiting_my_answer"] is False
        and row_b["awaiting_my_answer"] is True,
    )
    check("the calendar groups by day", bool(mine.get("days")))

    same = requests.post(
        f"{cal}/items/{invited['id']}/respond", headers=auth(a_token),
        json={"accept": True}, timeout=20,
    )
    check(
        "the asker cannot accept on their partner's behalf",
        same.status_code == 403,
        f"got {same.status_code}",
    )

    answered = requests.post(
        f"{cal}/items/{invited['id']}/respond", headers=auth(b_token),
        json={"accept": True}, timeout=20,
    ).json()
    check("the partner can accept", answered.get("partner_invite") == "accepted")

    declined = requests.post(
        f"{cal}/items/{invited['id']}/respond", headers=auth(b_token),
        json={"accept": False}, timeout=20,
    ).json()
    check("an answer can be changed", declined.get("partner_invite") == "declined")

    # ---- media ---------------------------------------------------------
    # The whole point of doing this here rather than in a unit test: the unit
    # suite runs against an in-memory storage backend with mocked HTTP, so it
    # proves the logic and nothing about whether a photo actually survives the
    # round trip through encryption, a real vendor, and back out of the proxy.
    print("\n== photos ==")

    photo = jpeg_with_gps()
    t0 = time.perf_counter()
    up = requests.post(
        f"{base}/media",
        headers=auth(a_token),
        files={"file": ("photo.jpg", photo, "image/jpeg")},
        data={"kind": "image"},
        timeout=60,
    )
    check("A uploads a photo", up.status_code == 201, f"{up.status_code} in {ms(t0)}")
    latencies["photo upload"] = (time.perf_counter() - t0) * 1000
    media = up.json() if up.status_code == 201 else {}
    check("the upload reports its dimensions", bool(media.get("width")), str(media.get("width")))

    # Round trip through storage. If Cloudinary is configured this really did
    # leave the building, get encrypted, and come back.
    t0 = time.perf_counter()
    blob = requests.get(f"{DJANGO}{media.get('url', '')}", headers=auth(b_token), timeout=60)
    check(
        "B can read the photo A sent",
        blob.status_code == 200 and blob.content.startswith(b"\xff\xd8\xff"),
        f"{blob.status_code}, {len(blob.content)}B in {ms(t0)}",
    )
    latencies["photo download"] = (time.perf_counter() - t0) * 1000

    check(
        "the decrypted photo is never cacheable",
        blob.headers.get("Cache-Control") == "private, no-store",
        blob.headers.get("Cache-Control", "missing"),
    )
    check("GPS did not survive the upload", not has_exif(blob.content))

    thumb = requests.get(f"{DJANGO}{media.get('thumb_url', '')}", headers=auth(b_token), timeout=60)
    check(
        "the thumbnail is smaller than the photo",
        thumb.status_code == 200 and 0 < len(thumb.content) < len(blob.content),
        f"{len(thumb.content)}B vs {len(blob.content)}B",
    )

    stranger = register(f"e2e-x-{stamp}@test.local")
    denied = requests.get(f"{DJANGO}{media.get('url', '')}", headers=auth(stranger), timeout=20)
    check(
        "a stranger cannot read the photo",
        denied.status_code == 404,
        f"got {denied.status_code}",
    )

    anon = requests.get(f"{DJANGO}{media.get('url', '')}", timeout=20)
    check(
        "an unauthenticated request cannot read it either",
        anon.status_code in (401, 403),
        f"got {anon.status_code}",
    )

    b_events.clear()
    sent = requests.post(
        f"{base}/messages/send",
        headers=auth(a_token),
        json={"kind": "image", "media": media.get("id"), "body": "us, last summer",
              "client_id": f"photo-{stamp}"},
        timeout=20,
    )
    check("the photo sends as a message", sent.status_code == 201, str(sent.status_code))
    photo_message = sent.json() if sent.status_code == 201 else {}
    check("the caption rides along", photo_message.get("body") == "us, last summer")

    event, took = await wait_for(
        b_events,
        lambda e: e.get("type") == "couple_message"
        and (e.get("message") or {}).get("kind") == "image",
    )
    check("the photo reaches B's socket", event is not None, f"{took:.0f}ms")
    latencies["photo delivery"] = took

    reused = requests.post(
        f"{base}/messages/send",
        headers=auth(a_token),
        json={"kind": "image", "media": media.get("id"), "client_id": f"photo-2-{stamp}"},
        timeout=20,
    )
    check(
        "the same upload cannot be sent twice",
        reused.status_code == 400,
        f"got {reused.status_code}",
    )

    quote = requests.post(
        f"{base}/messages/send",
        headers=auth(b_token),
        json={"body": "I love that one", "reply_to": photo_message.get("id"),
              "client_id": f"quote-{stamp}"},
        timeout=20,
    ).json()
    check(
        "a reply quoting a photo carries its thumbnail",
        bool((quote.get("reply_to") or {}).get("thumb_url")),
    )

    print("\n== voice notes ==")
    voice_up = requests.post(
        f"{base}/media",
        headers=auth(b_token),
        files={"file": ("note.m4a", m4a_bytes(), "audio/mp4")},
        data={"kind": "voice", "duration_ms": 4200, "waveform": json.dumps([10, 60, 90, 40])},
        timeout=60,
    )
    check("B uploads a voice note", voice_up.status_code == 201, str(voice_up.status_code))
    voice = voice_up.json() if voice_up.status_code == 201 else {}
    check("its duration survives", voice.get("duration_ms") == 4200)
    check("its waveform survives", voice.get("waveform") == [10, 60, 90, 40])
    check("a voice note has no thumbnail", voice.get("thumb_url") is None)

    voice_sent = requests.post(
        f"{base}/messages/send",
        headers=auth(b_token),
        json={"kind": "voice", "media": voice.get("id"), "client_id": f"voice-{stamp}"},
        timeout=20,
    )
    check("the voice note sends", voice_sent.status_code == 201, str(voice_sent.status_code))

    audio = requests.get(f"{DJANGO}{voice.get('url', '')}", headers=auth(a_token), timeout=60)
    check(
        "A can play what B recorded",
        audio.status_code == 200 and audio.content[4:8] == b"ftyp",
        f"{audio.status_code}, {len(audio.content)}B",
    )

    mismatched = requests.post(
        f"{base}/media",
        headers=auth(a_token),
        files={"file": ("fake.jpg", b"MZ\x90\x00 not a photo at all", "image/jpeg")},
        data={"kind": "image"},
        timeout=30,
    )
    check(
        "a file that is not what it claims is refused",
        mismatched.status_code == 400,
        f"got {mismatched.status_code}",
    )

    print("\n== deletion reaches the bytes ==")
    gone = requests.delete(
        f"{DJANGO}/api/v1/chat/messages/{photo_message.get('id')}",
        headers=auth(a_token), timeout=30,
    )
    check("A deletes the photo message", gone.status_code == 200, str(gone.status_code))
    check("the message no longer carries media", (gone.json() or {}).get("media") is None)

    after = requests.get(f"{DJANGO}{media.get('url', '')}", headers=auth(b_token), timeout=30)
    check(
        "the photo is unreadable after deletion",
        after.status_code == 404,
        f"got {after.status_code}",
    )

    # ---- the outcome loop ----------------------------------------------
    # The part unit tests structurally cannot check: that feedback given
    # through one endpoint changes what a different endpoint decides to offer,
    # across two processes and a real database.
    print("\n== the outcome loop ==")

    caution = requests.post(
        f"{base}/assist/caution-outcome",
        headers=auth(a_token),
        json={"choice": "sent_anyway"},
        timeout=20,
    )
    check("a caution outcome is recorded", caution.status_code == 200, str(caution.status_code))

    bad = requests.post(
        f"{base}/assist/caution-outcome",
        headers=auth(a_token),
        json={"choice": "shrugged"},
        timeout=20,
    )
    check("an unknown choice is refused", bad.status_code == 400, f"got {bad.status_code}")

    stranger_loop = requests.post(
        f"{DJANGO}/api/v1/chat/{rel}/assist/caution-outcome",
        headers=auth(stranger),
        json={"choice": "sent_anyway"},
        timeout=20,
    )
    check(
        "a stranger cannot report into this couple's loop",
        stranger_loop.status_code == 404,
        f"got {stranger_loop.status_code}",
    )

    # Four dismissals of the same kind at the same hour, then the policy should
    # hold that kind back. Driven through the real feedback endpoint.
    made = shell(
        "import json;"
        "from django.contrib.auth import get_user_model;"
        "from apps.chat.models import AssistNudge;"
        "from apps.relationships.models import Relationship;"
        "U=get_user_model();"
        f"a=U.objects.get(email='e2e-a-{stamp}@test.local');"
        f"r=Relationship.objects.get(id='{rel}');"
        "print(json.dumps([str(AssistNudge.objects.create("
        "relationship=r,user=a,kind='night',suggestion='say goodnight').id)"
        " for _ in range(4)]))"
    )
    nudge_ids = json.loads(made)
    check("four nudges staged", len(nudge_ids) == 4)

    for nudge_id in nudge_ids:
        requests.post(
            f"{DJANGO}/api/v1/chat/assist/nudges/{nudge_id}/feedback",
            headers=auth(a_token),
            json={"action": "dismissed"},
            timeout=20,
        )

    suppressed = shell(
        "from apps.personalization import outcomes;"
        f"print(outcomes.suppressed('{rel}', 'nudge_night', "
        "{'hour': __import__('django.utils.timezone', fromlist=['x'])"
        ".localtime().hour}))"
    )
    check(
        "four dismissals suppress that nudge",
        suppressed == "True",
        f"suppressed={suppressed}",
    )

    other = shell(
        "from apps.personalization import outcomes;"
        f"print(outcomes.suppressed('{rel}', 'nudge_repair', {{'hour': 23}}))"
    )
    check(
        "it does not suppress a different kind",
        other == "False",
        f"suppressed={other}",
    )

    # ---- the partner boundary -------------------------------------------
    print("\n== the partner boundary ==")

    shell(
        "from django.contrib.auth import get_user_model;"
        "from apps.personalization import behaviour;"
        "U=get_user_model();"
        f"a=U.objects.get(email='e2e-a-{stamp}@test.local');"
        "[behaviour.observe(a, s) for s in behaviour.SIGNALS for _ in range(6)];"
        "print('ok')"
    )

    own = requests.get(
        f"{DJANGO}/api/v1/personalization/behaviour", headers=auth(a_token), timeout=20
    )
    check(
        "A can read their own tendencies",
        own.status_code == 200 and bool(own.json()),
        str(own.status_code),
    )

    # Everything B can reach, checked for A's profile vocabulary. The unit
    # suite asserts this against the view layer; this asserts it against the
    # running server, with a profile that was populated through the real code.
    vocabulary = [
        "withdraws_after_conflict", "pursues_when_unanswered",
        "escalates_under_stress", "reaches_for_repair", "accepts_rephrasing",
    ]
    surfaces = {
        "the thread": requests.get(f"{base}/messages", headers=auth(b_token), timeout=20),
        "the nudge endpoint": requests.get(
            f"{base}/assist/nudge", headers=auth(b_token), timeout=20
        ),
        "assist settings": requests.get(
            f"{base}/assist/settings", headers=auth(b_token), timeout=20
        ),
        "the connection score": requests.get(
            f"{DJANGO}/api/v1/personalization/connection", headers=auth(b_token), timeout=20
        ),
    }
    leaked = {
        name: [word for word in vocabulary if word in response.text]
        for name, response in surfaces.items()
    }
    offenders = {name: words for name, words in leaked.items() if words}
    check(
        "B's surfaces say nothing about A's profile",
        not offenders,
        json.dumps(offenders) if offenders else "clean",
    )

    peek = requests.get(
        f"{DJANGO}/api/v1/personalization/behaviour", headers=auth(b_token), timeout=20
    )
    check(
        "there is no way to ask for a partner's tendencies",
        "withdraws_after_conflict" not in peek.text,
        "B's own profile is empty, and there is no id parameter to change that",
    )

    # ---- the connection score -------------------------------------------
    print("\n== the connection score ==")

    score_a = requests.get(
        f"{DJANGO}/api/v1/personalization/connection", headers=auth(a_token), timeout=20
    ).json()
    _ = score_a
    score_b = requests.get(
        f"{DJANGO}/api/v1/personalization/connection", headers=auth(b_token), timeout=20
    ).json()
    check(
        "both partners see the same number",
        score_a == score_b,
        f"{score_a.get('score')} vs {score_b.get('score')}",
    )
    check(
        "a brand new couple is shown nothing rather than a zero",
        score_a.get("score") is None and score_a.get("emphasis") == "hidden",
        json.dumps(score_a),
    )

    for token in (a_token, b_token):
        requests.post(
            f"{DJANGO}/api/v1/engagement/check-in",
            headers=auth(token),
            json={"connection_score": 4, "mood": "good"},
            timeout=20,
        )
        requests.post(
            f"{DJANGO}/api/v1/engagement/gratitude",
            headers=auth(token),
            json={"text": "thank you for yesterday"},
            timeout=20,
        )

    computed = shell(
        "from apps.personalization.tasks import refresh_connection_scores;"
        "refresh_connection_scores();"
        "from apps.personalization import connection;"
        f"print(connection.presentation('{rel}')['score'])"
    )
    check(
        "the nightly job runs and produces a score for an active couple",
        computed not in ("", "None"),
        f"score={computed}",
    )

    # ---- presence teardown ---------------------------------------------
    print("\n== presence teardown ==")
    a_events.clear()
    t0 = time.perf_counter()
    await b_ws.close()
    event, took = await wait_for(
        a_events, lambda e: e.get("type") == "presence" and e.get("online") is False
    )
    check("A is told B went offline", event is not None, f"{took:.0f}ms")
    latencies["presence offline"] = took

    await a_ws.close()
    for task in (a_task, b_task):
        task.cancel()


asyncio.run(run())

sys.exit(report())
