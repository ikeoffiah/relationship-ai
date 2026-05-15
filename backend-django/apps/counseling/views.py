from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.utils import timezone
from apps.counseling.models import Session
from apps.counseling.tasks import process_post_session_async
from apps.relationships.models import Relationship
import logging

logger = logging.getLogger(__name__)


class EndSessionView(APIView):
    """
    Endpoint to end a counseling session and trigger async processing.
    Expected payload:
    {
        "relationship_id": "uuid",
        "transcript": "full session transcript text"
    }
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        relationship_id = request.data.get("relationship_id")
        transcript = request.data.get("transcript")

        if not relationship_id or not transcript:
            return Response(
                {"error": "relationship_id and transcript are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            relationship = Relationship.objects.get(
                id=relationship_id, user=request.user
            )

            # Create a new completed session
            session = Session.objects.create(
                user=request.user,
                relationship=relationship,
                transcript=transcript,
                status=Session.Status.COMPLETED,
                completed_at=timezone.now(),
            )

            # Trigger async processing
            process_post_session_async.delay(session.id)

            logger.info(
                f"Session {session.id} ended and async processing triggered for user {request.user.id}"
            )

            return Response(
                {
                    "message": "Session ended successfully. Post-session processing started.",
                    "session_id": str(session.id),
                },
                status=status.HTTP_201_CREATED,
            )

        except Relationship.DoesNotExist:
            return Response(
                {"error": "Relationship not found or does not belong to user"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.exception(f"Error ending session: {e}")
            return Response(
                {"error": "An internal error occurred"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
