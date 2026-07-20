"""
Tests for the in-app notification API.

These endpoints were implemented but never routed, so this suite is the first
thing to exercise them. Ownership coverage is deliberate: every route is
addressed by an id in the URL, so authentication alone would leave them open
to trivial IDOR.
"""

import uuid

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.notifications.notification_models import Notification, NotificationType

User = get_user_model()


@pytest.fixture
def owner(db):
    return User.objects.create_user(email="owner@example.com", password="pw")


@pytest.fixture
def intruder(db):
    return User.objects.create_user(email="intruder@example.com", password="pw")


@pytest.fixture
def client_for():
    def _client(user):
        c = APIClient()
        c.force_authenticate(user=user)
        return c

    return _client


def make_notification(user, **kwargs):
    defaults = {
        "user_id": user.id,
        "type": NotificationType.SESSION_REMINDER,
        "title": "Session reminder",
        "body": "Your session starts soon.",
        "read": False,
    }
    defaults.update(kwargs)
    return Notification.objects.create(**defaults)


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_list_returns_own_notifications(owner, client_for):
    make_notification(owner, title="First")
    make_notification(owner, title="Second")

    res = client_for(owner).get(f"/api/v1/users/{owner.id}/notifications")

    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 2
    assert len(body["notifications"]) == 2
    assert body["has_more"] is False
    assert {n["title"] for n in body["notifications"]} == {"First", "Second"}


@pytest.mark.django_db
def test_list_paginates_and_reports_has_more(owner, client_for):
    for i in range(3):
        make_notification(owner, title=f"N{i}")

    res = client_for(owner).get(f"/api/v1/users/{owner.id}/notifications?page=1&limit=2")

    body = res.json()
    assert len(body["notifications"]) == 2
    assert body["total"] == 3
    assert body["has_more"] is True


@pytest.mark.django_db
def test_list_is_ordered_newest_first(owner, client_for):
    make_notification(owner, title="Older")
    make_notification(owner, title="Newer")

    res = client_for(owner).get(f"/api/v1/users/{owner.id}/notifications")

    titles = [n["title"] for n in res.json()["notifications"]]
    assert titles == ["Newer", "Older"]


@pytest.mark.django_db
def test_cannot_list_another_users_notifications(owner, intruder, client_for):
    make_notification(owner, title="Private")

    res = client_for(intruder).get(f"/api/v1/users/{owner.id}/notifications")

    assert res.status_code == 403


@pytest.mark.django_db
def test_list_requires_authentication(owner):
    res = APIClient().get(f"/api/v1/users/{owner.id}/notifications")
    assert res.status_code in (401, 403)


# ---------------------------------------------------------------------------
# unread count
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_unread_count_excludes_read(owner, client_for):
    make_notification(owner, read=False)
    make_notification(owner, read=False)
    make_notification(owner, read=True)

    res = client_for(owner).get(f"/api/v1/users/{owner.id}/notifications/unread-count")

    assert res.status_code == 200
    assert res.json()["count"] == 2


@pytest.mark.django_db
def test_cannot_read_another_users_unread_count(owner, intruder, client_for):
    make_notification(owner, read=False)
    res = client_for(intruder).get(f"/api/v1/users/{owner.id}/notifications/unread-count")
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# mark read
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_mark_read_sets_flag(owner, client_for):
    n = make_notification(owner, read=False)

    res = client_for(owner).put(f"/api/v1/notifications/{n.id}/read")

    assert res.status_code == 200
    n.refresh_from_db()
    assert n.read is True


@pytest.mark.django_db
def test_cannot_mark_another_users_notification_read(owner, intruder, client_for):
    n = make_notification(owner, read=False)

    res = client_for(intruder).put(f"/api/v1/notifications/{n.id}/read")

    # 404 rather than 403: do not confirm that the id exists.
    assert res.status_code == 404
    n.refresh_from_db()
    assert n.read is False


@pytest.mark.django_db
def test_mark_read_unknown_id_is_404(owner, client_for):
    res = client_for(owner).put(f"/api/v1/notifications/{uuid.uuid4()}/read")
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# mark all read
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_mark_all_read_only_touches_unread(owner, client_for):
    make_notification(owner, read=False)
    make_notification(owner, read=False)
    make_notification(owner, read=True)

    res = client_for(owner).put(f"/api/v1/users/{owner.id}/notifications/read-all")

    assert res.status_code == 200
    assert res.json()["marked_read"] == 2
    assert Notification.objects.filter(user_id=owner.id, read=False).count() == 0


@pytest.mark.django_db
def test_mark_all_read_does_not_affect_other_users(owner, intruder, client_for):
    mine = make_notification(owner, read=False)
    theirs = make_notification(intruder, read=False)

    client_for(owner).put(f"/api/v1/users/{owner.id}/notifications/read-all")

    mine.refresh_from_db()
    theirs.refresh_from_db()
    assert mine.read is True
    assert theirs.read is False


@pytest.mark.django_db
def test_cannot_mark_all_read_for_another_user(owner, intruder, client_for):
    n = make_notification(owner, read=False)

    res = client_for(intruder).put(f"/api/v1/users/{owner.id}/notifications/read-all")

    assert res.status_code == 403
    n.refresh_from_db()
    assert n.read is False


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_delete_removes_own_notification(owner, client_for):
    n = make_notification(owner)

    res = client_for(owner).delete(f"/api/v1/notifications/{n.id}")

    assert res.status_code == 204
    assert not Notification.objects.filter(id=n.id).exists()


@pytest.mark.django_db
def test_cannot_delete_another_users_notification(owner, intruder, client_for):
    n = make_notification(owner)

    res = client_for(intruder).delete(f"/api/v1/notifications/{n.id}")

    assert res.status_code == 404
    assert Notification.objects.filter(id=n.id).exists()
