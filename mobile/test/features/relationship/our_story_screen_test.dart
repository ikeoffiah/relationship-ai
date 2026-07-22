import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:provider/provider.dart';
import 'package:mobile/features/relationship/our_story_screen.dart';
import 'package:mobile/features/relationship/relationship_viewmodel.dart';

class MockRelationshipViewModel extends Mock implements RelationshipViewModel {}

void main() {
  late MockRelationshipViewModel vm;

  setUp(() {
    vm = MockRelationshipViewModel();
    when(() => vm.currentRelationship).thenReturn({'id': 'rel-1'});
    when(() => vm.fetchRelationshipStatus()).thenAnswer((_) async {});
    when(() => vm.fetchSharedContext()).thenAnswer((_) async {});
  });

  Future<void> pump(WidgetTester tester) async {
    await tester.pumpWidget(
      ChangeNotifierProvider<RelationshipViewModel>.value(
        value: vm,
        child: const MaterialApp(home: OurStoryScreen()),
      ),
    );
    await tester.pump();
  }

  testWidgets('with no active relationship, guides the user to connect',
      (tester) async {
    when(() => vm.status).thenReturn(RelationshipStatus.notConnected);
    when(() => vm.sharedContext).thenReturn(null);

    await pump(tester);

    expect(find.text('Connect with partner'), findsOneWidget);
    // Not an infinite spinner.
    expect(find.byType(CircularProgressIndicator), findsNothing);
  });

  testWidgets('while active but loading context, shows a spinner',
      (tester) async {
    when(() => vm.status).thenReturn(RelationshipStatus.active);
    when(() => vm.sharedContext).thenReturn(null);

    await pump(tester);

    expect(find.byType(CircularProgressIndicator), findsOneWidget);
  });

  testWidgets('renders the shared story sections when context is loaded',
      (tester) async {
    when(() => vm.status).thenReturn(RelationshipStatus.active);
    when(() => vm.sharedContext).thenReturn({
      'structural_facts': {
        'relationship_duration_months': 18,
        'cohabiting': true,
        'children': 1,
      },
      'named_recurring_conflicts': [],
      'agreed_goals_and_values': [
        {'description': 'Save for a house'},
      ],
      'repair_history': [
        {'description': 'We talked it through'},
      ],
    });

    await pump(tester);

    expect(find.text('Shared Goals'), findsOneWidget);
    expect(find.text('Save for a house'), findsOneWidget);
    expect(find.text('Repair Moments'), findsOneWidget);
    expect(find.text('We talked it through'), findsOneWidget);
  });
}
