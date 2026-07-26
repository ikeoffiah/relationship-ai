/// Data models for the couple-games feature. Plain classes with defensive
/// `fromJson`, matching the app's model convention.
library;

class GameSummary {
  final String key;
  final String title;
  final String description;
  final String gameType;
  final String category;
  final int questionCount;
  final bool iComplete;
  final bool partnerComplete;
  final bool revealed;

  const GameSummary({
    required this.key,
    required this.title,
    this.description = '',
    this.gameType = 'know_your_partner',
    this.category = 'relationship',
    this.questionCount = 0,
    this.iComplete = false,
    this.partnerComplete = false,
    this.revealed = false,
  });

  factory GameSummary.fromJson(Map<String, dynamic> j) => GameSummary(
        key: j['key'] as String,
        title: j['title'] as String? ?? '',
        description: j['description'] as String? ?? '',
        gameType: j['game_type'] as String? ?? 'know_your_partner',
        category: j['category'] as String? ?? 'relationship',
        questionCount: j['question_count'] as int? ?? 0,
        iComplete: j['i_complete'] as bool? ?? false,
        partnerComplete: j['partner_complete'] as bool? ?? false,
        revealed: j['revealed'] as bool? ?? false,
      );
}

class GameProgress {
  final int total;
  final int myAnswered;
  final int partnerAnswered;
  final bool iComplete;
  final bool partnerComplete;
  final bool revealed;

  const GameProgress({
    this.total = 0,
    this.myAnswered = 0,
    this.partnerAnswered = 0,
    this.iComplete = false,
    this.partnerComplete = false,
    this.revealed = false,
  });

  factory GameProgress.fromJson(Map<String, dynamic> j) => GameProgress(
        total: j['total'] as int? ?? 0,
        myAnswered: j['my_answered'] as int? ?? 0,
        partnerAnswered: j['partner_answered'] as int? ?? 0,
        iComplete: j['i_complete'] as bool? ?? false,
        partnerComplete: j['partner_complete'] as bool? ?? false,
        revealed: j['revealed'] as bool? ?? false,
      );
}

class GameQuestionView {
  final String id;
  final String prompt;
  final List<String> options;
  final int? myAnswer;
  final int? myGuess;

  const GameQuestionView({
    required this.id,
    required this.prompt,
    this.options = const [],
    this.myAnswer,
    this.myGuess,
  });

  factory GameQuestionView.fromJson(Map<String, dynamic> j) => GameQuestionView(
        id: j['id'] as String,
        prompt: j['prompt'] as String? ?? '',
        options: (j['options'] as List?)?.map((e) => e.toString()).toList() ?? const [],
        myAnswer: j['my_answer'] as int?,
        myGuess: j['my_guess'] as int?,
      );
}

class RevealItem {
  final String questionId;
  final String prompt;
  final List<String> options;
  final int? myAnswer;
  final int? partnerAnswer;
  final int? myGuess;
  final int? partnerGuess;
  final bool iGuessedThem;
  final bool theyGuessedMe;
  final bool surprise;

  const RevealItem({
    required this.questionId,
    required this.prompt,
    this.options = const [],
    this.myAnswer,
    this.partnerAnswer,
    this.myGuess,
    this.partnerGuess,
    this.iGuessedThem = false,
    this.theyGuessedMe = false,
    this.surprise = false,
  });

  factory RevealItem.fromJson(Map<String, dynamic> j) => RevealItem(
        questionId: j['question_id'] as String? ?? '',
        prompt: j['prompt'] as String? ?? '',
        options: (j['options'] as List?)?.map((e) => e.toString()).toList() ?? const [],
        myAnswer: j['my_answer'] as int?,
        partnerAnswer: j['partner_answer'] as int?,
        myGuess: j['my_guess'] as int?,
        partnerGuess: j['partner_guess'] as int?,
        iGuessedThem: j['i_guessed_them'] as bool? ?? false,
        theyGuessedMe: j['they_guessed_me'] as bool? ?? false,
        surprise: j['surprise'] as bool? ?? false,
      );

  String label(int? idx) => (idx != null && idx >= 0 && idx < options.length) ? options[idx] : '—';
}

class GameReveal {
  final List<RevealItem> questions;
  final int myScore;
  final int partnerScore;
  final int outOf;

  const GameReveal({
    this.questions = const [],
    this.myScore = 0,
    this.partnerScore = 0,
    this.outOf = 0,
  });

  factory GameReveal.fromJson(Map<String, dynamic> j) => GameReveal(
        questions: (j['questions'] as List?)
                ?.map((e) => RevealItem.fromJson(e as Map<String, dynamic>))
                .toList() ??
            const [],
        myScore: j['my_score'] as int? ?? 0,
        partnerScore: j['partner_score'] as int? ?? 0,
        outOf: j['out_of'] as int? ?? 0,
      );
}

class GameDetail {
  final String key;
  final String title;
  final String gameType;
  final String category;
  final bool isScored;
  final bool hasPartner;
  final String? partnerName;
  final GameProgress progress;
  final List<GameQuestionView> questions;
  final GameReveal? reveal;

  const GameDetail({
    required this.key,
    required this.title,
    this.gameType = 'know_your_partner',
    this.category = 'relationship',
    this.isScored = true,
    this.hasPartner = false,
    this.partnerName,
    this.progress = const GameProgress(),
    this.questions = const [],
    this.reveal,
  });

  factory GameDetail.fromJson(Map<String, dynamic> j) => GameDetail(
        key: j['key'] as String,
        title: j['title'] as String? ?? '',
        gameType: j['game_type'] as String? ?? 'know_your_partner',
        category: j['category'] as String? ?? 'relationship',
        isScored: j['is_scored'] as bool? ?? true,
        hasPartner: j['has_partner'] as bool? ?? false,
        partnerName: j['partner_name'] as String?,
        progress: GameProgress.fromJson(j['progress'] as Map<String, dynamic>? ?? const {}),
        questions: (j['questions'] as List?)
                ?.map((e) => GameQuestionView.fromJson(e as Map<String, dynamic>))
                .toList() ??
            const [],
        reveal: j['reveal'] != null
            ? GameReveal.fromJson(j['reveal'] as Map<String, dynamic>)
            : null,
      );
}

class SpicyConsent {
  final bool you;
  final bool partner;
  final bool bothAgeVerified;
  final bool unlocked;

  const SpicyConsent({
    this.you = false,
    this.partner = false,
    this.bothAgeVerified = false,
    this.unlocked = false,
  });

  factory SpicyConsent.fromJson(Map<String, dynamic> j) => SpicyConsent(
        you: j['you'] as bool? ?? false,
        partner: j['partner'] as bool? ?? false,
        bothAgeVerified: j['both_age_verified'] as bool? ?? false,
        unlocked: j['unlocked'] as bool? ?? false,
      );
}
