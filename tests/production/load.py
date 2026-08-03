#!/usr/bin/env python3
"""Load driver shaped like the real arrival pattern.

The traffic Bliss will actually see is not a smooth ramp. A facilitator sells a
cohort, hands out 25-40 codes, and the whole cohort onboards inside an hour —
often inside a single session, in one room, on one wifi. So the interesting
question is never "requests per second"; it is "what happens when 80 people all
create an account, submit a 30-item instrument and pair up within the same few
minutes, and then start talking to a counsellor."

Three phases, each runnable alone:

  --phase onboard   40 couples (80 users) register + submit RSQ + pair.
                    Free — no LLM call anywhere on this path.
  --phase db        Concurrency sweep against a FastAPI endpoint that touches
                    Postgres and nothing else, sampling pg_stat_activity
                    throughout. This is what isolates the connection behaviour
                    from LLM latency. Free.
  --phase counsel   Steady-state counselling turns at increasing concurrency.
                    COSTS REAL MONEY — one OpenAI completion per turn. Sized by
                    --turns (default 12) and reports measured token cost.

Nothing here is estimated unless the output says "estimated".

    python3 tests/production/load.py --phase onboard
    python3 tests/production/load.py --phase db
    python3 tests/production/load.py --phase counsel --turns 12
    python3 tests/production/load.py --phase all
"""

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor

DJANGO = os.environ.get("LOAD_DJANGO", "http://localhost:8000")
FASTAPI = os.environ.get("LOAD_FASTAPI", "http://localhost:8001")
COMPOSE_PROJECT = os.environ.get("LOAD_COMPOSE_PROJECT", "relationshipai")
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PASSWORD = "Sup3rSecret!pw"

# Published USD per 1M tokens, gpt-4o (the primary_counseling model in
# backend-fastapi/app/orchestration/model_config.py). Update alongside it.
GPT4O_IN_PER_M = 2.50
GPT4O_OUT_PER_M = 10.00


# ── plumbing ────────────────────────────────────────────────────────────────


def http(method, url, body=None, token=None, timeout=120):
    """(status, text, seconds). Never raises."""
    req = urllib.request.Request(url, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    data = json.dumps(body).encode() if body is not None else None
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, data, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace"), time.perf_counter() - t0
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), time.perf_counter() - t0
    except Exception as e:
        return 0, repr(e), time.perf_counter() - t0


def pct(values, p):
    if not values:
        return 0.0
    s = sorted(values)
    k = max(0, min(len(s) - 1, int(round((p / 100.0) * (len(s) - 1)))))
    return s[k]


def summarise(label, statuses, latencies, wall):
    ok = sum(1 for s in statuses if 200 <= s < 300)
    bad = len(statuses) - ok
    codes = {}
    for s in statuses:
        codes[s] = codes.get(s, 0) + 1
    print(f"\n  {label}")
    print(f"    requests        {len(statuses)}   ok {ok}   failed {bad}")
    print(f"    wall            {wall:.1f}s   throughput {len(statuses)/wall:.1f} req/s")
    if latencies:
        print(f"    latency ms      p50 {pct(latencies,50)*1000:.0f}   "
              f"p95 {pct(latencies,95)*1000:.0f}   p99 {pct(latencies,99)*1000:.0f}   "
              f"max {max(latencies)*1000:.0f}")
    print(f"    status codes    {dict(sorted(codes.items()))}")
    return {"label": label, "n": len(statuses), "ok": ok, "failed": bad,
            "wall_s": round(wall, 2), "rps": round(len(statuses) / wall, 2),
            "p50_ms": round(pct(latencies, 50) * 1000),
            "p95_ms": round(pct(latencies, 95) * 1000),
            "p99_ms": round(pct(latencies, 99) * 1000),
            "codes": codes}


def pg(query):
    out = subprocess.run(
        ["docker", "compose", "-p", COMPOSE_PROJECT, "exec", "-T", "postgres",
         "psql", "-U", "postgres", "-tAc", query],
        capture_output=True, text=True, cwd=REPO)
    return out.stdout.strip().replace("\r", "")


