from django.urls import path
from . import views

urlpatterns = [
    path("<uuid:user_id>/consent/", views.UserConsentView.as_view(), name="user-consent"),
]
