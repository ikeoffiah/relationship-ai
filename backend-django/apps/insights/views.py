from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.insights.models import RelationshipInsight
from apps.insights.serializers import RelationshipInsightSerializer


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def insights(request):
    """What Bliss has noticed, for the person asking.

    Reads through `objects.public(request.user)`, which is the only accessor —
    there is no unfiltered one, and there is deliberately no way to ask for a
    partner's. Everything returned today is shape-only and built from the
    couple's shared thread, so it says that a pattern exists without repeating
    anything either of them said.

    Expired insights are filtered rather than deleted. A theme from three
    months ago is a claim about a couple who may well have fixed it, and
    showing it would be telling them something that is no longer true.
    """
    rows = (
        RelationshipInsight.objects.public(request.user)
        .filter(expires_at__gt=timezone.now())
        .order_by("-created_at")
    )
    return Response(
        {"insights": RelationshipInsightSerializer(rows, many=True).data},
        status=status.HTTP_200_OK,
    )
