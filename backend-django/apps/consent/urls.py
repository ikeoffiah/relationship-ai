from django.urls import path
from . import views

urlpatterns = [
    path(
        "<uuid:user_id>/consent/", views.UserConsentView.as_view(), name="user-consent"
    ),
    path(
        "<uuid:user_id>/consent/audit/",
        views.ConsentAuditListView.as_view(),
        name="consent-audit",
    ),
]
