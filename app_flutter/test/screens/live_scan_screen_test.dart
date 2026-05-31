import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spoofvane_app/api.dart';
import 'package:spoofvane_app/models.dart';
import 'package:spoofvane_app/screens/live_scan_screen.dart';
import 'package:spoofvane_app/theme.dart';
import '../support/fake_api.dart';
import '../support/pump.dart';

void main() {
  late ApiClient original;
  late FakeApi fake;
  setUp(() {
    original = Api.instance;
    fake = FakeApi();
    Api.instance = fake;
  });
  tearDown(() => Api.instance = original);

  Future<void> pump(WidgetTester tester) async {
    useDesktopSurface(tester);
    await tester.pumpWidget(MaterialApp(
        theme: buildSvTheme(),
        home: const Scaffold(body: LiveScanScreen())));
    await tester.pumpAndSettle();
  }

  testWidgets('renders the URL/brand inputs, scan button and mode toggle',
      (tester) async {
    await pump(tester);
    expect(find.byKey(const Key('scan-url')), findsOneWidget);
    expect(find.byKey(const Key('scan-brand')), findsOneWidget);
    expect(find.byKey(const Key('scan-run')), findsOneWidget);
    expect(find.byKey(const Key('scan-mode-toggle')), findsOneWidget);
  });

  testWidgets('a live scan renders the merged verdict + per-model votes',
      (tester) async {
    await pump(tester);
    await tester.tap(find.byKey(const Key('scan-run')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('scan-result')), findsOneWidget);
    // The default fake returns a 2-model ensemble (Claude + GPT).
    expect(find.text('Claude'), findsOneWidget);
    expect(find.text('GPT'), findsOneWidget);
    // LIVE badge present (not demo).
    expect(find.text('LIVE'), findsOneWidget);
    // Both models appear as vote rows (Claude + GPT ensemble).
    expect(find.textContaining('claude-sonnet-4-6'), findsOneWidget);
    // Agent provenance chip proves it ran as a governed/audited agent.
    expect(find.textContaining('scan_agent'), findsOneWidget);
  });

  testWidgets('demo mode returns a canned sample tagged DEMO', (tester) async {
    await pump(tester);
    await tester.tap(find.byKey(const Key('scan-mode-demo')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('scan-run')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('scan-result')), findsOneWidget);
    expect(find.text('DEMO'), findsOneWidget);
    // The canned sample is a 3-model ensemble with dissent.
    expect(find.text('Gemini'), findsOneWidget);
    expect(find.textContaining('DISAGREED'), findsOneWidget);
  });

  testWidgets('an error result renders the error card, not a fake verdict',
      (tester) async {
    fake.scanStub = (url, brand) => ScanResult(
          mode: 'error',
          url: url,
          stage: 'fetch',
          error: 'Bright Data live-fetch failed: timeout',
        );
    await pump(tester);
    await tester.tap(find.byKey(const Key('scan-run')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('scan-error')), findsOneWidget);
    expect(find.byKey(const Key('scan-result')), findsNothing);
    expect(find.textContaining('could not run'), findsOneWidget);
  });
}
