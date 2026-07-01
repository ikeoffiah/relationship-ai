import uuid
from django.db import models
from django.conf import settings
from apps.relationships.models import Relationship
from utils.fields import encrypt_field_value, decrypt_field_value


class Session(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sessions"
    )
    relationship = models.ForeignKey(
        Relationship, on_delete=models.CASCADE, related_name="sessions"
    )

    transcript = models.TextField(
        blank=True, null=True, help_text="Encrypted full transcript"
    )
    summary = models.TextField(
        blank=True, null=True, help_text="Encrypted clinical summary"
    )

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "counselor_sessions"

    def __str__(self):
        return f"Session {self.id} ({self.status})"

    def save(self, *args, **kwargs):
        # Encrypt transcript and summary if provided
        if self.transcript and not self.transcript.startswith("ENC:"):
            self.transcript = encrypt_field_value(self.user, self.transcript)
        if self.summary and not self.summary.startswith("ENC:"):
            self.summary = encrypt_field_value(self.user, self.summary)
        super().save(*args, **kwargs)

    @property
    def decrypted_transcript(self):
        return decrypt_field_value(self.user, self.transcript)

    @property
    def decrypted_summary(self):
        return decrypt_field_value(self.user, self.summary)
