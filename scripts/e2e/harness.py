"""Shared plumbing for the end-to-end scripts.

Extracted from ``couple_thread.py`` when the scenario suite arrived and needed
the same three things: make a user, authenticate as them, and record a
PASS/FAIL. Copying them would have meant two definitions of "did this pass"
drifting apart, which is the sort of thing that makes a suite quietly stop
meaning anything.

Nothing here knows what is being tested. It knows how to talk to a running
stack, how to reach into the database for the setup a public API deliberately
does not expose (pairing, back-dating), and how to keep score.
"""

import functools
import io
import json
import pathlib
import subprocess
import time
import uuid

import requests

DJANGO = "http://localhost:8000"
WS = "ws://localhost:8001"

PASSWORD = "Sup3rSecret!pw"

# The compose project these scripts drive. Fixed rather than derived from the
# directory name so the scripts work from a git worktree, where the directory
# is named after the branch and compose would otherwise invent a second, empty
# stack on conflicting ports.
COMPOSE_PROJECT = "relationshipai"


@functools.lru_cache(maxsize=1)
def repo_root() -> str:
    """The checkout these scripts belong to, worktree or not.

    ``docker compose`` is run from here, so the container mounts the same
    source tree the scripts were read from. Resolved from this file rather
    than from the cwd, so the scripts run from anywhere.
    """
    return str(pathlib.Path(__file__).resolve().parents[2])


# Kept as a plain name because couple_thread.py already used it.
REPO = repo_root()


# ── keeping score ───────────────────────────────────────────────────────────

results = []
latencies = {}


def check(name, ok, detail=""):
    """Record one assertion and print it. Returns ``ok`` so it can be chained."""
    results.append((name, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{'  — ' + detail if detail else ''}")
    return ok


def failures():
    return [name for name, ok, _ in results if not ok]


def report(title="passed"):
    """Print the tally. Returns the process exit code."""
    failed = failures()
    if latencies:
        print("\n== latency (real, not floored by a sleep) ==")
        for name, value in latencies.items():
            print(f"  {name:<18} {value:6.0f}ms")

    print(f"\n{len(results) - len(failed)}/{len(results)} {title}")
    if failed:
        print("failed: " + "; ".join(failed))
    return 1 if failed else 0


# ── users ───────────────────────────────────────────────────────────────────


def register(email, password=PASSWORD):
    """Make a user and return an access token, or log in if they exist."""
    body = {
        "email": email,
        "password": password,
        "password_confirm": password,
        "first_name": email.split("@")[0],
    }
    r = requests.post(f"{DJANGO}/api/v1/auth/register/", json=body, timeout=20)
    if r.status_code not in (200, 201):
        r = requests.post(
            f"{DJANGO}/api/v1/auth/login/",
            json={"email": email, "password": password},
            timeout=20,
        )
    data = r.json()
    token = data.get("access") or data.get("access_token") or (data.get("tokens") or {}).get("access")
    assert token, f"no token in {data}"
    return token


def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ── reaching into the box ───────────────────────────────────────────────────


def shell(code: str) -> str:
    """Run one line of Django shell in the container, return its last line.

    Used for the setup a public API correctly refuses to provide: pairing two
    users without an emailed invite token, back-dating rows to simulate the
    passage of time, and reading internal state that no endpoint exposes
    because no endpoint should.

    Returns the *last* line so a caller can ``print`` its answer without
    fighting whatever warnings Django decided to emit first.
    """
    done = subprocess.run(
        [
            "docker", "compose", "-p", COMPOSE_PROJECT, "exec", "-T", "django",
            "python", "manage.py", "shell", "-c", code,
        ],
        capture_output=True, text=True, cwd=repo_root(),
    )
    lines = done.stdout.strip().splitlines()
    if not lines:
        raise RuntimeError(
            f"shell produced nothing.\nstdout: {done.stdout}\nstderr: {done.stderr[-2000:]}"
        )
    return lines[-1].strip()


def shell_json(code: str):
    return json.loads(shell(code))


def pair(email_a: str, email_b: str) -> str:
    """Put two registered users in an active relationship. Returns its id.

    Pairing is setup rather than something under test here: the invite flow
    only ever emails the raw token — correctly, since a token returned in an
    API response would be a token an attacker could enumerate.
    """
    return shell(
        "from django.contrib.auth import get_user_model;"
        "from apps.relationships.models import Relationship;"
        "U=get_user_model();"
        f"a=U.objects.get(email='{email_a}');"
        f"b=U.objects.get(email='{email_b}');"
        "r=Relationship.objects.create(partner_a=a,partner_b=b,status='active');"
        "print(r.id)"
    )


# ── fixtures ────────────────────────────────────────────────────────────────


def jpeg_with_gps() -> bytes:
    """A photo carrying GPS, as a phone camera produces one.

    The fixture matters: uploading a clean JPEG would prove nothing about the
    metadata strip, and a shared album quietly becoming a location history is
    the likeliest real harm in the whole feature.
    """
    from PIL import Image

    image = Image.new("RGB", (2400, 1800), (180, 90, 70))
    exif = image.getexif()
    exif[0x010F] = "TestPhone"  # Make
    gps = exif.get_ifd(0x8825)
    gps[1], gps[2] = "N", (51.0, 30.0, 0.0)
    gps[3], gps[4] = "W", (0.0, 7.0, 0.0)

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", exif=exif, quality=95)
    return buffer.getvalue()


def has_exif(blob: bytes) -> bool:
    from PIL import Image

    try:
        return bool(Image.open(io.BytesIO(blob)).getexif())
    except Exception:
        return False


def m4a_bytes(payload=4096) -> bytes:
    """Enough of an MP4 container header to pass the server's sniff."""
    return b"\x00\x00\x00\x20ftypM4A " + b"\x00" * payload


# ── timing ──────────────────────────────────────────────────────────────────


def ms(t0):
    return f"{(time.perf_counter() - t0) * 1000:.0f}ms"


async def wait_for(sink, predicate, timeout=5.0):
    """Block until a matching event lands, and report how long it took.

    Polling for an event beats sleeping a fixed interval and then looking: a
    sleep floors every measurement at the sleep length, which would have made
    a 20ms round trip read as 600ms in this script's own output.
    """
    import asyncio

    t0 = time.perf_counter()
    deadline = t0 + timeout
    while time.perf_counter() < deadline:
        for event in sink:
            if predicate(event):
                return event, (time.perf_counter() - t0) * 1000
        await asyncio.sleep(0.005)
    return None, (time.perf_counter() - t0) * 1000


def stamp() -> str:
    return uuid.uuid4().hex[:8]
