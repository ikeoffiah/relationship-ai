# ADR-AGE-VERIFICATION: Implementation of Age Verification Gate

## Status
Proposed

## Context
Per Section 12.2 of the RelationshipAI paper, age verification is a hard legal and ethical requirement due to the sensitive nature of the mental health and relationship data processed by the platform. Self-reported age is insufficient.

## Decision
We will implement **Option B: ID Verification Service** as the primary verification method for launch.

### Implementation Details:
1. **Third-Party Provider**: We will integrate with an identity verification provider (e.g., Stripe Identity or Jumio).
2. **Data Privacy**: RelationshipAI will NEVER store raw ID images or full dates of birth. We will only store the verification outcome, method, and timestamp.
3. **Verification Flow**:
   - The age gate is presented at the start of registration.
   - Users under 18 (self-reported) are blocked immediately.
   - Verified adults (>= 18) are granted full access.
   - EU users (16-17) may be allowed via a Parental Consent flow (Option C) if jurisdictional sign-off is obtained.
4. **Middleware Enforcement**: A mandatory check will be applied to all session, consent, and memory endpoints.

## Consequences
- Increased friction during onboarding, but essential for legal compliance and user safety.
- Requirement for external identity verification API keys and costs.
- Robust protection against minor usage in adult-oriented therapeutic contexts.
