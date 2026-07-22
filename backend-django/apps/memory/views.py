from rest_framework import status, views, permissions
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Memory

class MemoryListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, user_id):
        """
        GET /api/v1/users/{user_id}/memory[?session_id=<id>]

        Lists the user's memories. With session_id, returns only memories
        extracted from that session (extraction stamps source_session_id into
        metadata). category and session_id are surfaced at the top level so
        the session-history client can read them without digging into metadata.
        """
        if request.user.id != user_id:
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        memories = Memory.objects.filter(user_id=user_id).order_by('-created_at')

        session_id = request.query_params.get("session_id")
        if session_id:
            memories = memories.filter(metadata__source_session_id=session_id)

        results = []
        for mem in memories:
            meta = mem.metadata or {}
            results.append({
                "id": str(mem.id),
                "content": mem.decrypted_content,
                "category": meta.get("category"),
                "session_id": meta.get("source_session_id"),
                "metadata": meta,
                "reinforcement_count": mem.reinforcement_count,
                "created_at": mem.created_at.isoformat(),
            })

        return Response({"results": results}, status=status.HTTP_200_OK)

    def delete(self, request, user_id):
        """
        DELETE /api/v1/users/{user_id}/memory?session_id=<id>

        Bulk-deletes every memory extracted from one session. session_id is
        required — a blanket delete of all of a user's memories is not exposed
        here.
        """
        if request.user.id != user_id:
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        session_id = request.query_params.get("session_id")
        if not session_id:
            return Response(
                {"error": "session_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        deleted, _ = Memory.objects.filter(
            user_id=user_id, metadata__source_session_id=session_id
        ).delete()
        return Response({"deleted": deleted}, status=status.HTTP_200_OK)

class MemoryDetailView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, user_id, memory_id):
        """
        PUT /api/v1/users/{user_id}/memory/{memory_id}
        """
        if request.user.id != user_id:
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
            
        memory = get_object_or_404(Memory, id=memory_id, user_id=user_id)
        
        content = request.data.get("content")
        metadata = request.data.get("metadata")
        
        if content is not None:
            # Setting it will cause it to be encrypted on save
            memory.content = content
        if metadata is not None:
            memory.metadata = metadata
            
        memory.save()
        
        return Response({
            "id": str(memory.id),
            "content": memory.decrypted_content,
            "metadata": memory.metadata
        }, status=status.HTTP_200_OK)
        
    def delete(self, request, user_id, memory_id):
        """
        DELETE /api/v1/users/{user_id}/memory/{memory_id}
        """
        if request.user.id != user_id:
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
            
        memory = get_object_or_404(Memory, id=memory_id, user_id=user_id)
        memory.delete()
        
        return Response(status=status.HTTP_204_NO_CONTENT)
