from django.urls import path
from . import views

urlpatterns = [
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('change-email/', views.ChangeEmailView.as_view(), name='change-email'),
    path('notification-preferences/', views.NotificationPreferencesView.as_view(), name='notification-preferences'),
    path('fcm-token/', views.FCMTokenView.as_view(), name='fcm-token'),
    path('account/', views.AccountDeletionView.as_view(), name='account-delete'),
]
