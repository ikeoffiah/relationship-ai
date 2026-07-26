"""Tests for the opt-in faith / spirituality feature."""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.engagement import services
from apps.engagement.models import (
    DailyReading,
    FaithPractice,
    FaithPracticeLog,
    FaithReflection,
    PointsLedger,
)
from apps.personalization.models import UserProfile

User = get_user_model()


def make_user(email="u@e.com", religious_values=""):
    user = User.objects.create_user(email=email, password="pw", full_name="Sam")
    if religious_values:
        UserProfile.objects.create(user=user, religious_values=religious_values)
    return user


def seed_content():
    """Reset to a minimal, controlled catalog for tests (the seed migration
    ships its own content; we replace it so assertions are deterministic)."""
    FaithPractice.objects.all().delete()
    DailyReading.objects.all().delete()
    FaithPractice.objects.create(key="morning-prayer", label="Morning prayer", tradition="", order=1)
    FaithPractice.objects.create(key="scripture", label="Read the passage", tradition="", order=2)
    # A Christian-only practice, to prove the tradition filter.
    FaithPractice.objects.create(key="rosary", label="Pray the rosary", tradition="christian", order=3)
    DailyReading.objects.create(
        tradition="universal", title="Begin with gratitude", body="…",
        reflection_prompt="What are you grateful for?", order=1,
    )
    DailyReading.objects.create(
        tradition="christian", title="Dwelling together",
        reference="Psalm 133:1", body="…",
        reflection_prompt="What keeps you in unity?", order=1,
    )


class TraditionResolutionTests(APITestCase):
    def test_defaults_to_universal_without_profile(self):
        user = make_user()
        self.assertEqual(services.resolve_tradition(user), "universal")

    def test_infers_christian_from_free_text(self):
        user = make_user(religious_values="Practising Catholic")
        self.assertEqual(services.resolve_tradition(user), "christian")

    def test_infers_islamic(self):
        user = make_user(email="m@e.com", religious_values="Muslim")
        self.assertEqual(services.resolve_tradition(user), "islamic")

    def test_spiritual_but_not_religious_is_universal(self):
        user = make_user(religious_values="spiritual, not religious")
        self.assertEqual(services.resolve_tradition(user), "universal")


class TodaysReadingTests(APITestCase):
    def setUp(self):
        seed_content()

    def test_christian_user_gets_christian_reading(self):
        user = make_user(religious_values="Christian")
        self.assertEqual(services.todays_reading(user).tradition, "christian")

    def test_falls_back_to_universal_when_tradition_empty(self):
        # Buddhist has no seeded reading -> universal fallback.
        user = make_user(religious_values="Buddhist")
        self.assertEqual(services.todays_reading(user).tradition, "universal")

    def test_deterministic_same_reading_within_a_day(self):
        user = make_user(religious_values="Christian")
        self.assertEqual(services.todays_reading(user).id, services.todays_reading(user).id)


class FaithTodayEndpointTests(APITestCase):
    def setUp(self):
        seed_content()
        self.user = make_user(religious_values="Catholic")
        self.client.force_authenticate(self.user)

    def test_today_returns_reading_and_practices(self):
        r = self.client.get("/api/v1/engagement/faith/today")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["tradition"], "christian")
        self.assertIsNotNone(r.data["reading"])
        keys = {p["key"] for p in r.data["practices"]}
        # universal practices + the christian-only one, not other traditions'.
        self.assertIn("morning-prayer", keys)
        self.assertIn("rosary", keys)
        self.assertFalse(any(p["completed"] for p in r.data["practices"]))
        self.assertFalse(r.data["reflected"])

    def test_universal_user_does_not_see_christian_practice(self):
        other = make_user(email="n@e.com")  # no profile -> universal
        self.client.force_authenticate(other)
        r = self.client.get("/api/v1/engagement/faith/today")
        keys = {p["key"] for p in r.data["practices"]}
        self.assertIn("morning-prayer", keys)
        self.assertNotIn("rosary", keys)


class CompletePracticeTests(APITestCase):
    def setUp(self):
        seed_content()
        self.user = make_user()
        self.client.force_authenticate(self.user)

    def test_completing_awards_points_and_streak(self):
        r = self.client.post(
            "/api/v1/engagement/faith/practices/complete", {"practice_key": "morning-prayer"}
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["points_awarded"], services.POINTS["faith_practice"])
        self.assertEqual(FaithPracticeLog.objects.filter(user=self.user).count(), 1)
        self.assertEqual(services.points_balance(self.user), services.POINTS["faith_practice"])

    def test_completing_twice_is_idempotent_no_double_points(self):
        self.client.post(
            "/api/v1/engagement/faith/practices/complete", {"practice_key": "morning-prayer"}
        )
        r = self.client.post(
            "/api/v1/engagement/faith/practices/complete", {"practice_key": "morning-prayer"}
        )
        self.assertEqual(r.data["points_awarded"], 0)
        self.assertEqual(PointsLedger.objects.filter(user=self.user).count(), 1)

    def test_unknown_practice_is_404(self):
        r = self.client.post(
            "/api/v1/engagement/faith/practices/complete", {"practice_key": "nope"}
        )
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_missing_key_is_400(self):
        r = self.client.post("/api/v1/engagement/faith/practices/complete", {})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_cannot_complete_another_traditions_practice(self):
        # Universal user should not be able to check off a christian-only one.
        r = self.client.post(
            "/api/v1/engagement/faith/practices/complete", {"practice_key": "rosary"}
        )
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)


class ReflectTests(APITestCase):
    def setUp(self):
        seed_content()
        self.user = make_user()
        self.client.force_authenticate(self.user)

    def test_reflection_is_saved_encrypted_and_awards_points(self):
        r = self.client.post(
            "/api/v1/engagement/faith/reflect", {"text": "I felt a lot of peace today."}
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["points_awarded"], services.POINTS["faith_reflection"])
        reflection = FaithReflection.objects.get(user=self.user)
        # Stored ciphertext, readable back via the property.
        self.assertTrue(reflection.text.startswith("ENC:"))
        self.assertEqual(reflection.decrypted_text, "I felt a lot of peace today.")

    def test_second_reflection_same_day_no_double_points(self):
        self.client.post("/api/v1/engagement/faith/reflect", {"text": "first"})
        r = self.client.post("/api/v1/engagement/faith/reflect", {"text": "second"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["points_awarded"], 0)
        self.assertEqual(FaithReflection.objects.filter(user=self.user).count(), 1)

    def test_empty_text_is_rejected(self):
        r = self.client.post("/api/v1/engagement/faith/reflect", {"text": ""})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reflection_links_todays_reading(self):
        self.client.post("/api/v1/engagement/faith/reflect", {"text": "grateful"})
        reflection = FaithReflection.objects.get(user=self.user)
        self.assertEqual(reflection.reading_id, services.todays_reading(self.user).id)


class FaithAuthTests(APITestCase):
    def test_all_routes_require_auth(self):
        for method, path in [
            ("get", "/api/v1/engagement/faith/today"),
            ("post", "/api/v1/engagement/faith/practices/complete"),
            ("post", "/api/v1/engagement/faith/reflect"),
        ]:
            resp = getattr(self.client, method)(path)
            self.assertIn(
                resp.status_code,
                (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
            )
