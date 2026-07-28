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
    """How far through the thread each partner has read.

    Stored as a high-water timestamp rather than per-message rows: the unread
    count is one comparison, and it cannot go backwards.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    relationship = models.ForeignKey(
        Relationship, on_delete=models.CASCADE, related_name="read_receipts"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="read_receipts"
    )
    last_read_at = models.DateTimeField()

    class Meta:
        db_table = "couple_read_receipts"
        constraints = [
            models.UniqueConstraint(
                fields=["relationship", "user"], name="unique_receipt_per_user"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} read {self.relationship_id} to {self.last_read_at}"
