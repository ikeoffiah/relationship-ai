import 'package:flutter/foundation.dart';

import 'package:mobile/features/bliss/bliss_api_service.dart';
import 'package:mobile/features/bliss/bliss_models.dart';

/// State for the in-app calendar.
///
/// Loads a month at a time. The alternative — fetch everything and filter on
/// the client — is fine for a couple with nine plans and awful for one with
/// three years of them, and the difference only shows up on the accounts that
/// have been around longest.
class CalendarViewModel extends ChangeNotifier {
  final BlissApiService _api;

  CalendarViewModel({BlissApiService? api}) : _api = api ?? BlissApiService();

  /// Items keyed by the day they fall on, at local midnight.
  final Map<DateTime, List<BlissItem>> _byDay = {};

  DateTime _month = _monthOf(DateTime.now());
  DateTime? _selected;
  bool _loading = false;
  String? _error;

  DateTime get month => _month;
  DateTime? get selectedDay => _selected;
  bool get isLoading => _loading;
  String? get error => _error;

  static DateTime _monthOf(DateTime d) => DateTime(d.year, d.month);
  static DateTime dayOf(DateTime d) => DateTime(d.year, d.month, d.day);

  List<BlissItem> itemsOn(DateTime day) => _byDay[dayOf(day)] ?? const [];

  bool hasAnythingOn(DateTime day) => itemsOn(day).isNotEmpty;

  /// Anything on this day still waiting on *this user's* answer.
  bool needsMyAnswerOn(DateTime day) =>
      itemsOn(day).any((item) => item.awaitingMyAnswer);

  List<BlissItem> get selectedItems =>
      _selected == null ? const [] : itemsOn(_selected!);

  /// Every invitation waiting on this user, across the loaded window — surfaced
  /// above the grid, because an unanswered question should not depend on
  /// someone happening to tap the right day.
  List<BlissItem> get pendingInvites => [
    for (final items in _byDay.values)
      for (final item in items)
        if (item.awaitingMyAnswer) item,
  ]..sort((a, b) => (a.dueAt ?? DateTime(0)).compareTo(b.dueAt ?? DateTime(0)));

  Future<void> load({DateTime? month}) async {
    _month = _monthOf(month ?? _month);
    _loading = true;
    _error = null;
    notifyListeners();

    // A month's grid shows trailing days of the previous month and leading days
    // of the next, so the window is padded — otherwise those cells would render
    // as empty when they are not.
    final from = DateTime(_month.year, _month.month - 1, 20);
    final to = DateTime(_month.year, _month.month + 2, 10);

    try {
      final fetched = await _api.calendar(from: from, to: to);
      _byDay
        ..clear()
        ..addAll({
          for (final entry in fetched.entries) dayOf(entry.key): entry.value,
        });
      _selected ??= dayOf(DateTime.now());
    } catch (e) {
      _error = e.toString().replaceAll('Exception: ', '');
    }
    _loading = false;
    notifyListeners();
  }

  void select(DateTime day) {
    _selected = dayOf(day);
    notifyListeners();
  }

  Future<void> stepMonth(int delta) =>
      load(month: DateTime(_month.year, _month.month + delta));

  /// Answer an invitation, updating in place so the card resolves immediately
  /// rather than after a refetch.
  Future<void> respond(BlissItem item, {required bool accept}) async {
    try {
      final updated = await _api.respond(item.id, accept: accept);
      for (final entry in _byDay.entries) {
        final index = entry.value.indexWhere((i) => i.id == item.id);
        if (index != -1) entry.value[index] = updated;
      }
    } catch (e) {
      _error = e.toString().replaceAll('Exception: ', '');
    }
    notifyListeners();
  }
}
