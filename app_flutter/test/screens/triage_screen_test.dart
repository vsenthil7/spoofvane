import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spoofvane_app/api.dart';
import 'package:spoofvane_app/screens/triage_screen.dart';
import 'package:spoofvane_app/screens/alert_detail_screen.dart';
import '../support/fake_api.dart';
import '../support/pump.dart';

void main() {
  late ApiClient original;
  setUp(() {
    original = Api.instance;
    Api.instance = FakeApi();
  });
  tearDown(() => Api.instance = original);

  testWidgets('shows only non-benign alerts', (tester) async {
    await pumpScreen(tester, const TriageScreen());
    // 3 of 4 seed alerts are non-benign.
    expect(find.text('3 alerts'), findsOneWidget);
    expect(find.textContaining('acmebank-secure-login.top'), findsOneWidget);
    // The benign promo URL must NOT be in the triage queue.
    expect(find.textContaining('globex.com/promo'), findsNothing);
  });

  testWidgets('tapping a row opens the alert detail', (tester) async {
    await pumpScreen(tester, const TriageScreen());
    await tester.tap(find.byKey(const Key('alert-row-alert_seed_001')));
    await tester.pumpAndSettle();
    expect(find.byType(AlertDetailScreen), findsOneWidget);
    expect(find.text('Verdict trace (ensemble)'), findsOneWidget);
  });
}
