import uuid
from django.db import models
from django.conf import settings


class Relationship(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    partner_a = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="relationships_as_a")
    partner_b = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="relationships_as_b", null=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('dissolved', 'Dissolved'),
        ],
        default='active'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    dissolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'relationships'
        indexes = [
            models.Index(fields=['partner_a', 'status']),
            models.Index(fields=['partner_b', 'status']),
        ]

    def __str__(self):
        return f"Relationship {self.id} ({self.status})"


class RelationshipInvite(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inviter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_invites")
    invitee_email = models.EmailField()
    token_hash = models.CharField(max_length=255, unique=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('accepted', 'Accepted'),
            ('declined', 'Declined'),
            ('expired', 'Expired'),
        ],
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = 'relationship_invites'

    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at or self.status == 'expired'

    def __str__(self):
        return f"Invite from {self.inviter.email} to {self.invitee_email}"


class SharedRelationshipContext(models.Model):
    """
    Per REL-65, stores the shared context between partners.
    JSONB fields are to be encrypted with a relationship-scoped key.
    """
    relationship = models.OneToOneField(Relationship, on_delete=models.CASCADE, primary_key=True, related_name='shared_context')
    named_recurring_conflicts = models.JSONField(default=list, blank=True)
    agreed_goals_and_values = models.JSONField(default=list, blank=True)
    repair_history = models.JSONField(default=list, blank=True)
    structural_facts = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'shared_relationship_context'

    def __str__(self):
        return f"Shared Context for {self.relationship.id}"
