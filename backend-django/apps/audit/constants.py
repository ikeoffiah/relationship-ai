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

    # Memory
    MEMORY_CREATED = "memory_created"
    MEMORY_DELETED = "memory_deleted"

    # Auth
    LOGIN = "login"
    LOGOUT = "logout"
    FAILED_AUTH = "failed_auth"

    # GDPR
    GDPR_EXPORT_REQUESTED = "gdpr_export_requested"
