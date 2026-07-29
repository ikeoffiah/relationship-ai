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
import subprocess
import sys
import time
import uuid

import requests
import websockets

# Repo root, resolved from this file so the script is not tied to one machine.
REPO = str(pathlib.Path(__file__).resolve().parents[2])
DJANGO = "http://localhost:8000"
WS = "ws://localhost:8001"

results = []
latencies = {}


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{'  — ' + detail if detail else ''}")
    return ok


def register(email):
    body = {
        "email": email,
        "password": "Sup3rSecret!pw",
        "password_confirm": "Sup3rSecret!pw",
        "first_name": email.split("@")[0],
    }
    r = requests.post(f"{DJANGO}/api/v1/auth/register/", json=body, timeout=20)
    if r.status_code not in (200, 201):
        r = requests.post(
            f"{DJANGO}/api/v1/auth/login/",
            json={"email": email, "password": body["password"]},
            timeout=20,
        )
    data = r.json()
    token = data.get("access") or data.get("access_token") or (data.get("tokens") or {}).get("access")
    assert token, f"no token in {data}"
    return token


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def ms(t0):
    return f"{(time.perf_counter() - t0) * 1000:.0f}ms"


async def wait_for(sink, predicate, timeout=5.0):
    """Block until a matching event lands, and report how long it took.

    Polling for an event beats sleeping a fixed interval and then looking: a
    sleep floors every measurement at the sleep length, which would have made
    a 20ms round trip read as 600ms in this script's own output.
    """
    t0 = time.perf_counter()
    deadline = t0 + timeout
    while time.perf_counter() < deadline:
        for event in sink:
            if predicate(event):
                return event, (time.perf_counter() - t0) * 1000
        await asyncio.sleep(0.005)
    return None, (time.perf_counter() - t0) * 1000


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
    rel = subprocess.run(
        [
            "docker", "compose", "exec", "-T", "django",
            "python", "manage.py", "shell", "-c",
            "from django.contrib.auth import get_user_model;"
            "from apps.relationships.models import Relationship;"
            "U=get_user_model();"
            f"a=U.objects.get(email='e2e-a-{stamp}@test.local');"
            f"b=U.objects.get(email='e2e-b-{stamp}@test.local');"
            "r=Relationship.objects.create(partner_a=a,partner_b=b,status='active');"
            "print(r.id)",
        ],
        capture_output=True, text=True, cwd=REPO,
    ).stdout.strip().splitlines()[-1]
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

failed = [n for n, ok, _ in results if not ok]
if latencies:
    print("\n== latency (real, not floored by a sleep) ==")
    for name, value in latencies.items():
        print(f"  {name:<18} {value:6.0f}ms")

print(f"\n{len(results) - len(failed)}/{len(results)} passed")
if failed:
    print("failed: " + "; ".join(failed))
sys.exit(1 if failed else 0)
