import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spoofvane_app/api.dart';
import 'package:spoofvane_app/app.dart';
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

  Future<void> pump(WidgetTester tester) async {
    useDesktopSurface(tester);
    await tester.pumpWidget(
        MaterialApp(theme: buildSvTheme(), home: const LoginScreen()));
    await tester.pumpAndSettle();
  }

  testWidgets('renders the demo SSO options incl. Google', (tester) async {
    await pump(tester);
    expect(find.byKey(const Key('login-card')), findsOneWidget);
    expect(find.byKey(const Key('login-google')), findsOneWidget);
    expect(find.byKey(const Key('login-microsoft')), findsOneWidget);
    expect(find.byKey(const Key('login-sso')), findsOneWidget);
    expect(find.byKey(const Key('login-saml')), findsOneWidget);
    expect(find.textContaining('Continue with Google'), findsOneWidget);
  });

  testWidgets('has email/password fields, a role selector and sign-in',
      (tester) async {
    await pump(tester);
    expect(find.byKey(const Key('login-email')), findsOneWidget);
    expect(find.byKey(const Key('login-password')), findsOneWidget);
    expect(find.byKey(const Key('login-role')), findsOneWidget);
    expect(find.byKey(const Key('login-signin')), findsOneWidget);
  });

  testWidgets('demo Google button enters the console', (tester) async {
    await pump(tester);
    await tester.tap(find.byKey(const Key('login-google')));
    await tester.pumpAndSettle();
    expect(find.byType(Console), findsOneWidget);
    expect(find.text('Security Dashboard'), findsOneWidget);
  });

  testWidgets('sign-in button enters the console', (tester) async {
    await pump(tester);
    await tester.tap(find.byKey(const Key('login-signin')));
    await tester.pumpAndSettle();
    expect(find.byType(Console), findsOneWidget);
  });
}
