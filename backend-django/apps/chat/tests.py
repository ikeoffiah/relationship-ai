"""Tests for the couple thread.

Grouped by the property under test rather than by endpoint, because the things
most likely to hurt someone here are cross-cutting: a thread leaking to a third
party, a deleted message still being readable, a retry double-posting.
"""

import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.chat.models import CoupleMessage, MessageReaction, ReadReceipt
from apps.relationships.models import Relationship

User = get_user_model()


class ChatTestCase(TestCase):
    """A connected couple, plus an unrelated stranger for access-control tests."""

    def setUp(self):
        self.alex = User.objects.create_user(email="alex@test.local", password="pw12345!")
        self.sam = User.objects.create_user(email="sam@test.local", password="pw12345!")
        self.stranger = User.objects.create_user(
            email="stranger@test.local", password="pw12345!"
        )
        self.relationship = Relationship.objects.create(
            partner_a=self.alex, partner_b=self.sam, status="active"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.alex)

        # Realtime delivery is a side effect, not the unit under test. Patched
        # off by default so tests don't need Redis; asserted explicitly in
        # RealtimeDeliveryTests.
        patcher = patch("apps.chat.views.realtime.publish", return_value=True)
        self.publish = patcher.start()
        self.addCleanup(patcher.stop)

    # helpers
    def send_url(self):
        return reverse("chat-send", args=[self.relationship.id])

    def list_url(self):
        return reverse("chat-messages", args=[self.relationship.id])

    def make_message(self, sender=None, body="hello", **kwargs):
        msg = CoupleMessage(
            relationship=kwargs.pop("relationship", self.relationship),
            sender=sender or self.alex,
            **kwargs,
        )
        msg.body = body
        msg.save()
        return msg