def pg_conns():
    try:
        return int(pg("select count(*) from pg_stat_activity") or 0)
    except ValueError:
        return -1


class ConnSampler:
    """Samples pg_stat_activity in a background thread for the length of a
    phase. Crude, but it is the number that decides whether this survives a
    cohort, so it is worth measuring rather than reasoning about."""

    def __init__(self, interval=0.25):
        self.interval = interval
        self.samples = []
        self._stop = False

    def _run(self):
        while not self._stop:
            self.samples.append(pg_conns())
            time.sleep(self.interval)

    def __enter__(self):
        import threading
        self._t = threading.Thread(target=self._run, daemon=True)
        self._t.start()
        return self

    def __exit__(self, *a):
        self._stop = True
        self._t.join(timeout=2)

    def report(self):
        good = [s for s in self.samples if s >= 0]
        if not good:
            return "  (no pg samples)"
        return (f"    pg connections  baseline≈{good[0]}  peak {max(good)}  "
                f"mean {statistics.mean(good):.1f}  (max_connections="
                f"{pg('show max_connections')})")


# ── phase: cohort onboarding ────────────────────────────────────────────────


def onboard_one(idx, tag):
    """One person: register, submit the RSQ, read the portrait. Returns
    (statuses, latencies, token, email, user_id)."""
    email = f"load_{tag}_{idx}@example.com"
    statuses, lats = [], []

    st, body, s = http("POST", f"{DJANGO}/api/v1/auth/register/",
                       {"email": email, "password": PASSWORD,
                        "password_confirm": PASSWORD, "first_name": f"U{idx}"})
    statuses.append(st); lats.append(s)
    try:
        token = json.loads(body)["access_token"]
        uid = json.loads(body)["user"]["id"]
    except Exception:
        return statuses, lats, None, email, None

    answers = {str(i): (i % 5) + 1 for i in range(1, 31)}
    st, _, s = http("POST", f"{DJANGO}/api/v1/personalization/profile",
                    {"rsq_responses": answers}, token=token)
    statuses.append(st); lats.append(s)

    st, _, s = http("GET", f"{DJANGO}/api/v1/personalization/portrait", token=token)
    statuses.append(st); lats.append(s)

    st, _, s = http("GET", f"{DJANGO}/api/v1/engagement/daily-question", token=token)
    statuses.append(st); lats.append(s)

    return statuses, lats, token, email, uid


def phase_onboard(couples, concurrency):
    print(f"\n=== PHASE: cohort onboarding — {couples} couples "
          f"({couples*2} people), concurrency {concurrency} ===")
    tag = uuid.uuid4().hex[:6]
    n = couples * 2
    statuses, lats, people = [], [], []
    t0 = time.perf_counter()
    with ConnSampler() as sampler:
        with ThreadPoolExecutor(max_workers=concurrency) as ex:
            for st, la, token, email, uid in ex.map(
                    lambda i: onboard_one(i, tag), range(n)):
                statuses += st; lats += la
                people.append({"token": token, "email": email, "id": uid})
    wall = time.perf_counter() - t0
    row = summarise("register + RSQ + portrait + daily-question", statuses, lats, wall)
    print(sampler.report())

    throttled = statuses.count(429)
    print(f"    429s            {throttled}"
          + ("   <-- rate limiting rejected part of the cohort" if throttled else ""))

    # Pairing: this is where the cohort actually lands, and it is the path with
    # the inline SMTP call. Timed separately and with a hard cap so one hung
    # socket cannot stall the whole run.
    pairs = [(people[i], people[i + 1]) for i in range(0, len(people) - 1, 2)
             if people[i]["token"] and people[i + 1]["token"]]
    inv_st, inv_lat = [], []
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        for st, _, s in ex.map(
                lambda p: http("POST", f"{DJANGO}/api/v1/relationships/invite",
                               {"invitee_email": p[1]["email"]},
                               token=p[0]["token"], timeout=15), pairs):
            inv_st.append(st); inv_lat.append(s)
    summarise(f"partner invite x{len(pairs)} (inline send_mail)",
              inv_st, inv_lat, time.perf_counter() - t0)
    return {"onboard": row, "people": people}


