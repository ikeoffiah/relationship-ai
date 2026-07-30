"""Verifying the address on an account, and changing it while you still can.

The order matters and is the whole design: **verify first, change only until
verified.**

An email address is not just a login here. It is what a partner invitation is
sent to, so an unverified address means an invitation can be delivered to
somebody who never signed up — and it is the identifier the other person
recognises you by. Letting it move after verification would quietly turn a
verified account into an unverified one with nothing on screen looking
different, which is worse than never having verified it.

So: while unverified, the address is freely changeable, because the likeliest
reason someone cannot verify is that they typed it wrong. Once verified, it is
fixed, and a genuine change becomes a support conversation rather than a form —
which is the correct amount of friction for changing the thing that identifies
you to your partner.

Mail goes out through Django's configured backend, which is Resend over SMTP
(see config/settings.py). Nothing here knows that, which is the point: the
provider is a deployment detail.
"""

import logging
import secrets

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import EmailVerification

log = logging.getLogger(__name__)

CODE_LENGTH = 6


def _new_code() -> str:
    """A six-digit code from a cryptographic source.

    secrets, not random: this is a credential, however short-lived, and
    random's Mersenne Twister is predictable from previous outputs.
    """
    return "".join(secrets.choice("0123456789") for _ in range(CODE_LENGTH))


