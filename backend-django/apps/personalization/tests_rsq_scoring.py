"""The RSQ scorer: the published key, and refusing to guess.

Two defects are pinned here. See ``docs/engineering/rsq-scoring.md`` for why
the rest of the instrument is fine and my earlier, broader claim about it was
wrong.
"""

from django.test import TestCase

from apps.personalization.tasks import (
    MIN_ITEMS_TO_SCORE,
    calculate_rsq_attachment_style as score,
)


def answers(overrides=None):
    """All 30 items neutral, then whatever the test cares about.

    Takes a dict rather than kwargs because the item numbers are integers and
    Python keyword arguments must be strings.
    """
    base = {str(i): 3 for i in range(1, 31)}
    base.update({str(k): v for k, v in (overrides or {}).items()})
    return base


class RefusingToGuess(TestCase):
    def test_a_blank_submission_is_not_secure(self):
        """The bug this exists for.

        Every prototype landed on 3.0 and `max()` returned the first key, so
        anyone who skipped was labelled securely attached. Invisible while the
        questionnaire was mandatory; a live mislabelling the moment the
        onboarding gate is removed.
        """
        style, scores = score({})
        self.assertIsNone(style)
        self.assertEqual(set(scores), {
            'secure', 'dismissive-avoidant', 'anxious-preoccupied',
            'fearful-avoidant',
        })

    def test_a_tie_at_the_top_is_not_a_finding(self):
        style, _ = score(answers())
        self.assertIsNone(style)

    def test_too_few_items_declines_even_when_they_differ(self):
        sparse = {'1': 5, '5': 5, '12': 5}
        self.assertLess(len(sparse), MIN_ITEMS_TO_SCORE)
        style, _ = score(sparse)
        self.assertIsNone(style)

    def test_none_rather_than_the_string_unknown(self):
        """Every consumer guards on falsiness — `(x or "")` in portrait.py and
        engagement/services.py, `if getattr(...)` in chat/assist.py. None does
        the right thing in all three; "unknown" is truthy and would reach a
        prompt as `attachment style: unknown`."""
        style, _ = score({})
        self.assertIsNone(style)
        self.assertFalse(bool(style))


class ThePublishedKey(TestCase):
    def test_dismissing_reads_item_26_not_28(self):
        """The transcription slip. Item 26 ("I prefer not to depend on others")
        is a canonical dismissing item; 28 ("I worry about having others not
        accept me") is self-model anxiety and was duplicated from the secure
        line above, reverse-keying and all."""
        high_26 = score(answers({26: 5}))[1]['dismissive-avoidant']
        low_26 = score(answers({26: 1}))[1]['dismissive-avoidant']
        self.assertGreater(high_26, low_26)

    def test_item_28_no_longer_moves_dismissing(self):
        a = score(answers({28: 1}))[1]['dismissive-avoidant']
        b = score(answers({28: 5}))[1]['dismissive-avoidant']
        self.assertEqual(a, b)

    def test_item_28_still_moves_secure_and_is_reverse_keyed(self):
        worried = score(answers({28: 5}))[1]['secure']
        untroubled = score(answers({28: 1}))[1]['secure']
        self.assertGreater(untroubled, worried)

    def test_secure_and_dismissing_can_now_be_separated(self):
        """Before the fix the shared `(6 - r[28])` term cancelled between these
        two, so the scorer could not tell apart the prototypes that most need
        telling apart — one is comfortable with closeness, the other
        comfortable without it."""
        secure_ish = score(answers({3: 5, 10: 5, 15: 5, 9: 1, 28: 1}))
        self.assertEqual(secure_ish[0], 'secure')

        dismissing_ish = score(answers({2: 5, 6: 5, 19: 5, 22: 5, 26: 5}))
        self.assertEqual(dismissing_ish[0], 'dismissive-avoidant')

    def test_the_other_two_prototypes_still_resolve(self):
        self.assertEqual(
            score(answers({8: 5, 16: 5, 25: 5, 6: 1}))[0],
            'anxious-preoccupied',
        )
        self.assertEqual(
            score(answers({1: 5, 5: 5, 12: 5, 24: 5}))[0],
            'fearful-avoidant',
        )

    def test_all_four_are_means_and_so_comparable(self):
        _, scores = score(answers())
        self.assertTrue(all(1.0 <= v <= 5.0 for v in scores.values()))


class StoredBlobsStillWork(TestCase):
    def test_a_full_thirty_item_blob_scores(self):
        """Existing blobs all contain 30 items, because the hard gate forced
        completion. No migration is needed for any of this."""
        style, _ = score(answers({2: 5, 6: 5, 19: 5, 22: 5, 26: 5}))
        self.assertIsNotNone(style)

    def test_unknown_keys_are_ignored(self):
        """Blobs written before the item cut keep keys the scorer no longer
        reads. They must not break it."""
        blob = answers({2: 5, 6: 5, 19: 5, 22: 5, 26: 5})
        blob.update({'99': 4, 'notanumber': 2})
        style, _ = score(blob)
        self.assertEqual(style, 'dismissive-avoidant')
