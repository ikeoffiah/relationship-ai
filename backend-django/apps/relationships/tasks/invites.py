"""Sending the partner invite, off the request path.

It used to be sent inline from `RelationshipInviteView.post`, with no
`EMAIL_TIMEOUT`, so `smtplib` was constructed with `timeout=None`. Production
runs two synchronous gunicorn workers, which means two invites to a slow or
unreachable SMTP host were the entire Django API — measured at 40 concurrent
invites producing 40 failures and 0 successes.

The `try/except` around the old call did not help. It caught the *error*, not
the *wait*; a socket that never answers never raises.
"""

from __future__ import annotations

import logging

from celery import shared_task
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


@shared_task(
    name="relationships.send_invite_email",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def send_invite_email(invitee_email: str, invite_url: str) -> None:
    """Deliver one invite. Retried with backoff; never touches a web worker.

    Takes the already-built URL rather than the raw token, so the token is not
    re-derived here and nothing about it is logged on the retry path.
    """
    send_mail(
        subject="Connect on Bliss",
        message=(
            "Your partner has invited you to link accounts on Bliss. "
            f"Click here to accept: {invite_url}"
        ),
        from_email=None,
        recipient_list=[invitee_email],
    )
    logger.info("invite_email_sent")
