import hashlib
from django.core.management.base import BaseCommand
from apps.audit.models import AuditEvent


class Command(BaseCommand):
    help = "Replays all audit events and verifies hash chain integrity"

    def handle(self, *args, **options):
        # Ordered by created_at to verify the chain chronologically
        # We group by event_type because the chain is per event_type in the logger
        event_types = AuditEvent.objects.values_list("event_type", flat=True).distinct()

        total_errors = 0
        total_verified = 0

        for etype in event_types:
            events = AuditEvent.objects.filter(event_type=etype).order_by("created_at")
            prev_hash = "genesis"

            for event in events:
                # Reconstruct expected hash
                timestamp_str = event.created_at.isoformat()
                # If the timestamp in DB was stored as offset-naive vs aware, we might need careful formatting
                # But since logger uses isoformat() which includes UTC offset, we should be fine.

                expected = hashlib.sha256(
                    f"{event.prev_hash}{event.id}{timestamp_str}".encode()
                ).hexdigest()

                if event.hash != expected:
                    self.stderr.write(
                        self.style.ERROR(
                            f"Chain broken at event {event.id} (type: {etype})"
                        )
                    )
                    self.stderr.write(f"  Got:      {event.hash}")
                    self.stderr.write(f"  Expected: {expected}")
                    total_errors += 1

                if event.prev_hash != prev_hash:
                    self.stderr.write(
                        self.style.ERROR(
                            f"Chain sequence mismatch at event {event.id} (type: {etype})"
                        )
                    )
                    self.stderr.write(f"  Event prev_hash: {event.prev_hash}")
                    self.stderr.write(f"  Actual previous: {prev_hash}")
                    total_errors += 1

                prev_hash = event.hash
                total_verified += 1

        if total_errors:
            self.stderr.write(
                self.style.ERROR(
                    f"AUDIT CHAIN INTEGRITY FAILURE: {total_errors} errors detected"
                )
            )
            exit(1)
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Audit chain verified: {total_verified} events, no tampering detected"
                )
            )
