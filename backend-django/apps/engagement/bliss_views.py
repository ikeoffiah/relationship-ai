"""
API for the @bliss assistant.

* ``POST bliss/interpret`` — parse a raw "@bliss …" chat message into a draft
  (kind/title/due_at). Stateless: nothing is saved, so the client can preview
  and let the user confirm or edit before creating.
* ``POST bliss/items``     — create a reminder/event (shared with the partner);
  notifies the partner it was added.
* ``GET  bliss/items``     — the couple's upcoming (pending) items.
* ``POST bliss/items/<id>/done`` / ``.../cancel`` — update status.

Every route is scoped to the caller's own active relationship resolved from
``request.user`` — the relationship id is never taken from the client, so a
caller can only ever see or touch their own couple's items (no IDOR).
"""

from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.engagement import services
from apps.engagement.bliss import parse_bliss_command
from apps.engagement.models import BlissItem
from apps.engagement.serializers import (
    BlissItemSerializer,
    CreateBlissItemSerializer,
    InviteResponseSerializer,
)
from apps.engagement.views import _active_relationship, _partner_of
from apps.notifications.notification_models import NotificationType


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def interpret(request):
    """Parse a raw @bliss chat message into a draft (no persistence)."""
    text = (request.data.get("text") or "").strip()
    if not text:
        return Response({"detail": "text is required."}, status=status.HTTP_400_BAD_REQUEST)

    draft = parse_bliss_command(text)
    if draft is None:
        return Response(
            {
                "recognized": False,
                "message": "I couldn't find something to schedule in that. "
                "Try: “@bliss remind us to call the venue tomorrow at 5pm”.",
            }
        )
    return Response({"recognized": True, "draft": draft.as_dict()})


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def items(request):
    if request.method == "GET":
        relationship = _active_relationship(request.user)
        qs = BlissItem.objects.filter(status="pending").filter(
            Q(relationship=relationship) if relationship else Q(created_by=request.user)
        )
        return Response(
            {
                "items": BlissItemSerializer(
                    qs, many=True, context={"viewer_id": request.user.id}
                ).data
            }
        )

    serializer = CreateBlissItemSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    relationship = _active_relationship(request.user)

    partner = _partner_of(relationship, request.user)
    # Tagging only means anything when there is somebody to tag. Asking for an
    # invite in a solo relationship leaves the item un-invited rather than
    # stranded in "pending" forever with nobody able to answer it.
    invited = bool(serializer.validated_data.get("invite_partner")) and partner is not None

    item = BlissItem.objects.create(
        relationship=relationship,
        created_by=request.user,
        kind=serializer.validated_data["kind"],
        title=serializer.validated_data["title"],
        due_at=serializer.validated_data.get("due_at"),
        source=serializer.validated_data.get("source", "bliss"),
        partner_invite=(
            BlissItem.INVITE_PENDING if invited else BlissItem.INVITE_NONE
        ),
    )

    if item.source == "couple_chat" and relationship is not None:
        _announce_in_thread(relationship, item)

    if partner is not None:
        if invited:
            # An invitation, so the copy asks rather than announces. Saying
            # "added to your plan" for something they have not agreed to is how
            # a calendar starts feeling like it belongs to the other person.
            services.notify(
                partner.id,
                NotificationType.BLISS_INVITE,
                title=f"{_display_name(request.user)} asked you to something 🌸",
                body=f"{_short(item.title)} — tap to say yes or no.",
                data={
                    "deep_link": "/engagement/calendar",
                    "item_id": str(item.id),
                    "needs_response": True,
                },
            )
        else:
            services.notify(
                partner.id,
                NotificationType.BLISS_CREATED,
                title="Bliss added something 🌸",
                body=f"{_short(item.title)} — tap to see it.",
                data={"deep_link": "/engagement/calendar", "item_id": str(item.id)},
            )

    return Response(
        BlissItemSerializer(item, context={"viewer_id": request.user.id}).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def complete_item(request, item_id):
    return _set_status(request, item_id, "done")


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cancel_item(request, item_id):
    return _set_status(request, item_id, "cancelled")


def _set_status(request, item_id, new_status):
    relationship = _active_relationship(request.user)
    scope = Q(relationship=relationship) if relationship else Q(created_by=request.user)
    item = BlissItem.objects.filter(scope, id=item_id).first()
    if item is None:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    item.status = new_status
    item.save(update_fields=["status"])
    return Response(BlissItemSerializer(item).data)


def _announce_in_thread(relationship, item) -> None:
    """Drop a system line into the couple's thread.

    Written server-side rather than by the client on purpose. The send endpoint
    refuses ``kind=system`` precisely so that a message attributed to Bliss
    cannot be forged by whoever is holding the phone; the same guarantee would
    be worthless if there were a client-callable way to write one.

    Best-effort. An announcement that fails is a missing line in a thread; a
    reminder that fails to save is a promise broken.
    """
    try:
        from apps.chat import realtime
        from apps.chat.models import CoupleMessage
        from apps.chat.serializers import CoupleMessageSerializer

        when = ""
        if item.due_at is not None:
            # Deliberately plain and absolute. "in 3 hours" drifts the moment
            # anyone scrolls back to it.
            when = item.due_at.strftime(" — %a %-d %b, %-I:%M%p").replace("AM", "am").replace("PM", "pm")

        verb = "will remind you both about" if item.kind == "reminder" else "put this in your plan:"
        message = CoupleMessage(
            relationship=relationship,
            sender=None,
            kind=CoupleMessage.KIND_SYSTEM,
        )
        message.body = f"Bliss {verb} {item.title}{when}"
        message.save()
        realtime.publish(
            relationship.id,
            {
                "type": "couple_message",
                "message": CoupleMessageSerializer(message).data,
            },
        )
    except Exception:  # pragma: no cover - exercised via the failure test
        import logging

        logging.getLogger(__name__).warning(
            "bliss_thread_announcement_failed item=%s", item.id, exc_info=True
        )


def _display_name(user) -> str:
    """What to call someone in a notification.

    The user model has `full_name`, not Django's `first_name` — an easy thing
    to get wrong from memory, and it fails as a 500 at the moment a partner is
    invited rather than anywhere near where the mistake was made. First word
    only: "Sam asked you to something" reads as a person, "Sam Okonkwo asked
    you to something" reads as an email from HR.
    """
    name = (getattr(user, "full_name", "") or "").strip()
    return name.split()[0] if name else "Your partner"


def _short(text: str, n: int = 60) -> str:
    text = text.strip()
    return text if len(text) <= n else text[: n - 1] + "…"


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def respond_to_invite(request, item_id):
    """Accept or decline being tagged on a calendar item.

    Only the person who was *asked* may answer, never the one who asked. That
    check is the whole feature: without it, tagging your partner and accepting
    on their behalf is two API calls, and the invite becomes decoration on top
    of putting things in someone else's diary.

    Answering is idempotent and changeable — someone who declines on Tuesday
    and accepts on Thursday should not have to be re-invited. The reminder
    sweep reads the current value at fire time, so a late change still lands.
    """
    relationship = _active_relationship(request.user)
    item = BlissItem.objects.filter(id=item_id, relationship=relationship).first()
    if item is None or relationship is None:
        # 404 rather than 403 — a stranger probing ids should not learn which
        # items exist.
        return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    if item.created_by_id == request.user.id:
        return Response(
            {"error": "You cannot answer your own invitation."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if item.partner_invite == BlissItem.INVITE_NONE:
        return Response(
            {"error": "You were not asked about this one."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer = InviteResponseSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    accepted = serializer.validated_data["accept"]

    item.partner_invite = (
        BlissItem.INVITE_ACCEPTED if accepted else BlissItem.INVITE_DECLINED
    )
    item.partner_responded_at = timezone.now()
    item.save(update_fields=["partner_invite", "partner_responded_at"])

    # Tell the person who asked. A declined invite is worth knowing about
    # sooner than the moment the thing does not happen.
    services.notify(
        item.created_by_id,
        NotificationType.BLISS_CREATED,
        title="Yes 🌸" if accepted else "Not this time",
        body=(
            f"{_display_name(request.user)} "
            f"{'is in for' if accepted else 'said no to'} {_short(item.title)}."
        ),
        data={"deep_link": "/engagement/calendar", "item_id": str(item.id)},
    )

    return Response(
        BlissItemSerializer(item, context={"viewer_id": request.user.id}).data
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def calendar(request):
    """Dated items in a window, for the in-app calendar.

    Range-scoped rather than "everything pending": a calendar is scrolled
    through months, and the list endpoint's shape (all pending, no bounds)
    would fetch a year to draw a week. Undated items are excluded here on
    purpose — they belong on the plan list, not on a day.
    """
    relationship = _active_relationship(request.user)
    qs = BlissItem.objects.filter(due_at__isnull=False).exclude(status="cancelled")
    qs = qs.filter(
        Q(relationship=relationship) if relationship else Q(created_by=request.user)
    )

    start = _parse_when(request.query_params.get("from"))
    end = _parse_when(request.query_params.get("to"))
    if start is not None:
        qs = qs.filter(due_at__gte=start)
    if end is not None:
        qs = qs.filter(due_at__lte=end)

    items = BlissItemSerializer(
        qs.order_by("due_at"), many=True, context={"viewer_id": request.user.id}
    ).data

    # Grouped by local date, because that is the only way the client will ever
    # use it and doing it here keeps one definition of which day something
    # falls on rather than two that can disagree.
    days: dict[str, list] = {}
    for row in items:
        day = str(row["due_at"])[:10]
        days.setdefault(day, []).append(row)

    return Response({"items": items, "days": days})


def _parse_when(raw):
    if not raw:
        return None
    try:
        parsed = timezone.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed)
    return parsed
