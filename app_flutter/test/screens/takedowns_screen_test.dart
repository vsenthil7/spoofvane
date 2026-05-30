import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spoofvane_app/api.dart';
import 'package:spoofvane_app/models.dart';
import 'package:spoofvane_app/screens/takedowns_screen.dart';
import '../support/fake_api.dart';
import '../support/pump.dart';

void main() {
  late ApiClient original;
  setUp(() {
    original = Api.instance;
    Api.instance = FakeApi();
  });
  tearDown(() => Api.instance = original);

  testWidgets('lists takedown channels grouped by target', (tester) async {
    await pumpScreen(tester, const TakedownsScreen());
    expect(find.byKey(const Key('takedowns-list')), findsOneWidget);
    expect(find.text('Cloudflare'), findsOneWidget);
    expect(find.text('Hetzner'), findsOneWidget);
    expect(find.text('AWS'), findsOneWidget);
    // Reference ids surface.
    expect(find.textContaining('CF-AB-481920'), findsOneWidget);
  });

  testWidgets('shows the state for each channel', (tester) async {
    await pumpScreen(tester, const TakedownsScreen());
    expect(find.byKey(const Key('takedown-state-td_001')), findsOneWidget);
    expect(find.text('acknowledged'), findsOneWidget);
    expect(find.text('resolved'), findsWidgets);
    expect(find.text('rejected'), findsOneWidget);
  });

  testWidgets('summary counts targets, channels and resolved', (tester) async {
    await pumpScreen(tester, const TakedownsScreen());
    // 3 distinct targets, 5 channels, 1 resolved in seed.
    expect(find.textContaining('3 targets'), findsOneWidget);
    expect(find.textContaining('5 channels'), findsOneWidget);
    expect(find.textContaining('1 resolved'), findsOneWidget);
  });

  testWidgets('manual override updates the channel state', (tester) async {
    await pumpScreen(tester, const TakedownsScreen());
    // td_005 is draft; override it to resolved.
    await tester.tap(find.byKey(const Key('takedown-override-td_005')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('resolved').last);
    await tester.pumpAndSettle();
    // Resolved count goes from 1 to 2.
    expect(find.textContaining('2 resolved'), findsOneWidget);
  });
}
