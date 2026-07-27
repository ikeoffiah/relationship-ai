"""Tests for mirroring in-app notifications to push (signals.py)."""

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.profile.models import UserProfile
from apps.notifications import signals
from apps.notifications.notification_models import Notification, NotificationType

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(email="pushuser@example.com", password="pw")


def _set_token(user, token):
    UserProfile.objects.update_or_create(user=user, defaults={"fcm_token": token})


def _make_notification(user):
    return Notification.objects.create(
        user_id=user.id,
        type=NotificationType.SYSTEM,
        title="Bliss added something 🌸",
        body="Call the venue",
        data={"deep_link": "/engagement/bliss"},
    )


def test_push_sent_when_token_present(db, user, settings, mocker):
    settings.PUSH_SYNCHRONOUS = True
    _set_token(user, "device-token-123")
    send = mocker.patch.object(signals.push_service, "send_to_user", return_value=True)

    _make_notification(user)

    assert send.called
    token_arg, push_arg = send.call_args.args
    assert token_arg == "device-token-123"
    assert push_arg.title == "Bliss added something 🌸"
    assert push_arg.body == "Call the venue"
    # The notification type is carried in the push data payload.
    assert push_arg.data.get("type") == NotificationType.SYSTEM


def test_no_push_when_token_blank(db, user, settings, mocker):
    settings.PUSH_SYNCHRONOUS = True
    _set_token(user, "")
    send = mocker.patch.object(signals.push_service, "send_to_user")

    _make_notification(user)

    assert not send.called


def test_no_push_when_no_profile(db, user, settings, mocker):
    settings.PUSH_SYNCHRONOUS = True
    send = mocker.patch.object(signals.push_service, "send_to_user")

    _make_notification(user)  # user has no profile at all

    assert not send.called


def test_push_failure_never_breaks_notification_creation(db, user, settings, mocker):
    settings.PUSH_SYNCHRONOUS = True
    _set_token(user, "device-token-123")
    mocker.patch.object(signals.push_service, "send_to_user", side_effect=Exception("fcm down"))

    notification = _make_notification(user)  # must not raise

    assert Notification.objects.filter(id=notification.id).exists()
