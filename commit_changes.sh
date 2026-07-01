#!/bin/bash

# Exit on error, but we handle git add/commit failures ourselves
set -e

# ── Helpers ────────────────────────────────────────────────────────────────────

# Add paths that exist; silently skip ones that don't
safe_add() {
  for path in "$@"; do
    if [ -e "$path" ]; then
      git add "$path"
    else
      echo "  [skip] $path not found"
    fi
  done
}

# Commit only if something is actually staged
safe_commit() {
  local msg="$1"
  if git diff --cached --quiet; then
    echo "  [skip] nothing staged — commit skipped"
  else
    git commit -m "$msg"
  fi
}

# ── Commits ────────────────────────────────────────────────────────────────────

echo "Starting sequential commits for RelationshipAI features..."

# Group 1: Age Verification & Minor Access (REL-57)
echo ""
echo "Committing REL-57: Age Verification Flow..."
safe_add \
  backend-django/apps/accounts/ \
  backend-django/apps/safety/guardian_safety.py \
  mobile/lib/features/auth/views/age_verification_screen.dart \
  mobile/lib/features/auth/views/signup_screen.dart
safe_commit "feat(auth): implement age verification flow and minor access controls (REL-57)
- Added DOB and age gating in Django models and endpoints
- Integrated guardian consent loop for minors
- Created Flutter AgeVerificationScreen and integrated into auth flow"

# Group 2: Consent Data Model & API (REL-40, REL-41)
echo ""
echo "Committing REL-40 & REL-41: Consent Data Model and API..."
safe_add \
  backend-django/apps/consent/
safe_commit "feat(consent): design and implement consent data model and API endpoints (REL-40, REL-41)
- Built UserConsent model reflecting HIPAA/GDPR constraints
- Implemented API endpoints for reading/updating granular consent levels
- Added consent audit signals and backend verification gates"

# Group 3: Consent Dashboard & Summary UI (REL-42, REL-48)
echo ""
echo "Committing REL-42 & REL-48: Consent UI in Flutter..."
safe_add \
  mobile/lib/features/consent/ \
  mobile/test/features/consent/ \
  mobile/lib/core/api_services/consent_api_service.dart
safe_commit "feat(consent): build consent dashboard and summary UI (REL-42, REL-48)
- Added ConsentDashboardScreen with MemoryTransparencyPanel
- Implemented ConsentSummarySheet shown at start of joint sessions
- Connected Flutter UI to Django REST consent endpoints"

# Group 4: Relationship Pairing & Dissolution (REL-63)
echo ""
echo "Committing REL-63: Relationship Pairing..."
safe_add \
  backend-django/apps/relationships/ \
  mobile/lib/features/relationship/invite_partner_screen.dart \
  mobile/lib/features/relationship/accept_invite_screen.dart \
  mobile/lib/features/relationship/dissolve_relationship_screen.dart \
  mobile/lib/core/api_services/relationship_api_service.dart
safe_commit "feat(relationship): implement relationship pairing and dissolution flow (REL-63)
- Built relationship invite generation and acceptance API
- Implemented unilateral dissolution flow handling state resets
- Built Flutter screens for sending invites, accepting, and settings"

# Group 5: Joint Session Entry Consent Gate (REL-37)
echo ""
echo "Committing REL-37: Joint Session Entry..."
safe_add \
  backend-django/apps/sessions/views.py \
  backend-django/apps/sessions/urls.py \
  backend-django/apps/sessions/joint_session.py \
  backend-django/apps/sessions/models.py \
  mobile/lib/features/sessions/ \
  mobile/lib/core/api_services/joint_session_api_service.dart
safe_commit "feat(session): implement joint session entry consent gate (REL-37)
- Added strictly gated state machine for session entry (PENDING_A -> PENDING_B -> ACTIVE)
- Built backend validation confirming both partners affirmatively consent
- Built JointSessionEntryScreen polling for partner readiness"

# Group 6: Shared Relationship Context (REL-65)
echo ""
echo "Committing REL-65: Shared Relationship Context..."
safe_add \
  backend-fastapi/app/api/relationships.py \
  backend-fastapi/app/main.py \
  mobile/lib/features/relationship/our_story_screen.dart \
  mobile/lib/features/relationship/relationship_viewmodel.dart
safe_commit "feat(memory): implement shared relationship context layer (REL-65)
- Implemented FastAPI backend bridging shared data (goals, conflicts, repairs)
- Built bilateral consent verification across read/write operations
- Built 'Our Story' UI consolidating shared facts and history"

# Group 7: LangGraph Orchestration Pipeline (REL-66)
echo ""
echo "Committing REL-66: LangGraph StateGraph Pipeline..."
safe_add \
  backend-fastapi/app/orchestration/ \
  backend-fastapi/app/api/websockets.py \
  backend-fastapi/tests/test_graph.py \
  backend-fastapi/requirements/base.txt \
  backend-django/apps/sessions/tasks.py
safe_commit "feat(ai): implement LangGraph StateGraph 9-node pipeline (REL-66)
- Built SessionState dataclass and 9-node graph including safety pre/post screens
- Added websocket streaming integration and Celery async post-session hooks
- Integrated strict memory access routing based on active consent policies"

# Group 8: Main Navigation & Remaining Cleanup
echo ""
echo "Committing remaining structural changes and app wiring..."
safe_add \
  mobile/lib/main.dart \
  mobile/lib/features/home/ \
  mobile/lib/features/chat/ \
  mobile/lib/core/theme/app_colors.dart \
  mobile/lib/shared/ \
  mobile/pubspec.yaml \
  mobile/pubspec.lock \
  backend-django/config/ \
  backend-django/apps/safety/tests.py \
  backend-django/apps/audit/ \
  backend-django/apps/memory/ \
  backend-django/db.sqlite3 \
  mobile/android/ \
  mobile/ios/ \
  mobile/linux/ \
  mobile/macos/ \
  mobile/windows/ \
  mobile/test/ \
  mobile/lib/features/auth/ \
  mobile/lib/core/api_services/auth_api_service.dart \
  backend-django/apps/insights/ \
  backend-django/apps/personalization/ \
  backend-django/apps/therapist/serializers.py \
  backend-django/apps/therapist/urls.py \
  backend-django/apps/therapist/models.py \
  backend-django/apps/therapist/views.py \
  backend-fastapi/app/api/dialogue_models.py \
  backend-fastapi/app/api/dialogue_router.py \
  backend-fastapi/app/api/memory_router.py \
  backend-fastapi/app/api/relay_router.py \
  backend-fastapi/app/dialogue/ \
  mobile/lib/core/api_services/personalization_api_service.dart \
  mobile/lib/core/api_services/settings_api_service.dart \
  mobile/lib/features/home/home_notifier.dart \
  mobile/lib/features/home/home_notifier.g.dart \
  mobile/lib/features/home/views/home_screen.dart \
  mobile/lib/features/onboarding/ \
  mobile/lib/features/relationship/pending_invite_screen.dart \
  mobile/lib/features/relay/ \
  mobile/lib/features/settings/ \
  mobile/test/features/home/
safe_commit "chore: integrate main navigation, base styling, and system config
- Linked MainNavigationScreen with Chat, Our Story, and Privacy tabs
- Updated AppColors and global route tables in main.dart
- Registered API services into provider architecture
- Cleaned up unneeded test files and route guards"

echo ""
echo "All commits completed. Check 'git log --oneline' to review the sequence."