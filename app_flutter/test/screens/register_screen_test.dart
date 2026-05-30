import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spoofvane_app/screens/register_screen.dart';
import 'package:spoofvane_app/screens/onboarding_screen.dart';
import 'package:spoofvane_app/theme.dart';
import '../support/pump.dart';

void main() {
  Future<void> pump(WidgetTester tester) async {
    useDesktopSurface(tester);
    await tester.pumpWidget(
        MaterialApp(theme: buildSvTheme(), home: const RegisterScreen()));
    await tester.pumpAndSettle();
  }

  testWidgets('renders the registration form + demo SSO sign-up', (tester) async {
    await pump(tester);
    expect(find.byKey(const Key('register-card')), findsOneWidget);
    expect(find.byKey(const Key('register-google')), findsOneWidget);
    expect(find.byKey(const Key('register-email')), findsOneWidget);
    expect(find.byKey(const Key('register-company')), findsOneWidget);
    expect(find.byKey(const Key('register-password')), findsOneWidget);
  });

  testWidgets('submit is disabled until form valid + terms agreed',
      (tester) async {
    await pump(tester);
    // Initially cannot submit (button onPressed null).
    final btn0 = tester.widget<ElevatedButton>(
        find.byKey(const Key('register-submit')));
    expect(btn0.onPressed, isNull);

    await tester.enterText(
        find.byKey(const Key('register-email')), 'me@company.com');
    await tester.enterText(
        find.byKey(const Key('register-company')), 'Acme');
    await tester.enterText(
        find.byKey(const Key('register-password')), 'Str0ng!pass');
    await tester.tap(find.byKey(const Key('register-terms')));
    await tester.pumpAndSettle();

    final btn1 = tester.widget<ElevatedButton>(
        find.byKey(const Key('register-submit')));
    expect(btn1.onPressed, isNotNull);
  });

  testWidgets('demo Google sign-up proceeds to onboarding', (tester) async {
    await pump(tester);
    await tester.tap(find.byKey(const Key('register-google')));
    await tester.pumpAndSettle();
    expect(find.byType(OnboardingScreen), findsOneWidget);
  });
}
