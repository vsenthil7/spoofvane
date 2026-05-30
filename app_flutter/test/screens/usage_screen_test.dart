import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spoofvane_app/api.dart';
import 'package:spoofvane_app/screens/usage_screen.dart';
import '../support/fake_api.dart';
import '../support/pump.dart';

void main() {
  late ApiClient original;
  setUp(() {
    original = Api.instance;
    Api.instance = FakeApi();
  });
  tearDown(() => Api.instance = original);

  testWidgets('lists metered resources', (tester) async {
    await pumpScreen(tester, const UsageScreen());
    expect(find.byKey(const Key('usage-list')), findsOneWidget);
    expect(find.text('Scans'), findsOneWidget);
    expect(find.text('API calls'), findsOneWidget);
    expect(find.text('Bright Data spend'), findsOneWidget);
  });

  testWidgets('shows used/allowance per metric', (tester) async {
    await pumpScreen(tester, const UsageScreen());
    // Scans 38420 / 50000.
    expect(find.textContaining('38420 / 50000'), findsOneWidget);
    // Bright Data spend is a USD metric.
    expect(find.textContaining('\$168.94'), findsOneWidget);
  });

  testWidgets('unlimited metric (Takedowns) is flagged', (tester) async {
    await pumpScreen(tester, const UsageScreen());
    expect(find.byKey(const Key('usage-row-Takedowns')), findsOneWidget);
    expect(find.textContaining('unlimited'), findsOneWidget);
  });
}
