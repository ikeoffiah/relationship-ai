import uuid
from django.db import models, transaction
from django.conf import settings
from django.core.cache import cache
from apps.audit.logger import AuditLogger

class UserConsent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='consent')

    # DIMENSION 1: How long session transcripts are kept
    SESSION_RETENTION_CHOICES = [
        ('per_session', 'Per session only'),   # DEFAULT — cleared on session end
        ('30_days',     '30 days'),
        ('1_year',      '1 year'),
        ('indefinite',  'Indefinite'),
    ]
    session_transcript_retention = models.CharField(
        max_length=20, choices=SESSION_RETENTION_CHOICES, default='per_session'
    )

    # DIMENSION 2: What insights can be shared cross-partner
    INSIGHT_SHARING_CHOICES = [
        ('never',      'Never share anything with partner'),  # DEFAULT
        ('anonymized', 'Share anonymized themes only'),
        ('named',      'Share named insights'),
    ]
    cross_partner_insight_sharing = models.CharField(
        max_length=20, choices=INSIGHT_SHARING_CHOICES, default='never'
    )

    # DIMENSION 3: Joint session enrollment
    JOINT_SESSION_CHOICES = [
        ('not_enrolled', 'Not enrolled in joint sessions'),  # DEFAULT
        ('enrolled',     'Enrolled in joint sessions'),
    ]
    joint_session_participation = models.CharField(
        max_length=20, choices=JOINT_SESSION_CHOICES, default='not_enrolled'
    )

    # DIMENSION 4: Shared relationship context access
    SHARED_CONTEXT_CHOICES = [
        ('not_participating', 'Not participating'),  # DEFAULT
        ('read_only',         'Read only'),
        ('read_write',        'Read and contribute'),
    ]
    shared_relationship_context = models.CharField(
        max_length=20, choices=SHARED_CONTEXT_CHOICES, default='not_participating'
    )

    # DIMENSION 5: Therapist access to summaries
    therapist_summary_access = models.BooleanField(default=False)  # DEFAULT: off

    # DIMENSION 6: Model improvement (opt-in only)
    model_improvement_data = models.BooleanField(default=False)  # DEFAULT: off

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_consents'

    def save(self, *args, **kwargs):
        """
        Custom save override to enforce change detection, audit logging,
        cache invalidation, and event publishing.
        """
        # Extract optional context for auditing
        session_id = kwargs.pop('changed_from_session_id', None)
        ip_address = kwargs.pop('ip_address', None)
        user_agent = kwargs.pop('user_agent', None)

        if not self._state.adding:
            # Update case: detect changes
            try:
                old_instance = UserConsent.objects.get(pk=self.pk)
                fields_to_check = [
                    'session_transcript_retention',
                    'cross_partner_insight_sharing',
                    'joint_session_participation',
                    'shared_relationship_context',
                    'therapist_summary_access',
                    'model_improvement_data'
                ]
                
                changed_dimensions = []
                for field in fields_to_check:
                    old_val = getattr(old_instance, field)
                    new_val = getattr(self, field)
                    if old_val != new_val:
                        changed_dimensions.append((field, old_val, new_val))
                
                if changed_dimensions:
                    with transaction.atomic():
                        super().save(*args, **kwargs)
                        for dim, old, new in changed_dimensions:
                            ConsentChangeLog.objects.create(
                                user=self.user,
                                dimension=dim,
                                old_value=str(old),
                                new_value=str(new),
                                changed_from_session_id=session_id,
                                ip_address=ip_address,
                                user_agent=user_agent
                            )
                        
                        # Trigger Audit Event (Kafka-MVP)
                        AuditLogger.get_instance().log(
                            event_type="consent_change",
                            user_id=self.user.id,
                            metadata={
                                "changes": [
                                    {"dimension": d, "old": str(o), "new": str(n)}
                                    for d, o, n in changed_dimensions
                                ],
                                "ip_address": ip_address,
                                "user_agent": user_agent
                            },
                            session_id=session_id
                        )

                        # Invalidate Redis Cache
                        cache_key = f"consent_policy:{self.user.id}"
                        cache.delete(cache_key)
                else:
                    # No changes, just normal save (e.g. updated_at update)
                    super().save(*args, **kwargs)
            except UserConsent.DoesNotExist:
                # Should not happen for non-adding state, but fallback to super
                super().save(*args, **kwargs)
        else:
            # Create case
            super().save(*args, **kwargs)

    def __str__(self):
        return f"Consent for {self.user.email}"

class ConsentChangeLog(models.Model):
    """Append-only record of every consent change. Never updated or deleted."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING)
    dimension = models.CharField(max_length=50)   # which permission changed
    old_value = models.TextField()
    new_value = models.TextField()
    changed_at = models.DateTimeField(auto_now_add=True)
    changed_from_session_id = models.UUIDField(null=True)  # if changed mid-session
    ip_address = models.GenericIPAddressField(null=True)
    user_agent = models.TextField(null=True)

    class Meta:
        db_table = 'consent_change_log'
        # Note: Append-only enforcement (REVOKE UPDATE/DELETE) is handled in DB migration.
