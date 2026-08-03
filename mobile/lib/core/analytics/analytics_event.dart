/// Every event this product is allowed to emit, as types rather than strings.
///
/// The reason there is no `track(String name, Map props)` anywhere in this
/// directory is worth stating plainly, because the convenient API is the one
/// every analytics library ships with and it is the wrong one here.
///
/// This app carries the contents of arguments between partners, private
/// counselling sessions, and mental-health signal. A free-form event API is one
/// autocomplete away from `track('message_sent', {'text': draft})`. Nobody
/// would write that deliberately; somebody will write it at 6pm on a Friday.
/// A closed set of constructors whose parameters are enums, bools and ints
/// makes that line impossible to write rather than merely forbidden — the
/// compiler enforces it, not a code review.
///
/// Three rules follow from the same reasoning:
///
///   **No content, ever.** No message text, no draft, no note, no answer, no
///   theme, no name. Not truncated, not hashed. There is no property here that
///   accepts free text.
///
///   **No partner-identifying data.** Never a relationship id, never a partner
///   user id. Two partners appearing in one analytics account with a shared
///   key would let a vendor — or anyone with access to the dashboard —
///   reconstruct the couple graph and read one person's behaviour against the
///   other's. That is the exact thing `boundary.py` exists to prevent on the
///   server, and it would be undone by a property name.
///
///   **Counts and enums, not values.** `questionAnswered` carries how long the
///   answer took to write, not what it said. `checkInSubmitted` carries nothing
///   at all — the 1-5 score is a private self-report and the whole
///   perception-gap design rests on it not travelling.
library;

/// Where in the product an event happened. A closed set, so a new screen
/// cannot silently start reporting itself under a free-form label.
enum AnalyticsSurface {
  today,
  us,
  talk,
  you,
  onboarding,
  chat,
  coupleChat,
  games,
  invite,
}

/// How an onboarding run ended.
enum OnboardingOutcome { completed, abandoned }

/// The state the daily question was in when it was shown.
enum QuestionState { unanswered, waiting, reveal, done }

/// A single analytics event.
///
/// `name` is the wire name; `properties` is what travels with it. Both are
/// derived here rather than supplied by callers, which is what makes the
/// guarantees above checkable — see `analytics_test.dart`, which asserts that
/// no property value in the entire taxonomy is a free-form string.
sealed class AnalyticsEvent {
  const AnalyticsEvent();

  String get name;

  /// Always primitives, never free text. Enum values are serialised by `.name`,
  /// which is a compile-time constant, not user input.
  Map<String, Object> get properties;
}

// ── activation ──────────────────────────────────────────────────────────────

class OnboardingStarted extends AnalyticsEvent {
  const OnboardingStarted();
  @override
  String get name => 'onboarding_started';
  @override
  Map<String, Object> get properties => const {};
}

/// One step finished. `step` is the screen's own key, not anything typed.
class OnboardingStepCompleted extends AnalyticsEvent {
  const OnboardingStepCompleted({required this.step, required this.index});
  final String step;
  final int index;
  @override
  String get name => 'onboarding_step_completed';
  @override
  Map<String, Object> get properties => {'step': step, 'index': index};
}

/// The event the funnel actually turns on. `lastStep` is where they stopped.
class OnboardingFinished extends AnalyticsEvent {
  const OnboardingFinished({
    required this.outcome,
    required this.lastStep,
    required this.seconds,
  });
  final OnboardingOutcome outcome;
  final String lastStep;
  final int seconds;
  @override
  String get name => 'onboarding_finished';
  @override
  Map<String, Object> get properties => {
    'outcome': outcome.name,
    'last_step': lastStep,
    'seconds': seconds,
  };
}

/// How many of the 30 RSQ items were answered before leaving. The single most
/// useful number for deciding whether the questionnaire should be shortened,
/// and it carries none of the answers.
class RsqProgress extends AnalyticsEvent {
  const RsqProgress({required this.answered, required this.total});
  final int answered;
  final int total;
  @override
  String get name => 'rsq_progress';
  @override
  Map<String, Object> get properties => {'answered': answered, 'total': total};
}

// ── the two-sided loop ──────────────────────────────────────────────────────

class InviteSent extends AnalyticsEvent {
  const InviteSent({required this.channel});

  /// 'email' or 'link'. A closed vocabulary at the call site; never an address.
  final String channel;
  @override
  String get name => 'invite_sent';
  @override
  Map<String, Object> get properties => {'channel': channel};
}

class InviteAccepted extends AnalyticsEvent {
  const InviteAccepted();
  @override
  String get name => 'invite_accepted';
  @override
  Map<String, Object> get properties => const {};
}

class QuestionShown extends AnalyticsEvent {
  const QuestionShown({required this.state});
  final QuestionState state;
  @override
  String get name => 'question_shown';
  @override
  Map<String, Object> get properties => {'state': state.name};
}

/// Note what is absent: the answer. Only how long it took to write it, which
/// is a usability signal rather than a disclosure.
class QuestionAnswered extends AnalyticsEvent {
  const QuestionAnswered({required this.secondsToAnswer});
  final int secondsToAnswer;
  @override
  String get name => 'question_answered';
  @override
  Map<String, Object> get properties => {
    'seconds_to_answer': secondsToAnswer,
  };
}

/// Both partners are in. The moment the product's best mechanic fires.
class QuestionRevealed extends AnalyticsEvent {
  const QuestionRevealed();
  @override
  String get name => 'question_revealed';
  @override
  Map<String, Object> get properties => const {};
}

/// Nothing about the 1-5 score, deliberately. It is a private self-report, and
/// the perception-gap insight is built on the premise that it does not travel.
class CheckInSubmitted extends AnalyticsEvent {
  const CheckInSubmitted();
  @override
  String get name => 'check_in_submitted';
  @override
  Map<String, Object> get properties => const {};
}

// ── use ─────────────────────────────────────────────────────────────────────

/// Which of the twenty-one feature areas anyone actually opens. The question
/// the product cannot currently answer for a single one of them.
class SurfaceOpened extends AnalyticsEvent {
  const SurfaceOpened({required this.surface});
  final AnalyticsSurface surface;
  @override
  String get name => 'surface_opened';
  @override
  Map<String, Object> get properties => {'surface': surface.name};
}

class SessionStarted extends AnalyticsEvent {
  const SessionStarted({required this.isJoint});
  final bool isJoint;
  @override
  String get name => 'session_started';
  @override
  Map<String, Object> get properties => {'is_joint': isJoint};
}

/// Distinct from `SessionStarted` on purpose. The assessment's finding was that
/// a session opens onto a blank screen behind four disclosure bars; the gap
/// between these two events is the measure of whether that is being fixed.
class SessionFirstMessage extends AnalyticsEvent {
  const SessionFirstMessage({required this.secondsFromOpen});
  final int secondsFromOpen;
  @override
  String get name => 'session_first_message';
  @override
  Map<String, Object> get properties => {
    'seconds_from_open': secondsFromOpen,
  };
}

/// Retention, as a day index rather than a date — a date is closer to being
/// identifying and answers no question a day number does not.
class AppOpened extends AnalyticsEvent {
  const AppOpened({required this.dayNumber});
  final int dayNumber;
  @override
  String get name => 'app_opened';
  @override
  Map<String, Object> get properties => {'day_number': dayNumber};
}
