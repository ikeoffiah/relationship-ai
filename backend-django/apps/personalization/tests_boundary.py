"""The partner boundary, tested the way an auth boundary is tested.

These are not unit tests of a helper. They are the product promise: nothing the
system infers about one person reaches the other. Everything else in the
personalisation stack is a feature; this is the thing that makes the feature
safe to have.

The interesting tests here are the last group, which walk real endpoints with
a fully populated profile and assert the vocabulary of that profile appears
nowhere in what the partner can read. Those are the ones that will catch the
failure that actually happens — someone adds a field to a serializer without
thinking about who is on the other end of it.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.personalization import behaviour, boundary
from apps.relationships.models import Relationship

User = get_user_model()


def saturate(user) -> None:
    """Give someone every tendency, strongly enough to be reported."""
    for signal in behaviour.SIGNALS:
        for _ in range(behaviour.MIN_OBSERVATIONS + 2):
            behaviour.observe(user, signal)


class GuidanceTests(TestCase):
    def setUp(self):
        self.alex = User.objects.create_user(email="a@test.local", password="pw12345!")

    def test_guidance_is_instructions_not_labels(self):
        saturate(self.alex)

        guidance = boundary.phrasing_guidance_for(self.alex.id)

        self.assertTrue(guidance)
        joined = " ".join(guidance)
        # The words the profile is stored under must not travel with it.
        for signal in behaviour.SIGNALS:
            self.assertNotIn(signal, joined)
        # Nor the clinical vocabulary the whole design avoids.
        for label in ("avoidant", "anxious", "attachment style", "diagnos"):
            self.assertNotIn(label, joined.lower())

    def test_someone_with_no_history_yields_nothing(self):
        self.assertEqual(boundary.phrasing_guidance_for(self.alex.id), [])

    def test_a_single_observation_is_a_coincidence_not_a_pattern(self):
        behaviour.observe(self.alex, behaviour.WITHDRAWS)

        # Acting on one data point is how a wrong label gets attached to
        # someone on the strength of one bad afternoon.
        self.assertEqual(boundary.phrasing_guidance_for(self.alex.id), [])

    def test_self_description_speaks_to_the_person(self):
        saturate(self.alex)

        described = boundary.self_description_for(self.alex.id)

        self.assertTrue(described)
        joined = " ".join(described)
        self.assertIn("you", joined.lower())
        # "Lately" is load-bearing: the scores decay, so a claim about
        # character would be a claim the data does not support.
        self.assertIn("lately", joined.lower())

    def test_self_description_and_guidance_are_different_texts(self):
        saturate(self.alex)

        # Same tendencies, different audiences. If these ever collapse into one
        # string set, one of the two audiences is being addressed wrongly.
        self.assertNotEqual(
            set(boundary.self_description_for(self.alex.id)),
            set(boundary.phrasing_guidance_for(self.alex.id)),
        )


class LeakDetectorTests(TestCase):
    def setUp(self):
        self.alex = User.objects.create_user(email="a@test.local", password="pw12345!")

    def test_a_clean_payload_is_clean(self):
        self.assertEqual(boundary.leaks({"message": "are we still on for tomorrow?"}), [])

    def test_a_signal_name_anywhere_is_caught(self):
        self.assertIn(
            behaviour.WITHDRAWS,
            boundary.leaks({"insight": {"detail": behaviour.WITHDRAWS}}),
        )

    def test_a_signal_name_nested_in_a_list_is_caught(self):
        payload = {"results": [{"tags": ["fine", behaviour.ESCALATES]}]}
        self.assertTrue(boundary.leaks(payload))

    def test_a_copied_self_description_is_caught(self):
        sentence = behaviour.SELF_DESCRIPTION[behaviour.REPAIRS]
        self.assertTrue(boundary.leaks({"note": sentence}))

    def test_it_walks_keys_as_well_as_values(self):
        self.assertTrue(boundary.leaks({behaviour.PURSUES: 3}))

    def test_none_and_scalars_are_handled(self):
        self.assertEqual(boundary.leaks(None), [])
        self.assertEqual(boundary.leaks(42), [])


class EndpointBoundaryTests(TestCase):
    """A saturated profile, and every surface the partner can reach.

    If any of these fail, someone has plumbed a person's profile somewhere it
    can be read by the one person it must never reach.
    """

    def setUp(self):
        self.alex = User.objects.create_user(email="alex@test.local", password="pw12345!")
        self.sam = User.objects.create_user(email="sam@test.local", password="pw12345!")
        self.relationship = Relationship.objects.create(
            partner_a=self.alex, partner_b=self.sam, status="active"
        )
        saturate(self.alex)

        self.client = APIClient()
        # Sam throughout: everything below is read by Alex's *partner*.
        self.client.force_authenticate(user=self.sam)

    def assertNoLeak(self, response):
        found = boundary.leaks(getattr(response, "data", None))
        self.assertEqual(
            found,
            [],
            f"{response.request.get('PATH_INFO')} leaked {found} about the partner",
        )

    def test_the_thread_listing_says_nothing_about_the_partner(self):
        self.assertNoLeak(
            self.client.get(reverse("chat-messages", args=[self.relationship.id]))
        )

    def test_sending_a_message_says_nothing_about_the_partner(self):
        response = self.client.post(
            reverse("chat-send", args=[self.relationship.id]),
            {"body": "are we still on?"},
            format="json",
        )
        self.assertNoLeak(response)

    def test_a_rephrase_returns_a_rewrite_and_nothing_else(self):
        from unittest.mock import patch

        with patch("apps.chat.assist._complete", return_value="a kinder version"):
            response = self.client.post(
                reverse("chat-assist-rephrase", args=[self.relationship.id]),
                {"draft": "you always do this"},
                format="json",
            )

        # The rewrite may be *shaped* by knowing the recipient. It may not
        # describe them.
        self.assertNoLeak(response)

    def test_a_draft_check_returns_a_verdict_and_nothing_else(self):
        from unittest.mock import patch

        with patch(
            "apps.chat.assist._complete", return_value='{"verdict":"ok"}'
        ):
            response = self.client.post(
                reverse("chat-assist-check", args=[self.relationship.id]),
                {"draft": "hello"},
                format="json",
            )
        self.assertNoLeak(response)

    def test_a_nudge_says_nothing_about_the_partner(self):
        from unittest.mock import patch

        with patch("apps.chat.assist.nudge_for", return_value=None):
            self.assertNoLeak(
                self.client.get(
                    reverse("chat-assist-nudge", args=[self.relationship.id])
                )
            )

    def test_assist_settings_are_switches_not_profiles(self):
        self.assertNoLeak(
            self.client.get(
                reverse("chat-assist-settings", args=[self.relationship.id])
            )
        )

    def test_guidance_reaches_the_prompt_but_not_the_response(self):
        """The feature working and the boundary holding, in one test.

        Bliss is told how to phrase something for Alex — that is the whole
        point — and Sam, who asked for the rewrite, is told none of it.
        """
        from unittest.mock import patch

        with patch(
            "apps.chat.assist._complete", return_value="a kinder version"
        ) as complete:
            response = self.client.post(
                reverse("chat-assist-rephrase", args=[self.relationship.id]),
                {"draft": "you never listen"},
                format="json",
            )

        prompt = " ".join(str(arg) for arg in complete.call_args.args)
        guidance = boundary.phrasing_guidance_for(self.alex.id)
        self.assertTrue(guidance, "fixture should have produced guidance")
        self.assertTrue(
            any(g in prompt for g in guidance),
            "the guidance never reached the prompt — the feature is not working",
        )
        self.assertNoLeak(response)
