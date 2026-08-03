# D7 — crisis resources are never gated

Owner: QA. Written 2026-08-03, against `docs/execution-plan.md` D7 and the
one-SKU decision in D2.

> **D7 — Nothing that reaches crisis resources is ever gated.** No paywall, no
> trial wall, no entitlement check on the support icon, the safety path, or
> anything downstream of them. This is a hard test QA owns, not a convention.

The test is `tests/safety/test_crisis_never_gated.py`. The map it reasons over
is `tests/safety/crisis_surface_map.py`. The tests that prove the test works
are `tests/safety/test_crisis_gate_catches_violations.py`.

```bash
./tests/run_qa_gates.sh          # both QA gates
pytest tests/safety/ -v          # just this one; stdlib only, no DB, no keys
```

---

## 1. Why this needs a test and not a code review

Nobody is going to write `if not user.has_paid: hide_the_hotline()`. That is
not the failure mode. The failure modes are all boring:

- A `build()` method gets wrapped in an entitlement branch to show a paywall,
  and the support icon was in the app bar inside it.
- `crisis_resources()` grows a `user` argument for a good reason —
  regionalising hotlines — and six weeks later somebody filters on entitlement
  inside a function that now has the user in scope.
- An entitlement-check node is added to the front of the counseling graph,
  ahead of `node_1_safety_prescreen`, so an unpaid user's message is never
  screened for crisis at all.
- A screen is rebuilt for the paywall flow and the `SupportAction()` in its
  `actions:` list does not come back.

Every one of those is a normal day's work that a reviewer looking at a diff
about billing would approve. None of them look like a decision about crisis
resources. That is exactly why D7 is a test.

The product has, by its own assessment, "the part of the product most likely to
matter legally… treated most rigorously" (`product-assessment.md` §1.4). D7 is
the promise that the paywall does not undo that.

---

## 2. What the crisis path actually is

Mapped from the code on 2026-08-03. This is the thing the test covers; if this
section is wrong, the test is measuring the wrong product.

### 2.1 The support icon — the always-available path

`SupportAction` (`mobile/lib/shared/widgets/support_action.dart`) is one
`IconButton` with an unconditional `onPressed` that pushes `/safety`. It is
mounted in the `actions:` of **12 files**, one of which (`hub_scaffold.dart`)
covers every hub screen at once:

```
home_screen · chat_screen · couple_chat_screen · calendar_screen ·
hub_scaffold · session_history_screen · session_detail_screen ·
notification_center_screen · consent_dashboard_screen · settings_screen ·
security_settings_screen · about_screen
```

`/safety` is registered in the plain `routes:` map in `main.dart:234` and
resolves to `SafetyResourcesScreen`, which renders `safetyResources` from
`safety_resources_data.dart` — emergency services, crisis lines, domestic
violence lines — and launches `tel:` / `sms:` / chat URLs.

Four other places push `/safety` directly: `about_screen.dart:173`,
`chat_screen.dart:256` and `:353`, `notification_center_screen.dart:250`,
`couple_chat_screen.dart:981`.

### 2.2 The classifier escalation path

```
message
  └─ chat_router.stream_counseling_turn
       └─ build_counseling_graph()          entry: node_1_safety_prescreen
            ├─ SafetyPreScreener.screen     layer1 rules → layer2 semantic → layer3 LLM
            ├─ level = critical | elevated | safe
            └─ route_after_prescreen        score > 0.7  →  SAFETY_PROTOCOL → END
```

When `level != "safe"`, `chat_router.py:326` emits an SSE frame:

```json
{"type": "safety_triggered", "level": "critical", "resources": [...]}
```

`resources` comes from `crisis_resources()` (`chat_router.py:105`), which reads
the `CRISIS_RESOURCES` env var and returns `[]` if unset — deliberately, because
"publishing an incorrect or invented hotline number to someone in crisis is
worse than publishing none."

On the client, `chat_screen.dart` turns `level == "critical"` into a
non-dismissible `SafetyProtocolModal`, and anything else into a snackbar with a
"See support" action that pushes `/safety`.

### 2.3 The two tiers

The test splits these surfaces in two, and the split is the design decision
that makes it usable.

**Tier 1 — the crisis path proper.** Files whose job *is* reaching crisis
resources: everything under `features/safety/`, `app/safety/`, `apps/safety/`,
plus `support_action.dart`, `safety_protocol_modal.dart` and `graph.py`. Closed
transitively over imports — 33 files today. **No entitlement concept may appear
anywhere in this set**, under a deliberately broad word list.

**Tier 2 — mount points and callers.** Files that reference a crisis symbol but
have other jobs: the 12 screens carrying the icon, plus `main.dart` and
`chat_router.py` — 22 files today. These may legitimately gate something else
on the same screen, so the rule is narrower: **no entitlement token within 25
lines of a crisis reference**.

Why not one tier? `main.dart` imports every screen in the app. Closing over it
would make Tier 1 mean "the entire product," and the first legitimate paywall
anywhere would turn D7 red. A gate that cries wolf gets deleted, and then D7 is
protected by nothing.

---

## 3. What the test checks

