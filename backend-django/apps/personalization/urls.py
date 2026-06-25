from django.urls import path
from apps.personalization.views import ProfileView, QuestionnaireView

urlpatterns = [
    path('profile', ProfileView.as_view(), name='personalization-profile'),
    path('questionnaire', QuestionnaireView.as_view(), name='personalization-questionnaire'),
]
