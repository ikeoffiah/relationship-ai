"""Tests for the relationship portrait (the first-open reveal)."""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.personalization.models import UserProfile
from apps.personalization.portrait import _STYLES, build_portrait

User = get_user_model()


class PortraitBuilderTests(APITestCase):
    def _profile(self, **kwargs):
        user = User.objects.create_user(email=f"{kwargs.get('attachment_style','x')}@e.com", password="pw")
        return UserProfile.objects.create(user=user, **kwargs)

    def test_ready_false_without_attachment_style(self):
        p = self._profile(attachment_style="")
        out = build_portrait(p)
        self.assertFalse(out["ready"])

    def test_portrait_is_specific_to_attachment_style(self):
        p = self._profile(attachment_style="anxious-preoccupied")
        out = build_portrait(p)
        self.assertTrue(out["ready"])
        self.assertEqual(out["archetype"], "The Devoted Connector")
        self.assertEqual(len(out["likely_friction"]), 3)

    def test_beats_the_horoscope_test(self):
        # Every style must yield a distinct headline/summary/archetype — if any
        # two collide, the portrait is generic and worthless.
        headlines, summaries, archetypes = set(), set(), set()
        for style in _STYLES:
            p = self._profile(attachment_style=style)
            out = build_portrait(p)
            headlines.add(out["headline"])
            summaries.add(out["summary"])
            archetypes.add(out["archetype"])
        self.assertEqual(len(headlines), len(_STYLES))
        self.assertEqual(len(summaries), len(_STYLES))
        self.assertEqual(len(archetypes), len(_STYLES))

    def test_communication_note_woven_in(self):
        p = self._profile(attachment_style="secure", communication_style_self_report="avoidant")
        out = build_portrait(p)
        self.assertIn("confrontation", out["communication_note"])

    def test_context_note_reflects_cohabiting_and_kids(self):
        p = self._profile(attachment_style="secure", cohabiting=True, children_count=2)
        out = build_portrait(p)
        self.assertIn("Living together", out["context_note"])
        self.assertIn("kids", out["context_note"])

    def test_context_note_absent_when_no_context(self):
        p = self._profile(attachment_style="secure")
        out = build_portrait(p)
        self.assertIsNone(out["context_note"])


class PortraitEndpointTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="u@e.com", password="pw")
        UserProfile.objects.create(user=self.user, attachment_style="fearful-avoidant")

    def test_endpoint_returns_portrait(self):
        self.client.force_authenticate(self.user)
        r = self.client.get("/api/v1/personalization/portrait")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(r.data["ready"])
        self.assertEqual(r.data["archetype"], "The Guarded Heart")

    def test_endpoint_requires_auth(self):
        r = self.client.get("/api/v1/personalization/portrait")
        self.assertIn(r.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))
