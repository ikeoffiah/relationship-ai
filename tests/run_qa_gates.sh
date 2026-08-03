#!/usr/bin/env bash
#
# QA gates: the D7 crisis-gating suite and the RSQ scorer contract.
#
# These live outside the per-service test suites because they assert across
# service boundaries — the crisis path runs from a Flutter widget through a
# FastAPI graph, and the RSQ contract binds a Django view to a Django task via
# a JSON blob written by a Dart view-model. Neither belongs to one service, so
# neither would be run by that service's CI job.
#
# Two interpreters on purpose: the crisis gate is stdlib-only and runs under
# anything, while the RSQ blob tests import the real scorer and need Django's
# app registry (no database).
#
#   ./tests/run_qa_gates.sh
#
# See docs/qa/crisis-gating.md and docs/qa/baseline.md.

set -uo pipefail

cd "$(dirname "$0")/.." || exit 1

FASTAPI_PY="backend-fastapi/venv/bin/python"
DJANGO_PY="backend-django/venv/bin/python"
[ -x "$FASTAPI_PY" ] || FASTAPI_PY="python3"
[ -x "$DJANGO_PY" ] || DJANGO_PY="python3"

status=0

echo "== D7 crisis gating =="
"$FASTAPI_PY" -m pytest tests/safety/ -q || status=1

echo
echo "== Money path (D2 one-SKU + entitlement allowlist) =="
"$FASTAPI_PY" -m pytest tests/money_path/ -q || status=1

echo
echo "== Silent-failure ratchet =="
"$FASTAPI_PY" -m pytest tests/observability/ -q || status=1

echo
echo "== RSQ scorer contract =="
"$DJANGO_PY" -m pytest tests/personalization/ -q || status=1

echo
if [ "$status" -eq 0 ]; then
  echo "QA gates: pass"
else
  echo "QA gates: FAIL"
fi
exit "$status"
