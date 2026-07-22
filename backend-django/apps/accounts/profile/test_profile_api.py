"""
Tests for the profile / notification-preference / account endpoints.

These are all scoped to request.user (no user id in the URL). The notification
preferences model the four events the mobile app surfaces.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.accounts.profile.models import NotificationPreference, UserProfile

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(email="u@example.com", password="pw")


def api(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


# ---------------------------------------------------------------------------
# profile
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_get_profile_returns_full_name_and_email(user):
    user.full_name = "Ada Lovelace"
    user.save()
    UserProfile.objects.create(user=user, full_name="Ada Lovelace")

    res = api(user).get("/api/v1/users/profile/")

    assert res.status_code == 200
    body = res.json()
    assert body["full_name"] == "Ada Lovelace"
    # email is sourced read-only from the User, which the client reads here.
    assert body["email"] == "u@example.com"


@pytest.mark.django_db
def test_get_profile_autocreates_for_a_new_user(user):
    res = api(user).get("/api/v1/users/profile/")
    assert res.status_code == 200
    assert UserProfile.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_update_full_name(user):
    UserProfile.objects.create(user=user)

    res = api(user).patch(
        "/api/v1/users/profile/", {"full_name": "Grace Hopper"}, format="json"
    )

    assert res.status_code == 200
    user.profile.refresh_from_db()
    assert user.profile.full_name == "Grace Hopper"


@pytest.mark.django_db
def test_email_is_read_only_on_the_profile(user):
    UserProfile.objects.create(user=user)

    api(user).patch(
        "/api/v1/users/profile/", {"email": "hacker@example.com"}, format="json"
    )

    user.refresh_from_db()
    assert user.email == "u@example.com"


@pytest.mark.django_db
def test_profile_requires_authentication():
    res = APIClient().get("/api/v1/users/profile/")
    assert res.status_code in (401, 403)


# ---------------------------------------------------------------------------
# notification preferences
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_notification_preferences_expose_the_four_events(user):
    res = api(user).get("/api/v1/users/notification-preferences/")

    assert res.status_code == 200
    body = res.json()
    assert set(body.keys()) == {
        "session_reminders",
        "partner_joined_session",
        "relay_message_received",
        "insight_detected",
    }


@pytest.mark.django_db
def test_update_a_single_notification_toggle(user):
    NotificationPreference.objects.create(user=user)

    res = api(user).patch(
        "/api/v1/users/notification-preferences/",
        {"insight_detected": True},
        format="json",
    )

    assert res.status_code == 200
    user.notification_pref.refresh_from_db()
    assert user.notification_pref.insight_detected is True


@pytest.mark.django_db
def test_notification_preferences_require_authentication():
    res = APIClient().get("/api/v1/users/notification-preferences/")
    assert res.status_code in (401, 403)


# ---------------------------------------------------------------------------
# account deletion
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_delete_account_deactivates_the_user(user):
    res = api(user).delete("/api/v1/users/account/")

    assert res.status_code in (200, 204)
    user.refresh_from_db()
    assert user.is_active is False