| # | Check | Catches |
|---|---|---|
| 1 | Map still finds its anchors | The gate going vacuously green after a rename |
| 2 | `REVIEWED_EXCEPTIONS` entries still apply | Allowlist rot |
| 3 | No entitlement word in the Tier 1 closure | A gate on, or one import away from, the crisis path |
| 4 | No entitlement token within 25 lines of a crisis reference in Tier 2 | A paywall branch wrapping a screen that carries the icon |
| 5 | `/safety` is a plain entry in the `routes:` map | The destination moving behind any guard |
| 6 | `support_action.dart` has no `if (`, `Visibility`, `Offstage`, `SizedBox.shrink()`, `onPressed: null` | The icon becoming conditional or disabled |
| 7 | The 12 mount points have not shrunk | Reach quietly eroding during a paywall refactor |
| 8 | `crisis_resources()` takes zero arguments | The function becoming caller-dependent, which is step one |
| 9 | Graph entry point is `node_1_safety_prescreen` | A node inserted ahead of the crisis classifier |
| 10 | Prescreen's conditional edges include `SAFETY_PROTOCOL` | The escalation exit being routed through something new |
| 11 | Runtime test exists once billing lands | The static gate being all we ever have |

Checks 3 and 4 use two different word lists, at two precisions.

The high-precision list (`PAYMENT_PATTERNS`) runs product-wide and matches the
shapes gates take in code — `entitlement`, `paywall`, `stripe`, `paystack`,
`checkout_session`, `redemption_code`, `is_paid`, `premium`, `feature_gate`.
It deliberately excludes `entitled` (because `apps/chat/views.py` says
"entitled to" about a person's data) and `can_access` (because the *consent*
system legitimately owns that phrase, and consent is not payment).

The high-recall list adds broad words — `billing`, `trial`, `tier`, `purchase`,
`subscription`, `has_access` — and only ever runs over Tier 1, where prose
about billing has no business appearing and a miss is worst.

### The reviewed-exceptions escape hatch

`REVIEWED_EXCEPTIONS` in `crisis_surface_map.py` is empty today and should stay
close to empty. Adding a line is a standing decision to let an entitlement
concept sit near a crisis path. It needs a reason, a reviewer and a date, and
check 2 deletes it for you once it stops being true.

**Do not widen the pattern lists to make a failure go away.** Widening is
invisible in review and permanent; an exception is visible and expires.

---

## 4. The runtime test — spec for when P0.2 lands

Everything above is static analysis. It reads source and reasons about words.
That is proportionate while there is nothing to gate with, and insufficient the
moment there is: none of it can prove that an account holding no entitlement
actually receives crisis resources at runtime.

`test_runtime_gate_test_exists_once_billing_lands` currently **skips**. It stops
skipping the moment payment code appears anywhere in `mobile/lib`,
`backend-fastapi/app` or `backend-django/apps`, and then fails until
`tests/safety/test_crisis_runtime_ungated.py` exists. That is intentional: the
coverage should arrive with the risk, not in a follow-up ticket competing with
launch.

That file must assert, against a real stack, with **an account that holds no
entitlement**:

1. **The escalation still fires.** POST a clear-crisis message to the
   counseling endpoint. Assert a `safety_triggered` SSE frame arrives with
   `level == "critical"`, and that it arrives *before* any paywall response.
2. **The resources are identical.** Run the same message on an entitled account
   and an unentitled one. Assert the `resources` arrays are byte-identical.
   Not "both non-empty" — identical. A shortened list for unpaid users is the
   violation dressed as a compromise.
3. **The support screen renders with no network call to billing.** A widget
   test that pumps `SafetyResourcesScreen` with no entitlement provider in the
   tree at all. If it needs one to build, the entitlement system is on the
   crisis path.
4. **The icon survives the paywall state.** A widget test that puts the app in
   its most-locked state — unentitled, expired code, whatever the worst case
   turns out to be — and asserts `SupportAction` is present, enabled, and still
   navigates to `/safety`.

Add a fifth if redemption codes gate anything in-app: an account whose code was
refunded or revoked must still pass 1–4. Someone whose access was just removed
is not obviously in a good week.

---

## 5. Known weaknesses, stated plainly

- **Proximity is a proxy.** Check 4 approximates "is guarded by" with "is
  within 25 lines of." Deciding it properly needs a Dart parser and a Python
  one, both of which would then have to stay correct through every refactor.
  The instrument is tuned to over-report: a false positive costs somebody
  reading twenty lines of diff, a false negative costs a person in crisis
  hitting a paywall. Those are not the same cost.
- **A gate in a file with no crisis symbol and no import edge is invisible.**
  If billing is enforced in middleware that wraps every route, no static check
  here will see it. §4 check 1 is the only thing that catches that, which is
  another reason the tripwire is not optional.
- **The Dart import walk does not follow `part`/`part of` directives.** Not
  used on any current crisis surface. It would become a hole if that changed.
- **`crisis_resources()` returns `[]` unless `CRISIS_RESOURCES` is set.** The
  test asserts the plumbing is ungated, not that anything comes out of it. In
  the deployed environment the list being populated is a separate, unautomated
  fact — see the release checklist item in `docs/qa/baseline.md`.

---

## 6. If this test fails

Do not add the exception first. In order:

1. Read the diff it is pointing at. The failure message names the file, the
   line, the rule and the crisis reference it is near.
2. Ask whether a person in crisis, holding no entitlement, in the worst state
   the product can put them in, still reaches a phone number in one tap.
3. If yes and the match is genuinely incidental, add the file to
   `REVIEWED_EXCEPTIONS` with a reason, a reviewer and a date.
4. If no, that is a release blocker. It goes to the PM, not into the allowlist.
