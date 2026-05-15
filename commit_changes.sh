#!/bin/bash

# Exit on error
set -e

echo "Starting sequential commits for RelationshipAI features..."

# Group 1: Age Verification & Minor Access (REL-57)
echo "Committing REL-57: Age Verification Flow..."
git add backend-django/apps/accounts/
git add backend-django/apps/safety/guardian_safety.py
git add mobile/lib/features/auth/views/age_verification_screen.dart
git add mobile/lib/features/auth/views/signup_screen.dart
git commit -m "feat(auth): implement age verification flow and minor access controls (REL-57)
- Added DOB and age gating in Django models and endpoints
- Integrated guardian consent loop for minors
- Created Flutter AgeVerificationScreen and integrated into auth flow"

# Group 2: Consent Data Model & API (REL-40, REL-41)
echo "Committing REL-40 & REL-41: Consent Data Model and API..."
git add backend-django/apps/consent/
git commit -m "feat(consent): design and implement consent data model and API endpoints (REL-40, REL-41)
- Built UserConsent model reflecting HIPAA/GDPR constraints
- Implemented API endpoints for reading/updating granular consent levels
- Added consent audit signals and backend verification gates"

# Group 3: Consent Dashboard & Summary UI (REL-42, REL-48)
echo "Committing REL-42 & REL-48: Consent UI in Flutter..."
git add mobile/lib/features/consent/
git add mobile/test/features/consent/
git add mobile/lib/core/api_services/consent_api_service.dart
git commit -m "feat(consent): build consent dashboard and summary UI (REL-42, REL-48)
- Added ConsentDashboardScreen with MemoryTransparencyPanel
- Implemented ConsentSummarySheet shown at start of joint sessions
- Connected Flutter UI to Django REST consent endpoints"

# Group 4: Relationship Pairing & Dissolution (REL-63)
echo "Committing REL-63: Relationship Pairing..."
git add backend-django/apps/relationships/
git add mobile/lib/features/relationship/invite_partner_screen.dart
git add mobile/lib/features/relationship/accept_invite_screen.dart
git add mobile/lib/features/relationship/dissolve_relationship_screen.dart
git add mobile/lib/core/api_services/relationship_api_service.dart
git commit -m "feat(relationship): implement relationship pairing and dissolution flow (REL-63)
- Built relationship invite generation and acceptance API
- Implemented unilateral dissolution flow handling state resets
- Built Flutter screens for sending invites, accepting, and settings"

# Group 5: Joint Session Entry Consent Gate (REL-37)
echo "Committing REL-37: Joint Session Entry..."
git add backend-django/apps/sessions/views.py
git add backend-django/apps/sessions/urls.py
git add backend-django/apps/sessions/joint_session.py
git add backend-django/apps/sessions/models.py
git add mobile/lib/features/sessions/
git add mobile/lib/core/api_services/joint_session_api_service.dart
git commit -m "feat(session): implement joint session entry consent gate (REL-37)
- Added strictly gated state machine for session entry (PENDING_A -> PENDING_B -> ACTIVE)
- Built backend validation confirming both partners affirmatively consent
- Built JointSessionEntryScreen polling for partner readiness"

# Group 6: Shared Relationship Context (REL-65)
echo "Committing REL-65: Shared Relationship Context..."
git add backend-fastapi/app/api/relationships.py
git add backend-fastapi/app/main.py
git add mobile/lib/features/relationship/our_story_screen.dart
git add mobile/lib/features/relationship/relationship_viewmodel.dart
git commit -m "feat(memory): implement shared relationship context layer (REL-65)
- Implemented FastAPI backend bridging shared data (goals, conflicts, repairs)
- Built bilateral consent verification across read/write operations
- Built 'Our Story' UI consolidating shared facts and history"

# Group 7: LangGraph Orchestration Pipeline (REL-66)
echo "Committing REL-66: LangGraph StateGraph Pipeline..."
git add backend-fastapi/app/orchestration/
git add backend-fastapi/app/api/websockets.py
git add backend-fastapi/tests/test_graph.py
git add backend-fastapi/requirements/base.txt
git add backend-django/apps/sessions/tasks.py
git commit -m "feat(ai): implement LangGraph StateGraph 9-node pipeline (REL-66)
- Built SessionState dataclass and 9-node graph including safety pre/post screens
- Added websocket streaming integration and Celery async post-session hooks
- Integrated strict memory access routing based on active consent policies"

# Group 8: Main Navigation & Remaining Cleanup
echo "Committing remaining structural changes and app wiring..."
git add mobile/lib/main.dart
git add mobile/lib/features/home/
git add mobile/lib/features/chat/
git add mobile/lib/core/theme/app_colors.dart
git add mobile/lib/shared/
git add mobile/pubspec.yaml
git add mobile/pubspec.lock
git add backend-django/config/
git add backend-django/apps/safety/tests.py
git add backend-django/apps/audit/
git add backend-django/apps/memory/
git add backend-django/db.sqlite3
git add mobile/android/
git add mobile/ios/
git add mobile/linux/
git add mobile/macos/
git add mobile/windows/
git add mobile/test/
git add mobile/lib/features/auth/
git add mobile/lib/core/api_services/auth_api_service.dart
git commit -m "chore: integrate main navigation, base styling, and system config
- Linked MainNavigationScreen with Chat, Our Story, and Privacy tabs
- Updated AppColors and global route tables in main.dart
- Registered API services into provider architecture
- Cleaned up unneeded test files and route guards"

echo "All commits completed successfully! Check 'git log' to review the sequence."
