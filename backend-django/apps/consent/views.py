from rest_framework import generics, status, response, permissions
from django.shortcuts import get_object_or_404
from apps.consent.models import UserConsent, ConsentChangeLog
from apps.consent.serializers import ConsentSerializer, ConsentChangeLogSerializer
from apps.consent.permissions import IsConsentOwner

class ConsentDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = ConsentSerializer
    permission_classes = [permissions.IsAuthenticated, IsConsentOwner]
    lookup_field = 'user_id'

    def get_object(self):
        user_id = self.kwargs.get('user_id')
        obj = get_object_or_404(UserConsent, user_id=user_id)
        self.check_object_permissions(self.request, obj)
        return obj

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return response.Response({"data": serializer.data})

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        # Pass auditing context to the model save method
        serializer.save(
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT')
        )
        
        return response.Response({"data": serializer.data})

class ConsentHistoryView(generics.ListAPIView):
    serializer_class = ConsentChangeLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # User can only see their own history
        user_id = self.kwargs.get('user_id')
        if str(self.request.user.id) != user_id:
            return ConsentChangeLog.objects.none()
        
        return ConsentChangeLog.objects.filter(user_id=user_id).order_by('-changed_at')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        if not queryset.exists() and str(request.user.id) != self.kwargs.get('user_id'):
             return response.Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
             
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return response.Response({"data": serializer.data})
