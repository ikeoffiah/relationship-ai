from rest_framework import status, views, permissions
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Memory

class MemoryListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, user_id):
        """
        GET /api/v1/users/{user_id}/memory
        Get list of memories for a user.
        """
        if request.user.id != user_id:
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        
        memories = Memory.objects.filter(user_id=user_id).order_by('-created_at')
        results = []
        for mem in memories:
            results.append({
                "id": str(mem.id),
                "content": mem.decrypted_content,
                "metadata": mem.metadata,
                "reinforcement_count": mem.reinforcement_count,
                "created_at": mem.created_at.isoformat(),
            })
            
        return Response({"results": results}, status=status.HTTP_200_OK)

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
