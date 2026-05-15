import uuid
from datetime import timedelta
from dataclasses import dataclass
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db import models
from rest_framework import views, status, response, permissions
from apps.relationships.models import Relationship
from apps.consent.models import UserConsent
from apps.accounts.models import User, AgeVerification
from apps.accounts.permissions import IsAdult
from apps.sessions.models import JointSession
from apps.sessions.joint_session import JointSessionState, VALID_TRANSITIONS
from apps.audit.logger import AuditLogger

@dataclass
class JointConsentResult:
    both_enrolled: bool
    both_age_verified: bool
    no_active_safety_escalation: bool

    @property
    def is_valid(self):
        return self.both_enrolled and self.both_age_verified and self.no_active_safety_escalation

def has_active_safety_escalation(user_id):
    # Placeholder for safety escalation logic.
    return False

def validate_joint_session_consent(relationship) -> JointConsentResult:
    partner_a_id = relationship.partner_a_id
    partner_b_id = relationship.partner_b_id
    
    partner_a_consent = UserConsent.objects.get(user_id=partner_a_id)
    partner_b_consent = UserConsent.objects.get(user_id=partner_b_id)
    
    partner_a_age = AgeVerification.objects.filter(user_id=partner_a_id).first()
    partner_b_age = AgeVerification.objects.filter(user_id=partner_b_id).first()

    return JointConsentResult(
        both_enrolled=(
            partner_a_consent.joint_session_participation == 'enrolled' and
            partner_b_consent.joint_session_participation == 'enrolled'
        ),
        both_age_verified=(
            partner_a_age and partner_a_age.status == 'verified' and
            partner_b_age and partner_b_age.status == 'verified'
        ),
        no_active_safety_escalation=(
            not has_active_safety_escalation(partner_a_id) and
            not has_active_safety_escalation(partner_b_id)
        )
    )

class JointSessionInitiateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdult]

    def post(self, request):
        user = request.user
        relationship = Relationship.objects.filter(
            (models.Q(partner_a_id=user.id) | models.Q(partner_b_id=user.id)) & 
            models.Q(status='active')
        ).first()
        
        if not relationship:
            return response.Response({"error": "no_active_relationship"}, status=status.HTTP_400_BAD_REQUEST)
        
        partner_id = relationship.partner_b_id if relationship.partner_a_id == user.id else relationship.partner_a_id
        
        # Check partner enrollment
        try:
            partner_consent = UserConsent.objects.get(user_id=partner_id)
            if partner_consent.joint_session_participation != 'enrolled':
                return response.Response({"error": "partner_not_enrolled"}, status=status.HTTP_400_BAD_REQUEST)
        except UserConsent.DoesNotExist:
            return response.Response({"error": "partner_not_enrolled"}, status=status.HTTP_400_BAD_REQUEST)

        # Create joint session
        joint_session = JointSession.objects.create(
            relationship=relationship,
            initiator=user,
            expires_at=timezone.now() + timedelta(minutes=15)
        )
        
        return response.Response({
            "joint_session_id": str(joint_session.id),
            "state": joint_session.state,
            "expires_at": joint_session.expires_at.isoformat()
        }, status=status.HTTP_201_CREATED)

class JointSessionConfirmView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdult]

    def post(self, request, session_id):
        user = request.user
        joint_session = get_object_or_404(JointSession, id=session_id)
        
        if joint_session.state == JointSessionState.ACTIVE.value:
            return response.Response({
                "state": joint_session.state,
                "partner_confirmed": True,
                "both_confirmed": True
            })

        relationship = joint_session.relationship
        is_partner_a = relationship.partner_a_id == user.id
        
        if is_partner_a:
            joint_session.partner_a_confirmed = True
        else:
            joint_session.partner_b_confirmed = True
            
        from_state = JointSessionState(joint_session.state)
        to_state = from_state
        
        if from_state == JointSessionState.PENDING_A:
            if joint_session.partner_a_confirmed:
                to_state = JointSessionState.PENDING_B
        elif from_state == JointSessionState.PENDING_B:
            if joint_session.partner_a_confirmed and joint_session.partner_b_confirmed:
                # Validate consent before going live
                consent_result = validate_joint_session_consent(relationship)
                if consent_result.is_valid:
                    to_state = JointSessionState.ACTIVE
                else:
                    to_state = JointSessionState.TERMINATED
        
        if to_state != from_state:
            joint_session.state = to_state.value
            
            AuditLogger.get_instance().log(
                event_type="joint_session_state_transition",
                user_id=user.id,
                relationship_id=relationship.id,
                metadata={
                    "joint_session_id": str(joint_session.id),
                    "from_state": from_state.value,
                    "to_state": to_state.value,
                    "triggered_by": f"partner_{'a' if is_partner_a else 'b'}_confirmation"
                }
            )
            
        joint_session.save()
        
        partner_confirmed = joint_session.partner_b_confirmed if is_partner_a else joint_session.partner_a_confirmed
        
        return response.Response({
            "state": joint_session.state,
            "partner_confirmed": partner_confirmed,
            "both_confirmed": joint_session.state == JointSessionState.ACTIVE.value
        })

class JointSessionExitView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdult]

    def post(self, request, session_id):
        user = request.user
        joint_session = get_object_or_404(JointSession, id=session_id)
        
        from_state = JointSessionState(joint_session.state)
        joint_session.state = JointSessionState.EXITED.value
        joint_session.save()
        
        AuditLogger.get_instance().log(
            event_type="joint_session_state_transition",
            user_id=user.id,
            relationship_id=joint_session.relationship.id,
            metadata={
                "joint_session_id": str(joint_session.id),
                "from_state": from_state.value,
                "to_state": JointSessionState.EXITED.value,
                "triggered_by": "partner_exit"
            }
        )
        
        return response.Response({"status": "exited"}, status=status.HTTP_200_OK)

class JointSessionStatusView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdult]

    def get(self, request, session_id):
        joint_session = get_object_or_404(JointSession, id=session_id)
        
        if joint_session.is_expired:
            joint_session.state = JointSessionState.TERMINATED.value
            joint_session.save()
            
        user = request.user
        is_partner_a = joint_session.relationship.partner_a_id == user.id
        partner_confirmed = joint_session.partner_b_confirmed if is_partner_a else joint_session.partner_a_confirmed

        return response.Response({
            "state": joint_session.state,
            "partner_confirmed": partner_confirmed,
            "both_confirmed": joint_session.state == JointSessionState.ACTIVE.value
        })
