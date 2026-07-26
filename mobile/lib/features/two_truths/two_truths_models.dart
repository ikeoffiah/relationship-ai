/// Models for Two Truths & a Lie (Django engagement API).
library;

class TwoTruthsReveal {
  final int partnerLieIndex;
  final bool iCaughtThem;
  final int? partnerGuess;
  final bool theyCaughtMe;
  final int myLieIndex;

  const TwoTruthsReveal({
    this.partnerLieIndex = 0,
    this.iCaughtThem = false,
    this.partnerGuess,
    this.theyCaughtMe = false,
    this.myLieIndex = 0,
  });

  factory TwoTruthsReveal.fromJson(Map<String, dynamic> j) => TwoTruthsReveal(
        partnerLieIndex: j['partner_lie_index'] as int? ?? 0,
        iCaughtThem: j['i_caught_them'] as bool? ?? false,
        partnerGuess: j['partner_guess'] as int?,
        theyCaughtMe: j['they_caught_me'] as bool? ?? false,
        myLieIndex: j['my_lie_index'] as int? ?? 0,
      );
}

class TwoTruthsState {
  final bool hasPartner;
  final String? partnerName;
  final bool authored;
  final bool partnerAuthored;
  final bool iGuessed;
  final bool partnerGuessed;
  final bool revealed;
  final List<String>? myStatements;
  final int? myLieIndex;
  final int? myGuess;
  final List<String>? partnerStatements;
  final TwoTruthsReveal? reveal;

  const TwoTruthsState({
    this.hasPartner = false,
    this.partnerName,
    this.authored = false,
    this.partnerAuthored = false,
    this.iGuessed = false,
    this.partnerGuessed = false,
    this.revealed = false,
    this.myStatements,
    this.myLieIndex,
    this.myGuess,
    this.partnerStatements,
    this.reveal,
  });

  /// Which UI phase to show.
  /// - author: I haven't written my statements yet.
  /// - guess: I've authored and my partner has too, but I haven't guessed.
  /// - waiting: I've done my part; waiting on my partner.
  /// - reveal: both authored + both guessed.
  String get phase {
    if (revealed) return 'reveal';
    if (!authored) return 'author';
    if (partnerAuthored && !iGuessed) return 'guess';
    return 'waiting';
  }

  static List<String>? _strList(dynamic v) =>
      v == null ? null : (v as List).map((e) => e.toString()).toList();

  factory TwoTruthsState.fromJson(Map<String, dynamic> j) => TwoTruthsState(
        hasPartner: j['has_partner'] as bool? ?? false,
        partnerName: j['partner_name'] as String?,
        authored: j['authored'] as bool? ?? false,
        partnerAuthored: j['partner_authored'] as bool? ?? false,
        iGuessed: j['i_guessed'] as bool? ?? false,
        partnerGuessed: j['partner_guessed'] as bool? ?? false,
        revealed: j['revealed'] as bool? ?? false,
        myStatements: _strList(j['my_statements']),
        myLieIndex: j['my_lie_index'] as int?,
        myGuess: j['my_guess'] as int?,
        partnerStatements: _strList(j['partner_statements']),
        reveal: j['reveal'] != null
            ? TwoTruthsReveal.fromJson(j['reveal'] as Map<String, dynamic>)
            : null,
      );
}
