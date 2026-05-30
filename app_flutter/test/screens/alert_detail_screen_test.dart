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

  Future<void> pump(WidgetTester tester) async {
    useDesktopSurface(tester);
    await tester.pumpWidget(MaterialApp(
        theme: buildSvTheme(), home: AlertDetailScreen(alert: alert)));
    await tester.pumpAndSettle();
  }

  testWidgets('has all ten canonical evidence tabs', (tester) async {
    await pump(tester);
    for (final t in kAlertTabs) {
      expect(find.byKey(Key('tab-$t')), findsOneWidget, reason: 'tab $t');
    }
    expect(kAlertTabs.length, 10);
  });

  testWidgets('summary tab renders verdict + score + first seen', (tester) async {
    await pump(tester);
    expect(find.text('Summary'), findsWidgets);
    expect(find.textContaining('0.91'), findsWidgets);
    expect(find.text('banking'), findsOneWidget);
  });

  testWidgets('kit tab shows the matched phishing kit', (tester) async {
    await pump(tester);
    await tester.tap(find.byKey(const Key('tab-Kit')));
    await tester.pumpAndSettle();
    expect(find.textContaining('16Shop'), findsOneWidget);
  });

  testWidgets('mitre tab shows the technique id', (tester) async {
    await pump(tester);
    await tester.tap(find.byKey(const Key('tab-MITRE')));
    await tester.pumpAndSettle();
    expect(find.textContaining('T1566.002'), findsOneWidget);
  });

  testWidgets('verdict trace tab shows the ensemble', (tester) async {
    await pump(tester);
    await tester.tap(find.byKey(const Key('tab-Verdict trace')));
    await tester.pumpAndSettle();
    expect(find.textContaining('claude: phish'), findsOneWidget);
    expect(find.textContaining('no dissent'), findsOneWidget);
  });

  testWidgets('multi-region tab flags cloaking', (tester) async {
    await pump(tester);
    await tester.tap(find.byKey(const Key('tab-Multi-region')));
    await tester.pumpAndSettle();
    expect(find.text('Cloaking detected'), findsOneWidget);
  });

  testWidgets('deepfake tab is empty for a non-deepfake family', (tester) async {
    await pump(tester);
    await tester.tap(find.byKey(const Key('tab-Deepfake')));
    await tester.pumpAndSettle();
    expect(find.textContaining('No synthetic media'), findsOneWidget);
  });

  testWidgets('takedown button shows confirmation snackbar', (tester) async {
    await pump(tester);
    await tester.tap(find.byKey(const Key('takedown-button')));
    await tester.pump();
    expect(find.textContaining('Takedown requested'), findsOneWidget);
  });
}
