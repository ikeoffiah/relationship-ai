import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class SystemConfig(models.Model):
    """
    Key-value store for operational configuration.
    All changes are audited with a mandatory change_reason.
    """
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)
    last_changed_by = models.ForeignKey(
        User, on_delete=models.DO_NOTHING,
        null=True, blank=True, related_name='config_changes'
    )
    last_changed_at = models.DateTimeField(auto_now=True)
    change_reason = models.TextField(blank=True)

    class Meta:
        db_table = 'system_config'
        ordering = ['key']

    def __str__(self):
        return f"{self.key} = {self.value}"

    @classmethod
    def get_float(cls, key: str, default: float) -> float:
        try:
            return float(cls.objects.get(key=key).value)
        except cls.DoesNotExist:
            return default

    @classmethod
    def get_str(cls, key: str, default: str = '') -> str:
        try:
            return cls.objects.get(key=key).value
        except cls.DoesNotExist:
            return default


class SystemConfigAudit(models.Model):
    """Immutable audit log for every threshold change."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    config_key = models.CharField(max_length=100)
    old_value = models.TextField()
    new_value = models.TextField()
    changed_by = models.ForeignKey(
        User, on_delete=models.DO_NOTHING,
        null=True, blank=True
    )
    change_reason = models.TextField()
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'system_config_audit'
        ordering = ['-changed_at']

    def __str__(self):
        return f"[{self.changed_at:%Y-%m-%d}] {self.config_key}: {self.old_value} → {self.new_value}"