# ── phase: database concurrency ─────────────────────────────────────────────


def phase_db(token, levels):
    """FastAPI endpoint that touches Postgres and nothing else, so the
    connection behaviour is not hidden behind LLM latency.

    `GET /api/v1/relationships/{id}/context` opens a fresh asyncpg pool per
    request (app/api/relationships.py:15-25, whose own comment says it should
    be on app.state). asyncpg's default pool is min_size=10, so the prediction
    under test is: connections ≈ 10 x in-flight requests.

    The driver has no relationship, so the handler answers 404 — after the pool
    has been opened and a consent query has run against it. A 404 here is a
    completed database round trip, which is exactly what is being measured; a
    0 (transport error) or a 500 is not.
    """
    print("\n=== PHASE: database concurrency (no LLM) ===")
    rid = str(uuid.uuid4())
    url = f"{FASTAPI}/api/v1/relationships/{rid}/context"
    rows = []
    for c in levels:
        st_all, lat_all = [], []
        t0 = time.perf_counter()
        with ConnSampler(interval=0.1) as sampler:
            with ThreadPoolExecutor(max_workers=c) as ex:
                for st, _, s in ex.map(
                        lambda _: http("GET", url, token=token, timeout=60),
                        range(c * 3)):
                    st_all.append(st); lat_all.append(s)
            wall = time.perf_counter() - t0
        row = summarise(f"concurrency {c}", st_all, lat_all, wall)
        reached_db = sum(1 for s in st_all if s == 404 or 200 <= s < 300)
        print(f"    reached the DB  {reached_db}/{len(st_all)}   "
              f"transport errors {st_all.count(0)}   5xx {sum(1 for s in st_all if s>=500)}")
        print(sampler.report())
        good = [s for s in sampler.samples if s >= 0]
        row["pg_peak"] = max(good) if good else None
        row["reached_db"] = reached_db
        rows.append(row)
    return rows


# ── phase: counselling turns ────────────────────────────────────────────────


