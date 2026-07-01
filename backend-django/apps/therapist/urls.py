from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TherapistLoginView, TherapistConnectionViewSet, TherapistStrategyNoteViewSet

router = DefaultRouter()
router.register(r'connections', TherapistConnectionViewSet, basename='therapist-connection')
router.register(r'notes', TherapistStrategyNoteViewSet, basename='therapist-note')

urlpatterns = [
    path('auth/login/', TherapistLoginView.as_view(), name='therapist-login'),
    path('', include(router.urls)),
]
