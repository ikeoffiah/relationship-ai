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
        # Note: In mobile consent_api_service it sends `{'event_type': 'session_consent_summary_shown', 'user_id': userId}`.
        # We handle any extra top-level keys by merging them into metadata, except event_type and user_id.
        user_id = request.data.get("user_id", request.user.id)
        
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
