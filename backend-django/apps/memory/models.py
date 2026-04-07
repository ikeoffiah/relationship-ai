import uuid
from django.db import models
from django.conf import settings
from pgvector.django import VectorField
from utils.fields import encrypt_field_value, decrypt_field_value


class Memory(models.Model):
    # UUID PK as per spec
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memories"
    )
    content = models.TextField(help_text="Encrypted memory content")
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Memories"
        db_table = "user_memories"  # Explicitly match spec name

    def __str__(self):
        return f"Memory {self.id} for {self.user.id}"

    def save(self, *args, **kwargs):
        # Only encrypt if not already encrypted (basic check)
        if self.content and not self.content.startswith("ENC:"):
            self.content = encrypt_field_value(self.user, self.content)
        super().save(*args, **kwargs)

    @property
    def decrypted_content(self):
        return decrypt_field_value(self.user, self.content)


class MemoryVector(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    memory = models.ForeignKey(Memory, on_delete=models.CASCADE, related_name="vectors")
    user_id = models.UUIDField()
    relationship_id = models.UUIDField(null=True, blank=True)

    zone = models.CharField(max_length=50, default="private")
    memory_type = models.CharField(max_length=100, null=True, blank=True)

    # 1536 dimension for OpenAI/standard embeddings
    embedding = VectorField(dimensions=1536, null=True, blank=True)

    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "memory_vectors"

    def __str__(self):
        return f"Vector for Memory {self.memory_id}"
