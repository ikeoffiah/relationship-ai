from django.urls import path
from . import views

urlpatterns = [
    path("me", views.RelationshipMeView.as_view(), name="relationship-me"),
    path("invite", views.RelationshipInviteView.as_view(), name="relationship-invite"),
    path("accept/<str:token>", views.RelationshipAcceptView.as_view(), name="relationship-accept"),
    path("decline/<str:token>", views.RelationshipDeclineView.as_view(), name="relationship-decline"),
    path("<uuid:relationship_id>", views.RelationshipDetailView.as_view(), name="relationship-detail"),
]
