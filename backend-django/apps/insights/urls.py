from django.urls import path

from apps.insights import views

urlpatterns = [
    path("", views.insights, name="insights"),
]
