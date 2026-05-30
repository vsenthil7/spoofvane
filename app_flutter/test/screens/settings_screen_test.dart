import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spoofvane_app/screens/settings_screen.dart';
import '../support/pump.dart';

void main() {
  testWidgets('renders profile, security and api-key sections', (tester) async {
    await pumpScreen(tester, const SettingsScreen());
    expect(find.byKey(const Key('settings-list')), findsOneWidget);
    expect(find.text('Profile'), findsOneWidget);
    expect(find.text('Security'), findsOneWidget);
    expect(find.text('API keys'), findsOneWidget);
  });

  testWidgets('MFA toggle flips enrolled state', (tester) async {
    await pumpScreen(tester, const SettingsScreen());
    expect(find.text('Enrolled'), findsOneWidget);
    await tester.tap(find.byKey(const Key('settings-mfa')));
    await tester.pumpAndSettle();
    expect(find.text('Not enrolled'), findsOneWidget);
  });

  testWidgets('reveal shows the full api key', (tester) async {
    await pumpScreen(tester, const SettingsScreen());
    expect(find.textContaining('sv_live_8f2c…a91b'), findsOneWidget);
    await tester.tap(find.byKey(const Key('settings-reveal-key')));
    await tester.pumpAndSettle();
    expect(find.text('sv_live_8f2c0d4471e2a91b'), findsOneWidget);
  });

  testWidgets('rotate replaces the key and confirms', (tester) async {
    await pumpScreen(tester, const SettingsScreen());
    await tester.tap(find.byKey(const Key('settings-rotate-key')));
    await tester.pump();
    expect(find.textContaining('rotated'), findsOneWidget);
  });
}
