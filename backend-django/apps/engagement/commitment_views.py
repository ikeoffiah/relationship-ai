"""
API for partner commitments.

* ``GET  commitments``            — the caller's visible active commitments:
  every "with each other" commitment for the couple, plus the caller's own
  "for my partner" ones (a partner's private surprises stay hidden).
* ``POST commitments``            — add a commitment {kind, text, remind_at?}.
* ``POST commitments/<id>/done``  / ``.../cancel`` — update status.

All routes resolve the caller's own active relationship from ``request.user``,
so a caller can only ever see or touch their own couple's commitments, and never
a partner's private "for you" ones.
"""

from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.engagement import services
from apps.engagement.models import Commitment
from apps.engagement.serializers import CommitmentSerializer, CreateCommitmentSerializer
from apps.engagement.views import _active_relationship, _partner_of
from apps.notifications.notification_models import NotificationType


def _visible(relationship, user):
    """Shared 'with' commitments for the couple + the caller's own 'for' ones."""
    return Commitment.objects.filter(
        Q(relationship=relationship),
        Q(kind="with_partner") | Q(created_by=user),
        status="active",
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def commitments(request):
    relationship = _active_relationship(request.user)

    if request.method == "GET":
        if relationship is None:
            return Response({"commitments": []})
        qs = _visible(relationship, request.user)
        return Response({"commitments": CommitmentSerializer(qs, many=True).data})

    if relationship is None:
        return Response(
            {"detail": "Commitments are shared with a partner — invite yours first."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    serializer = CreateCommitmentSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    item = Commitment.objects.create(
        relationship=relationship,
        created_by=request.user,
        kind=serializer.validated_data["kind"],
        text=serializer.validated_data["text"],
        remind_at=serializer.validated_data.get("remind_at"),
    )

    # A "with each other" commitment is shared, so tell the partner. A
    # "for my partner" one stays a private surprise — no notification.
    if item.kind == "with_partner":
        partner = _partner_of(relationship, request.user)
        if partner is not None:
            services.notify(
                partner.id,
                NotificationType.COMMITMENT_CREATED,
                title="A new commitment together 💞",
                body=item.text,
                data={"deep_link": "/engagement/commitments", "item_id": str(item.id)},
            )

    return Response(CommitmentSerializer(item).data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def complete_commitment(request, item_id):
    return _set_status(request, item_id, "done")


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cancel_commitment(request, item_id):
    return _set_status(request, item_id, "cancelled")


def _set_status(request, item_id, new_status):
    relationship = _active_relationship(request.user)
    if relationship is None:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    # A caller may only act on a commitment they can see (own 'for', or any 'with').
    item = _visible(relationship, request.user).filter(id=item_id).first()
    if item is None:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    item.status = new_status
    item.save(update_fields=["status"])
    return Response(CommitmentSerializer(item).data)
