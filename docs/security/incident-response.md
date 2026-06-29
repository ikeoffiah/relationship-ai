# Security Incident Response (MVP)

For the first 20 pilot users, a lightweight process is sufficient.

## If a security issue is discovered

1. **Assess scope** immediately: how many users are affected?
2. **If data leak**: notify affected users within 72 hours by email via Resend.
3. **Revoke affected tokens**: `POST /admin/revoke-tokens` with affected `user_id` list.
4. **Rotate `MASTER_ENCRYPTION_SECRET`** in Railway env vars if the encryption key is compromised. Old sessions will need re-encryption — contact `security@relationshipai.app`.
5. **Document incident** in GitHub issue tagged `security-incident`.
6. **Post-mortem** within 7 days.

## Contact

`security@relationshipai.app`

## Severity Levels

| Level | Definition | Response Time |
|---|---|---|
| **P0 — Critical** | Data breach, namespace isolation failure | Immediate (within 1 hour) |
| **P1 — High** | Authentication bypass, JWT forgery | Same-day |
| **P2 — Medium** | OWASP Top 10 vulnerability | Within 72 hours |
| **P3 — Low** | Security misconfiguration, minor info disclosure | Next sprint |
