#!/usr/bin/env python3
"""Release smoke suite — the short, deterministic set that must pass before any
release, run against a running stack.

    make -f /dev/null   # (no make target yet)
    python3 tests/production/smoke.py
    python3 tests/production/smoke.py --no-llm       # skip the paid OpenAI turn
    python3 tests/production/smoke.py --json         # machine-readable summary

Design rules, because a smoke suite that drifts stops meaning anything:

* **Fast and deterministic.** Target is under 60s. Nothing here sleeps waiting
  for a beat job, and nothing asserts on model wording — only on the shape and
  the guarantees.
* **Stdlib only.** It has to run from a bare shell on a deploy box, not from a
  configured virtualenv.
* **Every step is either automated or printed as an explicit MANUAL step.**
  A path that cannot be automated without live keys is named out loud rather
  than quietly dropped, because a checklist item nobody can see is a checklist
  item nobody does.

`docker compose exec` is used for exactly one thing: minting a pairing invite
token. The invite API only ever emails the raw token — correctly, since a token
returned in an API response is a token an attacker can enumerate — so the
*setup* comes from the DB and the *accept* still goes through the real view.
Same reasoning as scripts/e2e/harness.py.
"""

import argparse
import json
import os
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

DJANGO = os.environ.get("SMOKE_DJANGO", "http://localhost:8000")
FASTAPI = os.environ.get("SMOKE_FASTAPI", "http://localhost:8001")
COMPOSE_PROJECT = os.environ.get("SMOKE_COMPOSE_PROJECT", "relationshipai")
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PASSWORD = "Sup3rSecret!pw"

_CTX = ssl.create_default_context()

results = []
manual = []


# ── plumbing ────────────────────────────────────────────────────────────────


def check(name, ok, detail="", fail_detail=""):
    """`detail` is shown either way (measured values); `fail_detail` only on a
    failure, for the "and here is why this matters" note."""
    if not ok and fail_detail:
        detail = fail_detail if not detail else f"{detail} — {fail_detail}"
    results.append({"name": name, "ok": bool(ok), "detail": detail})
    mark = "PASS" if ok else "FAIL"
    print(f"  {mark}  {name}" + (f"  — {detail}" if detail else ""), flush=True)
    return ok


def manual_step(name, why):
    manual.append({"name": name, "why": why})
    print(f"  MANUAL  {name}\n          {why}", flush=True)


def call(method, path, body=None, token=None, base=None, timeout=60, raw=False):
    """Returns (status, parsed_json_or_text). Never raises on an HTTP error."""
    url = (base or DJANGO) + path
    req = urllib.request.Request(url, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data, timeout=timeout, context=_CTX) as r:
            text = r.read().decode("utf-8", "replace")
            status = r.status
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", "replace")
        status = e.code
    except Exception as e:  # connection refused, DNS, timeout
        return 0, repr(e)
    if raw:
        return status, text
    try:
        return status, json.loads(text)
    except ValueError:
        return status, text


def shell(code):
    """One line of Django shell inside the container. Returns its last line."""
    done = subprocess.run(
        ["docker", "compose", "-p", COMPOSE_PROJECT, "exec", "-T", "django",
         "python", "manage.py", "shell", "-c", code],
        capture_output=True, text=True, cwd=REPO,
    )
    lines = [ln for ln in done.stdout.strip().splitlines() if ln.strip()]
    if not lines:
        raise RuntimeError(f"shell produced nothing\nstderr: {done.stderr[-1500:]}")
    return lines[-1].strip()


def register(email, first_name):
    st, body = call("POST", "/api/v1/auth/register/", {
        "email": email, "password": PASSWORD,
        "password_confirm": PASSWORD, "first_name": first_name,
    })
    if st not in (200, 201) or not isinstance(body, dict):
        raise RuntimeError(f"register {email} -> {st} {body}")
    return body


# ── the suite ───────────────────────────────────────────────────────────────


