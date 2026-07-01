import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:mobile/features/relationship/relationship_viewmodel.dart';

part 'home_notifier.g.dart';

class HomeState {
  final RelationshipStatus relationshipStatus;
  final String? partnerDisplayName;
  final bool partnerJointSessionEnrolled;
  final int pendingRelayMessageCount;
  final String? lastSessionSummary;

  HomeState({
    required this.relationshipStatus,
    this.partnerDisplayName,
    this.partnerJointSessionEnrolled = false,
    this.pendingRelayMessageCount = 0,
    this.lastSessionSummary,
  });

  HomeState copyWith({
    RelationshipStatus? relationshipStatus,
    String? partnerDisplayName,
    bool? partnerJointSessionEnrolled,
    int? pendingRelayMessageCount,
    String? lastSessionSummary,
  }) {
    return HomeState(
      relationshipStatus: relationshipStatus ?? this.relationshipStatus,
      partnerDisplayName: partnerDisplayName ?? this.partnerDisplayName,
      partnerJointSessionEnrolled: partnerJointSessionEnrolled ?? this.partnerJointSessionEnrolled,
      pendingRelayMessageCount: pendingRelayMessageCount ?? this.pendingRelayMessageCount,
      lastSessionSummary: lastSessionSummary ?? this.lastSessionSummary,
    );
  }
}

@riverpod
class HomeNotifier extends _$HomeNotifier {
  @override
  HomeState build() => HomeState(relationshipStatus: RelationshipStatus.loading);

  Future<void> fetchHomeData(RelationshipViewModel relationshipViewModel) async {
    state = state.copyWith(relationshipStatus: RelationshipStatus.loading);
    try {
      await relationshipViewModel.fetchRelationshipStatus();
      
      final currentRel = relationshipViewModel.currentRelationship;
      final partnerName = currentRel != null ? currentRel['partner_name'] as String? : null;
      final enrolled = currentRel != null && currentRel['joint_session_participation'] == 'enrolled';
      
      state = state.copyWith(
        relationshipStatus: relationshipViewModel.status,
        partnerDisplayName: partnerName,
        partnerJointSessionEnrolled: enrolled,
        pendingRelayMessageCount: 0,
      );
    } catch (e) {
      state = state.copyWith(relationshipStatus: RelationshipStatus.notConnected);
    }
  }
}