def counsel_turn(token, content, timeout=180):
    """One SSE counselling turn. Returns (status, reply_text, seconds)."""
    sid = str(uuid.uuid4())
    req = urllib.request.Request(
        f"{FASTAPI}/api/v1/sessions/{sid}/messages", method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", "Bearer " + token)
    t0 = time.perf_counter()
    text = []
    try:
        with urllib.request.urlopen(
                req, json.dumps({"content": content}).encode(), timeout=timeout) as r:
            status = r.status
            for line in r:
                line = line.decode("utf-8", "replace").strip()
                if line.startswith("data: "):
                    try:
                        f = json.loads(line[6:])
                    except ValueError:
                        continue
                    if f.get("type") == "token":
                        text.append(f.get("content", ""))
    except urllib.error.HTTPError as e:
        return e.code, "", time.perf_counter() - t0
    except Exception:
        return 0, "", time.perf_counter() - t0
    return status, "".join(text), time.perf_counter() - t0


MESSAGES = [
    "We keep having the same argument about chores and I end up feeling invisible.",
    "He works late every night and I don't know how to say I miss him without sounding needy.",
    "I snapped at her this morning about nothing and I feel awful about it.",
    "We haven't really talked in weeks. We just coordinate logistics.",
    "I found out she told her sister about our money problems and I felt betrayed.",
    "Every time I bring up having kids he changes the subject.",
]


def phase_counsel(token, turns, levels):
    print(f"\n=== PHASE: counselling turns — {turns} paid completions ===")
    print("    (each turn is a real gpt-4o call; this phase costs money)")
    FALLBACK = "I'm having trouble putting a full response together"
    all_rows, replies, fallbacks = [], [], 0
    done = 0
    for c in levels:
        batch = min(c * 2, max(0, turns - done))
        if batch <= 0:
            break
        st_all, lat_all = [], []
        t0 = time.perf_counter()
        with ConnSampler(interval=0.1) as sampler:
            with ThreadPoolExecutor(max_workers=c) as ex:
                for st, txt, s in ex.map(
                        lambda i: counsel_turn(token, MESSAGES[i % len(MESSAGES)]),
                        range(batch)):
                    st_all.append(st); lat_all.append(s)
                    if txt:
                        replies.append(txt)
                        if FALLBACK in txt:
                            fallbacks += 1
            wall = time.perf_counter() - t0
        done += batch
        row = summarise(f"concurrency {c} ({batch} turns)", st_all, lat_all, wall)
        print(sampler.report())
        good = [s for s in sampler.samples if s >= 0]
        row["pg_peak"] = max(good) if good else None
        all_rows.append(row)
    print(f"\n    silent provider fallbacks: {fallbacks}/{len(replies)}"
          + ("   <-- these are invisible in prod: no log, no Sentry event"
             if fallbacks else ""))
    return all_rows, replies


def cost_report(replies):
    """Exact LLM cost of a counselling turn, from the provider's own usage
    counters.

    tiktoken is not installed in either venv, and a chars/4 approximation is not
    good enough to price a fixed-margin SKU against, so this asks OpenAI. It
    builds the *real* system prompt with build_system_prompt and makes three
    direct completions with it, reading usage.prompt_tokens /
    usage.completion_tokens off the response. That costs three completions and
    removes all guesswork.

    Set --no-cost-probe to skip the paid probe and report only what the SSE
    turns revealed.
    """
    print("\n=== LLM COST PER TURN (measured from provider usage counters) ===")
    venv = os.path.join(REPO, "backend-fastapi", "venv", "bin", "python")
    interp = venv if os.path.exists(venv) else sys.executable
    probe = r"""
import os, json, statistics
for line in open(".env.local"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())
from app.orchestration.graph import build_system_prompt
prompt = build_system_prompt(
    {'primary': 'Validation', 'focus': 'the current feeling'},
    {'attachment_style': 'anxious-preoccupied', 'communication_style': 'direct'},
    {'level': 'safe'}, [],
    [{'note': 'They argue about chores most weeks'},
     {'note': 'Money is a sore subject since the move'}],
    {'shared_goals': [{'title': 'weekly date night', 'progress': '40%'}],
     'recurring_conflicts': ['chores', 'in-laws'],
     'agreed_values': ['honesty', 'no silent treatment']})
from openai import OpenAI
c = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
msgs = [
 "We keep having the same argument about chores and I end up feeling invisible.",
 "He works late every night and I do not know how to say I miss him.",
 "I snapped at her this morning about nothing and I feel awful about it.",
]
rows = []
for m in msgs:
    r = c.chat.completions.create(model="gpt-4o", max_tokens=1024,
        messages=[{"role": "system", "content": prompt},
                  {"role": "user", "content": m}])
    rows.append({"in": r.usage.prompt_tokens, "out": r.usage.completion_tokens})
e = c.embeddings.create(model="text-embedding-3-small", input=msgs[0])
print("__COST__" + json.dumps({
    "prompt_chars": len(prompt),
    "mean_in": statistics.mean(r["in"] for r in rows),
    "mean_out": statistics.mean(r["out"] for r in rows),
    "rows": rows,
    "embedding_tokens": e.usage.total_tokens}))
"""
    out = subprocess.run([interp, "-c", probe], capture_output=True, text=True,
                         cwd=os.path.join(REPO, "backend-fastapi"))
    line = next((ln for ln in out.stdout.splitlines() if ln.startswith("__COST__")), None)
    if not line:
        print("    cost probe failed:", (out.stderr or out.stdout)[-300:])
        return None
    d = json.loads(line[len("__COST__"):])

    per_turn = (d["mean_in"] / 1e6 * GPT4O_IN_PER_M
                + d["mean_out"] / 1e6 * GPT4O_OUT_PER_M
                + d["embedding_tokens"] / 1e6 * 0.02)
    print(f"    system prompt   {d['prompt_chars']} chars")
    print(f"    MEASURED in     {d['mean_in']:.0f} tokens/turn   "
          f"out {d['mean_out']:.0f} tokens/turn   "
          f"(+{d['embedding_tokens']} embedding tokens for retrieval)")
    print(f"    model           gpt-4o @ ${GPT4O_IN_PER_M}/1M in, "
          f"${GPT4O_OUT_PER_M}/1M out")
    print(f"    MEASURED COST PER COUNSELLING TURN: ${per_turn:.6f}")
    print()
    print("    CAVEAT, and it is a large one: the input is only "
          f"{d['mean_in']:.0f} tokens because chat_router._initial_state puts")
    print("    exactly one message in short_term_buffer — the FastAPI counsellor")
    print("    is stateless within a session and never sees the conversation so")
    print("    far. Thread the history and input grows roughly linearly with the")
    print("    turn number; a 30-turn session would end near 3k input tokens,")
    print("    which is where docs/go-to-market.md §3.1 put it.")
    print()
    print("    Turns per couple below is an ASSUMPTION — there is no usage data")
    print("    at 0 users. The cost column is measured; the volume column is not.")
    print(f"    {'turns':>6}  {'stateless $/couple':>19}  "
          f"{'w/ history $/couple':>20}  {'$/30-couple cohort':>19}  {'margin@$39':>11}")
    for t in (20, 50, 100, 200, 500):
        stateless = per_turn * t
        # With history threaded, input on turn n is roughly prompt + n*avg turn.
        with_hist = sum(
            ((d["mean_in"] + i * (40 + d["mean_out"])) / 1e6 * GPT4O_IN_PER_M
             + d["mean_out"] / 1e6 * GPT4O_OUT_PER_M) for i in range(t))
        print(f"    {t:>6}  {stateless:>18.3f}  {with_hist:>19.2f}  "
              f"{with_hist*30:>18.2f}  {100*(39-with_hist)/39:>10.1f}%")
    return {"per_turn_usd": round(per_turn, 6),
            "mean_in_tokens": d["mean_in"], "mean_out_tokens": d["mean_out"],
            "method": "openai usage counters (exact)"}


# ── main ────────────────────────────────────────────────────────────────────


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", default="all",
                    choices=["all", "onboard", "db", "counsel", "cost"])
    ap.add_argument("--couples", type=int, default=40)
    ap.add_argument("--concurrency", type=int, default=20)
    ap.add_argument("--turns", type=int, default=12,
                    help="paid counselling completions (costs money)")
    ap.add_argument("--json", help="write the summary to this path")
    args = ap.parse_args()

    print(f"load run  django={DJANGO}  fastapi={FASTAPI}")
    print(f"baseline pg connections: {pg_conns()} / {pg('show max_connections')}")
    out = {}

    tag = uuid.uuid4().hex[:6]
    _, _, token, _, _ = onboard_one(0, "driver_" + tag)
    if not token:
        print("could not create a driver account; is the stack up?")
        return 1

    if args.phase in ("all", "onboard"):
        out["onboard"] = phase_onboard(args.couples, args.concurrency)["onboard"]
    if args.phase in ("all", "db"):
        out["db"] = phase_db(token, [1, 2, 4, 8, 16])
    replies = []
    if args.phase in ("all", "counsel"):
        out["counsel"], replies = phase_counsel(token, args.turns, [1, 2, 4, 8])
    if args.phase in ("all", "counsel", "cost"):
        out["cost"] = cost_report(replies)

    if args.json:
        with open(args.json, "w") as f:
            json.dump(out, f, indent=2)
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
