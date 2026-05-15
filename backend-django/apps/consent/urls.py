from django.urls import path
from apps.consent.views import ConsentDetailView, ConsentHistoryView

urlpatterns = [
    path('<uuid:user_id>/consent', ConsentDetailView.as_view(), name='consent-detail'),
    path('<uuid:user_id>/consent/history', ConsentHistoryView.as_view(), name='consent-history'),
]
