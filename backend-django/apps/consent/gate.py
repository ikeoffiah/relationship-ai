import logging
from dataclasses import dataclass
from django.core.cache import cache
from apps.consent.models import UserConsent
from apps.audit.logger import AuditLogger

logger = logging.getLogger(__name__)

@dataclass
class AccessPolicy:
    user_id: str
    session_transcript_retention: str
    cross_partner_insight_sharing: str
    joint_session_participation: str
    shared_relationship_context: str
    therapist_summary_access: bool
    model_improvement_data: bool
    
    def can_share_with_partner(self) -> bool:
        return self.cross_partner_insight_sharing != 'never'

class NamespaceAccessDenied(Exception):
    pass

class ConsentGate:
    """
    Internal enforcement gate for consent-aware data access.
    Used by memory stores and synthesis engines.
    """
    
    @staticmethod
    def get_access_policy(user_id: str) -> AccessPolicy:
        """
        Fetches from Redis cache first (TTL: 5 min).
        Falls back to DB on cache miss.
        Returns most-restrictive policy on any error.
        """
        cache_key = f"consent_policy:{user_id}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return AccessPolicy(**cached_data)
        
        try:
            consent = UserConsent.objects.get(user_id=user_id)
            policy_dict = {
                'user_id': str(user_id),
                'session_transcript_retention': consent.session_transcript_retention,
                'cross_partner_insight_sharing': consent.cross_partner_insight_sharing,
                'joint_session_participation': consent.joint_session_participation,
                'shared_relationship_context': consent.shared_relationship_context,
                'therapist_summary_access': consent.therapist_summary_access,
                'model_improvement_data': consent.model_improvement_data,
            }
            # Cache for 5 minutes
            cache.set(cache_key, policy_dict, timeout=300)
            return AccessPolicy(**policy_dict)
            
        except Exception as e:
            logger.error(f"Error fetching consent for {user_id}: {e}")
            # Fail-safe: return most restrictive policy
            return AccessPolicy(
                user_id=str(user_id),
                session_transcript_retention='per_session',
                cross_partner_insight_sharing='never',
                joint_session_participation='not_enrolled',
                shared_relationship_context='not_participating',
                therapist_summary_access=False,
                model_improvement_data=False
            )

    @staticmethod
    def assert_can_read_namespace(user_id: str, namespace: str, access_policy: AccessPolicy) -> None:
        """
        Raises NamespaceAccessDenied if access_policy doesn't permit reading namespace.
        Logs cross_partner_access_denied event to Kafka on denial.
        """
        # Logic for namespace isolation:
        # 'private:{user_id}' -> always allowed for owner
        # 'shared:{relationship_id}' -> allowed if shared_relationship_context != 'not_participating'
        # 'partner:{partner_id}' -> allowed if partner's cross_partner_insight_sharing != 'never'
        
        is_denied = False
        reason = ""
        
        if namespace.startswith("partner:"):
            if access_policy.cross_partner_insight_sharing == 'never':
                is_denied = True
                reason = "partner_insight_sharing_disabled"
        
        elif namespace.startswith("shared:"):
            if access_policy.shared_relationship_context == 'not_participating':
                is_denied = True
                reason = "shared_context_disabled"

        if is_denied:
            # Log denial to Kafka
            AuditLogger.get_instance().log(
                event_type="cross_partner_access_denied",
                user_id=user_id,
                metadata={
                    "requested_namespace": namespace,
                    "denial_reason": reason,
                    "policy": {
                        "insight_sharing": access_policy.cross_partner_insight_sharing,
                        "shared_context": access_policy.shared_relationship_context
                    }
                }
            )
            raise NamespaceAccessDenied(f"Access to namespace {namespace} denied: {reason}")
