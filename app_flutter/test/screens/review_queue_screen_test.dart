import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spoofvane_app/api.dart';
import 'package:spoofvane_app/screens/review_queue_screen.dart';
import '../support/fake_api.dart';
import '../support/pump.dart';

void main() {
  late ApiClient original;
  setUp(() {
    original = Api.instance;
    Api.instance = FakeApi();
  });
  tearDown(() => Api.instance = original);

  testWidgets('lists pending review actions', (tester) async {
    await pumpScreen(tester, const ReviewQueueScreen());
    expect(find.byKey(const Key('review-list')), findsOneWidget);
    expect(find.textContaining('awaiting approval'), findsOneWidget);
    expect(find.text('takedown.submit'), findsWidgets);
    expect(find.text('analyst.kim'), findsOneWidget);
  });

  testWidgets('approve records the decision', (tester) async {
    await pumpScreen(tester, const ReviewQueueScreen());
    await tester.tap(find.byKey(const Key('review-approve-rv_001')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('review-decision-rv_001')), findsOneWidget);
    expect(find.textContaining('Approved'), findsOneWidget);
  });

  testWidgets('deny records the decision', (tester) async {
    await pumpScreen(tester, const ReviewQueueScreen());
    await tester.tap(find.byKey(const Key('review-deny-rv_002')));
    await tester.pumpAndSettle();
    expect(find.textContaining('Denied'), findsOneWidget);
  });

  testWidgets('segregation of duties blocks self-raised items', (tester) async {
    // Default reviewer is reviewer.osei, who raised rv_003.
    await pumpScreen(tester, const ReviewQueueScreen());
    // The self-raised item shows the SoD block, not approve/deny buttons.
    expect(find.byKey(const Key('review-sod-rv_003')), findsOneWidget);
    expect(find.byKey(const Key('review-approve-rv_003')), findsNothing);
    expect(find.textContaining('you raised this'), findsOneWidget);
  });

  testWidgets('a different reviewer CAN action items others raised', (tester) async {
    await pumpScreen(
        tester, const ReviewQueueScreen(currentReviewer: 'reviewer.diff'));
    // Now nothing is self-raised: every row has approve buttons, no SoD block.
    expect(find.byKey(const Key('review-approve-rv_001')), findsOneWidget);
    expect(find.byKey(const Key('review-approve-rv_003')), findsOneWidget);
    expect(find.byKey(const Key('review-sod-rv_003')), findsNothing);
  });
}
