import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spoofvane_app/models.dart';
import 'package:spoofvane_app/screens/alert_detail_screen.dart';
import 'package:spoofvane_app/theme.dart';
import '../support/pump.dart';

void main() {
  final alert = Alert(
    id: 'a1',
    brandId: 'b1',
    url: 'https://evil-login.top/verify',
    verdict: Verdict.phish,
    composite: 0.91,
    family: 'banking',
    kit: '16Shop',
    renderedFrom: 'US',
    discoveredAt: '2026-05-29T09:10:00Z',
    mitreTechniques: ['T1566.002'],
  );

  testWidgets('renders summary fields and ensemble trace', (tester) async {
    useDesktopSurface(tester);
    await tester.pumpWidget(MaterialApp(
        theme: buildSvTheme(), home: AlertDetailScreen(alert: alert)));
    await tester.pumpAndSettle();
    expect(find.text('Summary'), findsOneWidget);
    expect(find.textContaining('0.91'), findsWidgets);
    expect(find.textContaining('16Shop'), findsOneWidget);
    expect(find.textContaining('T1566.002'), findsOneWidget);
    expect(find.textContaining('claude: phish'), findsOneWidget);
  });

  testWidgets('takedown button shows confirmation snackbar', (tester) async {
    useDesktopSurface(tester);
    await tester.pumpWidget(MaterialApp(
        theme: buildSvTheme(), home: AlertDetailScreen(alert: alert)));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('takedown-button')));
    await tester.pump();
    expect(find.textContaining('Takedown requested'), findsOneWidget);
  });
}
