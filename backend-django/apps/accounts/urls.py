from django.urls import path
from . import views

urlpatterns = [
    path("signup/", views.RegisterView.as_view(), name="signup"),
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("authorize/", views.AuthorizeView.as_view(), name="authorize"),
    path("token/", views.TokenView.as_view(), name="token"),
    path("refresh/", views.RefreshView.as_view(), name="refresh"),
    path("revoke/", views.RevokeView.as_view(), name="revoke"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("me/", views.MeView.as_view(), name="me"),
    path("google/", views.GoogleLoginView.as_view(), name="google"),
    path(
        "forgot-password/", views.ForgotPasswordView.as_view(), name="forgot-password"
    ),
    path("reset-password/", views.ResetPasswordView.as_view(), name="reset-password"),
]
