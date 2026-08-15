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
from django.core.mail import EmailMultiAlternatives

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

    `invite_url` is now an https link to the invite landing page, not a
    `bliss://` deep link. Mail clients only linkify http(s) — a custom scheme
    rendered as unclickable plain text, which is what the first recipients got.
    The landing page carries the button that opens the app.
    """
    text = (
        "Your partner has invited you to link accounts on Bliss.\n\n"
        f"Open this link on the phone where Bliss is installed:\n{invite_url}\n\n"
        "This invite expires in 72 hours and can only be used once.\n"
    )
    html = f"""\
<div style="background:#FFF6ED;padding:32px 16px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <div style="max-width:440px;margin:0 auto;background:#FFFDF9;border-radius:20px;padding:32px 28px;">
    <p style="font-size:32px;letter-spacing:-6px;margin:0 0 8px;">&#9711;&#9711;</p>
    <h1 style="font-size:22px;color:#3B2A24;margin:0 0 14px;">Your partner invited you to Bliss</h1>
    <p style="font-size:16px;line-height:1.55;color:#4A4A4A;margin:0 0 8px;">
      Bliss is a private space for two people to understand each other a little
      better. Tap below to link your accounts.
    </p>
    <a href="{invite_url}"
       style="display:block;background:#FF9B8A;color:#3B2A24;text-decoration:none;
              font-weight:600;font-size:17px;padding:16px 20px;border-radius:14px;
              text-align:center;margin:26px 0 14px;">Accept the invite</a>
    <p style="font-size:14px;line-height:1.5;color:#7a7a7a;margin:18px 0 0;">
      You will need the Bliss app installed on your phone first. This invite
      expires in 72 hours and can only be used once.
    </p>
    <p style="font-size:13px;color:#9a9a9a;margin:16px 0 0;word-break:break-all;">
      If the button does not work, paste this into your browser:<br>{invite_url}
    </p>
  </div>
</div>"""

    message = EmailMultiAlternatives(
        subject="Your partner invited you to Bliss",
        body=text,
        from_email=None,
        to=[invitee_email],
    )
    message.attach_alternative(html, "text/html")
    message.send()
    logger.info("invite_email_sent")
