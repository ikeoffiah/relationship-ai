"""Tests for the @bliss assistant: the NL parser and the API."""

from datetime import datetime, timedelta, timezone as dt_timezone
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase as DjangoTestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.engagement.bliss import is_bliss_command, parse_bliss_command
from apps.engagement.models import BlissItem
from apps.notifications.notification_models import Notification
from apps.relationships.models import Relationship

User = get_user_model()

# A fixed "now": Monday 2026-07-20, 10:00 UTC. Weekday math below is relative
# to this Monday.
NOW = datetime(2026, 7, 20, 10, 0, tzinfo=dt_timezone.utc)


# ── Parser (deterministic, `now` injected) ───────────────────────────────

class BlissParserTests(APITestCase):
    def test_non_bliss_text_is_ignored(self):
        self.assertFalse(is_bliss_command("let's have dinner"))
        self.assertIsNone(parse_bliss_command("let's have dinner", now=NOW))

    def test_undated_reminder(self):
        d = parse_bliss_command("@bliss remind us to water the plants", now=NOW)
        assert d is not None
        self.assertEqual(d.kind, "reminder")
        self.assertEqual(d.title, "water the plants")
        self.assertIsNone(d.due_at)
        self.assertFalse(d.has_time)

    def test_tomorrow_with_clock_time(self):
        d = parse_bliss_command("@bliss remind me to call the venue tomorrow at 5pm", now=NOW)
        self.assertEqual(d.kind, "reminder")  # timed task, still a reminder
        self.assertEqual(d.title, "call the venue")
        self.assertTrue(d.has_time)
        self.assertEqual(d.due_at.date().isoformat(), "2026-07-21")
        self.assertEqual((d.due_at.hour, d.due_at.minute), (17, 0))

    def test_relative_offset_hours(self):
        d = parse_bliss_command("@bliss remind me to take meds in 2 hours", now=NOW)
        self.assertEqual(d.title, "take meds")
        self.assertTrue(d.has_time)
        self.assertEqual(d.due_at, datetime(2026, 7, 20, 12, 0, tzinfo=dt_timezone.utc))

    def test_next_weekday_jumps_a_full_week(self):
        # From Monday 7/20, "next friday" is 7/31 (not the 24th).
        d = parse_bliss_command("@bliss book anniversary dinner next friday at 7pm", now=NOW)
        self.assertEqual(d.kind, "event")  # "dinner"/"anniversary" => calendar event
        self.assertEqual(d.title, "anniversary dinner")
        self.assertEqual(d.due_at.date().isoformat(), "2026-07-31")
        self.assertEqual(d.due_at.hour, 19)

    def test_bare_weekday_is_the_upcoming_one(self):
        # From Monday 7/20, a bare "friday" is 7/24.
        d = parse_bliss_command("@bliss remind us to pay rent on friday", now=NOW)
        self.assertEqual(d.due_at.date().isoformat(), "2026-07-24")
        self.assertFalse(d.has_time)  # no clock time given

    def test_time_only_rolls_to_tomorrow_if_passed(self):
        # 8am is already past 10am "now" -> tomorrow.
        d = parse_bliss_command("@bliss remind me to stretch at 8am", now=NOW)
        self.assertEqual(d.due_at.date().isoformat(), "2026-07-21")
        self.assertEqual(d.due_at.hour, 8)

    def test_tonight(self):
        d = parse_bliss_command("@bliss remind us to talk tonight", now=NOW)
        self.assertEqual(d.due_at.date().isoformat(), "2026-07-20")
        self.assertEqual(d.due_at.hour, 19)
        self.assertTrue(d.has_time)

    def test_event_word_without_lead_verb(self):
        d = parse_bliss_command("@bliss dinner with friends on saturday", now=NOW)
        self.assertEqual(d.kind, "event")
        self.assertEqual(d.title, "dinner with friends")
        self.assertEqual(d.due_at.date().isoformat(), "2026-07-25")

    def test_tag_only_has_no_task(self):
        self.assertIsNone(parse_bliss_command("@bliss", now=NOW))


# ── API ──────────────────────────────────────────────────────────────────

def make_couple():
    a = User.objects.create_user(email="a@e.com", password="pw", full_name="Alex")
    b = User.objects.create_user(email="b@e.com", password="pw", full_name="Blake")
    rel = Relationship.objects.create(partner_a=a, partner_b=b, status="active")
    return a, b, rel


