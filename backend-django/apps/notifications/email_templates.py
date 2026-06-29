"""
Email HTML templates for all 8 transactional emails.
No tracking pixels. Plain Python f-strings — no template service required.
"""


def email_verify(otp: str) -> tuple[str, str]:
    """1. Welcome & Email Verification"""
    subject = "Verify your RelationshipAI account"
    html = f"""
<div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px;">
  <h2 style="color:#2D3748;">Welcome to RelationshipAI</h2>
  <p style="color:#4A5568;">Your email verification code is:</p>
  <h1 style="font-size:48px;letter-spacing:8px;color:#2D3748;text-align:center;
             background:#F7FAFC;padding:16px;border-radius:8px;">{otp}</h1>
  <p style="color:#718096;">This code expires in <strong>10 minutes</strong>.</p>
  <hr style="border:none;border-top:1px solid #E2E8F0;margin:24px 0;">
  <p style="color:#A0AEC0;font-size:12px;">
    <strong>RelationshipAI is an AI-powered support tool, not a licensed therapy service.</strong>
    If you are in crisis, please call or text 988.
  </p>
</div>"""
    return subject, html


def email_partner_invite(accept_url: str, inviter_name: str = "Someone you know") -> tuple[str, str]:
    """2. Partner Invite"""
    subject = f"{inviter_name} invited you to RelationshipAI"
    html = f"""
<div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px;">
  <h2 style="color:#2D3748;">You've been invited to RelationshipAI</h2>
  <p style="color:#4A5568;">{inviter_name} has invited you to try RelationshipAI together.</p>
  <a href="{accept_url}" style="display:inline-block;background:#4F46E5;color:white;
     padding:12px 24px;border-radius:6px;text-decoration:none;margin:16px 0;">
    Accept Invitation
  </a>
  <p style="color:#718096;font-size:13px;"><em>This invitation expires in 72 hours.</em></p>
  <hr style="border:none;border-top:1px solid #E2E8F0;margin:24px 0;">
  <p style="color:#A0AEC0;font-size:12px;">
    RelationshipAI is an AI-powered support tool, not a licensed therapy service.
  </p>
</div>"""
    return subject, html


def email_password_reset(reset_url: str) -> tuple[str, str]:
    """3. Password Reset"""
    subject = "Reset your RelationshipAI password"
    html = f"""
<div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px;">
  <h2 style="color:#2D3748;">Reset your password</h2>
  <p style="color:#4A5568;">Click the link below to reset your password. This link expires in 1 hour.</p>
  <a href="{reset_url}" style="display:inline-block;background:#4F46E5;color:white;
     padding:12px 24px;border-radius:6px;text-decoration:none;margin:16px 0;">
    Reset Password
  </a>
  <p style="color:#A0AEC0;font-size:12px;">If you did not request this, you can safely ignore this email.</p>
</div>"""
    return subject, html


def email_erasure_complete() -> tuple[str, str]:
    """4. Erasure Complete (GDPR Article 17)"""
    subject = "Your data has been deleted — RelationshipAI"
    html = """
<div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px;">
  <h2 style="color:#2D3748;">Your data has been deleted</h2>
  <p style="color:#4A5568;">All your personal data has been permanently removed from RelationshipAI,
  in accordance with your deletion request and GDPR Article 17.</p>
  <p style="color:#4A5568;">This includes: session summaries, stored memories, consent records, and your profile.</p>
  <p style="color:#718096;font-size:13px;">If you have questions, contact us at support@relationshipai.app</p>
</div>"""
    return subject, html


def email_gdpr_export_ready(download_url: str) -> tuple[str, str]:
    """5. GDPR Data Export Ready"""
    subject = "Your data export is ready — RelationshipAI"
    html = f"""
<div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px;">
  <h2 style="color:#2D3748;">Your data export is ready</h2>
  <p style="color:#4A5568;">Your personal data export (GDPR Article 20) is available for download.</p>
  <a href="{download_url}" style="display:inline-block;background:#4F46E5;color:white;
     padding:12px 24px;border-radius:6px;text-decoration:none;margin:16px 0;">
    Download Your Data
  </a>
  <p style="color:#718096;font-size:13px;"><em>This link expires in 48 hours.</em></p>
</div>"""
    return subject, html


def email_relay_waiting(partner_name: str) -> tuple[str, str]:
    """6. Relay Message Waiting"""
    subject = f"{partner_name} sent you a reflection — RelationshipAI"
    html = f"""
<div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px;">
  <h2 style="color:#2D3748;">A message is waiting for you</h2>
  <p style="color:#4A5568;">{partner_name} has sent you a reflection via RelationshipAI's async relay.</p>
  <p style="color:#4A5568;">Open the app to read it at your own pace.</p>
</div>"""
    return subject, html


def email_therapist_connected(therapist_name: str) -> tuple[str, str]:
    """7. Therapist Connected"""
    subject = "A therapist has connected to your account — RelationshipAI"
    html = f"""
<div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px;">
  <h2 style="color:#2D3748;">A therapist has connected</h2>
  <p style="color:#4A5568;"><strong>{therapist_name}</strong> has been connected to your RelationshipAI account
  with your consent.</p>
  <p style="color:#4A5568;">They can view aggregated session summaries only — never raw transcripts.</p>
  <p style="color:#718096;font-size:13px;">
    You can revoke this access at any time from your Consent Dashboard.
  </p>
</div>"""
    return subject, html


def email_safety_followup() -> tuple[str, str]:
    """8. Safety Follow-up"""
    subject = "Checking in — RelationshipAI"
    html = """
<div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px;">
  <h2 style="color:#2D3748;">We're checking in on you</h2>
  <p style="color:#4A5568;">We noticed you may have been going through a difficult time in a recent session.</p>
  <p style="color:#4A5568;">If you need immediate support, please reach out:</p>
  <ul style="color:#4A5568;">
    <li><strong>988 Suicide & Crisis Lifeline</strong>: Call or text <strong>988</strong></li>
    <li><strong>Crisis Text Line</strong>: Text HOME to <strong>741741</strong></li>
    <li><strong>Emergency</strong>: Call <strong>911</strong></li>
  </ul>
  <p style="color:#718096;font-size:13px;">
    RelationshipAI is not a crisis service. Please use the resources above if you need immediate help.
  </p>
</div>"""
    return subject, html