def _send_code(email: str, code: str) -> bool:
    """Deliver the code. Returns whether it was handed to the mail backend."""
    try:
        send_mail(
            subject="Your Bliss verification code",
            message=(
                f"Your verification code is {code}\n\n"
                "It expires in 15 minutes. If you did not ask to verify this "
                "address, you can ignore this email — nothing has changed on "
                "the account.\n\n"
                "Bliss, from owjar.co"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        return True
    except Exception as exc:
        # Logged, not raised. The caller reports a generic failure: an error
        # that distinguishes "mail provider rejected this address" from
        # "delivered" is an address-validity oracle for anyone with an account.
        log.warning("verification_email_failed: %s", exc)
        return False


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def email_status(request):
    """Where this account's address stands, and what may be done to it.

    `can_change` is computed here rather than left to the client to infer from
    `verified`. The rule is a server rule — the change endpoint enforces it — and
    two independent implementations of the same rule is how a UI ends up
    offering a button the API refuses.
    """
    user = request.user
    latest = user.email_verifications.first()
    cooling_down = (
        latest is not None
        and latest.created_at + EmailVerification.RESEND_COOLDOWN > timezone.now()
    )

    return Response(
        {
            "email": user.email,
            "verified": user.email_verified,
            "verified_at": user.email_verified_at.isoformat()
            if user.email_verified_at
            else None,
            "can_change": not user.email_verified,
            "code_sent": latest is not None and latest.is_usable,
            "resend_available_in": max(
                0,
                int(
                    (
                        latest.created_at
                        + EmailVerification.RESEND_COOLDOWN
                        - timezone.now()
                    ).total_seconds()
                ),
            )
            if cooling_down
            else 0,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def send_verification(request):
    """Send a fresh code to the address on the account."""
    user = request.user
    if user.email_verified:
        return Response(
            {"message": "This address is already verified.", "code": "already_verified"},
            status=status.HTTP_409_CONFLICT,
        )

    latest = user.email_verifications.first()
    if (
        latest is not None
        and latest.created_at + EmailVerification.RESEND_COOLDOWN > timezone.now()
    ):
        wait = int(
            (
                latest.created_at + EmailVerification.RESEND_COOLDOWN - timezone.now()
            ).total_seconds()
        )
        return Response(
            {
                "message": f"Please wait {wait} seconds before asking again.",
                "code": "cooldown",
                "resend_available_in": wait,
            },
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    code = _new_code()
    with transaction.atomic():
        # Supersede any outstanding code. Two live codes for one address means
        # an older one keeps working after the user has asked for a new one,
        # which doubles the window for no benefit.
        user.email_verifications.filter(used_at__isnull=True).update(
            used_at=timezone.now()
        )
        EmailVerification.objects.create(
            user=user,
            email=user.email,
            code_hash=EmailVerification.hash_code(code),
            expires_at=timezone.now() + EmailVerification.TTL,
        )

    delivered = _send_code(user.email, code)
    return Response(
        {
            "sent": delivered,
            "message": "Check your inbox for a six-digit code."
            if delivered
            else "We could not send that just now. Try again shortly.",
        },
        status=status.HTTP_200_OK if delivered else status.HTTP_502_BAD_GATEWAY,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def confirm_verification(request):
    """Check a code and, if it matches, mark the address verified."""
    user = request.user
    if user.email_verified:
        return Response({"verified": True}, status=status.HTTP_200_OK)

    submitted = str(request.data.get("code", "")).strip()
    if not submitted:
        return Response(
            {"message": "Enter the code from your email.", "code": "code_required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    record = user.email_verifications.filter(used_at__isnull=True).first()
    if record is None or not record.is_usable:
        return Response(
            {
                "message": "That code has expired. Ask for a new one.",
                "code": "code_expired",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # A code issued to a different address must not verify the current one —
    # someone can change their address while a code is outstanding.
    if record.email.lower() != user.email.lower():
        record.used_at = timezone.now()
        record.save(update_fields=["used_at"])
        return Response(
            {
                "message": "That code was sent to a different address. Ask for a new one.",
                "code": "code_stale",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not secrets.compare_digest(
        record.code_hash, EmailVerification.hash_code(submitted)
    ):
        # Count the attempt before answering, so a wrong guess costs something
        # even if the response is discarded.
        record.attempts += 1
        record.save(update_fields=["attempts"])
        remaining = EmailVerification.MAX_ATTEMPTS - record.attempts
        return Response(
            {
                "message": "That code does not match."
                if remaining > 0
                else "Too many attempts. Ask for a new code.",
                "code": "code_mismatch",
                "attempts_remaining": max(0, remaining),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        record.used_at = timezone.now()
        record.save(update_fields=["used_at"])
        user.email_verified = True
        user.email_verified_at = timezone.now()
        user.save(update_fields=["email_verified", "email_verified_at"])

    return Response({"verified": True, "email": user.email})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_email(request):
    """Change the address — only while it is still unverified.

    Refused afterwards, deliberately. See the module docstring: this address is
    what a partner invitation was sent to and what the other person recognises,
    so moving it after verification is not a settings change.
    """
    user = request.user
    if user.email_verified:
        return Response(
            {
                "message": "Your email is verified, so it cannot be changed here. "
                "Contact support@owjar.co if you need to move it.",
                "code": "email_locked",
            },
            status=status.HTTP_409_CONFLICT,
        )

    new_email = str(request.data.get("email", "")).strip().lower()
    if not new_email or "@" not in new_email:
        return Response(
            {"message": "Enter a valid email address.", "code": "invalid_email"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if new_email == user.email.lower():
        return Response({"email": user.email, "changed": False})

    User = type(user)
    if User.objects.filter(email__iexact=new_email).exclude(pk=user.pk).exists():
        # Same wording whether or not the address is taken. A distinct "already
        # registered" reply lets anyone with an account enumerate who else has
        # one.
        return Response(
            {
                "message": "That address cannot be used. Try another.",
                "code": "email_unavailable",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        user.email = new_email
        user.save(update_fields=["email"])
        # Any outstanding code went to the old address.
        user.email_verifications.filter(used_at__isnull=True).update(
            used_at=timezone.now()
        )

    return Response({"email": user.email, "changed": True, "verified": False})


# ── Changing a password from inside the app ─────────────────────────────────


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password(request):
    """Change a password by proving you know the current one.

    Settings used to fire off a reset email and show a toast saying one had been
    sent, which is the wrong flow for somebody who is already signed in: it
    sends them out of the app to their inbox to do something they were holding
    the credential for anyway, and it means anyone with an unlocked phone can
    trigger mail to the owner's address.

    Requiring the current password is the substance here, not a formality. A
    signed-in session only proves someone has the phone; the current password is
    what proves they are the account holder. That distinction is the entire
    reason this cannot just take a new password.

    Every other session is signed out on success. A password change is what
    someone does when they think another person has access, and leaving that
    person's refresh token alive would make the change cosmetic.
    """
    from django.contrib.auth import authenticate
    from django.contrib.auth.password_validation import validate_password
    from django.core.exceptions import ValidationError

    from apps.accounts.models import RefreshToken
    from apps.audit.constants import AuditEventType
    from apps.audit.logger import AuditLogger

    user = request.user
    current = str(request.data.get("current_password", ""))
    new = str(request.data.get("new_password", ""))

    if not current or not new:
        return Response(
            {
                "message": "Enter your current password and a new one.",
                "code": "fields_required",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if authenticate(username=user.email, password=current) is None:
        AuditLogger.get_instance().log(
            AuditEventType.FAILED_AUTH,
            user_id=user.id,
            metadata={"reason": "change_password_wrong_current"},
        )
        return Response(
            {
                "message": "That is not your current password.",
                "code": "current_password_incorrect",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if new == current:
        return Response(
            {
                "message": "Your new password needs to be different.",
                "code": "password_unchanged",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Django's configured validators — length, commonness, similarity to the
        # user's own details. Reusing them rather than inventing a rule here
        # keeps this consistent with signup and with the reset flow.
        validate_password(new, user=user)
    except ValidationError as exc:
        return Response(
            {"message": " ".join(exc.messages), "code": "password_rejected"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        user.set_password(new)
        user.save(update_fields=["password"])
        # Sign every other session out. Marking them used is what the refresh
        # flow already treats as spent, so no new state is needed.
        RefreshToken.objects.filter(user=user, used_at__isnull=True).update(
            used_at=timezone.now()
        )

    AuditLogger.get_instance().log(
        AuditEventType.PASSWORD_CHANGED,
        user_id=user.id,
        metadata={"event": "password_changed", "sessions_revoked": True},
    )

    return Response(
        {
            "changed": True,
            "message": "Password changed. Other devices have been signed out.",
        }
    )
