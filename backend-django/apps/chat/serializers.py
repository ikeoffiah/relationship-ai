"""Wire format for the couple thread."""

from rest_framework import serializers

from .models import CoupleMessage, MessageMedia


class MessageMediaSerializer(serializers.ModelSerializer):
    """A photo or voice note as the client needs it.

    The URLs point at our own proxy endpoints, never at the storage vendor.
    They have to: the blob is encrypted with a key derived from the master
    secret, so only Django can turn it back into a photo.
    """

    url = serializers.SerializerMethodField()
    thumb_url = serializers.SerializerMethodField()
    transcript = serializers.SerializerMethodField()

    class Meta:
        model = MessageMedia
        fields = [
            "id",
            "kind",
            "mime",
            "byte_size",
            "duration_ms",
            "waveform",
            "width",
            "height",
            "url",
            "thumb_url",
            "transcript",
            "transcript_status",
        ]

    def get_url(self, obj) -> str:
        return f"/api/v1/chat/media/{obj.id}"

    def get_thumb_url(self, obj) -> str | None:
        return f"/api/v1/chat/media/{obj.id}/thumb" if obj.thumb_key else None

    def get_transcript(self, obj) -> str:
        return obj.transcript


def _reactions_payload(message: CoupleMessage) -> list:
    """Group reactions by emoji.

    The client renders "😍 2" chips, not a flat list, so grouping here keeps
    that from being an N-query loop in the UI. ``mine`` drives the highlighted
    state on the reacting user's own device.
    """
    grouped: dict[str, dict] = {}
    for reaction in message.reactions.all():
        entry = grouped.setdefault(
            reaction.emoji, {"emoji": reaction.emoji, "count": 0, "user_ids": []}
        )
        entry["count"] += 1
        entry["user_ids"].append(str(reaction.user_id))
    return list(grouped.values())


class ReplyPreviewSerializer(serializers.Serializer):
    """The quoted stub shown above a reply — never the full nested chain."""

    id = serializers.UUIDField()
    sender_id = serializers.SerializerMethodField()
    body = serializers.SerializerMethodField()
    kind = serializers.CharField()
    is_deleted = serializers.BooleanField()
    thumb_url = serializers.SerializerMethodField()

    def get_sender_id(self, obj) -> str | None:
        return str(obj.sender_id) if obj.sender_id else None

    def get_body(self, obj) -> str:
        # A quote of a deleted message shows the tombstone, not the old text.
        # On a photo this is the caption, which is worth quoting; a voice note
        # has none, and the client renders a label from `kind` instead.
        return "" if obj.is_deleted else obj.body[:180]

    def get_thumb_url(self, obj) -> str | None:
        """Just enough for the quote to show the photo being replied to.

        Only the thumbnail — a quote stub must never pull the full image, and
        it must go dark the moment the media is destroyed rather than pointing
        at bytes that are gone.
        """
        if obj.is_deleted or obj.media_id is None or not obj.media.thumb_key:
            return None
        return f"/api/v1/chat/media/{obj.media_id}/thumb"


#: Delivery state of a message, from the sender's point of view. ``sending``
#: and ``failed`` never come from the server — the client owns those, because
#: only it knows about a request that has not landed yet.
STATUS_SENT = "sent"
STATUS_DELIVERED = "delivered"
STATUS_SEEN = "seen"


def message_status(message: CoupleMessage, cursor) -> str:
    """Where this message has got to, given the *partner's* thread cursor.

    Derived on read from two timestamps rather than stored per message. The
    alternative — a status column updated on every receipt — means writing to
    every unread message each time a partner opens the app, and gets the
    ordering wrong the moment two receipts race.

    ``cursor`` is the partner's :class:`ReadReceipt`, or None when there is no
    partner yet or they have never opened the thread. Both cases mean the same
    thing to a sender, and it is the truthful one: sent, not delivered.
    """
    if cursor is None:
        return STATUS_SENT
    if cursor.last_read_at and message.created_at <= cursor.last_read_at:
        return STATUS_SEEN
    if cursor.last_delivered_at and message.created_at <= cursor.last_delivered_at:
        return STATUS_DELIVERED
    return STATUS_SENT


