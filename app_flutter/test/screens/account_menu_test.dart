import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spoofvane_app/api.dart';
import 'package:spoofvane_app/app.dart';
import 'package:spoofvane_app/roles.dart';
import 'package:spoofvane_app/screens/login_screen.dart';
import 'package:spoofvane_app/theme.dart';
import '../support/fake_api.dart';
import '../support/pump.dart';

void main() {
  late ApiClient original;
  setUp(() {
    original = Api.instance;
    Api.instance = FakeApi();
  });
  tearDown(() => Api.instance = original);

  Future<void> pumpConsole(WidgetTester tester, {Role role = Role.owner}) async {
    useDesktopSurface(tester);
    await tester.pumpWidget(
        MaterialApp(theme: buildSvTheme(), home: Console(role: role)));
    await tester.pumpAndSettle();
  }

  testWidgets('account menu chip shows current role + tenant', (tester) async {
    await pumpConsole(tester, role: Role.owner);
    expect(find.byKey(const Key('account-menu')), findsOneWidget);
    // The chip surfaces the role label and the default tenant.
    expect(find.text('Owner'), findsWidgets);
    expect(find.text('AcmeBank'), findsWidgets);
  });

  testWidgets('opening the menu reveals switch-role, switch-tenant and logout',
      (tester) async {
    await pumpConsole(tester);
    await tester.tap(find.byKey(const Key('account-menu')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('account-logout')), findsOneWidget);
    expect(find.byKey(const Key('account-role-analyst')), findsOneWidget);
    expect(find.byKey(const Key('account-tenant-GlobalPay')), findsOneWidget);
    expect(find.text('Log out'), findsOneWidget);
  });

  testWidgets('logout returns to the login screen and clears the console',
      (tester) async {
    await pumpConsole(tester);
    await tester.tap(find.byKey(const Key('account-menu')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('account-logout')));
    await tester.pumpAndSettle();
    expect(find.byType(LoginScreen), findsOneWidget);
    expect(find.byType(Console), findsNothing);
  });

  testWidgets('switching role re-enters the console gated to the new role',
      (tester) async {
    // Start as owner (sees Admin pages), switch to viewer (does not).
    await pumpConsole(tester, role: Role.owner);
    await tester.tap(find.byKey(const Key('account-menu')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('account-role-viewer')));
    await tester.pumpAndSettle();
    // Still in the console, now as Viewer.
    expect(find.byType(Console), findsOneWidget);
    expect(find.text('Viewer'), findsWidgets);
  });

  testWidgets('switching tenant updates the chip label', (tester) async {
    await pumpConsole(tester);
    await tester.tap(find.byKey(const Key('account-menu')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('account-tenant-NorthVault')));
    await tester.pumpAndSettle();
    expect(find.text('NorthVault'), findsWidgets);
  });
}
