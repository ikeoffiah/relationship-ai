from django.urls import path
from apps.sessions.views import (
    JointSessionInitiateView,
    JointSessionConfirmView,
    JointSessionExitView,
    JointSessionStatusView,
)

urlpatterns = [
    path("joint/initiate", JointSessionInitiateView.as_view(), name="joint_session_initiate"),
    path("joint/<uuid:session_id>/confirm", JointSessionConfirmView.as_view(), name="joint_session_confirm"),
    path("joint/<uuid:session_id>/exit", JointSessionExitView.as_view(), name="joint_session_exit"),
    path("joint/<uuid:session_id>/status", JointSessionStatusView.as_view(), name="joint_session_status"),
]