class CoupleMessageSerializer(serializers.ModelSerializer):
    sender_id = serializers.SerializerMethodField()
    body = serializers.SerializerMethodField()
    reactions = serializers.SerializerMethodField()
    reply_to = serializers.SerializerMethodField()
    is_deleted = serializers.BooleanField(read_only=True)
    status = serializers.SerializerMethodField()
    media = serializers.SerializerMethodField()

    class Meta:
        model = CoupleMessage
        fields = [
            "id",
            "relationship",
            "sender_id",
            "kind",
            "body",
            "sticker",
            "media",
            "reply_to",
            "reactions",
            "client_id",
            "is_deleted",
            "status",
            "created_at",
            "edited_at",
        ]

    def get_status(self, obj) -> str | None:
        """Only ever populated on the reader's own messages.

        You get ticks on what you sent; you do not get to watch your own
        reading habits reported back at you, and neither partner learns
        anything about the other beyond what the other's own ticks show them.
        """
        viewer_id = self.context.get("viewer_id")
        if viewer_id is None or obj.sender_id != viewer_id:
            return None
        return message_status(obj, self.context.get("partner_cursor"))

    def get_sender_id(self, obj) -> str | None:
        return str(obj.sender_id) if obj.sender_id else None

    def get_body(self, obj) -> str:
        return obj.body

    def get_reactions(self, obj) -> list:
        return _reactions_payload(obj)

    def get_reply_to(self, obj) -> dict | None:
        if not obj.reply_to_id:
            return None
        return ReplyPreviewSerializer(obj.reply_to).data

    def get_media(self, obj) -> dict | None:
        """Null once the bytes are gone, even though the bubble survives.

        Hard-deleting media nulls this FK but leaves the message, so a photo
        someone deleted renders as a tombstone rather than a broken image.
        """
        if obj.media_id is None or obj.is_deleted:
            return None
        return MessageMediaSerializer(obj.media).data


class SendMessageSerializer(serializers.Serializer):
    body = serializers.CharField(required=False, allow_blank=True, max_length=8000)
    sticker = serializers.CharField(required=False, allow_blank=True, max_length=64)
    media = serializers.UUIDField(required=False, allow_null=True)
    kind = serializers.ChoiceField(
        choices=[c[0] for c in CoupleMessage.KIND_CHOICES if c[0] != "system"],
        default=CoupleMessage.KIND_TEXT,
    )
    reply_to = serializers.UUIDField(required=False, allow_null=True)
    client_id = serializers.CharField(required=False, allow_blank=True, max_length=64)

    def validate(self, attrs):
        kind = attrs.get("kind", CoupleMessage.KIND_TEXT)
        if kind == CoupleMessage.KIND_STICKER:
            if not (attrs.get("sticker") or "").strip():
                raise serializers.ValidationError(
                    {"sticker": "A sticker message needs a sticker."}
                )
        elif kind in CoupleMessage.MEDIA_KINDS:
            # The body stays optional here: on an image it is the caption, and
            # a photo sent without one is the common case.
            if not attrs.get("media"):
                raise serializers.ValidationError(
                    {"media": "A photo or voice message needs an uploaded file."}
                )
        elif not (attrs.get("body") or "").strip():
            raise serializers.ValidationError({"body": "Message cannot be empty."})
        return attrs


class UploadMediaSerializer(serializers.Serializer):
    """Metadata accompanying a multipart upload. The file itself is in FILES."""

    kind = serializers.ChoiceField(choices=[c[0] for c in MessageMedia.KIND_CHOICES])
    duration_ms = serializers.IntegerField(required=False, min_value=0)
    # Cosmetic, and clamped in media.normalise_waveform rather than here — a bad
    # waveform should cost the sender a flat bar, not a failed upload.
    waveform = serializers.JSONField(required=False)

    def validate(self, attrs):
        if attrs["kind"] == MessageMedia.KIND_VOICE and not attrs.get("duration_ms"):
            raise serializers.ValidationError(
                {"duration_ms": "A voice note needs its duration."}
            )
        return attrs


class ReactionSerializer(serializers.Serializer):
    # Bounded so the field cannot be used to smuggle a message into a reaction.
    emoji = serializers.CharField(max_length=32)

    def validate_emoji(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Emoji required.")
        return value