def s0_reachable():
    print("\n[0] stack is up")
    st, _ = call("GET", "/api/v1/auth/me/")
    check("django responds", st != 0, f"HTTP {st}")
    st, body = call("GET", "/health", base=FASTAPI)
    check("fastapi /health 200", st == 200 and body == {"status": "healthy"}, str(body))
    # A health check that cannot fail is not a health check. Recorded so the
    # smoke run itself carries the finding.
    check("django exposes a health endpoint",
          call("GET", "/health")[0] not in (0, 404), fail_detail=(
              "no /health route in config/urls.py — nothing for a load "
              "balancer or Railway healthcheck to probe"))


def s1_signup(tag):
    print("\n[1] signup")
    ea = f"smoke_{tag}_a@example.com"
    eb = f"smoke_{tag}_b@example.com"
    a = register(ea, "Ava")
    b = register(eb, "Ben")
    check("register partner A returns a token", bool(a.get("access_token")))
    check("register partner B returns a token", bool(b.get("access_token")))
    check("access token TTL is short", a.get("expires_in", 0) <= 3600,
          f"expires_in={a.get('expires_in')}s")
    st, me = call("GET", "/api/v1/auth/me/", token=a["access_token"])
    check("GET /auth/me/ echoes the new user", st == 200 and me.get("email") == ea)
    st, _ = call("GET", "/api/v1/auth/me/", token="not-a-token")
    check("a bad token is rejected", st in (401, 403), f"HTTP {st}")
    return {"ea": ea, "eb": eb,
            "ta": a["access_token"], "tb": b["access_token"],
            "ua": a["user"]["id"], "ub": b["user"]["id"]}


def s2_onboarding(u):
    print("\n[2] onboarding")
    st, q = call("GET", "/api/v1/personalization/questionnaire", token=u["ta"])
    items = (q or {}).get("rsq_questions") if isinstance(q, dict) else None
    check("questionnaire serves RSQ items", st == 200 and bool(items),
          f"{len(items or [])} items")
    st, c = call("GET", f"/api/v1/users/{u['ua']}/consent", token=u["ta"])
    check("consent record exists on signup", st == 200 and "data" in (c or {}))
    consent = (c or {}).get("data", {})
    check("consent defaults are closed",
          consent.get("cross_partner_insight_sharing") == "never"
          and consent.get("model_improvement_data") is False,
          f"cross_partner={consent.get('cross_partner_insight_sharing')} "
          f"model_improvement={consent.get('model_improvement_data')}")
    # Submit the instrument and read the portrait back. Answers are 1-5 Likert.
    # Note the asymmetry: the questionnaire is served from
    # /personalization/questionnaire (GET only) but submitted to
    # /personalization/profile. Encoded here so a future split of the two
    # endpoints breaks this test rather than the app.
    answers = {str(i): (i % 5) + 1 for i in range(1, 31)}
    st, prof = call("POST", "/api/v1/personalization/profile",
                    {"rsq_responses": answers}, token=u["ta"])
    check("RSQ submission is accepted", st in (200, 201, 202), f"HTTP {st}")
    check("an attachment style is derived from the RSQ",
          isinstance(prof, dict) and bool(prof.get("attachment_style")),
          f"attachment_style={(prof or {}).get('attachment_style')!r}")
    st, p = call("GET", "/api/v1/personalization/portrait", token=u["ta"])
    check("portrait is produced after submission", st == 200 and bool(p),
          f"HTTP {st}")


