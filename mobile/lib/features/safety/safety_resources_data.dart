class SafetyResource {
  final String category;
  final String name;
  final String? description;
  final String? phoneNumber;
  final String? textNumber;
  final String? textKeyword;
  final String? chatUrl;
  final String available;

  const SafetyResource({
    required this.category,
    required this.name,
    this.description,
    this.phoneNumber,
    this.textNumber,
    this.textKeyword,
    this.chatUrl,
    required this.available,
  });
}

const List<SafetyResource> safetyResources = [
  SafetyResource(
    category: 'Emergency',
    name: 'Emergency Services',
    description: 'For immediate physical danger',
    phoneNumber: '911',
    available: '24/7',
  ),
  SafetyResource(
    category: 'Crisis',
    name: '988 Suicide & Crisis Lifeline',
    description: 'Call or text for mental health crisis support',
    phoneNumber: '988',
    textNumber: '988',
    available: '24/7',
  ),
  SafetyResource(
    category: 'Crisis',
    name: 'Crisis Text Line',
    description: 'Text HOME to 741741',
    textNumber: '741741',
    textKeyword: 'HOME',
    available: '24/7',
  ),
  SafetyResource(
    category: 'DomesticViolence',
    name: 'National Domestic Violence Hotline',
    phoneNumber: '18007997233',
    chatUrl: 'https://www.thehotline.org',
    available: '24/7',
  ),
];
