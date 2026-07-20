"""
The audit trail is the evidence the consent and joint-session features rely
on, so an event's subject must be the authenticated caller. A caller-supplied
user_id previously won over request.user.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def caller(db):
    return User.objects.create_user(email="caller@example.com", password="pw")


@pytest.fixture
def victim(db):
    return User.objects.create_user(email="victim@example.com", password="pw")


def client_for(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.mark.django_db
def test_event_is_attributed_to_the_caller_not_the_payload(caller, victim, mocker):
    logged = mocker.patch("apps.audit.logger.AuditLogger.log", return_value="evt-1")

    res = client_for(caller).post(
        "/api/v1/audit/log",
        {"event_type": "consent_changed", "user_id": str(victim.id)},
        format="json",
    )

    assert res.status_code == 201
    assert logged.call_args.kwargs["user_id"] == caller.id, (
        "a caller must not be able to forge audit events against another user"
    )


@pytest.mark.django_db
def test_event_type_is_still_required(caller):
    res = client_for(caller).post("/api/v1/audit/log", {}, format="json")
    assert res.status_code == 400


@pytest.mark.django_db
def test_requires_authentication(victim):
    res = APIClient().post(
        "/api/v1/audit/log", {"event_type": "x"}, format="json"
    )
    assert res.status_code in (401, 403)
