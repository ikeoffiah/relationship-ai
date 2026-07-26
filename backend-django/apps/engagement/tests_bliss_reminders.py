"""Tests for the @bliss due-reminder sweep (apps/engagement/tasks.py)."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.engagement.models import BlissItem
from apps.engagement.tasks import _deliver
from apps.notifications.notification_models import Notification
from apps.relationships.models import Relationship

User = get_user_model()


def make_couple():
    a = User.objects.create_user(email="a@e.com", password="pw", full_name="Alex")
    b = User.objects.create_user(email="b@e.com", password="pw", full_name="Blake")
    rel = Relationship.objects.create(partner_a=a, partner_b=b, status="active")
    return a, b, rel


class DeliverDueRemindersTests(APITestCase):
    def setUp(self):
        self.a, self.b, self.rel = make_couple()
        self.now = timezone.now()

    def _item(self, **kwargs):
        defaults = dict(
            relationship=self.rel, created_by=self.a, kind="reminder",
            title="call the venue", due_at=self.now - timedelta(minutes=1),
        )
        defaults.update(kwargs)
        return BlissItem.objects.create(**defaults)

    def test_due_reminder_notifies_both_partners(self):
        item = self._item()
        delivered = _deliver(now=self.now)
        self.assertEqual(delivered, 1)
        # Both partners get a bliss_reminder notification.
        self.assertTrue(Notification.objects.filter(user_id=self.a.id, type="bliss_reminder").exists())
        self.assertTrue(Notification.objects.filter(user_id=self.b.id, type="bliss_reminder").exists())
        item.refresh_from_db()
        self.assertIsNotNone(item.reminded_at)

    def test_future_reminder_does_not_fire(self):
        self._item(due_at=self.now + timedelta(hours=1))
        self.assertEqual(_deliver(now=self.now), 0)
        self.assertEqual(Notification.objects.filter(type="bliss_reminder").count(), 0)

    def test_undated_item_does_not_fire(self):
        self._item(due_at=None)
        self.assertEqual(_deliver(now=self.now), 0)

    def test_non_pending_items_do_not_fire(self):
        self._item(status="done")
        self._item(status="cancelled")
        self.assertEqual(_deliver(now=self.now), 0)

    def test_sweep_is_idempotent(self):
        self._item()
        self.assertEqual(_deliver(now=self.now), 1)
        # A second sweep at a later time must not re-fire the same reminder.
        self.assertEqual(_deliver(now=self.now + timedelta(minutes=10)), 0)
        self.assertEqual(Notification.objects.filter(type="bliss_reminder").count(), 2)  # a + b, once

    def test_solo_item_notifies_creator_only(self):
        solo = User.objects.create_user(email="s@e.com", password="pw", full_name="Sol")
        BlissItem.objects.create(
            relationship=None, created_by=solo, title="water plants",
            due_at=self.now - timedelta(minutes=1),
        )
        self.assertEqual(_deliver(now=self.now), 1)
        self.assertEqual(Notification.objects.filter(user_id=solo.id, type="bliss_reminder").count(), 1)

    def test_event_kind_also_fires(self):
        self._item(kind="event", title="anniversary dinner")
        self.assertEqual(_deliver(now=self.now), 1)
