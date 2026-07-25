"""Tests for the joint-session LiveKit video token endpoint."""

from datetime import timedelta

import jwt
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.relationships.models import Relationship
from apps.sessions.joint_session import JointSessionState
from apps.sessions.models import JointSession

User = get_user_model()

SECRET = "test-livekit-secret"


def adult(email):
    user = User.objects.create_user(email=email, password="pw")
    user.date_of_birth = timezone.now().date() - timedelta(days=365 * 30)
    user.save()
    return user


@pytest.fixture
def livekit_env(settings):
    settings.LIVEKIT_API_KEY = "APIkey123"
    settings.LIVEKIT_API_SECRET = SECRET
    settings.LIVEKIT_URL = "wss://demo.livekit.cloud"
    return settings


@pytest.fixture
def partners(db):
    return adult("va@example.com"), adult("vb@example.com")


@pytest.fixture
def session(db, partners):
    a, b = partners
    rel = Relationship.objects.create(partner_a=a, partner_b=b, status="active")
    return JointSession.objects.create(
        relationship=rel,
        initiator=a,
        state=JointSessionState.ACTIVE.value,
        partner_a_confirmed=True,
        partner_b_confirmed=True,
        expires_at=timezone.now() + timedelta(hours=1),
    )


def client_for(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def url(session):
    return f"/api/v1/sessions/joint/{session.id}/video-token"


@pytest.mark.django_db
def test_both_partners_get_a_token_for_the_same_room(livekit_env, partners, session):
    a, b = partners
    ra = client_for(a).post(url(session))
    rb = client_for(b).post(url(session))
    assert ra.status_code == 200 and rb.status_code == 200
    # Same room for both partners; the URL is passed through.
    assert ra.data["room"] == rb.data["room"] == f"joint-{session.id}"
    assert ra.data["url"] == "wss://demo.livekit.cloud"


@pytest.mark.django_db
def test_token_encodes_room_identity_and_join_grant(livekit_env, partners, session):
    a, _ = partners
    res = client_for(a).post(url(session))
    claims = jwt.decode(res.data["token"], SECRET, algorithms=["HS256"])
    assert claims["sub"] == str(a.id)
    assert claims["video"]["room"] == f"joint-{session.id}"
    assert claims["video"]["roomJoin"] is True
    assert claims["exp"] > claims["nbf"]


@pytest.mark.django_db
def test_outsider_cannot_get_a_token(livekit_env, session):
    outsider = adult("outsider@example.com")
    res = client_for(outsider).post(url(session))
    assert res.status_code == 404  # 404, not 403 — don't confirm the session exists


@pytest.mark.django_db
def test_returns_503_when_livekit_unconfigured(settings, partners, session):
    settings.LIVEKIT_API_KEY = None
    settings.LIVEKIT_API_SECRET = None
    settings.LIVEKIT_URL = None
    a, _ = partners
    res = client_for(a).post(url(session))
    assert res.status_code == 503
    assert res.data["code"] == "video_unconfigured"


@pytest.mark.django_db
def test_expired_session_rejected(livekit_env, partners):
    a, b = partners
    rel = Relationship.objects.create(partner_a=a, partner_b=b, status="active")
    expired = JointSession.objects.create(
        relationship=rel,
        initiator=a,
        state=JointSessionState.PENDING_B.value,
        expires_at=timezone.now() - timedelta(minutes=1),
    )
    res = client_for(a).post(url(expired))
    assert res.status_code == 409


@pytest.mark.django_db
def test_requires_authentication(livekit_env, session):
    res = APIClient().post(url(session))
    assert res.status_code in (401, 403)
