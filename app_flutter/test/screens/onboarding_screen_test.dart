import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spoofvane_app/app.dart';
import 'package:spoofvane_app/screens/onboarding_screen.dart';
import 'package:spoofvane_app/theme.dart';
import '../support/pump.dart';

void main() {
  Future<void> pump(WidgetTester tester) async {
    useDesktopSurface(tester);
    await tester.pumpWidget(
        MaterialApp(theme: buildSvTheme(), home: const OnboardingScreen()));
    await tester.pumpAndSettle();
  }

  testWidgets('starts on the company step', (tester) async {
    await pump(tester);
    expect(find.byKey(const Key('onboarding-card')), findsOneWidget);
    expect(find.byKey(const Key('onboarding-step-company')), findsOneWidget);
  });

  testWidgets('advances through the steps to done', (tester) async {
    await pump(tester);
    await tester.tap(find.byKey(const Key('onboarding-next'))); // -> brand
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('onboarding-step-brand')), findsOneWidget);

    await tester.tap(find.byKey(const Key('onboarding-next'))); // -> invite
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('onboarding-step-invite')), findsOneWidget);

    await tester.tap(find.byKey(const Key('onboarding-next'))); // -> done
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('onboarding-step-done')), findsOneWidget);
    expect(find.textContaining("all set"), findsOneWidget);
  });

  testWidgets('finishing enters the console', (tester) async {
    await pump(tester);
    for (var i = 0; i < 4; i++) {
      await tester.tap(find.byKey(const Key('onboarding-next')));
      await tester.pumpAndSettle();
    }
    expect(find.byType(Console), findsOneWidget);
  });

  testWidgets('back returns to the previous step', (tester) async {
    await pump(tester);
    await tester.tap(find.byKey(const Key('onboarding-next')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('onboarding-back')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('onboarding-step-company')), findsOneWidget);
  });
}
