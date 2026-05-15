CONSENT_PLAIN_LANGUAGE_MAP = {
    'session_transcript_retention': {
        'per_session': 'Your session conversations are deleted when the session ends.',
        '30_days':     'Your session conversations are kept for 30 days, then deleted.',
        '1_year':      'Your session conversations are kept for 1 year, then deleted.',
        'indefinite':  'Your session conversations are kept until you delete them.',
    },
    'cross_partner_insight_sharing': {
        'never':      'Nothing from your sessions is shared with your partner.',
        'anonymized': 'General themes (no personal details) may be shared with your partner.',
        'named':      'Specific insights about relationship patterns may be shared with your partner.',
    },
    'joint_session_participation': {
        'not_enrolled': 'You are not enrolled in joint sessions with your partner.',
        'enrolled':     'You are enrolled and ready to participate in joint sessions.',
    },
    'shared_relationship_context': {
        'not_participating': 'You are not contributing to a shared relationship space.',
        'read_only':         'You can read shared pattern insights but not contribute new data.',
        'read_write':        'You can read and contribute to shared relationship pattern insights.',
    },
    'therapist_summary_access': {
        True:  'Your therapist can see anonymized summaries of your patterns.',
        False: 'Your therapist cannot see any summaries of your sessions.',
    },
    'model_improvement_data': {
        True:  'Your data is used anonymously to improve the AI therapeutic models.',
        False: 'Your data is not used to improve the AI.',
    },
}
