from django.urls import path
from apps.personalization.views import (
    BehaviourView,
    ConnectionScoreView,
    PortraitView,
    ProfileView,
    QuestionnaireView,
)

urlpatterns = [
    path('profile', ProfileView.as_view(), name='personalization-profile'),
    path('questionnaire', QuestionnaireView.as_view(), name='personalization-questionnaire'),
    path('portrait', PortraitView.as_view(), name='personalization-portrait'),
    # Self only. There is deliberately no id parameter — see BehaviourView.
    path('behaviour', BehaviourView.as_view(), name='personalization-behaviour'),
    # Joint by design: both partners see the same number, because it is built
    # from what they both did.
    path(
        'connection',
        ConnectionScoreView.as_view(),
        name='personalization-connection',
    ),
]
