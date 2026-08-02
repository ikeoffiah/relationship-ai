from rest_framework import serializers

from apps.insights.models import RelationshipInsight


class RelationshipInsightSerializer(serializers.ModelSerializer):
    """What a partner is allowed to see.

    Deliberately narrow. The narrative halves and the synthesis are *not*
    exposed — they are empty today, and when a detector starts filling them
    they will need the consent flow in `docs/relationship-insights.md` §5
    before anything renders them. Adding them here now would mean the day
    somebody writes to those fields, they ship to both partners by default.

    A serializer is exactly where that kind of leak arrives: somebody adds a
    field because it is on the model and obviously relevant, and no test goes
    red.
    """

    id = serializers.UUIDField(source="insight_id", read_only=True)

    class Meta:
        model = RelationshipInsight
        fields = ["id", "type", "theme", "confidence", "created_at"]
        read_only_fields = fields
