import uuid
from django.db import models
from django.conf import settings
from utils.fields import encrypt_field_value, decrypt_field_value


class Relationship(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="relationships"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(
        blank=True, null=True, help_text="Encrypted description"
    )

    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "relationships"

    def __str__(self):
        return f"{self.name} ({self.user.id})"

    def save(self, *args, **kwargs):
        if self.description and not self.description.startswith("ENC:"):
            self.description = encrypt_field_value(self.user, self.description)
        super().save(*args, **kwargs)

    @property
    def decrypted_description(self):
        return decrypt_field_value(self.user, self.description)


class RelationshipNote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    relationship = models.ForeignKey(
        Relationship, on_delete=models.CASCADE, related_name="notes"
    )
    content = models.TextField(help_text="Encrypted note content")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "relationship_notes"

    def __str__(self):
        return f"Note on {self.relationship.id} at {self.created_at}"

    def save(self, *args, **kwargs):
        if self.content and not self.content.startswith("ENC:"):
            self.content = encrypt_field_value(self.relationship.user, self.content)
        super().save(*args, **kwargs)

    @property
    def decrypted_content(self):
        return decrypt_field_value(self.relationship.user, self.content)
