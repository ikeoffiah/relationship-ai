/// Data models for the opt-in faith / spirituality feature. Plain classes with
/// defensive `fromJson`, matching the app's model convention.
library;

class FaithReading {
  final String id;
  final String title;
  final String reference;
  final String body;
  final String reflectionPrompt;

  const FaithReading({
    required this.id,
    this.title = '',
    this.reference = '',
    this.body = '',
    this.reflectionPrompt = '',
  });

  factory FaithReading.fromJson(Map<String, dynamic> j) => FaithReading(
        id: j['id'] as String? ?? '',
        title: j['title'] as String? ?? '',
        reference: j['reference'] as String? ?? '',
        body: j['body'] as String? ?? '',
        reflectionPrompt: j['reflection_prompt'] as String? ?? '',
      );
}

class FaithPracticeItem {
  final String key;
  final String label;
  final String icon;
  final bool completed;

  const FaithPracticeItem({
    required this.key,
    this.label = '',
    this.icon = '',
    this.completed = false,
  });

  FaithPracticeItem copyWith({bool? completed}) => FaithPracticeItem(
        key: key,
        label: label,
        icon: icon,
        completed: completed ?? this.completed,
      );

  factory FaithPracticeItem.fromJson(Map<String, dynamic> j) => FaithPracticeItem(
        key: j['key'] as String,
        label: j['label'] as String? ?? '',
        icon: j['icon'] as String? ?? '',
        completed: j['completed'] as bool? ?? false,
      );
}

class FaithToday {
  final String dateKey;
  final String tradition;
  final FaithReading? reading;
  final List<FaithPracticeItem> practices;
  final bool reflected;

  const FaithToday({
    this.dateKey = '',
    this.tradition = 'universal',
    this.reading,
    this.practices = const [],
    this.reflected = false,
  });

  FaithToday copyWith({
    List<FaithPracticeItem>? practices,
    bool? reflected,
  }) =>
      FaithToday(
        dateKey: dateKey,
        tradition: tradition,
        reading: reading,
        practices: practices ?? this.practices,
        reflected: reflected ?? this.reflected,
      );

  factory FaithToday.fromJson(Map<String, dynamic> j) => FaithToday(
        dateKey: j['date_key'] as String? ?? '',
        tradition: j['tradition'] as String? ?? 'universal',
        reading: j['reading'] != null
            ? FaithReading.fromJson(j['reading'] as Map<String, dynamic>)
            : null,
        practices: (j['practices'] as List?)
                ?.map((e) => FaithPracticeItem.fromJson(e as Map<String, dynamic>))
                .toList() ??
            const [],
        reflected: j['reflected'] as bool? ?? false,
      );
}
