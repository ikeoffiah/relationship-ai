import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.relationships.models import Relationship
from apps.sessions.joint_session import JointSessionState

class JointSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    relationship = models.ForeignKey(Relationship, on_delete=models.CASCADE, related_name="joint_sessions")
    initiator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="initiated_joint_sessions")
    
    state = models.CharField(
        max_length=20, 
        choices=[(s.value, s.name) for s in JointSessionState], 
        default=JointSessionState.PENDING_A.value
    )
    
    partner_a_confirmed = models.BooleanField(default=False)
    partner_b_confirmed = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        db_table = "joint_sessions"

    def __str__(self):
        return f"Joint Session {self.id} ({self.state})"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at and self.state in [JointSessionState.PENDING_A.value, JointSessionState.PENDING_B.value]

class LangGraphSession(models.Model):
    """
    Persists LangGraph SessionState to DB after every node transition.
    State is stored as an encrypted JSONB column (encryption logic applied before save/at DB layer).
    Enables agent resumption if connection drops.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="langgraph_sessions")
    relationship = models.ForeignKey(Relationship, on_delete=models.CASCADE, null=True, blank=True, related_name="langgraph_sessions")
    session_type = models.CharField(
        max_length=20, 
        choices=[('individual', 'individual'), ('joint', 'joint'), ('async_relay', 'async_relay')]
    )
    
    state_payload = models.JSONField(default=dict) # Encrypted JSONB in production

    # Denormalised fields for the session-history list, kept current by the
    # FastAPI chat endpoint as turns happen, so the list view never has to
    # decrypt or parse state_payload. summary_preview holds a short plaintext
    # excerpt of the latest assistant turn (encrypt at the DB layer in prod,
    # as with the rest of this table).
    turn_count = models.PositiveIntegerField(default=0)
    summary_preview = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "langgraph_sessions"
        indexes = [
            models.Index(fields=["user", "-created_at"], name="idx_lgsession_user_created"),
        ]

    def __str__(self):
        return f"LangGraph Session {self.id} ({self.session_type})"


class SessionFeedback(models.Model):
    """Post-session feedback collected from users (1–5 star rating + optional text)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session_id = models.CharField(max_length=64, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='session_feedbacks'
    )
    rating = models.PositiveSmallIntegerField()  # 1–5
    # Encrypted in production at the DB layer
    feedback_text = models.TextField(blank=True, max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'session_feedback'
        ordering = ['-created_at']

    def __str__(self):
        return f"Feedback {self.rating}★ for session {self.session_id}"
