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
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.engagement import services
from apps.engagement.bliss import parse_bliss_command
from apps.engagement.models import BlissItem
from apps.engagement.serializers import BlissItemSerializer, CreateBlissItemSerializer
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
        return Response({"items": BlissItemSerializer(qs, many=True).data})

    serializer = CreateBlissItemSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    relationship = _active_relationship(request.user)

    item = BlissItem.objects.create(
        relationship=relationship,
        created_by=request.user,
        kind=serializer.validated_data["kind"],
        title=serializer.validated_data["title"],
        due_at=serializer.validated_data.get("due_at"),
        source=serializer.validated_data.get("source", "bliss"),
    )

    # Let the partner know Bliss added something to their shared plan.
    partner = _partner_of(relationship, request.user)
    if partner is not None:
        services.notify(
            partner.id,
            NotificationType.BLISS_CREATED,
            title="Bliss added something 🌸",
            body=f"{_short(item.title)} — tap to see it.",
            data={"deep_link": "/engagement/bliss", "item_id": str(item.id)},
        )

    return Response(BlissItemSerializer(item).data, status=status.HTTP_201_CREATED)


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


def _short(text: str, n: int = 60) -> str:
    text = text.strip()
    return text if len(text) <= n else text[: n - 1] + "…"
