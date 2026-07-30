"""Making account deletion true for media.

Deactivating a user is a defensible soft delete for rows in a database we
control: the data is unreachable, and it can be finished off later. It is not
defensible for a photograph sitting in a third party's bucket, because
"unreachable" there means nothing — the bytes are on someone else's disk under
a key we are still holding.

So deletion has to reach the storage vendor, and it has to do so at the moment
the person asks rather than whenever a retention job next runs. This module is
that reach. It is deliberately callable on its own, because erasure requests
arrive by other routes than the in-app button.
"""

import logging

from apps.chat.models import MessageMedia
from apps.relationships.models import Relationship

log = logging.getLogger(__name__)


def relationships_for(user) -> list:
    return list(
        Relationship.objects.filter(partner_a=user) | Relationship.objects.filter(partner_b=user)
    )


def erase_media_for_user(user) -> tuple[int, int]:
    """Destroy every media blob in every thread this user is part of.

    Returns ``(destroyed, failed)``.

    Deleting a couple's thread on one partner's request destroys photographs
    the *other* partner sent, which is worth being deliberate about rather than
    discovering later. The thread is one shared object encrypted under one
    relationship key: there is no version of it that belongs to only one of
    them, and a half-erased thread would leave the requester's own face in the
    other person's app with no way to ask for it back. Erasing the shared
    artefact is the reading that actually honours the request.

    Failures are counted, not raised. A vendor being unavailable must not make
    the account deletion itself fail — the rows are left unreferenced, which is
    what the orphan sweep collects.
    """
    destroyed = failed = 0
    media = MessageMedia.objects.filter(
        relationship__in=relationships_for(user), deleted_at__isnull=True
    )

    for record in media.iterator():
        try:
            record.destroy()
            destroyed += 1
        except Exception:
            log.exception("erasure_media_failed media=%s", record.id)
            failed += 1

    if destroyed or failed:
        log.info("erasure_media user=%s destroyed=%s failed=%s", user.id, destroyed, failed)
        _audit(user, destroyed, failed)
    return destroyed, failed


def _audit(user, destroyed: int, failed: int) -> None:
    """Record what was actually erased, including what was not.

    An erasure log that only ever says "complete" is worth nothing when someone
    later asks whether a specific request was honoured.
    """
    try:
        from apps.audit.constants import AuditEventType
        from apps.audit.logger import AuditLogger

        AuditLogger.get_instance().log(
            AuditEventType.MEDIA_ERASED,
            user_id=user.id,
            metadata={"destroyed": destroyed, "failed": failed},
        )
    except Exception:
        log.exception("erasure_audit_failed user=%s", user.id)
