import uuid
from django.db import models
from django.utils import timezone


class RelationshipInsight(models.Model):
    """Core data model for insight synthesis.

    Fields follow the specification in Linear issue REL‑72. Sensitive narrative
    fields are stored encrypted using the project's `StorageService` utilities
    (see other encrypted models for reference).
    """

    INSIGHT_TYPES = [
        ("perception_gap", "Perception Gap"),
        ("recurring_theme", "Recurring Conflict Theme"),
        ("needs_gap", "Emotional Needs Gap"),
        ("progress", "Progress / Positive Signal"),
        ("flourishing_pattern", "Flourishing Pattern"),
    ]

    insight_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    relationship = models.ForeignKey(
        "relationships.Relationship",
        on_delete=models.CASCADE,
        related_name="insights",
    )
    type = models.CharField(max_length=30, choices=INSIGHT_TYPES)
    theme = models.TextField(blank=True)
    confidence = models.FloatField()

    # Narrative fields – stored encrypted at rest via StorageService (see utils)
    a_narrative_summary = models.TextField(blank=True)
    b_narrative_summary = models.TextField(blank=True)
    synthesis = models.TextField(blank=True)
    suggested_intervention = models.TextField(blank=True)

    session_evidence = models.JSONField(default=list, blank=True)

    # Consent flags – enforced at the data‑access layer
    shared_with_a = models.BooleanField(default=False)
    shared_with_b = models.BooleanField(default=False)
    approved_for_joint = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "relationship_insights"
        indexes = [
            models.Index(
                fields=["relationship", "type"],
                name="idx_insight_rel_type",
            ),
        ]

    def __str__(self):
        return f"Insight {self.insight_id} ({self.type}) for {self.relationship_id}"
