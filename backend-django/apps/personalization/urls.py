from django.urls import path
from apps.personalization.views import PortraitView, ProfileView, QuestionnaireView

urlpatterns = [
    path('profile', ProfileView.as_view(), name='personalization-profile'),
    path('questionnaire', QuestionnaireView.as_view(), name='personalization-questionnaire'),
    path('portrait', PortraitView.as_view(), name='personalization-portrait'),
]