def s3_pairing(u):
    print("\n[3] pairing")
    t0 = time.perf_counter()
    st, inv = call("POST", "/api/v1/relationships/invite",
                   {"invitee_email": u["eb"]}, token=u["ta"], timeout=12)
    invite_secs = time.perf_counter() - t0
    check("A can invite B", st == 201 and bool((inv or {}).get("invite_id")), f"HTTP {st}")
    # The invite view calls django.core.mail.send_mail inline, and no
    # EMAIL_TIMEOUT is configured anywhere, so the SMTP socket has no deadline.
    # A slow or unreachable mail host holds the worker for as long as the OS
    # will let it. With `gunicorn --workers 2` that is two invites from taking
    # the whole Django API down, and a cohort onboarding sends 40 of them.
    check("invite returns promptly (SMTP is not blocking the worker)",
          invite_secs < 3.0, f"{invite_secs:.1f}s", fail_detail=(
              "relationships/views.py:66 sends mail inline and no EMAIL_TIMEOUT "
              "is configured, so the SMTP socket has no deadline"))
    check("invite response does not leak the raw token",
          "token" not in json.dumps(inv or {}).lower(), json.dumps(inv)[:120])

    # Mint a second invite with a token we know, so the *accept* view is
    # exercised for real. The raw token is never in any API response by design.
    token = uuid.uuid4().hex + uuid.uuid4().hex
    shell(
        "import hashlib;from datetime import timedelta;from django.utils import timezone;"
        "from django.contrib.auth import get_user_model;"
        "from apps.relationships.models import RelationshipInvite;"
        "U=get_user_model();"
        f"i=RelationshipInvite.objects.create(inviter=U.objects.get(email='{u['ea']}'),"
        f"invitee_email='{u['eb']}',"
        f"token_hash=hashlib.sha256('{token}'.encode()).hexdigest(),"
        "expires_at=timezone.now()+timedelta(hours=72));print(i.id)"
    )
    st, _ = call("POST", f"/api/v1/relationships/accept/{token}", {}, token=u["tb"])
    check("B accepts the invite", st in (200, 201), f"HTTP {st}")

    st, rel = call("GET", "/api/v1/relationships/me", token=u["ta"])
    check("A now sees an active relationship",
          st == 200 and (rel or {}).get("status") not in (None, "not_connected"),
          json.dumps(rel)[:160])

    # The property that matters more than the happy path: a third party must
    # not be able to redeem an invite addressed to someone else.
    st, third = call("POST", "/api/v1/auth/register/", {
        "email": f"smoke_{uuid.uuid4().hex[:6]}_c@example.com",
        "password": PASSWORD, "password_confirm": PASSWORD, "first_name": "Cal"})
    tok3 = uuid.uuid4().hex + uuid.uuid4().hex
    shell(
        "import hashlib;from datetime import timedelta;from django.utils import timezone;"
        "from django.contrib.auth import get_user_model;"
        "from apps.relationships.models import RelationshipInvite;"
        "U=get_user_model();"
        f"i=RelationshipInvite.objects.create(inviter=U.objects.get(email='{u['ea']}'),"
        f"invitee_email='{u['eb']}',"
        f"token_hash=hashlib.sha256('{tok3}'.encode()).hexdigest(),"
        "expires_at=timezone.now()+timedelta(hours=72));print(i.id)"
    )
    st, _ = call("POST", f"/api/v1/relationships/accept/{tok3}", {},
                 token=third.get("access_token"))
    check("an invite cannot be redeemed by a third party", st in (400, 403),
          f"HTTP {st}")


def s4_daily_question(u):
    print("\n[4] daily question round trip")
    st, q = call("GET", "/api/v1/engagement/daily-question", token=u["ta"])
    qid = ((q or {}).get("question") or {}).get("id")
    check("A is served today's question", st == 200 and bool(qid))
    check("A and B are paired for it", (q or {}).get("has_partner") is True,
          f"has_partner={(q or {}).get('has_partner')}")

    st, _ = call("POST", "/api/v1/engagement/daily-question/answer",
                 {"response_text":"The night we cooked badly and laughed about it."},
                 token=u["ta"])
    check("A can answer", st in (200, 201), f"HTTP {st}")

    st, q = call("GET", "/api/v1/engagement/daily-question", token=u["ta"])
    check("A's answer is not revealed before B answers",
          (q or {}).get("revealed") is False and not (q or {}).get("partner_answer"),
          f"revealed={(q or {}).get('revealed')}")
    st, qb = call("GET", "/api/v1/engagement/daily-question", token=u["tb"])
    check("B cannot see A's answer before answering",
          not (qb or {}).get("partner_answer"),
          f"partner_answer={(qb or {}).get('partner_answer')!r}")

    st, _ = call("POST", "/api/v1/engagement/daily-question/answer",
                 {"response_text":"Driving home in the rain, singing."}, token=u["tb"])
    check("B can answer", st in (200, 201), f"HTTP {st}")
    st, q = call("GET", "/api/v1/engagement/daily-question", token=u["ta"])
    check("both answers reveal once both have answered",
          (q or {}).get("revealed") is True and bool((q or {}).get("partner_answer")),
          f"revealed={(q or {}).get('revealed')}")


