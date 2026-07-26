"""
Celery tasks for the engagement app.

``deliver_due_reminders`` is the sweep that actually fires @bliss reminders: on a
schedule (see ``config.celery.beat_schedule``) it finds pending reminders whose
time has arrived and sends both partners an in-app notification, marking each so
it never fires twice.
"""

import logging

from celery import shared_task
from django.db.models import Q
from django.utils import timezone

from apps.engagement import services
from apps.engagement.models import BlissItem, Commitment
from apps.notifications.notification_models import NotificationType

logger = logging.getLogger(__name__)


def _recipients(item: BlissItem) -> list:
    """Both partners (or just the creator when solo)."""
    ids = {item.created_by_id}
    rel = item.relationship
    if rel is not None:
        ids.add(rel.partner_a_id)
        ids.add(rel.partner_b_id)
    return [uid for uid in ids if uid is not None]


def _deliver(now=None) -> int:
    """Notify for every due, un-reminded, pending reminder. Returns the count
    delivered. Kept separate from the task wrapper so it's callable in tests."""
    now = now or timezone.now()
    due = BlissItem.objects.filter(
        Q(kind="reminder") | Q(kind="event"),
        status="pending",
        reminded_at__isnull=True,
        due_at__isnull=False,
        due_at__lte=now,
    )
    delivered = 0
    for item in due:
        for uid in _recipients(item):
            services.notify(
                uid,
                NotificationType.BLISS_REMINDER,
                title="Reminder 🌸",
                body=item.title,
                data={"deep_link": "/engagement/bliss", "item_id": str(item.id)},
            )
        # Stamp after sending so a mid-loop failure re-delivers rather than
        # silently dropping the reminder.
        item.reminded_at = now
        item.save(update_fields=["reminded_at"])
        delivered += 1
    return delivered


@shared_task(name="engagement.tasks.deliver_due_reminders")
def deliver_due_reminders() -> int:
    count = _deliver()
    if count:
        logger.info("Delivered %d due @bliss reminder(s)", count)
    return count


def _commitment_recipients(item: Commitment) -> list:
    """Who a commitment reminder goes to. A 'with each other' commitment reminds
    both partners; a 'for my partner' one reminds only its author, so it can
    stay a private surprise."""
    if item.kind == "with_partner" and item.relationship is not None:
        rel = item.relationship
        return [uid for uid in {rel.partner_a_id, rel.partner_b_id} if uid is not None]
    return [item.created_by_id]


def _deliver_commitments(now=None) -> int:
    """Fire reminders for due, un-reminded, active commitments. Callable in
    tests via an injected ``now``."""
    now = now or timezone.now()
    due = Commitment.objects.filter(
        status="active",
        reminded_at__isnull=True,
        remind_at__isnull=False,
        remind_at__lte=now,
    )
    delivered = 0
    for item in due:
        body = (
            item.text
            if item.kind == "with_partner"
            else f"You wanted to do this for your partner: {item.text}"
        )
        for uid in _commitment_recipients(item):
            services.notify(
                uid,
                NotificationType.COMMITMENT_REMINDER,
                title="A little commitment 💞",
                body=body,
                data={"deep_link": "/engagement/commitments", "item_id": str(item.id)},
            )
        item.reminded_at = now
        item.save(update_fields=["reminded_at"])
        delivered += 1
    return delivered


@shared_task(name="engagement.tasks.deliver_due_commitments")
def deliver_due_commitments() -> int:
    count = _deliver_commitments()
    if count:
        logger.info("Delivered %d due commitment reminder(s)", count)
    return count
