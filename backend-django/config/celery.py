import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "audit-chain-verification": {
        "task": "audit.tasks.verify_audit_chain",
        "schedule": crontab(day_of_month=1, hour=2),  # monthly at 2am
    },
    "deliver-due-bliss-reminders": {
        "task": "engagement.tasks.deliver_due_reminders",
        "schedule": crontab(minute="*/5"),  # every 5 minutes
    },
    "deliver-due-commitment-reminders": {
        "task": "engagement.tasks.deliver_due_commitments",
        "schedule": crontab(minute="*/5"),  # every 5 minutes
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
