"""
Authorization tests for the therapist API.

A therapist can propose a connection, but must not be able to manufacture the
client's side of the consent. Nothing in the codebase currently reads these
flags, so there is no live breach — these tests exist so that the first
endpoint which does serve client data inherits a trustworthy gate.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.therapist.models import Therapist, TherapistConnection, TherapistStrategyNote

User = get_user_model()


@pytest.fixture
def therapist_user(db):
    user = User.objects.create_user(email="dr@example.com", password="pw")
    Therapist.objects.create(user=user, name="Dr Example", email="dr@example.com")
    return user


@pytest.fixture
def client_user(db):
    return User.objects.create_user(email="client@example.com", password="pw")


@pytest.fixture
def stranger(db):
    return User.objects.create_user(email="stranger@example.com", password="pw")


def api(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


# ---------------------------------------------------------------------------
# connections
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_therapist_cannot_grant_the_clients_consent(therapist_user, stranger):
    """The core property: only the client may set consent_client."""
    res = api(therapist_user).post(
        "/api/v1/therapist/connections/",
        {"client": str(stranger.id), "consent_therapist": True, "consent_client": True},
        format="json",
    )

    assert res.status_code == 201
    connection = TherapistConnection.objects.get(client=stranger)
    assert connection.consent_client is False
    assert connection.is_active is False, (
        "a therapist must not be able to create an active connection alone"
    )


@pytest.mark.django_db
def test_therapist_cannot_patch_the_clients_consent(therapist_user, client_user):
    connection = TherapistConnection.objects.create(
        therapist=therapist_user.therapist_profile,
        client=client_user,
        consent_therapist=True,
    )

    api(therapist_user).patch(
        f"/api/v1/therapist/connections/{connection.id}/",
        {"consent_client": True},
        format="json",
    )

    connection.refresh_from_db()
    assert connection.consent_client is False


@pytest.mark.django_db
def test_connection_to_unknown_user_is_rejected(therapist_user):
    res = api(therapist_user).post(
        "/api/v1/therapist/connections/",
        {"client": "00000000-0000-0000-0000-000000000000"},
        format="json",
    )
    assert res.status_code == 400


@pytest.mark.django_db
def test_connection_without_a_client_is_rejected(therapist_user):
    res = api(therapist_user).post(
        "/api/v1/therapist/connections/", {}, format="json"
    )
    assert res.status_code == 400


@pytest.mark.django_db
def test_therapist_only_sees_their_own_connections(therapist_user, client_user):
    other_user = User.objects.create_user(email="other-dr@example.com", password="pw")
    other = Therapist.objects.create(
        user=other_user, name="Other", email="other-dr@example.com"
    )
    TherapistConnection.objects.create(therapist=other, client=client_user)

    res = api(therapist_user).get("/api/v1/therapist/connections/")

    assert res.status_code == 200
    assert res.json() == []


# ---------------------------------------------------------------------------
# is_active
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@pytest.mark.parametrize(
    "therapist_consent,client_consent,expected",
    [(False, False, False), (True, False, False), (False, True, False), (True, True, True)],
)
def test_is_active_requires_both_consents(
    therapist_user, client_user, therapist_consent, client_consent, expected
):
    connection = TherapistConnection.objects.create(
        therapist=therapist_user.therapist_profile,
        client=client_user,
        consent_therapist=therapist_consent,
        consent_client=client_consent,
    )
    assert connection.is_active is expected


# ---------------------------------------------------------------------------
# strategy notes
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_cannot_write_notes_about_a_non_client(therapist_user, stranger):
    res = api(therapist_user).post(
        "/api/v1/therapist/notes/",
        {"client": str(stranger.id), "note": "clinical observation"},
        format="json",
    )

    assert res.status_code == 403
    assert not TherapistStrategyNote.objects.filter(client=stranger).exists()


@pytest.mark.django_db
def test_cannot_write_notes_on_a_half_consented_connection(
    therapist_user, client_user
):
    TherapistConnection.objects.create(
        therapist=therapist_user.therapist_profile,
        client=client_user,
        consent_therapist=True,
        consent_client=False,
    )

    res = api(therapist_user).post(
        "/api/v1/therapist/notes/",
        {"client": str(client_user.id), "note": "clinical observation"},
        format="json",
    )

    assert res.status_code == 403


@pytest.mark.django_db
def test_can_write_notes_on_a_fully_consented_connection(
    therapist_user, client_user
):
    TherapistConnection.objects.create(
        therapist=therapist_user.therapist_profile,
        client=client_user,
        consent_therapist=True,
        consent_client=True,
    )

    res = api(therapist_user).post(
        "/api/v1/therapist/notes/",
        {"client": str(client_user.id), "note": "clinical observation"},
        format="json",
    )

    assert res.status_code == 201
    note = TherapistStrategyNote.objects.get(client=client_user)
    assert note.therapist == therapist_user.therapist_profile


@pytest.mark.django_db
def test_note_payload_cannot_override_the_therapist(
    therapist_user, client_user, stranger
):
    TherapistConnection.objects.create(
        therapist=therapist_user.therapist_profile,
        client=client_user,
        consent_therapist=True,
        consent_client=True,
    )
    other_user = User.objects.create_user(email="other-dr2@example.com", password="pw")
    other = Therapist.objects.create(
        user=other_user, name="Other", email="other-dr2@example.com"
    )

    api(therapist_user).post(
        "/api/v1/therapist/notes/",
        {
            "client": str(client_user.id),
            "note": "misattributed",
            "therapist": other.id,
        },
        format="json",
    )

    note = TherapistStrategyNote.objects.get(client=client_user)
    assert note.therapist == therapist_user.therapist_profile
