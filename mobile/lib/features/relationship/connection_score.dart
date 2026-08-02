/// The one number for how the relationship is going, and how loudly to say it.
///
/// Mirrors `personalization.connection.presentation`. The important field is
/// [emphasis], not [score] — the server decides how prominent the number should
/// be, and the answer on a bad week is "not very". Rendering the number the
/// same size whatever it says would undo the whole design: the morning after a
/// fight, somebody opening the app for help should be met with something
/// useful rather than a low mark.
///
/// Not to be confused with the `connection_score` a partner submits in their
/// daily check-in. That is a private 1–5 feeling, this is a 0–100 number built
/// from behaviour both partners watched happen, and the whole design rests on
/// the second never reading the first.
library;

enum ScoreEmphasis {
  /// Not enough has happened to say anything — a new couple, or one who
  /// stopped. Show nothing at all: "—/100" reads as a zero to anyone already
  /// anxious about it.
  hidden,

  /// A number exists and is not the headline. Lead with something useful.
  quiet,

  /// Things are going well enough that the number can lead.
  feature;

  static ScoreEmphasis parse(String? raw) => switch (raw) {
    'feature' => ScoreEmphasis.feature,
    'quiet' => ScoreEmphasis.quiet,
    _ => ScoreEmphasis.hidden,
  };
}

/// Weekly, never daily. A daily delta is noise carrying emotional weight.
enum ScoreDirection {
  up,
  down,
  steady;

  static ScoreDirection? parse(String? raw) => switch (raw) {
    'up' => ScoreDirection.up,
    'down' => ScoreDirection.down,
    'steady' => ScoreDirection.steady,
    _ => null,
  };
}

class ConnectionScore {
  final int? score;
  final ScoreEmphasis emphasis;
  final ScoreDirection? direction;
  final List<int> series;

  const ConnectionScore({
    this.score,
    this.emphasis = ScoreEmphasis.hidden,
    this.direction,
    this.series = const [],
  });

  /// What to show when the request failed. Deliberately `hidden` rather than a
  /// zero or a spinner that never resolves — an outage should look like "we
  /// have nothing to say today", which is a true statement, rather than like a
  /// relationship that has collapsed.
  static const unknown = ConnectionScore();

  bool get isVisible => emphasis != ScoreEmphasis.hidden && score != null;

  factory ConnectionScore.fromJson(Map<String, dynamic> json) {
    final points = (json['series'] as List<dynamic>? ?? [])
        .map((p) => ((p as Map<String, dynamic>)['value'] as num?)?.round() ?? 0)
        .toList();
    return ConnectionScore(
      score: (json['score'] as num?)?.round(),
      emphasis: ScoreEmphasis.parse(json['emphasis'] as String?),
      direction: ScoreDirection.parse(json['direction'] as String?),
      series: points,
    );
  }
}
