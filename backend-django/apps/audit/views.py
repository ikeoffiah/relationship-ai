from rest_framework import status, views, permissions
from rest_framework.response import Response
from .logger import AuditLogger

class AuditLogView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """
        POST /api/v1/audit/log
        Log an audit event.
        Payload expected:
        {
            "event_type": "...",
            "metadata": {...}
        }
        """
        event_type = request.data.get("event_type")
        if not event_type:
            return Response({"error": "event_type is required"}, status=status.HTTP_400_BAD_REQUEST)

        metadata = request.data.get("metadata", {})
        # The audit trail is the evidence the consent and joint-session
        # features rely on, so the subject is always the authenticated caller.
        # A caller-supplied user_id previously won over request.user, which let
        # any logged-in user forge events attributed to anyone else. The mobile
        # client still sends its own user_id; it is ignored rather than trusted.
        user_id = request.user.id

        # Pull out session/relationship if provided
        session_id = request.data.get("session_id")
        relationship_id = request.data.get("relationship_id")

        # Any other data into metadata
        for k, v in request.data.items():
            if k not in ["event_type", "user_id", "session_id", "relationship_id", "metadata"]:
                metadata[k] = v

        logger = AuditLogger.get_instance()
        event_id = logger.log(
            event_type=event_type,
            user_id=user_id,
            metadata=metadata,
            session_id=session_id,
            relationship_id=relationship_id
        )

        return Response({"event_id": event_id, "status": "logged"}, status=status.HTTP_201_CREATED)
