"""Do Django and FastAPI agree on the JWT signing key?

    docker compose up -d
    backend-django/venv/bin/python scripts/check_jwt_alignment.py

Exits 0 if they agree, 1 if they do not, and prints what to change either way.

This exists because the failure it detects is silent and expensive. Django
signs tokens with its SECRET_KEY; FastAPI verifies with its own; the two live
in separate .env.local files and nothing checks that they match. When they
diverged, every couple-thread WebSocket rejected every token with a bare
HTTP 403 — which reads as "this user is not allowed" rather than "these two
services are holding different keys". Live delivery was broken for an unknown
length of time and nothing in any log said so.

The check compares fingerprints, never the keys: each service computes an HMAC
of a fixed public label under its own key, so nothing secret crosses a process
boundary or reaches this script's output.
"""

import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]


def fingerprint(service: str, snippet: str) -> str | None:
    """Ask a running container for its key fingerprint."""
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", service, "python", "-c", snippet],
        capture_output=True,
        text=True,
        cwd=REPO,
    )
    if result.returncode != 0:
        print(f"  could not reach the {service} container:")
        print("    " + (result.stderr.strip().splitlines() or ["(no output)"])[-1])
        return None
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return lines[-1] if lines else None


DJANGO_SNIPPET = (
    "import django, os; "
    "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings'); "
    "os.environ['DJANGO_SKIP_KEY_LOG'] = '1'; "
    "django.setup(); "
    "from apps.accounts.auth import key_fingerprint; print(key_fingerprint())"
)

FASTAPI_SNIPPET = "from app.auth import key_fingerprint; print(key_fingerprint())"


def main() -> int:
    print("Comparing JWT signing keys (fingerprints only — no key material)\n")

    django = fingerprint("django", DJANGO_SNIPPET)
    fastapi = fingerprint("fastapi", FASTAPI_SNIPPET)
    print(f"  django   signs   with  {django or '?'}")
    print(f"  fastapi  verifies with {fastapi or '?'}")

    if django is None or fastapi is None:
        print("\nInconclusive — bring the stack up with `docker compose up -d`.")
        return 1

    if "unset" in (django, fastapi):
        which = "django" if django == "unset" else "fastapi"
        print(f"\nFAIL: {which} has no SECRET_KEY. Every authenticated request will fail.")
        return 1

    if django != fastapi:
        print(
            "\nFAIL: the keys differ, so FastAPI will reject every token Django\n"
            "issues — as a bare HTTP 403, which looks like a permissions problem.\n\n"
            "Fix: set SECRET_KEY in backend-fastapi/.env.local to the same value\n"
            "as in backend-django/.env.local, then\n\n"
            "    docker compose up -d --force-recreate fastapi\n\n"
            "Note that `docker compose restart` does NOT re-read env_file, which\n"
            "makes it look as though the change had no effect."
        )
        return 1

    print("\nOK: both services are using the same signing key.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