class AccessControlTests(ChatTestCase):
    """A thread belongs to exactly two people."""

    def test_stranger_cannot_read_the_thread(self):
        self.make_message(body="something private")
        self.client.force_authenticate(user=self.stranger)

        response = self.client.get(self.list_url())

        # 404 rather than 403: probing ids must not confirm a thread exists.
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_stranger_cannot_send_into_the_thread(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.post(self.send_url(), {"body": "hi"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(CoupleMessage.objects.count(), 0)

    def test_stranger_cannot_react(self):
        msg = self.make_message()
        self.client.force_authenticate(user=self.stranger)

        response = self.client.post(
            reverse("chat-react", args=[msg.id]), {"emoji": "😍"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(MessageReaction.objects.count(), 0)

    def test_stranger_cannot_mark_read(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.post(reverse("chat-mark-read", args=[self.relationship.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_both_partners_can_read_the_same_thread(self):
        self.make_message(sender=self.alex, body="from alex")
        for user in (self.alex, self.sam):
            self.client.force_authenticate(user=user)
            response = self.client.get(self.list_url())
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["results"][0]["body"], "from alex")

    def test_unauthenticated_is_rejected(self):
        self.client.force_authenticate(user=None)
        self.assertIn(
            self.client.get(self.list_url()).status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )


class SendMessageTests(ChatTestCase):
    def test_send_text_message(self):
        response = self.client.post(
            self.send_url(), {"body": "I picked up your coffee ☕"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["body"], "I picked up your coffee ☕")
        self.assertEqual(response.data["sender_id"], str(self.alex.id))
        self.assertEqual(response.data["kind"], "text")

    def test_send_sticker_message(self):
        response = self.client.post(
            self.send_url(), {"kind": "sticker", "sticker": "heart_eyes"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["sticker"], "heart_eyes")

    def test_empty_body_is_rejected(self):
        for payload in ({"body": ""}, {"body": "    "}, {}):
            response = self.client.post(self.send_url(), payload, format="json")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(CoupleMessage.objects.count(), 0)

    def test_sticker_kind_requires_a_sticker(self):
        response = self.client.post(self.send_url(), {"kind": "sticker"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_a_client_cannot_forge_a_system_message(self):
        """System messages are narrated by the server, never by a partner."""
        response = self.client.post(
            self.send_url(), {"kind": "system", "body": "Alex left"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_body_is_encrypted_at_rest(self):
        secret = "something we would not want sitting in plaintext"
        self.client.post(self.send_url(), {"body": secret}, format="json")

        stored = CoupleMessage.objects.get()
        self.assertNotIn(secret, stored.ciphertext)
        self.assertTrue(stored.ciphertext)
        # ...and still round-trips for both partners.
        self.assertEqual(stored.body, secret)

    def test_whitespace_is_trimmed(self):
        response = self.client.post(self.send_url(), {"body": "  hey  "}, format="json")
        self.assertEqual(response.data["body"], "hey")


class IdempotencyTests(ChatTestCase):
    """A retry after a dropped response must not double-post."""

    def test_same_client_id_returns_the_original_message(self):
        first = self.client.post(
            self.send_url(), {"body": "hi", "client_id": "abc-123"}, format="json"
        )
        second = self.client.post(
            self.send_url(), {"body": "hi", "client_id": "abc-123"}, format="json"
        )

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        # 200, not 201 — nothing new was created.
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(CoupleMessage.objects.count(), 1)

    def test_blank_client_ids_do_not_collide(self):
        """Clients that send no id must still be able to send twice."""
        self.client.post(self.send_url(), {"body": "one"}, format="json")
        self.client.post(self.send_url(), {"body": "two"}, format="json")
        self.assertEqual(CoupleMessage.objects.count(), 2)

    def test_client_ids_are_scoped_per_thread(self):
        other_rel = Relationship.objects.create(
            partner_a=self.alex, partner_b=self.stranger, status="active"
        )
        self.client.post(self.send_url(), {"body": "a", "client_id": "dup"}, format="json")
        response = self.client.post(
            reverse("chat-send", args=[other_rel.id]),
            {"body": "b", "client_id": "dup"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class ReplyTests(ChatTestCase):
    def test_reply_carries_a_quote_preview(self):
        parent = self.make_message(sender=self.sam, body="are we still on for friday?")

        response = self.client.post(
            self.send_url(),
            {"body": "yes! booked it", "reply_to": str(parent.id)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        preview = response.data["reply_to"]
        self.assertEqual(preview["id"], str(parent.id))
        self.assertEqual(preview["body"], "are we still on for friday?")
        self.assertEqual(preview["sender_id"], str(self.sam.id))

    def test_cannot_reply_to_a_message_in_another_thread(self):
        """Otherwise the quote preview leaks a line of someone else's thread."""
        other_rel = Relationship.objects.create(
            partner_a=self.stranger, partner_b=None, status="pending"
        )
        foreign = self.make_message(
            sender=self.stranger, body="another couple's message", relationship=other_rel
        )

        response = self.client.post(
            self.send_url(), {"body": "hi", "reply_to": str(foreign.id)}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(CoupleMessage.objects.filter(relationship=self.relationship).count(), 0)

    def test_reply_to_unknown_id_is_rejected(self):
        response = self.client.post(
            self.send_url(), {"body": "hi", "reply_to": str(uuid.uuid4())}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reply_survives_the_parent_being_deleted(self):
        parent = self.make_message(sender=self.alex, body="original")
        reply = self.make_message(sender=self.sam, body="responding", reply_to=parent)

        self.client.delete(reverse("chat-delete", args=[parent.id]))

        response = self.client.get(self.list_url())
        rendered = {m["id"]: m for m in response.data["results"]}
        # The reply still renders, and its quote shows a tombstone rather than
        # the deleted text.
        self.assertEqual(rendered[str(reply.id)]["body"], "responding")
        self.assertEqual(rendered[str(reply.id)]["reply_to"]["body"], "")
        self.assertTrue(rendered[str(reply.id)]["reply_to"]["is_deleted"])


class DeleteTests(ChatTestCase):
    def test_author_can_delete_their_own_message(self):
        msg = self.make_message(sender=self.alex, body="oops")
        response = self.client.delete(reverse("chat-delete", args=[msg.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        msg.refresh_from_db()
        self.assertTrue(msg.is_deleted)

    def test_deleting_destroys_the_ciphertext(self):
        """A soft delete keeps the row for replies — it must not keep the text."""
        msg = self.make_message(sender=self.alex, body="please forget this")
        self.client.delete(reverse("chat-delete", args=[msg.id]))

        msg.refresh_from_db()
        self.assertEqual(msg.ciphertext, "")
        self.assertEqual(msg.body, "")

    def test_cannot_delete_your_partners_message(self):
        msg = self.make_message(sender=self.sam, body="theirs")
        response = self.client.delete(reverse("chat-delete", args=[msg.id]))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        msg.refresh_from_db()
        self.assertFalse(msg.is_deleted)

    def test_stranger_cannot_delete(self):
        msg = self.make_message(sender=self.alex)
        self.client.force_authenticate(user=self.stranger)
        response = self.client.delete(reverse("chat-delete", args=[msg.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_deleting_twice_is_harmless(self):
        msg = self.make_message(sender=self.alex)
        url = reverse("chat-delete", args=[msg.id])
        self.client.delete(url)
        first_deleted_at = CoupleMessage.objects.get(id=msg.id).deleted_at

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # The original deletion time is preserved rather than bumped.
        self.assertEqual(CoupleMessage.objects.get(id=msg.id).deleted_at, first_deleted_at)


class ReactionTests(ChatTestCase):
    def test_reaction_is_added_then_toggled_off(self):
        msg = self.make_message(sender=self.sam)
        url = reverse("chat-react", args=[msg.id])

        added = self.client.post(url, {"emoji": "😍"}, format="json")
        self.assertEqual(added.data["reactions"][0]["emoji"], "😍")
        self.assertEqual(added.data["reactions"][0]["count"], 1)

        removed = self.client.post(url, {"emoji": "😍"}, format="json")
        self.assertEqual(removed.data["reactions"], [])
        self.assertEqual(MessageReaction.objects.count(), 0)

    def test_reactions_group_by_emoji_across_partners(self):
        msg = self.make_message(sender=self.alex)
        url = reverse("chat-react", args=[msg.id])

        self.client.post(url, {"emoji": "🔥"}, format="json")
        self.client.force_authenticate(user=self.sam)
        response = self.client.post(url, {"emoji": "🔥"}, format="json")

        self.assertEqual(len(response.data["reactions"]), 1)
        self.assertEqual(response.data["reactions"][0]["count"], 2)

    def test_one_user_can_leave_several_different_reactions(self):
        msg = self.make_message(sender=self.sam)
        url = reverse("chat-react", args=[msg.id])
        self.client.post(url, {"emoji": "😍"}, format="json")
        response = self.client.post(url, {"emoji": "🔥"}, format="json")
        self.assertEqual(len(response.data["reactions"]), 2)

    def test_cannot_react_to_a_deleted_message(self):
        msg = self.make_message(sender=self.alex)
        self.client.delete(reverse("chat-delete", args=[msg.id]))

        response = self.client.post(
            reverse("chat-react", args=[msg.id]), {"emoji": "😍"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_empty_emoji_is_rejected(self):
        msg = self.make_message(sender=self.sam)
        response = self.client.post(
            reverse("chat-react", args=[msg.id]), {"emoji": "   "}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_reaction_cannot_be_stored_twice(self):
        """The unique constraint backs the toggle, so a race cannot double it."""
        msg = self.make_message(sender=self.sam)
        MessageReaction.objects.create(message=msg, user=self.alex, emoji="😍")
        from django.db import IntegrityError, transaction

        with self.assertRaises(IntegrityError), transaction.atomic():
            MessageReaction.objects.create(message=msg, user=self.alex, emoji="😍")


class ReadReceiptTests(ChatTestCase):
    def test_marking_read_creates_then_advances_the_mark(self):
        url = reverse("chat-mark-read", args=[self.relationship.id])

        self.client.post(url)
        first = ReadReceipt.objects.get(relationship=self.relationship, user=self.alex)
        self.client.post(url)
        second = ReadReceipt.objects.get(relationship=self.relationship, user=self.alex)

        self.assertGreaterEqual(second.last_read_at, first.last_read_at)
        self.assertEqual(ReadReceipt.objects.count(), 1)

    def test_read_mark_never_moves_backwards(self):
        future = timezone.now() + timezone.timedelta(hours=1)
        ReadReceipt.objects.create(
            relationship=self.relationship, user=self.alex, last_read_at=future
        )

        self.client.post(reverse("chat-mark-read", args=[self.relationship.id]))

        self.assertEqual(
            ReadReceipt.objects.get(relationship=self.relationship, user=self.alex).last_read_at,
            future,
        )

    def test_unread_counts_only_the_partners_messages(self):
        self.make_message(sender=self.sam, body="one")
        self.make_message(sender=self.sam, body="two")
        self.make_message(sender=self.alex, body="mine doesn't count")

        response = self.client.get(reverse("chat-unread", args=[self.relationship.id]))
        self.assertEqual(response.data["unread"], 2)

    def test_unread_drops_to_zero_after_reading(self):
        self.make_message(sender=self.sam, body="unread")
        self.client.post(reverse("chat-mark-read", args=[self.relationship.id]))

        response = self.client.get(reverse("chat-unread", args=[self.relationship.id]))
        self.assertEqual(response.data["unread"], 0)

    def test_deleted_messages_do_not_count_as_unread(self):
        msg = self.make_message(sender=self.sam, body="will be deleted")
        self.client.force_authenticate(user=self.sam)
        self.client.delete(reverse("chat-delete", args=[msg.id]))

        self.client.force_authenticate(user=self.alex)
        response = self.client.get(reverse("chat-unread", args=[self.relationship.id]))
        self.assertEqual(response.data["unread"], 0)


class HistoryPaginationTests(ChatTestCase):
    def test_history_is_newest_first(self):
        for i in range(3):
            self.make_message(body=f"m{i}")

        response = self.client.get(self.list_url())
        bodies = [m["body"] for m in response.data["results"]]
        self.assertEqual(bodies, ["m2", "m1", "m0"])

    def test_limit_and_has_more(self):
        for i in range(5):
            self.make_message(body=f"m{i}")

        response = self.client.get(self.list_url(), {"limit": 2})

        self.assertEqual(len(response.data["results"]), 2)
        self.assertTrue(response.data["has_more"])
        self.assertIsNotNone(response.data["next_before"])

    def test_cursor_walks_the_whole_thread_without_gaps_or_repeats(self):
        for i in range(7):
            self.make_message(body=f"m{i}")

        seen, cursor, guard = [], None, 0
        while guard < 10:
            guard += 1
            params = {"limit": 3}
            if cursor:
                params["before"] = cursor
            page = self.client.get(self.list_url(), params).data
            seen.extend(m["body"] for m in page["results"])
            if not page["has_more"]:
                break
            cursor = page["next_before"]

        self.assertEqual(seen, [f"m{i}" for i in reversed(range(7))])
        self.assertEqual(len(seen), len(set(seen)))

    def test_limit_is_clamped(self):
        self.make_message()
        response = self.client.get(self.list_url(), {"limit": "99999"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_garbage_limit_falls_back_to_the_default(self):
        self.make_message()
        response = self.client.get(self.list_url(), {"limit": "banana"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_one_couples_thread_never_contains_anothers_messages(self):
        other_rel = Relationship.objects.create(
            partner_a=self.stranger, partner_b=None, status="pending"
        )
        self.make_message(sender=self.stranger, body="not ours", relationship=other_rel)
        self.make_message(sender=self.alex, body="ours")

        response = self.client.get(self.list_url())

        self.assertEqual([m["body"] for m in response.data["results"]], ["ours"])


class RealtimeDeliveryTests(ChatTestCase):
    def test_send_publishes_to_the_partner_only(self):
        self.client.post(self.send_url(), {"body": "hey"}, format="json")

        self.publish.assert_called_once()
        args, kwargs = self.publish.call_args
        self.assertEqual(args[0], self.relationship.id)
        self.assertEqual(args[1]["type"], "couple_message")
        # The sender already rendered it optimistically; echoing would duplicate.
        self.assertEqual(kwargs["exclude_user_id"], self.alex.id)

    def test_delete_and_reaction_are_broadcast(self):
        msg = self.make_message(sender=self.alex)
        self.publish.reset_mock()

        self.client.delete(reverse("chat-delete", args=[msg.id]))
        self.assertEqual(self.publish.call_args[0][1]["type"], "couple_message_deleted")

        other = self.make_message(sender=self.sam)
        self.client.post(
            reverse("chat-react", args=[other.id]), {"emoji": "😍"}, format="json"
        )
        self.assertEqual(
            self.publish.call_args[0][1]["type"], "couple_message_reaction"
        )

    def test_a_failed_broadcast_does_not_lose_the_message(self):
        """Redis being down must not cost someone their message."""
        self.publish.side_effect = Exception("redis unreachable")

        with self.assertRaises(Exception):
            self.client.post(self.send_url(), {"body": "important"}, format="json")

        # The row is committed regardless of the delivery attempt.
        self.assertEqual(CoupleMessage.objects.count(), 1)


class RealtimePublisherTests(TestCase):
    """The publisher itself swallows failures rather than raising."""

    def test_publish_returns_false_when_redis_is_unavailable(self):
        from apps.chat import realtime

        with patch("redis.from_url", side_effect=Exception("down")):
            self.assertFalse(realtime.publish(uuid.uuid4(), {"type": "x"}))

    def test_channel_matches_the_broker_subscription(self):
        from apps.chat import realtime

        rid = uuid.uuid4()
        # app/counseling/broker.py subscribes to f"joint_session:{room}".
        self.assertEqual(realtime.channel_for(rid), f"joint_session:{rid}")
