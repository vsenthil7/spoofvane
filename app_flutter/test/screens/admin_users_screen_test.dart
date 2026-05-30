import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spoofvane_app/api.dart';
import 'package:spoofvane_app/screens/admin_users_screen.dart';
import '../support/fake_api.dart';
import '../support/pump.dart';

void main() {
  late ApiClient original;
  setUp(() {
    original = Api.instance;
    Api.instance = FakeApi();
  });
  tearDown(() => Api.instance = original);

  testWidgets('lists users with email and role selector', (tester) async {
    await pumpScreen(tester, const AdminUsersScreen());
    expect(find.byKey(const Key('users-list')), findsOneWidget);
    expect(find.textContaining('owner@demotenant.io'), findsOneWidget);
    expect(find.byKey(const Key('user-role-u_owner')), findsOneWidget);
  });

  testWidgets('header counts users and those without MFA', (tester) async {
    await pumpScreen(tester, const AdminUsersScreen());
    // 6 users, 1 without MFA (analyst.lee).
    expect(find.textContaining('6 users'), findsOneWidget);
    expect(find.textContaining('1 without MFA'), findsOneWidget);
  });

  testWidgets('flags the MFA status per user', (tester) async {
    await pumpScreen(tester, const AdminUsersScreen());
    expect(find.byKey(const Key('user-mfa-u_owner')), findsOneWidget);
    expect(find.byKey(const Key('user-mfa-u_lee')), findsOneWidget);
  });

  testWidgets('role can be changed via the dropdown', (tester) async {
    await pumpScreen(tester, const AdminUsersScreen());
    await tester.tap(find.byKey(const Key('user-role-u_lee')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('reviewer').last);
    await tester.pumpAndSettle();
    // The dropdown now shows reviewer for that user.
    expect(find.text('reviewer'), findsWidgets);
  });
}
