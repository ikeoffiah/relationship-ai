"""Replay scripted conversations against the running stack.

    docker compose up -d postgres redis django fastapi
    backend-django/venv/bin/python scripts/e2e/run_scenarios.py          # all
    backend-django/venv/bin/python scripts/e2e/run_scenarios.py S1 S2    # some
    backend-django/venv/bin/python scripts/e2e/run_scenarios.py quiet    # a group

Companion to ``couple_thread.py``, which checks that the plumbing between two
processes works. This checks whether the intelligence behaves sensibly across a
whole conversation, which is a different question and the one the product is
actually judged on.

See ``docs/intelligence-test-plan.md``.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from harness import report, results  # noqa: E402
from scenarios import crosscutting, intervene, loop, quiet, route, score  # noqa: E402
from scenarios.runner import play  # noqa: E402

GROUPS = {
    "quiet": quiet.SCENARIOS,
    "intervene": intervene.SCENARIOS,
    "route": route.SCENARIOS,
    "loop": loop.SCENARIOS,
    "score": score.SCENARIOS,
    "crosscutting": crosscutting.SCENARIOS,
}

# The order §4 of the plan asks for: silence first, because if the system
# comments during ordinary chat then everything else is noise; then the places
# where a wrong answer does the most harm; then the loop and the score; then
# the slow accumulation ones last, since they need back-dating and real media.
ORDER = ["quiet", "route", "intervene", "loop", "score", "crosscutting"]


def selected(argv):
    if not argv:
        return [s for group in ORDER for s in GROUPS[group]]

    chosen, unknown = [], []
    by_key = {s.key.upper(): s for group in GROUPS.values() for s in group}
    for arg in argv:
        if arg.lower() in GROUPS:
            chosen.extend(GROUPS[arg.lower()])
        elif arg.upper() in by_key:
            chosen.append(by_key[arg.upper()])
        else:
            unknown.append(arg)
    if unknown:
        print(f"unknown: {', '.join(unknown)}")
        print(f"scenarios: {', '.join(sorted(by_key))}")
        print(f"groups: {', '.join(GROUPS)}")
        sys.exit(2)
    # Keep the plan's order regardless of what order they were named in.
    ranked = {s.key: i for i, s in enumerate(s for g in ORDER for s in GROUPS[g])}
    return sorted(dict.fromkeys(chosen), key=lambda s: ranked.get(s.key, 999))


def main():
    scenarios = selected(sys.argv[1:])
    stats = [play(scenario) for scenario in scenarios]

    # Recorded per scenario so a cost or latency regression surfaces here
    # rather than on a bill. The check path is tiered specifically so that
    # ordinary chat costs nothing; if that gate ever widens, this is the
    # number that moves.
    #
    # It counts every completion attempted anywhere in the stack while the
    # scenario ran, which with a live Celery worker includes the rolling
    # thread summaries the scenario's own messages queued. That is the right
    # number — those summaries are real spend caused by that conversation —
    # but it is not attributable line by line, and the tail of one scenario's
    # summaries can land inside the next one's window. Read it as the cost of
    # a conversation of that shape, not as an exact per-endpoint tally.
    print("\n== cost and latency ==")
    print(f"  {'scenario':<6} {'seconds':>8} {'model calls':>12}")
    for row in stats:
        print(f"  {row['key']:<6} {row['seconds']:>8.1f} {row['model_calls']:>12}")
    print(
        f"  {'total':<6} {sum(r['seconds'] for r in stats):>8.1f}"
        f" {sum(r['model_calls'] for r in stats):>12}"
    )

    _ = results
    return report()


if __name__ == "__main__":
    sys.exit(main())
