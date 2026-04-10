from django.urls import path
from apps.counseling.views import EndSessionView

urlpatterns = [
    path("sessions/end/", EndSessionView.as_view(), name="end-session"),
]
