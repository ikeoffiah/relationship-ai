import logging
import os

from django.apps import AppConfig

log = logging.getLogger(__name__)


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"

    def ready(self):
        import apps.accounts.signals  # noqa: F401

        self._announce_signing_key()

    def _announce_signing_key(self) -> None:
        """Log which key this process signs JWTs with.

        The FastAPI service logs the same fingerprint for the key it *verifies*
        with. Two different values in the two startup logs is the entire
        diagnosis for a failure that is otherwise silent — a mismatch makes
        every FastAPI WebSocket reject every token as a bare HTTP 403, which is
        indistinguishable from a permissions bug and sends you looking in the
        wrong place.

        Skipped under the test runner, where it is noise on every process
        start. Never raises: a missing log line is not worth a service that
        will not boot.
        """
        if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("DJANGO_SKIP_KEY_LOG"):
            return
        try:
            from apps.accounts.auth import key_fingerprint

            fingerprint = key_fingerprint()
            if fingerprint == "unset":
                log.error("jwt_signing_key_unset: SECRET_KEY is empty")
            else:
                log.info("jwt_signing_key fingerprint=%s", fingerprint)
        except Exception:  # pragma: no cover - diagnostics must not break boot
            log.warning("jwt_signing_key_fingerprint_failed", exc_info=True)
