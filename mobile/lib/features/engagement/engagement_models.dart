/// Data models for the daily-engagement feature (daily question, check-in,
/// shared goals, micro-action, points & streak). Plain classes with defensive
/// `fromJson` factories, matching the app's model convention.
library;

class DailyQuestionState {
  final String? questionId;
  final String? promptText;
  final String category;
  final bool hasPartner;
  final bool iAnswered;
  final bool partnerAnswered;
  final bool revealed;
  final String? myAnswer;
  final String? partnerAnswer;
  final String? partnerName;

  const DailyQuestionState({
    this.questionId,
    this.promptText,
    this.category = 'connection',
    this.hasPartner = false,
    this.iAnswered = false,
    this.partnerAnswered = false,
    this.revealed = false,
    this.myAnswer,
    this.partnerAnswer,
    this.partnerName,
  });

  bool get hasQuestion => promptText != null;

  factory DailyQuestionState.fromJson(Map<String, dynamic> json) {
    final q = json['question'] as Map<String, dynamic>?;
    return DailyQuestionState(
      questionId: q?['id'] as String?,
      promptText: q?['prompt_text'] as String?,
      category: (q?['category'] as String?) ?? 'connection',
      hasPartner: json['has_partner'] as bool? ?? false,
      iAnswered: json['i_answered'] as bool? ?? false,
      partnerAnswered: json['partner_answered'] as bool? ?? false,
      revealed: json['revealed'] as bool? ?? false,
      myAnswer: json['my_answer'] as String?,
      partnerAnswer: json['partner_answer'] as String?,
      partnerName: json['partner_name'] as String?,
    );
  }
}

class MicroActionState {
  final String? actionId;
  final String? text;
  final String category;
  final bool completed;

  const MicroActionState({
    this.actionId,
    this.text,
    this.category = '',
    this.completed = false,
  });

  bool get hasAction => text != null;

  factory MicroActionState.fromJson(Map<String, dynamic> json) {
    final a = json['action'] as Map<String, dynamic>?;
    return MicroActionState(
      actionId: a?['id'] as String?,
      text: a?['text'] as String?,
      category: (a?['category'] as String?) ?? '',
      completed: json['completed'] as bool? ?? false,
    );
  }
}

class EngagementSummary {
  final int pointsBalance;
  final int currentStreak;
  final int longestStreak;
  final bool didQuestion;
  final bool didCheckIn;
  final bool didMicroAction;
  final bool hasPartner;

  const EngagementSummary({
    this.pointsBalance = 0,
    this.currentStreak = 0,
    this.longestStreak = 0,
    this.didQuestion = false,
    this.didCheckIn = false,
    this.didMicroAction = false,
    this.hasPartner = false,
  });

  factory EngagementSummary.fromJson(Map<String, dynamic> json) {
    final today = json['today'] as Map<String, dynamic>? ?? const {};
    return EngagementSummary(
      pointsBalance: json['points_balance'] as int? ?? 0,
      currentStreak: json['current_streak'] as int? ?? 0,
      longestStreak: json['longest_streak'] as int? ?? 0,
      didQuestion: today['daily_question'] as bool? ?? false,
      didCheckIn: today['check_in'] as bool? ?? false,
      didMicroAction: today['micro_action'] as bool? ?? false,
      hasPartner: json['has_partner'] as bool? ?? false,
    );
  }
}

class SharedGoal {
  final String id;
  final String title;
  final String description;
  final String category;
  final String cadence;
  final double? targetValue;
  final double currentValue;
  final double progressFraction;
  final String unit;
  final String status;

  const SharedGoal({
    required this.id,
    required this.title,
    this.description = '',
    this.category = 'relationship',
    this.cadence = 'daily',
    this.targetValue,
    this.currentValue = 0,
    this.progressFraction = 0,
    this.unit = '',
    this.status = 'active',
  });

  factory SharedGoal.fromJson(Map<String, dynamic> json) {
    double? toD(dynamic v) => v == null ? null : (v as num).toDouble();
    return SharedGoal(
      id: json['id'] as String,
      title: json['title'] as String? ?? '',
      description: json['description'] as String? ?? '',
      category: json['category'] as String? ?? 'relationship',
      cadence: json['cadence'] as String? ?? 'daily',
      targetValue: toD(json['target_value']),
      currentValue: toD(json['current_value']) ?? 0,
      progressFraction: toD(json['progress_fraction']) ?? 0,
      unit: json['unit'] as String? ?? '',
      status: json['status'] as String? ?? 'active',
    );
  }
}

/// Result of a daily action that awards points/advances the streak.
class ActionReward {
  final int pointsAwarded;
  final int currentStreak;
  final bool revealed;

  const ActionReward({
    this.pointsAwarded = 0,
    this.currentStreak = 0,
    this.revealed = false,
  });

  factory ActionReward.fromJson(Map<String, dynamic> json) => ActionReward(
        pointsAwarded: json['points_awarded'] as int? ?? 0,
        currentStreak: json['current_streak'] as int? ?? 0,
        revealed: json['revealed'] as bool? ?? false,
      );
}
