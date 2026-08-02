"""The only way to read an insight.

An insight is derived from what each partner said to Bliss alone. That makes
this the narrowest and most consequential read path in the product: everything
else crossing between partners goes through ``personalization/boundary.py`` as
a tone instruction, and this is the one place where the *content* of a private
session could reach the other person.

See ``docs/relationship-insights.md``. Nothing is built yet — the model has
never held a row — so this is deliberately restrictive rather than
accommodating. It is easier to open a door later than to find one was ajar.
"""

from django.db import models


class InsightQuerySet(models.QuerySet):
    """Consent-aware reads. There is no unfiltered accessor, on purpose."""

    def public(self, user):
        """Insights this user has consented to see about themselves.

        The flag means "this partner agreed their own side could be named",
        not "an administrator enabled it". Nothing is visible by default, and
        nothing becomes visible to one partner on the strength of the other's
        consent.
        """
        return self.filter(
            models.Q(relationship__partner_a=user, shared_with_a=True)
            | models.Q(relationship__partner_b=user, shared_with_b=True)
        )


class InsightManager(models.Manager):
    """Attached to the model, which it was not before.

    ``RelationshipInsight.objects.public(user)`` raised ``AttributeError``:
    this manager was written and never wired up. An unattached consent filter
    is worse than no filter at all, because the next person to read the file
    assumes something is enforcing it.
    """

    def get_queryset(self):
        return InsightQuerySet(self.model, using=self._db)

    def public(self, user):
        return self.get_queryset().public(user)

    # ── `for_joint_prompt()` was here, and is deliberately gone ──────────
    #
    # It returned everything with ``approved_for_joint=True`` and explained
    # that "no per-user consent check is required because the joint session is
    # a shared context".
    #
    # That conflates the *session* being shared with the *evidence* being
    # shared. It would take an insight derived from one partner's private solo
    # session and place it in a prompt both of them see, with no check, by
    # design — which is the exact thing ``boundary.py`` exists to prevent, and
    # the reason that module says an inferred model of one partner surfaced to
    # the other is a manipulation manual.
    #
    # Removed rather than corrected, because the correction is a consent flow
    # that does not exist: ``approved_for_joint`` should be *derived* from both
    # partners having approved their own half and neither having withdrawn,
    # never a boolean somebody sets. Whoever builds that adds the reader back
    # beside it. Until then there is nothing to read, and an accessor that
    # would leak the day it were called is not worth keeping warm.
