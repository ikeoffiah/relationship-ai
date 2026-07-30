from django.urls import path
from . import email_views, views

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
    # Email verification. Verify first; change only while still unverified.
    path("email/status", email_views.email_status, name="email-status"),
    path("email/send", email_views.send_verification, name="email-send"),
    path("email/confirm", email_views.confirm_verification, name="email-confirm"),
    path("email/change", email_views.change_email, name="email-change"),
    path("google/", views.GoogleLoginView.as_view(), name="google"),
    path(
        "forgot-password/", views.ForgotPasswordView.as_view(), name="forgot-password"
    ),
    path("reset-password/", views.ResetPasswordView.as_view(), name="reset-password"),
    # Changing a password while signed in, by proving the current one. Distinct
    # from the reset flow, which exists for people who cannot sign in.
    path("change-password", email_views.change_password, name="change-password"),
    path("verify-age/", views.VerifyAgeView.as_view(), name="verify-age"),
    path("guardian-consent/", views.GuardianConsentView.as_view(), name="guardian-consent"),
]
