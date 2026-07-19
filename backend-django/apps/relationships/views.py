import secrets
import logging
import hashlib
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from rest_framework import status, views, permissions
from rest_framework.response import Response
from .models import Relationship, RelationshipInvite


logger = logging.getLogger(__name__)

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

class RelationshipInviteView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """
        POST /api/v1/relationships/invite
        Partner A sends an invite to Partner B's email.
        """
        user = request.user
        invitee_email = request.data.get('invitee_email')

        if not invitee_email:
            return Response({"error": "invitee_email is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Validation: Partner A must not already be in an active relationship
        if Relationship.objects.filter(
            (Q(partner_a=user) | Q(partner_b=user)),
            status='active'
        ).exists():
            return Response({"error": "You are already in an active relationship."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # Invalidate any previous pending invites from this user to this email
            RelationshipInvite.objects.filter(
                inviter=user,
                invitee_email=invitee_email,
                status='pending'
            ).update(status='expired')

            # Create invite
            token = secrets.token_urlsafe(32)
            token_hash = hash_token(token)
            expires_at = timezone.now() + timedelta(hours=72)
            
            invite = RelationshipInvite.objects.create(
                inviter=user,
                invitee_email=invitee_email,
                token_hash=token_hash,
                expires_at=expires_at
            )

            # Send email
            invite_url = f"relationshipai://accept-invite?token={token}"
            try:
                send_mail(
                    subject="Connect on RelationshipAI",
                    message=f"Your partner has invited you to link accounts on RelationshipAI. Click here to accept: {invite_url}",
                    from_email=None,
                    recipient_list=[invitee_email],
                )
            except Exception as e:
                logger.error(f"Failed to send invite email: {e}")

        return Response({
            "invite_id": str(invite.id),
            "status": invite.status,
            "expires_at": invite.expires_at.isoformat()
        }, status=status.HTTP_201_CREATED)

class RelationshipAcceptView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, token):
        """
        POST /api/v1/relationships/accept/{token}
        Partner B accepts the invite.
        """
        token_hash = hash_token(token)
        invite = get_object_or_404(RelationshipInvite, token_hash=token_hash)
        user = request.user

        # Validations
        if invite.status != 'pending':
            return Response({"error": f"Invite is already {invite.status}"}, status=status.HTTP_400_BAD_REQUEST)
        
        if invite.is_expired():
            invite.status = 'expired'
            invite.save()
            return Response({"error": "Invite has expired"}, status=status.HTTP_400_BAD_REQUEST)

        if invite.invitee_email.lower() != user.email.lower():
            return Response({"error": "This invite was sent to a different email address."}, status=status.HTTP_403_FORBIDDEN)

        with transaction.atomic():
            # Check if user B is already in an active relationship
            if Relationship.objects.filter(
                (Q(partner_a=user) | Q(partner_b=user)),
                status='active'
            ).exists():
                return Response({"error": "You are already in an active relationship."}, status=status.HTTP_400_BAD_REQUEST)

            # Accept the invite
            invite.status = 'accepted'
            invite.save()

            # Create the relationship
            relationship = Relationship.objects.create(
                partner_a=invite.inviter,
                partner_b=user,
                status='active'
            )

            # Log audit event
            # TODO: Integrate with audit store

        return Response({
            "relationship_id": str(relationship.id),
            "status": relationship.status
        }, status=status.HTTP_200_OK)

class RelationshipDeclineView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, token):
        """
        POST /api/v1/relationships/decline/{token}
        """
        token_hash = hash_token(token)
        invite = get_object_or_404(RelationshipInvite, token_hash=token_hash)
        
        if invite.status != 'pending':
            return Response({"error": f"Invite is already {invite.status}"}, status=status.HTTP_400_BAD_REQUEST)

        invite.status = 'declined'
        invite.save()

        return Response({"status": "declined"}, status=status.HTTP_200_OK)

class RelationshipDetailView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, relationship_id):
        """
        DELETE /api/v1/relationships/{relationship_id}
        Unilateral dissolution.
        """
        user = request.user
        relationship = get_object_or_404(Relationship, id=relationship_id, status='active')

        if relationship.partner_a != user and relationship.partner_b != user:
            return Response({"error": "Not authorized"}, status=status.HTTP_403_FORBIDDEN)

        with transaction.atomic():
            relationship.status = 'dissolved'
            relationship.dissolved_at = timezone.now()
            relationship.save()

            # Trigger Celery Task for cleanup
            from .tasks import RelationshipDissolutionJob
            RelationshipDissolutionJob.delay(str(relationship.id))

        return Response(status=status.HTTP_204_NO_CONTENT)

class RelationshipMeView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """
        GET /api/v1/relationships/me
        Get the current user's active relationship.
        """
        user = request.user
        relationship = Relationship.objects.filter(
            (Q(partner_a=user) | Q(partner_b=user)),
            status='active'
        ).first()

        if not relationship:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        
        # Serialize simply
        partner = relationship.partner_b if relationship.partner_a == user else relationship.partner_a
        
        return Response({
            "id": str(relationship.id),
            "status": relationship.status,
            "created_at": relationship.created_at.isoformat(),
            "partner": {
                "id": str(partner.id),
                "email": partner.email,
            }
        }, status=status.HTTP_200_OK)
