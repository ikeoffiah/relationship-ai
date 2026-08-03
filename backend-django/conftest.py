"""Test-wide configuration.

Set before Django reads settings, because pytest imports conftest first.
"""

import os

# Run Celery tasks inline under test.
#
# Without this, moving a side effect into a task silently stops it being
# exercised: the assertion that an invite sends an email would pass by never
# running the code that sends it. Eager mode keeps those tests honest and
# covers the task body too.
#
# `setdefault`, so a run can still opt out explicitly.
os.environ.setdefault("CELERY_TASK_ALWAYS_EAGER", "True")
