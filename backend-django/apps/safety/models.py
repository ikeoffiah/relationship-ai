import uuid
from django.db import models
from pgvector.django import VectorField


class SafetySignal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.CharField(max_length=100)
    phrase = models.TextField()

    # 1536 dimensions for OpenAI embeddings
    embedding = VectorField(dimensions=1536, null=True, blank=True)

    severity = models.FloatField(default=0.5)
    source = models.CharField(max_length=255, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "safety_signals"
        verbose_name_plural = "Safety Signals"

    def __str__(self):
        return f"[{self.category}] {self.phrase[:30]}..."


class SafetyIncident(models.Model):
    """Logs a detected safety signal for clinical review."""

    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    STATUS_CHOICES = [
        ('unreviewed', 'Unreviewed'),
        ('reviewed', 'Reviewed'),
        ('escalated', 'Escalated'),
        ('resolved', 'Resolved'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Anonymised: stored as first 8 chars of user_id only
    user_id_anon = models.CharField(max_length=8, db_index=True)
    session_id = models.CharField(max_length=64, null=True, blank=True)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='medium')
    category = models.CharField(max_length=100)  # e.g. suicidal_ideation, physical_abuse
    safety_score = models.FloatField()
    layer_detected = models.IntegerField(default=1)  # 1, 2, or 3
    action_taken = models.TextField(blank=True)
    therapist_notes = models.TextField(blank=True)
    reviewed_by = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unreviewed')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'safety_incidents'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.severity.upper()}] {self.category} (user ...{self.user_id_anon})"
