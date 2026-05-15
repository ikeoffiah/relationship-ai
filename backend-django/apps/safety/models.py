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
