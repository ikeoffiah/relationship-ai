import 'package:flutter/material.dart';
import 'package:provider/provider.dart' as provider;

import 'package:mobile/core/theme/app_colors.dart';
import 'package:mobile/features/auth/viewmodels/auth_viewmodel.dart';
import 'package:mobile/features/couple_chat/couple_chat_viewmodel.dart';
import 'package:mobile/features/couple_chat/views/couple_chat_screen.dart';
import 'package:mobile/features/hubs/hub_scaffold.dart';
import 'package:mobile/features/relationship/relationship_viewmodel.dart';

/// The three ways to work something out — previously scattered across the home
/// screen, a conditional card and a snackbar.
///
/// The couple's own conversation sits first, because it is the one they use
/// daily; the AI sessions are what you reach for when talking directly is not
/// enough.
class TalkScreen extends StatelessWidget {
  const TalkScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final relVM = provider.Provider.of<RelationshipViewModel>(context);
    final authVM = provider.Provider.of<AuthViewModel>(context);
    final relationshipId = relVM.currentRelationship?['id'] as String?;
    final userId = authVM.user?.id;
    final partnerName =
        relVM.currentRelationship?['partner_name'] as String? ?? 'your partner';
    final connected =
        relationshipId != null &&
        userId != null &&
        relVM.status == RelationshipStatus.active;

    return HubScaffold(
      title: 'Talk',
      intro: connected
          ? 'Talk to each other, or bring Bliss in when it helps.'
          : 'Private sessions are open to you now. Connect a partner to unlock the rest.',
      destinations: [
        if (connected)
          HubDestination(
            icon: Icons.chat_bubble_outline_rounded,
            title: 'Chat with $partnerName',
            blurb: 'Your conversation, with Bliss alongside.',
            accent: AppColors.warmCoral,
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => provider.ChangeNotifierProvider(
                  create: (_) => CoupleChatViewModel(
                    relationshipId: relationshipId,
                    userId: userId,
                  ),
                  child: CoupleChatScreen(
                    relationshipId: relationshipId,
                    userId: userId,
                    partnerName: partnerName,
                  ),
                ),
              ),
            ),
          ),
        HubDestination(
          icon: Icons.lock_outline_rounded,
          title: 'Private session',
          blurb: 'Think something through on your own, with Bliss.',
          accent: AppColors.calmTeal,
          onTap: () => Navigator.of(context).pushNamed('/chat'),
        ),
        if (connected)
          HubDestination(
            icon: Icons.people_outline_rounded,
            title: 'Together session',
            blurb: 'Sit down with $partnerName and Bliss at the same time.',
            accent: AppColors.softRose,
            onTap: () => Navigator.of(
              context,
            ).pushNamed('/chat', arguments: {'isJoint': true}),
          ),
        if (connected)
          HubDestination(
            icon: Icons.mark_email_unread_outlined,
            title: 'Say it better',
            blurb: 'Write something hard and let Bliss help it land.',
            accent: AppColors.goldDark,
            onTap: () => Navigator.of(context).pushNamed('/relay/inbox'),
          ),
        if (!connected)
          HubDestination(
            icon: Icons.link_rounded,
            title: 'Connect with your partner',
            blurb: 'Invite them, and the rest of this opens up.',
            accent: AppColors.warmCoral,
            onTap: () => Navigator.of(context).pushNamed('/relationship/invite'),
          ),
      ],
    );
  }
}
