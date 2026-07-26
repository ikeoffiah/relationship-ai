/// Models for partner commitments (Django engagement API).
library;

class Commitment {
  final String id;
  final String kind; // 'for_partner' | 'with_partner'
  final String text;
  final DateTime? remindAt;
  final String status;

  const Commitment({
    required this.id,
    this.kind = 'for_partner',
    this.text = '',
    this.remindAt,
    this.status = 'active',
  });

  bool get isWithPartner => kind == 'with_partner';

  factory Commitment.fromJson(Map<String, dynamic> j) => Commitment(
        id: j['id'] as String,
        kind: j['kind'] as String? ?? 'for_partner',
        text: j['text'] as String? ?? '',
        remindAt: j['remind_at'] != null ? DateTime.tryParse(j['remind_at'] as String) : null,
        status: j['status'] as String? ?? 'active',
      );
}
