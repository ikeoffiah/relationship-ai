/// Represents a user's profile
class UserProfile {
  final String id;
  final String name;
  final String email;
  final String? avatarUrl;

  const UserProfile({
    required this.id,
    required this.name,
    required this.email,
    this.avatarUrl,
  });

  // Sample user profile
  static UserProfile get sample => const UserProfile(
    id: '1',
    name: 'Test User',
    email: 'test@example.com',
  );

  // Serialization
  Map<String, dynamic> toJson() => {
    'id': id,
    'name': name,
    'email': email,
    'avatarUrl': avatarUrl,
  };

  factory UserProfile.fromJson(Map<String, dynamic> json) {
    return UserProfile(
      id: json['id'] as String,
      name: json['name'] as String,
      email: json['email'] as String? ?? '',
      avatarUrl: json['avatarUrl'] as String?,
    );
  }
}