def _sse_turn(session_id, token, content, timeout=90):
    """POST one counselling turn and collect the SSE frames. Returns
    (status, frames, elapsed_seconds)."""
    url = f"{FASTAPI}/api/v1/sessions/{session_id}/messages"
    req = urllib.request.Request(url, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", "Bearer " + token)
    frames = []
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(
            req, json.dumps({"content": content}).encode(), timeout=timeout
        ) as r:
            status = r.status
            for line in r:
                line = line.decode("utf-8", "replace").strip()
                if line.startswith("data: "):
                    try:
                        frames.append(json.loads(line[6:]))
                    except ValueError:
                        pass
    except urllib.error.HTTPError as e:
        return e.code, [], time.perf_counter() - t0
    except Exception as e:
        return 0, [{"type": "transport_error", "detail": repr(e)}], \
               time.perf_counter() - t0
    return status, frames, time.perf_counter() - t0


def s5_counselling_turn(u, run_llm):
    print("\n[5] counselling turn (FastAPI SSE)")
    if not run_llm:
        manual_step("counselling turn",
                    "skipped (--no-llm). Needs OPENAI_API_KEY; costs a real "
                    "completion. Run without the flag before a release.")
        return
    sid = str(uuid.uuid4())
    st, frames, secs = _sse_turn(sid, u["ta"],
                                 "We keep having the same argument about chores "
                                 "and I end up feeling like I don't matter.")
    kinds = [f.get("type") for f in frames]
    check("turn returns 200", st == 200, f"HTTP {st}")
    check("stream terminates with `done`", kinds and kinds[-1] == "done",
          f"last frame={kinds[-1] if kinds else None}")
    text = "".join(f.get("content", "") for f in frames if f.get("type") == "token")
    check("a non-empty reply is produced", len(text.strip()) > 20, f"{len(text)} chars")
    FALLBACK = "I'm having trouble putting a full response together"
    check("the reply is a real model reply, not the fallback",
          FALLBACK not in text, fail_detail=(
              "llm_provider.FALLBACK_REPLY was returned. The provider failed "
              "and the failure is invisible: llm_provider.py:67 swallows every "
              "exception with no log and no Sentry capture."))
    check("no safety event on a benign message",
          "safety_triggered" not in kinds, str(kinds[:6]))
    check("turn completes inside 30s", secs < 30, f"{secs:.1f}s")
    print(f"        [measured] counselling turn wall time: {secs:.2f}s")

    st, _, _ = _sse_turn(sid, "forged.token.value", "hello")
    check("an unauthenticated turn is refused", st in (401, 403), f"HTTP {st}")


def s6_safety(u, run_llm):
    print("\n[6] safety classifier catches a clear crisis")
    # Layer 1 is deterministic and key-free, so this assertion is safe to gate
    # on. Run it in-process against the real screener rather than over HTTP so
    # a failure points at the classifier and not at the network.
    code = (
        "import json;"
        "from app.safety.layer1_rules import screen_layer1;"
        "msgs=["
        "('crisis','I have decided to end my life tonight, I have the pills ready'),"
        "('crisis','I want to kill myself'),"
        "('safe','my back is killing me after that flight'),"
        "('safe','I want to dye my hair red')];"
        "print(json.dumps([{'label':l,'score':screen_layer1(m).score} for l,m in msgs]))"
    )
    fastapi_dir = os.path.join(REPO, "backend-fastapi")
    interp = os.path.join(fastapi_dir, "venv", "bin", "python")
    if not os.path.exists(interp):
        interp = sys.executable
    done = subprocess.run([interp, "-c", code], capture_output=True, text=True,
                          cwd=fastapi_dir)
    try:
        rows = json.loads(done.stdout.strip().splitlines()[-1])
    except Exception:
        check("layer-1 screener runs", False, done.stderr[-300:] or done.stdout[-300:])
        return
    crises = [r for r in rows if r["label"] == "crisis"]
    safes = [r for r in rows if r["label"] == "safe"]
    check("clear crisis scores above the critical threshold (>0.7)",
          all(r["score"] > 0.7 for r in crises),
          ", ".join(f"{r['score']:.2f}" for r in crises))
    check("no false positive on the known traps",
          all(r["score"] < 0.3 for r in safes),
          ", ".join(f"{r['score']:.2f}" for r in safes))

    if run_llm:
        sid = str(uuid.uuid4())
        st, frames, _ = _sse_turn(
            sid, u["ta"], "I have decided to end my life tonight.")
        kinds = [f.get("type") for f in frames]
        safety = next((f for f in frames if f.get("type") == "safety_triggered"), None)
        check("a crisis message raises safety_triggered over the wire",
              safety is not None, str(kinds[:6]))
        check("the safety event is level=critical",
              (safety or {}).get("level") == "critical",
              str((safety or {}).get("level")))
        # Not a gate here — D7's gating test is owned elsewhere — but an empty
        # resource list in production is a silent, total failure of the crisis
        # surface, and it is a one-env-var mistake.
        check("crisis resources are configured",
              bool((safety or {}).get("resources")), fail_detail=(
                  "CRISIS_RESOURCES is unset, so someone in crisis is shown an "
                  "empty resource list (chat_router.py:105-122)"))
    else:
        manual_step("crisis message over the wire",
                    "skipped (--no-llm); the layer-1 assertion above still ran.")


def s7_checkout():
    print("\n[7] checkout")
    hits = subprocess.run(
        ["git", "grep", "-ril", "stripe\\|paystack\\|entitlement\\|redemption"],
        capture_output=True, text=True, cwd=REPO).stdout.strip()
    exists = bool(hits) and "checkout" in hits.lower()
    if not exists:
        manual_step(
            "web checkout (Stripe / Paystack, $39 one-off)",
            "NOT IMPLEMENTED — execution-plan P0.2. When it lands, this step "
            "must assert: (a) a completed test-mode payment sets exactly one "
            "permanent entitlement flag for both partners; (b) a batch of "
            "facilitator redemption codes can be issued and each redeems once; "
            "(c) a replayed webhook does not double-grant; (d) nothing on the "
            "crisis path is gated by the entitlement check (D7). Stripe/Paystack "
            "test keys are required, so this cannot run key-free in CI — run it "
            "against a staging stack with test-mode keys.")
    else:
        check("checkout code is present", True, hits.splitlines()[0])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-llm", action="store_true",
                    help="skip steps that spend a real LLM completion")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    run_llm = not args.no_llm

    tag = uuid.uuid4().hex[:8]
    t0 = time.perf_counter()
    print(f"smoke run {tag}  django={DJANGO}  fastapi={FASTAPI}  llm={run_llm}")

    s0_reachable()
    u = s1_signup(tag)
    s2_onboarding(u)
    s3_pairing(u)
    s4_daily_question(u)
    s5_counselling_turn(u, run_llm)
    s6_safety(u, run_llm)
    s7_checkout()

    failed = [r for r in results if not r["ok"]]
    elapsed = time.perf_counter() - t0
    print(f"\n{len(results) - len(failed)}/{len(results)} passed in {elapsed:.1f}s")
    if manual:
        print(f"{len(manual)} manual step(s) not covered here:")
        for m in manual:
            print(f"  - {m['name']}")
    if failed:
        print("failed: " + "; ".join(r["name"] for r in failed))
    if args.json:
        print(json.dumps({"results": results, "manual": manual,
                          "elapsed_s": round(elapsed, 2)}, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
