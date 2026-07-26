/// Lightweight, dependency-free formatting for Bliss due dates (shown in the
/// device's local time).
library;

const _months = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
];
const _weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

String _clock(DateTime d) {
  final h = d.hour % 12 == 0 ? 12 : d.hour % 12;
  final m = d.minute.toString().padLeft(2, '0');
  final ampm = d.hour < 12 ? 'am' : 'pm';
  return '$h:$m$ampm';
}

/// e.g. "Fri, Jul 31 · 7:00pm", or "Fri, Jul 31" when [hasTime] is false, or
/// "No time set" when [due] is null.
String formatDue(DateTime? due, {bool hasTime = true}) {
  if (due == null) return 'No time set';
  final local = due.toLocal();
  final date = '${_weekdays[local.weekday - 1]}, ${_months[local.month - 1]} ${local.day}';
  return hasTime ? '$date · ${_clock(local)}' : date;
}
