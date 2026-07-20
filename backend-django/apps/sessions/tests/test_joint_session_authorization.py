"""
Authorization regression tests for the joint-session routes.

These routes are addressed by session id with only IsAuthenticated + IsAdult.
Before the scoped fetch, any logged-in adult who knew a session UUID could
confirm, terminate or read a joint session belonging to two other people --
`is_partner_a` was a branch selector, so a stranger fell into the else branch
and was treated as partner B.
"""

import uuid
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.relationships.models import Relationship
from apps.sessions.joint_session import JointSessionState
from apps.sessions.models import JointSession

User = get_user_model()


def adult(email):
    user = User.objects.create_user(email=email, password="pw")
    user.date_of_birth = timezone.now().date() - timedelta(days=365 * 30)
    user.save()
    return user


@pytest.fixture
def partners(db):
    return adult("a@example.com"), adult("b@example.com")


@pytest.fixture
def outsider(db):
    return adult("outsider@example.com")


@pytest.fixture
def session(db, partners):
    a, b = partners
    relationship = Relationship.objects.create(partner_a=a, partner_b=b, status="active")
    return JointSession.objects.create(
        relationship=relationship,
        initiator=a,
        state=JointSessionState.PENDING_B.value,
        partner_a_confirmed=True,
        partner_b_confirmed=False,
        expires_at=timezone.now() + timedelta(hours=1),
    )


def client_for(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.mark.django_db
def test_outsider_cannot_confirm_someone_elses_session(session, outsider):
    """The worst case: a stranger consenting on partner B's behalf and
    starting a live counseling session between two other people."""
    res = client_for(outsider).post(f"/api/v1/sessions/joint/{session.id}/confirm")

    assert res.status_code == 404
    session.refresh_from_db()
    assert session.partner_b_confirmed is False
    assert session.state == JointSessionState.PENDING_B.value


@pytest.mark.django_db
def test_outsider_cannot_terminate_someone_elses_session(session, outsider):
    res = client_for(outsider).post(f"/api/v1/sessions/joint/{session.id}/exit")

    assert res.status_code == 404
    session.refresh_from_db()
    assert session.state != JointSessionState.EXITED.value


@pytest.mark.django_db
def test_outsider_cannot_read_someone_elses_session_status(session, outsider):
    res = client_for(outsider).get(f"/api/v1/sessions/joint/{session.id}/status")
    assert res.status_code == 404


@pytest.mark.django_db
def test_partner_can_still_confirm(session, partners):
    _, partner_b = partners

    res = client_for(partner_b).post(f"/api/v1/sessions/joint/{session.id}/confirm")

    assert res.status_code == 200
    session.refresh_from_db()
    assert session.partner_b_confirmed is True


@pytest.mark.django_db
def test_partner_can_still_read_status(session, partners):
    partner_a, _ = partners
    res = client_for(partner_a).get(f"/api/v1/sessions/joint/{session.id}/status")
    assert res.status_code == 200


@pytest.mark.django_db
def test_unknown_session_is_404(outsider):
    res = client_for(outsider).get(f"/api/v1/sessions/joint/{uuid.uuid4()}/status")
    assert res.status_code == 404
