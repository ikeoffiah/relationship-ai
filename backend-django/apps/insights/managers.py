from django.db import models
from .models import RelationshipInsight

class InsightQuerySet(models.QuerySet):
    """Custom queryset for RelationshipInsight providing consent‑aware filters.

    * ``public(user)`` – returns insights visible to the given user based on the
      ``shared_with_a`` / ``shared_with_b`` flags.
    * ``for_joint_prompt()`` – returns insights approved for inclusion in a joint
      session prompt (``approved_for_joint=True``) regardless of user consent because the
      joint session will be presented to both partners.
    """

    def public(self, user):
        """Filter insights that the *user* is allowed to see.

        The user can be either partner A or partner B in the relationship.  The
        appropriate ``shared_*`` flag must be ``True``.
        """
        return self.filter(
            models.Q(relationship__partner_a=user, shared_with_a=True)
            | models.Q(relationship__partner_b=user, shared_with_b=True)
        )

    def for_joint_prompt(self):
        """Return insights approved for joint session prompts.

        These insights are included in the LLM prompt when both partners
        participate in a joint session.  No per‑user consent check is required
        because the joint session is a shared context.
        """
        return self.filter(approved_for_joint=True)


class InsightManager(models.Manager):
    """Expose the custom queryset via ``objects``.

    Usage examples:
        RelationshipInsight.objects.public(request.user)
        RelationshipInsight.objects.for_joint_prompt()
    """

    def get_queryset(self):
        return InsightQuerySet(self.model, using=self._db)

    def public(self, user):
        return self.get_queryset().public(user)

    def for_joint_prompt(self):
        return self.get_queryset().for_joint_prompt()
