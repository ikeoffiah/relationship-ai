from uuid import uuid4
from django.db import models, transaction
from django.core.exceptions import ValidationError


class UserConsent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    user_id = models.UUIDField(db_index=True)
    relationship_id = models.UUIDField(null=True, blank=True, db_index=True)

    # All six consent dimensions from Section 4.2
    session_transcript_retention = models.CharField(
        max_length=20,
        choices=[
            ("per_session", "Per Session"),
            ("30_days", "30 Days"),
            ("1_year", "1 Year"),
            ("indefinite", "Indefinite"),
        ],
        default="per_session",  # most restrictive default
    )
    cross_partner_insight_sharing = models.CharField(
        max_length=20,
        choices=[("never", "Never"), ("anonymized", "Anonymized"), ("named", "Named")],
        default="never",
    )
    joint_session_participation = models.CharField(
        max_length=20,
        choices=[("not_enrolled", "Not Enrolled"), ("enrolled", "Enrolled")],
        default="not_enrolled",
    )
    shared_relationship_context = models.CharField(
        max_length=20,
        choices=[
            ("not_participating", "Not Participating"),
            ("read_only", "Read Only"),
            ("read_write", "Read/Write"),
        ],
        default="not_participating",
    )
    therapist_summary_access = models.BooleanField(default=False)
    model_improvement_data = models.BooleanField(default=False)  # opt-in only

    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.UUIDField()  # must match user_id (self-only updates)

    class Meta:
        db_table = "user_consents"
        indexes = [models.Index(fields=["user_id", "relationship_id"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    session_transcript_retention__in=[
                        "per_session",
                        "30_days",
                        "1_year",
                        "indefinite",
                    ]
                ),
                name="check_session_transcript_retention",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    cross_partner_insight_sharing__in=["never", "anonymized", "named"]
                ),
                name="check_cross_partner_insight_sharing",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    joint_session_participation__in=["not_enrolled", "enrolled"]
                ),
                name="check_joint_session_participation",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    shared_relationship_context__in=[
                        "not_participating",
                        "read_only",
                        "read_write",
                    ]
                ),
                name="check_shared_relationship_context",
            ),
        ]

    def __str__(self):
        return f"Consent for {self.user_id}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        session_context = kwargs.pop("session_context", None)

        if not is_new:
            # Enforcement: user_id is immutable
            orig = UserConsent.objects.get(pk=self.pk)
            if orig.user_id != self.user_id:
                raise ValidationError("user_id cannot be changed.")

            # Enforcement: updated_by must match user_id
            if self.updated_by != self.user_id:
                raise ValidationError(
                    "Consent can only be updated by the record's own user_id."
                )

            # Every consent change must produce a ConsentAuditEntry record before the change is committed
            with transaction.atomic():
                audit_entries = []
                fields_to_check = [
                    "session_transcript_retention",
                    "cross_partner_insight_sharing",
                    "joint_session_participation",
                    "shared_relationship_context",
                    "therapist_summary_access",
                    "model_improvement_data",
                ]
                for field in fields_to_check:
                    old_val = getattr(orig, field)
                    new_val = getattr(self, field)
                    if old_val != new_val:
                        audit_entries.append(
                            ConsentAuditEntry(
                                user_id=self.user_id,
                                relationship_id=self.relationship_id,
                                changed_field=field,
                                old_value=str(old_val),
                                new_value=str(new_val),
                                session_context=session_context,
                            )
                        )

                if audit_entries:
                    ConsentAuditEntry.objects.bulk_create(audit_entries)

                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)


class ConsentAuditEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    user_id = models.UUIDField(db_index=True)
    relationship_id = models.UUIDField(null=True)
    changed_field = models.CharField(max_length=60)
    old_value = models.CharField(max_length=50)
    new_value = models.CharField(max_length=50)
    changed_at = models.DateTimeField(auto_now_add=True)
    session_context = models.UUIDField(null=True)  # session where change was made

    class Meta:
        db_table = "consent_audit_log"
