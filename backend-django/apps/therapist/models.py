from django.db import models
from django.conf import settings

class Therapist(models.Model):
    """Therapist profile linked to a User."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="therapist_profile")
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Therapist {self.email}"

class TherapistConnection(models.Model):
    """Bilateral connection between a therapist and a client (regular user)."""
    therapist = models.ForeignKey(Therapist, on_delete=models.CASCADE, related_name="connections")
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="therapist_connections")
    consent_therapist = models.BooleanField(default=False)
    consent_client = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("therapist", "client")

    @property
    def is_active(self) -> bool:
        """
        Whether this connection actually authorises access to client data.

        Both sides must have consented. Anything that exposes client data to a
        therapist must gate on this rather than on the connection's existence
        or on `consent_therapist` alone -- a therapist can create their own
        connection row, so its existence proves nothing about the client's
        wishes.
        """
        return self.consent_therapist and self.consent_client

    def __str__(self):
        return f"Connection {self.therapist.email} ↔ {self.client.email}"

class TherapistStrategyNote(models.Model):
    """Internal notes a therapist can attach to a client."""
    therapist = models.ForeignKey(Therapist, on_delete=models.CASCADE, related_name="strategy_notes")
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="strategy_notes")
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Note by {self.therapist.email} for {self.client.email}"
