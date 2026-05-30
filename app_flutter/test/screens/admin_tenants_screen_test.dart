import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spoofvane_app/api.dart';
import 'package:spoofvane_app/screens/admin_tenants_screen.dart';
import '../support/fake_api.dart';
import '../support/pump.dart';

void main() {
  late ApiClient original;
  setUp(() {
    original = Api.instance;
    Api.instance = FakeApi();
  });
  tearDown(() => Api.instance = original);

  testWidgets('lists tenants with plan and region', (tester) async {
    await pumpScreen(tester, const AdminTenantsScreen());
    expect(find.byKey(const Key('tenants-list')), findsOneWidget);
    expect(find.text('DemoTenant'), findsOneWidget);
    expect(find.text('Acme Corp'), findsOneWidget);
    expect(find.text('eu-west'), findsOneWidget);
    expect(find.text('enterprise'), findsOneWidget);
  });

  testWidgets('header counts tenants, active and seats', (tester) async {
    await pumpScreen(tester, const AdminTenantsScreen());
    // 3 tenants, 2 active, 41 seats total in seed.
    expect(find.textContaining('3 tenants'), findsOneWidget);
    expect(find.textContaining('2 active'), findsOneWidget);
    expect(find.textContaining('41 seats'), findsOneWidget);
  });

  testWidgets('shows suspended status for inactive tenant', (tester) async {
    await pumpScreen(tester, const AdminTenantsScreen());
    expect(find.byKey(const Key('tenant-status-t_globex')), findsOneWidget);
    expect(find.text('suspended'), findsOneWidget);
  });
}
