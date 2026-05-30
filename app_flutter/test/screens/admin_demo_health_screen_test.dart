import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spoofvane_app/api.dart';
import 'package:spoofvane_app/screens/admin_demo_health_screen.dart';
import '../support/fake_api.dart';
import '../support/pump.dart';

void main() {
  late ApiClient original;
  setUp(() {
    original = Api.instance;
    Api.instance = FakeApi();
  });
  tearDown(() => Api.instance = original);

  testWidgets('lists demo-health checks', (tester) async {
    await pumpScreen(tester, const AdminDemoHealthScreen());
    expect(find.byKey(const Key('demo-health-list')), findsOneWidget);
    expect(find.text('Brands seeded'), findsOneWidget);
    expect(find.text('21-page coverage'), findsOneWidget);
  });

  testWidgets('header counts passing checks', (tester) async {
    await pumpScreen(tester, const AdminDemoHealthScreen());
    // 5 of 6 passing in seed (deepfake-family is the honest fail).
    expect(find.textContaining('5/6 checks passing'), findsOneWidget);
  });

  testWidgets('surfaces the honest deepfake-family gap', (tester) async {
    await pumpScreen(tester, const AdminDemoHealthScreen());
    expect(find.textContaining('Deepfake-family alerts'), findsOneWidget);
    expect(find.textContaining('falls back to SEED'), findsOneWidget);
  });
}
