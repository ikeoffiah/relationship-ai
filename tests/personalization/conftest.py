"""Django bootstrap for the RSQ scorer tests.

`calculate_rsq_attachment_style` is a pure function, but it lives in a module
that imports `apps.personalization.models`, so Django's app registry has to be
loaded before it can be imported. No database is touched by anything in this
directory.

Run these with the Django venv:

    backend-django/venv/bin/python -m pytest tests/personalization/

If Django cannot be set up this fails at collection rather than skipping. A
skipped invariant is an untested invariant that looks tested in the output.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DJANGO_ROOT = REPO_ROOT / "backend-django"


def pytest_configure(config):  # noqa: ARG001
    if str(DJANGO_ROOT) not in sys.path:
        sys.path.insert(0, str(DJANGO_ROOT))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        import django
    except ImportError:  # pragma: no cover
        return  # item-contract tests are stdlib-only and still worth running
    django.setup()
