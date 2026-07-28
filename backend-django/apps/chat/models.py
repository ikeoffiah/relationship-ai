"""The couple's own conversation.

This is the partner-to-partner thread — distinct from a counseling session with
the AI. One relationship has exactly one thread, which is why messages hang off
``Relationship`` rather than off a session.

Message bodies are encrypted at rest with a key derived from the relationship
id, not from a single user id: both partners read the same thread, and Bliss
needs to read it too in order to offer a rephrase or notice that something is
about to land badly. That is a deliberate trade — this cannot be an
end-to-end-encrypted product and still coach the conversation — and it is why
the couple can switch assistance off entirely (see ``ChatSettings``).
"""

import uuid

from django.conf import settings
from django.db import models

from apps.relationships.models import Relationship
from utils.encryption import decrypt, encrypt


class CoupleMessage(models.Model):
    """A single message in the couple's thread."""

    KIND_TEXT = "text"
    KIND_STICKER = "sticker"
    KIND_SYSTEM = "system"
    KIND_CHOICES = [
        (KIND_TEXT, "Text"),
        (KIND_STICKER, "Sticker"),
        # System messages narrate something that happened (a call ended, Bliss
        # scheduled something) and are authored by no one.
        (KIND_SYSTEM, "System"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    relationship = models.ForeignKey(
        Relationship, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_couple_messages",
        null=True,
        blank=True,
        help_text="Null for system messages.",
    )
    kind = models.CharField(max_length=16, choices=KIND_CHOICES, default=KIND_TEXT)

    # Encrypted body. Never read directly — use the `body` property.
    ciphertext = models.TextField(blank=True, default="")

    # Sticker identifier when kind == sticker (the art ships with the client, so
    # only the id travels).
    sticker = models.CharField(max_length=64, blank=True, default="")

    # WhatsApp-style quote reply. Constrained to the same thread in clean().
    reply_to = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replies",
    )

    # Client-generated id, so a retried send after a dropped connection updates
    # the optimistic bubble instead of duplicating it.
    client_id = models.CharField(max_length=64, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    # Soft delete: the row survives so replies pointing at it still render
    # ("this message was deleted") rather than dangling.
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "couple_messages"
        ordering = ["created_at", "id"]
        indexes = [
            # The history query: newest-first within one thread.
            models.Index(fields=["relationship", "-created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["relationship", "client_id"],
                condition=models.Q(client_id__gt=""),
                name="unique_client_id_per_thread",
            ),
        ]

    # ── Body ────────────────────────────────────────────────────────────────
    # Encryption is keyed on the relationship so either partner (and Bliss) can
    # read the thread, unlike the per-user keys used for private material.

    @property
    def body(self) -> str:
        if self.deleted_at is not None or not self.ciphertext:
            return ""
        try:
            return decrypt(self.ciphertext, str(self.relationship_id))
        except Exception:
            # A body we cannot decrypt must not take down the whole thread.
            return ""

    @body.setter
    def body(self, value: str) -> None:
        self.ciphertext = encrypt(value or "", str(self.relationship_id)) if value else ""

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def __str__(self) -> str:
        return f"Message {self.id} in relationship {self.relationship_id}"


class MessageReaction(models.Model):
    """An emoji reaction. One row per (message, user, emoji), so a person can
    leave several different reactions but never the same one twice."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(
        CoupleMessage, on_delete=models.CASCADE, related_name="reactions"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reactions"
    )
    # Emoji are multi-codepoint (ZWJ sequences, skin-tone modifiers), so this is
    # deliberately roomy rather than a single character.
    emoji = models.CharField(max_length=32)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "couple_message_reactions"
        constraints = [
            models.UniqueConstraint(
                fields=["message", "user", "emoji"], name="unique_reaction_per_user"
            ),
        ]
        indexes = [models.Index(fields=["message"])]

    def __str__(self) -> str:
        return f"{self.emoji} on {self.message_id}"


class ReadReceipt(models.Model):
    """How far through the thread each partner has got.

    Two high-water timestamps rather than per-message rows: the unread count is
    one comparison, delivery status is one comparison, and neither can go
    backwards. Per-message receipt rows would mean one write per message per
    partner and a join on every history page, to answer a question two integers
    already answer.

    ``last_delivered_at`` is how far the partner's *device* has received —
    reaching the phone, not reaching their attention. ``last_read_at`` is how
    far they have actually opened. The pair is what makes a sender's ticks
    honest: one tick means we hold it, two means their phone holds it, two in
    colour means they looked. Collapsing the two would force us to call a
    message "read" the moment it was delivered, which is the specific lie that
    makes read receipts feel untrustworthy.

    Delivery is necessarily client-asserted — only the receiving device knows
    it has the message — so this is an acknowledgement, not a proof. That is
    also true of every chat app that shows two ticks.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    relationship = models.ForeignKey(
        Relationship, on_delete=models.CASCADE, related_name="read_receipts"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="read_receipts"
    )
    last_read_at = models.DateTimeField()
    # Null on rows written before delivery tracking existed. Those threads
    # simply show one tick until the partner's app next opens, which is the
    # honest reading: we genuinely do not know that it arrived.
    last_delivered_at = models.DateTimeField(null=True, blank=True)

    def advance(self, *, delivered_at=None, read_at=None) -> bool:
        """Move the cursors forward. Returns True if anything actually moved.

        Reading implies delivery — you cannot open a message that never
        arrived — so a read that outruns the delivery cursor drags it along.
        Without that, a message read straight from a push notification would be
        stuck showing one tick behind a blue one.
        """
        moved = False
        if read_at is not None and read_at > self.last_read_at:
            self.last_read_at = read_at
            moved = True
        effective = max(filter(None, [delivered_at, read_at]), default=None)
        if effective is not None and (
            self.last_delivered_at is None or effective > self.last_delivered_at
        ):
            self.last_delivered_at = effective
            moved = True
        return moved

    class Meta:
        db_table = "couple_read_receipts"
        constraints = [
            models.UniqueConstraint(
                fields=["relationship", "user"], name="unique_receipt_per_user"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} read {self.relationship_id} to {self.last_read_at}"


class ChatAssistSettings(models.Model):
    """Whether Bliss may participate in this couple's thread.

    Two separate switches, because they are different asks. ``assist_enabled``
    governs whether Bliss reads the thread at all — turning it off disables
    every feature below. ``interception_enabled`` governs only the unprompted
    "this might land badly" warning, which some couples will want off even
    while keeping rephrase-on-demand.

    Both partners share one row: this is a joint decision about a shared space,
    not a per-user preference one partner could impose on the other.
    """

    relationship = models.OneToOneField(
        Relationship, on_delete=models.CASCADE, related_name="chat_assist"
    )
    assist_enabled = models.BooleanField(default=True)
    interception_enabled = models.BooleanField(default=True)
    # Quiet hours for the nightly suggestion, in the couple's local hour.
    night_nudge_enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "couple_chat_assist_settings"

    def __str__(self) -> str:
        return f"Assist settings for {self.relationship_id}"


class AssistNudge(models.Model):
    """A suggestion Bliss offered, unprompted.

    Recorded rather than fired-and-forgotten for two reasons: it enforces the
    daily budget (an assist that appears constantly stops being an assist and
    becomes a nag), and it is the only way to learn which kinds are actually
    worth showing — an unacted nudge is a nudge that should probably not have
    fired.
    """

    KIND_NIGHT = "night"
    KIND_OPPORTUNITY = "opportunity"
    KIND_REPAIR = "repair"
    KIND_CHOICES = [
        (KIND_NIGHT, "End of day"),
        (KIND_OPPORTUNITY, "Opening in the conversation"),
        (KIND_REPAIR, "Way back in after a rough exchange"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    relationship = models.ForeignKey(
        Relationship, on_delete=models.CASCADE, related_name="assist_nudges"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assist_nudges"
    )
    kind = models.CharField(max_length=16, choices=KIND_CHOICES)
    suggestion = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    # Set when the suggestion was sent (possibly edited); the signal that it landed.
    acted_at = models.DateTimeField(null=True, blank=True)
    dismissed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "couple_assist_nudges"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["relationship", "user", "-created_at"])]

    def __str__(self) -> str:
        return f"{self.kind} nudge for {self.user_id}"


class ThreadSummary(models.Model):
    """A rolling précis of the conversation so far.

    The pre-send check reads the last handful of messages verbatim, which keeps
    its cost flat however long a couple has been together — but it also means
    it cannot see a pattern that spans weeks. This closes that gap without
    reintroducing unbounded input: a few hundred tokens of recurring themes,
    refreshed periodically, prepended to the verbatim window.

    Refreshed **asynchronously**, never on the send path. Summarising costs a
    whole extra model round-trip, and paying that while someone waits to send a
    message would undo the latency work entirely.
    """

    relationship = models.OneToOneField(
        Relationship, on_delete=models.CASCADE, related_name="thread_summary"
    )
    summary = models.TextField(blank=True, default="")
    # Message count when this was written, so we know when it has drifted.
    covered_message_count = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "couple_thread_summaries"

    def __str__(self) -> str:
        return f"Summary for {self.relationship_id} @ {self.covered_message_count} msgs"


# Re-exported so background tasks can import everything from one place.
Relationship = Relationship