class BlissApiTests(APITestCase):
    def setUp(self):
        self.a, self.b, self.rel = make_couple()
        self.client.force_authenticate(self.a)

    def test_interpret_recognizes_a_command(self):
        r = self.client.post(
            "/api/v1/engagement/bliss/interpret",
            {"text": "@bliss remind us to call the caterer tomorrow at 3pm"},
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(r.data["recognized"])
        self.assertEqual(r.data["draft"]["title"], "call the caterer")

    def test_interpret_unrecognized(self):
        r = self.client.post(
            "/api/v1/engagement/bliss/interpret", {"text": "just chatting, no tag"}
        )
        self.assertFalse(r.data["recognized"])

    def test_interpret_requires_text(self):
        r = self.client.post("/api/v1/engagement/bliss/interpret", {})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_item_notifies_partner(self):
        r = self.client.post(
            "/api/v1/engagement/bliss/items",
            {"kind": "reminder", "title": "call the caterer", "due_at": "2026-07-21T15:00:00Z"},
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(BlissItem.objects.count(), 1)
        # The PARTNER is notified, not the creator.
        self.assertTrue(Notification.objects.filter(user_id=self.b.id, type="bliss_created").exists())
        self.assertFalse(Notification.objects.filter(user_id=self.a.id, type="bliss_created").exists())

    def test_list_returns_couple_pending_items(self):
        BlissItem.objects.create(relationship=self.rel, created_by=self.a, title="one")
        BlissItem.objects.create(relationship=self.rel, created_by=self.b, title="two")
        BlissItem.objects.create(
            relationship=self.rel, created_by=self.a, title="done one", status="done"
        )
        r = self.client.get("/api/v1/engagement/bliss/items")
        titles = {i["title"] for i in r.data["items"]}
        self.assertEqual(titles, {"one", "two"})  # done item excluded

    def test_complete_and_cancel(self):
        item = BlissItem.objects.create(relationship=self.rel, created_by=self.a, title="x")
        r = self.client.post(f"/api/v1/engagement/bliss/items/{item.id}/done")
        self.assertEqual(r.data["status"], "done")
        r = self.client.post(f"/api/v1/engagement/bliss/items/{item.id}/cancel")
        self.assertEqual(r.data["status"], "cancelled")

    def test_cannot_touch_another_couples_item(self):
        item = BlissItem.objects.create(relationship=self.rel, created_by=self.a, title="private")
        outsider = User.objects.create_user(email="c@e.com", password="pw", full_name="Cass")
        self.client.force_authenticate(outsider)
        r = self.client.post(f"/api/v1/engagement/bliss/items/{item.id}/done")
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)
        r = self.client.get("/api/v1/engagement/bliss/items")
        self.assertEqual(r.data["items"], [])

    def test_auth_required(self):
        self.client.force_authenticate(user=None)
        for method, path in [
            ("post", "/api/v1/engagement/bliss/interpret"),
            ("get", "/api/v1/engagement/bliss/items"),
        ]:
            resp = getattr(self.client, method)(path)
            self.assertIn(resp.status_code, (401, 403))


class BlissThreadAnnouncementTests(DjangoTestCase):
    """A @bliss item raised inside the couple thread should show up there.

    The property that matters most is the negative one: an item created
    anywhere else must NOT post into the thread, because doing so would tell a
    partner that the other was in a private counseling session.
    """

    def setUp(self):
        from apps.chat.models import CoupleMessage

        self.CoupleMessage = CoupleMessage
        self.alex = User.objects.create_user(email="a@t.local", password="pw12345!")
        self.sam = User.objects.create_user(email="s@t.local", password="pw12345!")
        self.relationship = Relationship.objects.create(
            partner_a=self.alex, partner_b=self.sam, status="active"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.alex)
        self.url = reverse("engagement-bliss-items")

    def create(self, **overrides):
        payload = {
            "kind": "reminder",
            "title": "call the venue",
            "due_at": (timezone.now() + timedelta(days=1)).isoformat(),
            "source": "couple_chat",
        }
        payload.update(overrides)
        return self.client.post(self.url, payload, format="json")

    def thread(self):
        return self.CoupleMessage.objects.filter(relationship=self.relationship)

    def test_a_couple_chat_item_posts_a_system_message(self):
        response = self.create()
        self.assertEqual(response.status_code, 201)

        message = self.thread().get()
        self.assertEqual(message.kind, "system")
        self.assertIsNone(message.sender_id)
        self.assertIn("call the venue", message.body)

    def test_an_item_from_elsewhere_stays_out_of_the_thread(self):
        # The privacy case. An item raised in a private counseling session must
        # not announce itself to the partner.
        self.create(source="bliss")
        self.create(source="manual")
        self.assertEqual(self.thread().count(), 0)

    def test_the_announcement_carries_the_time(self):
        due = timezone.now() + timedelta(days=2)
        self.create(due_at=due.isoformat())
        self.assertIn(due.strftime("%a"), self.thread().get().body)

    def test_an_undated_item_still_announces(self):
        self.create(due_at=None)
        self.assertIn("call the venue", self.thread().get().body)

    def test_a_broken_announcement_does_not_lose_the_reminder(self):
        """A missing line in a thread is a cosmetic failure. A reminder that
        never saved is a promise broken, so the announcement must not be able
        to take the item down with it."""
        with patch(
            "apps.chat.models.CoupleMessage.save", side_effect=RuntimeError("boom")
        ):
            response = self.create()
        self.assertEqual(response.status_code, 201)
        self.assertTrue(BlissItem.objects.filter(title="call the venue").exists())

    def test_a_solo_user_gets_no_announcement(self):
        solo = User.objects.create_user(email="solo@t.local", password="pw12345!")
        client = APIClient()
        client.force_authenticate(user=solo)
        response = client.post(
            self.url,
            {"kind": "reminder", "title": "water the plants", "source": "couple_chat"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.CoupleMessage.objects.count(), 0)


class CalendarInviteTests(DjangoTestCase):
    """Tagging a partner asks them; it does not schedule them.

    Most of these are access-control tests, because the feature is only worth
    anything if the person who sends an invite cannot answer it.
    """

    def setUp(self):
        self.alex = User.objects.create_user(email="ci-a@t.local", password="pw12345!")
        self.sam = User.objects.create_user(email="ci-b@t.local", password="pw12345!")
        self.relationship = Relationship.objects.create(
            partner_a=self.alex, partner_b=self.sam, status="active"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.alex)
        self.partner = APIClient()
        self.partner.force_authenticate(user=self.sam)

    def create(self, invite=True, **kw):
        payload = {
            "kind": "event",
            "title": "dinner out",
            "due_at": (timezone.now() + timedelta(days=1)).isoformat(),
            "invite_partner": invite,
        }
        payload.update(kw)
        return self.client.post(reverse("engagement-bliss-items"), payload, format="json")

    def respond(self, item_id, accept, client=None):
        return (client or self.partner).post(
            reverse("engagement-bliss-respond", args=[item_id]),
            {"accept": accept},
            format="json",
        )

    # ── The invite ───────────────────────────────────────────────────────

    def test_tagging_the_partner_leaves_it_waiting_on_them(self):
        body = self.create().json()
        self.assertEqual(body["partner_invite"], "pending")

    def test_not_tagging_leaves_it_untagged(self):
        self.assertEqual(self.create(invite=False).json()["partner_invite"], "none")

    def test_the_partner_is_asked_rather_than_told(self):
        self.create()
        note = Notification.objects.filter(user_id=self.sam.id).latest("created_at")
        self.assertEqual(note.type, "bliss_invite")
        self.assertIn("yes or no", note.body)

    def test_accepting_records_who_and_when(self):
        item_id = self.create().json()["id"]
        body = self.respond(item_id, True).json()
        self.assertEqual(body["partner_invite"], "accepted")
        self.assertIsNotNone(body["partner_responded_at"])

    def test_declining_is_recorded_and_the_asker_is_told(self):
        item_id = self.create().json()["id"]
        self.respond(item_id, False)
        self.assertEqual(
            BlissItem.objects.get(id=item_id).partner_invite, "declined"
        )
        note = Notification.objects.filter(user_id=self.alex.id).latest("created_at")
        self.assertIn("said no", note.body)

    def test_an_answer_can_be_changed(self):
        """Declining on Tuesday and accepting on Thursday should not need a
        fresh invitation."""
        item_id = self.create().json()["id"]
        self.respond(item_id, False)
        self.respond(item_id, True)
        self.assertEqual(BlissItem.objects.get(id=item_id).partner_invite, "accepted")

    # ── Who may answer ───────────────────────────────────────────────────

    def test_you_cannot_accept_your_own_invitation(self):
        """The whole feature rests on this. Without it, tagging your partner
        and accepting for them is two API calls."""
        item_id = self.create().json()["id"]
        response = self.respond(item_id, True, client=self.client)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(BlissItem.objects.get(id=item_id).partner_invite, "pending")

    def test_a_stranger_gets_a_404_not_a_403(self):
        stranger = APIClient()
        stranger.force_authenticate(
            user=User.objects.create_user(email="ci-x@t.local", password="pw12345!")
        )
        item_id = self.create().json()["id"]
        self.assertEqual(self.respond(item_id, True, client=stranger).status_code, 404)

    def test_you_cannot_answer_something_you_were_not_asked_about(self):
        item_id = self.create(invite=False).json()["id"]
        self.assertEqual(self.respond(item_id, True).status_code, 400)

    def test_only_the_asked_partner_sees_an_answer_prompt(self):
        item_id = self.create().json()["id"]
        mine = self.client.get(reverse("engagement-bliss-items")).json()["items"]
        theirs = self.partner.get(reverse("engagement-bliss-items")).json()["items"]
        self.assertFalse(next(i for i in mine if i["id"] == item_id)["awaiting_my_answer"])
        self.assertTrue(next(i for i in theirs if i["id"] == item_id)["awaiting_my_answer"])

    # ── The reminder gate ────────────────────────────────────────────────

    def test_a_pending_invite_does_not_alarm_the_partner(self):
        """Silence is the commonest response to a notification. Reading it as
        a yes would make tagging someone a way to put an alarm in their pocket
        for something they never agreed to."""
        from apps.engagement.tasks import _recipients

        item = BlissItem.objects.get(id=self.create().json()["id"])
        self.assertEqual(_recipients(item), [self.alex.id])

    def test_a_declined_invite_does_not_alarm_the_partner(self):
        from apps.engagement.tasks import _recipients

        item_id = self.create().json()["id"]
        self.respond(item_id, False)
        item = BlissItem.objects.get(id=item_id)
        self.assertEqual(_recipients(item), [self.alex.id])

    def test_an_accepted_invite_alarms_both(self):
        from apps.engagement.tasks import _recipients

        item_id = self.create().json()["id"]
        self.respond(item_id, True)
        item = BlissItem.objects.get(id=item_id)
        self.assertCountEqual(_recipients(item), [self.alex.id, self.sam.id])

    def test_an_untagged_item_still_reminds_both(self):
        """Existing behaviour, deliberately preserved: not tagging someone is a
        shared plan, not a request, and those already reminded both."""
        from apps.engagement.tasks import _recipients

        item = BlissItem.objects.get(id=self.create(invite=False).json()["id"])
        self.assertCountEqual(_recipients(item), [self.alex.id, self.sam.id])

    def test_a_solo_user_cannot_leave_an_item_waiting_forever(self):
        solo = User.objects.create_user(email="ci-solo@t.local", password="pw12345!")
        client = APIClient()
        client.force_authenticate(user=solo)
        body = client.post(
            reverse("engagement-bliss-items"),
            {"kind": "event", "title": "gym", "invite_partner": True},
            format="json",
        ).json()
        self.assertEqual(body["partner_invite"], "none")

    # ── The calendar feed ────────────────────────────────────────────────

    def test_the_calendar_groups_by_day(self):
        self.create(due_at=(timezone.now() + timedelta(days=1)).isoformat())
        body = self.client.get(reverse("engagement-bliss-calendar")).json()
        self.assertEqual(len(body["days"]), 1)
        self.assertEqual(len(next(iter(body["days"].values()))), 1)

    def test_the_calendar_respects_the_window(self):
        self.create(due_at=(timezone.now() + timedelta(days=40)).isoformat())
        url = reverse("engagement-bliss-calendar")
        near = self.client.get(
            url, {"to": (timezone.now() + timedelta(days=7)).isoformat()}
        ).json()
        self.assertEqual(near["items"], [])

    def test_undated_items_stay_off_the_calendar(self):
        """They belong on the plan list. A to-do with no time is not a day."""
        self.create(due_at=None)
        self.assertEqual(self.client.get(reverse("engagement-bliss-calendar")).json()["items"], [])

    def test_cancelled_items_stay_off_the_calendar(self):
        item_id = self.create().json()["id"]
        self.client.post(reverse("engagement-bliss-cancel", args=[item_id]))
        self.assertEqual(self.client.get(reverse("engagement-bliss-calendar")).json()["items"], [])

    def test_the_calendar_is_scoped_to_your_own_couple(self):
        self.create()
        other = User.objects.create_user(email="ci-o@t.local", password="pw12345!")
        client = APIClient()
        client.force_authenticate(user=other)
        self.assertEqual(client.get(reverse("engagement-bliss-calendar")).json()["items"], [])
