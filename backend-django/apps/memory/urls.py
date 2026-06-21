from django.urls import path
from . import views

urlpatterns = [
    path("<uuid:user_id>/memory", views.MemoryListView.as_view(), name="memory-list"),
    path("<uuid:user_id>/memory/<uuid:memory_id>", views.MemoryDetailView.as_view(), name="memory-detail"),
]
