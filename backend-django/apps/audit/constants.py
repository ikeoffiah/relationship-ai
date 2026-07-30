class AuditEventType:
    # Session
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    TURN_COMPLETED = "turn_completed"

    # Consent
    CONSENT_CHANGE = "consent_change"
    ERASURE_REQUEST = "erasure_request"
    ERASURE_COMPLETE = "erasure_complete"

    # Safety
    SAFETY_TRIGGERED = "safety_triggered"
    ESCALATION_REQUESTED = "escalation_requested"
    CRISIS_RESOURCES_SHOWN = "crisis_resources_shown"

    # Cross-partner access
    CROSS_PARTNER_ACCESS = "cross_partner_access"

    # Relationship lifecycle
    RELATIONSHIP_CREATED = "relationship_created"

    # Memory
    MEMORY_CREATED = "memory_created"
    MEMORY_DELETED = "memory_deleted"

    # Auth
    LOGIN = "login"
    LOGOUT = "logout"
    FAILED_AUTH = "failed_auth"

    # GDPR
    GDPR_EXPORT_REQUESTED = "gdpr_export_requested"

    # Credentials
    PASSWORD_CHANGED = "password_changed"

    # Chat media. Uploads and destructions are logged; reads deliberately are
    # not — a partner opening a photo in their own thread dozens of times is
    # not an event, and logging it would build a record of when each of them
    # looks at what, which is a more intimate thing than the photo.
    MEDIA_UPLOADED = "media_uploaded"
    MEDIA_ERASED = "media_erased"
