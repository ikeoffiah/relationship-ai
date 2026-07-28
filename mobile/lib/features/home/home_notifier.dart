import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:mobile/features/relationship/relationship_viewmodel.dart';
import 'package:mobile/features/relay/relay_api_service.dart';

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

  Future<void> fetchHomeData(
    RelationshipViewModel relationshipViewModel, {
    String? userId,
  }) async {
    state = state.copyWith(relationshipStatus: RelationshipStatus.loading);
    try {
      await relationshipViewModel.fetchRelationshipStatus();
      
      final currentRel = relationshipViewModel.currentRelationship;
      final partnerName = currentRel != null ? currentRel['partner_name'] as String? : null;
      final enrolled = currentRel != null && currentRel['joint_session_participation'] == 'enrolled';
      
      // Previously pinned to 0, which meant the relay card on Home could never
      // appear no matter how many messages were waiting — the feature was
      // effectively unreachable. Fetched now, and a failure here degrades to
      // "no badge" rather than taking down the whole home screen.
      var pendingRelays = 0;
      if (userId != null) {
        try {
          pendingRelays = (await RelayApiService().fetchPending(userId)).length;
        } catch (_) {
          pendingRelays = 0;
        }
      }

      state = state.copyWith(
        relationshipStatus: relationshipViewModel.status,
        partnerDisplayName: partnerName,
        partnerJointSessionEnrolled: enrolled,
        pendingRelayMessageCount: pendingRelays,
      );
    } catch (e) {
      state = state.copyWith(relationshipStatus: RelationshipStatus.notConnected);
    }
  }
}
