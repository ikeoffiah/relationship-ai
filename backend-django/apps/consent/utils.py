from uuid import UUID
from dataclasses import dataclass, field
from typing import List, Optional
import logging

from .models import UserConsent
from apps.audit.logger import AuditLogger

logger = logging.getLogger(__name__)


class ConsentDeniedError(Exception):
    """Raised when a required consent permission is missing."""

    def __init__(self, message: str, missing_permissions: List[str]):
        super().__init__(message)
        self.missing_permissions = missing_permissions


@dataclass
class ConsentCheckResult:
    allowed: bool
    missing_permissions: List[str] = field(default_factory=list)
    both_partners_consented: bool = False


def check_consent(
    user_id: UUID,
    relationship_id: Optional[UUID] = None,
    required_permissions: List[str] = None,
    session_id: Optional[UUID] = None,
) -> ConsentCheckResult:
    """
    Internal utility to verify consent dimensions before performing operations.
    Logs the check to the audit event store.
    """
    required_permissions = required_permissions or []
    missing_permissions = []
    both_partners_consented = True  # Default to True, set to False if any partner fails

    # 1. Fetch primary user consent
    try:
        user_consent = UserConsent.objects.get(user_id=user_id)
    except UserConsent.DoesNotExist:
        # If no record exists, fall back to default implicit "per_session / never" logic
        # For safety, we assume no permissions are granted if the record is missing
        return ConsentCheckResult(
            allowed=False,
            missing_permissions=required_permissions,
            both_partners_consented=False,
        )

    # 2. Check each required permission
    for permission in required_permissions:
        # Map permission string to model field
        # Requirement: "Returns current consent state matching database"
        # We assume the permission names match the model field names.
        if hasattr(user_consent, permission):
            value = getattr(user_consent, permission)
            # Logic for boolean fields
            if isinstance(value, bool):
                if not value:
                    missing_permissions.append(permission)
            # Logic for choice fields (e.g. cross_partner_insight_sharing)
            elif isinstance(value, str):
                if value in ["never", "not_enrolled", "not_participating"]:
                    missing_permissions.append(permission)
        else:
            logger.warning(f"Unknown consent permission requested: {permission}")
            missing_permissions.append(permission)

    # 3. Check partner consent if relationship_id is provided
    if relationship_id:
        # Fetch all consents for this relationship
        relationship_consents = UserConsent.objects.filter(
            relationship_id=relationship_id
        )

        # Cross-partner check logic: for certain permissions, BOTH must consent
        # Specifically: cross_partner_insight_sharing, shared_relationship_context
        cross_partner_fields = [
            "cross_partner_insight_sharing",
            "shared_relationship_context",
        ]

        for consent in relationship_consents:
            # Skip the user we already checked
            if str(consent.user_id) == str(user_id):
                continue

            for field in cross_partner_fields:
                if field in required_permissions:
                    val = getattr(consent, field)
                    if val in ["never", "not_participating"]:
                        both_partners_consented = False
                        # We don't necessarily add to missing_permissions for the primary user,
                        # but we mark both_partners_consented as False.

    # 4. Log the check to audit store
    AuditLogger.get_instance().log(
        event_type="consent_check",
        user_id=user_id,
        relationship_id=relationship_id,
        session_id=session_id,
        metadata={
            "required_permissions": required_permissions,
            "allowed": len(missing_permissions) == 0,
            "both_partners_consented": both_partners_consented,
            "missing_permissions": missing_permissions,
        },
    )

    allowed = len(missing_permissions) == 0

    if not allowed:
        raise ConsentDeniedError(
            f"Consent check failed for user {user_id}. Missing: {missing_permissions}",
            missing_permissions=missing_permissions,
        )

    return ConsentCheckResult(
        allowed=allowed,
        missing_permissions=missing_permissions,
        both_partners_consented=both_partners_consented,
    )
