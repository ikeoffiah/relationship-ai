"""Wire format for the couple thread."""

from rest_framework import serializers

from .models import CoupleMessage


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

    def get_sender_id(self, obj) -> str | None:
        return str(obj.sender_id) if obj.sender_id else None

    def get_body(self, obj) -> str:
        # A quote of a deleted message shows the tombstone, not the old text.
        return "" if obj.is_deleted else obj.body[:180]


class CoupleMessageSerializer(serializers.ModelSerializer):
    sender_id = serializers.SerializerMethodField()
    body = serializers.SerializerMethodField()
    reactions = serializers.SerializerMethodField()
    reply_to = serializers.SerializerMethodField()
    is_deleted = serializers.BooleanField(read_only=True)

    class Meta:
        model = CoupleMessage
        fields = [
            "id",
            "relationship",
            "sender_id",
            "kind",
            "body",
            "sticker",
            "reply_to",
            "reactions",
            "client_id",
            "is_deleted",
            "created_at",
            "edited_at",
        ]

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


class SendMessageSerializer(serializers.Serializer):
    body = serializers.CharField(required=False, allow_blank=True, max_length=8000)
    sticker = serializers.CharField(required=False, allow_blank=True, max_length=64)
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
        elif not (attrs.get("body") or "").strip():
            raise serializers.ValidationError({"body": "Message cannot be empty."})
        return attrs


class ReactionSerializer(serializers.Serializer):
    # Bounded so the field cannot be used to smuggle a message into a reaction.
    emoji = serializers.CharField(max_length=32)

    def validate_emoji(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Emoji required.")
        return value
