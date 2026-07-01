from dataclasses import dataclass
from typing import Optional
from django.db import models
from apps.consent.models import UserConsent
from apps.relationships.models import Relationship

@dataclass
class AccessPolicy:
    user_id: str
    relationship_id: Optional[str]
    session_type: str                    # individual | joint | async_relay

    # Derived from UserConsent at session start
    can_read_private_memories: bool      # always True for own data
    can_read_shared_context: bool        # True if shared_relationship_context != 'not_participating'
    can_read_partner_insights: bool      # True if cross_partner_insight_sharing != 'never' AND partner also consented
    can_write_shared_context: bool       # True if shared_relationship_context == 'read_write'
    can_participate_joint: bool          # True if joint_session_participation == 'enrolled'
    therapist_can_read_summaries: bool   # True if therapist_summary_access == True

    insight_sharing_level: str           # 'never' | 'anonymized' | 'named'

    @classmethod
    def from_user_id(cls, user_id: str, session_type: str) -> 'AccessPolicy':
        """
        Builds AccessPolicy from DB. Called at Node 2 (Consent Gate) in LangGraph.
        This follows Section 4.2 of the paper.
        """
        try:
            consent = UserConsent.objects.get(user_id=user_id)
        except UserConsent.DoesNotExist:
            # Fallback for safety if record missing
            return cls(
                user_id=str(user_id),
                relationship_id=None,
                session_type=session_type,
                can_read_private_memories=True,
                can_read_shared_context=False,
                can_read_partner_insights=False,
                can_write_shared_context=False,
                can_participate_joint=False,
                therapist_can_read_summaries=False,
                insight_sharing_level='never'
            )
        
        # Check if user is in an active relationship
        relationship = Relationship.objects.filter(
            models.Q(partner_a_id=user_id) | models.Q(partner_b_id=user_id)
        ).first()
        
        relationship_id = str(relationship.id) if relationship else None
        
        # Cross-partner checks require partner's consent too
        can_read_partner_insights = False
        if relationship:
            partner_id = relationship.partner_b_id if relationship.partner_a_id == user_id else relationship.partner_a_id
            try:
                partner_consent = UserConsent.objects.get(user_id=partner_id)
                # Mutual consent required for insight sharing
                if consent.cross_partner_insight_sharing != 'never' and partner_consent.cross_partner_insight_sharing != 'never':
                    can_read_partner_insights = True
            except UserConsent.DoesNotExist:
                pass

        return cls(
            user_id=str(user_id),
            relationship_id=relationship_id,
            session_type=session_type,
            can_read_private_memories=True,
            can_read_shared_context=consent.shared_relationship_context != 'not_participating',
            can_read_partner_insights=can_read_partner_insights,
            can_write_shared_context=consent.shared_relationship_context == 'read_write',
            can_participate_joint=consent.joint_session_participation == 'enrolled',
            therapist_can_read_summaries=consent.therapist_summary_access,
            insight_sharing_level=consent.cross_partner_insight_sharing
        )

    def can_access_namespace(self, namespace: str) -> bool:
        """Used by VectorMemoryStore to gate every query."""
        if namespace.startswith(f'private_{self.user_id}'):
            return True
        if namespace.startswith('shared_') and self.can_read_shared_context:
            return True
        return False
