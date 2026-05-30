import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spoofvane_app/api.dart';
import 'package:spoofvane_app/screens/api_keys_screen.dart';
import '../support/fake_api.dart';
import '../support/pump.dart';

void main() {
  late ApiClient original;
  setUp(() {
    original = Api.instance;
    Api.instance = FakeApi();
  });
  tearDown(() => Api.instance = original);

  testWidgets('lists keys with masked value and scope', (tester) async {
    await pumpScreen(tester, const ApiKeysScreen());
    expect(find.byKey(const Key('apikeys-list')), findsOneWidget);
    expect(find.text('CI pipeline'), findsOneWidget);
    expect(find.text('SIEM export'), findsOneWidget);
    expect(find.text('read_write'), findsOneWidget);
  });

  testWidgets('a revoked key shows revoked state, not a revoke button',
      (tester) async {
    await pumpScreen(tester, const ApiKeysScreen());
    // key_old is inactive in seed.
    expect(find.byKey(const Key('apikey-revoke-key_old')), findsNothing);
    expect(find.text('revoked'), findsWidgets);
  });

  testWidgets('revoking an active key removes its revoke button', (tester) async {
    await pumpScreen(tester, const ApiKeysScreen());
    expect(find.byKey(const Key('apikey-revoke-key_ci')), findsOneWidget);
    await tester.tap(find.byKey(const Key('apikey-revoke-key_ci')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('apikey-revoke-key_ci')), findsNothing);
  });

  testWidgets('create flow reveals the full secret exactly once', (tester) async {
    await pumpScreen(tester, const ApiKeysScreen());
    await tester.tap(find.byKey(const Key('apikey-create')));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('apikey-name-field')), 'My key');
    await tester.tap(find.byKey(const Key('apikey-create-confirm')));
    await tester.pumpAndSettle();
    // The one-time secret reveal dialog appears with a full sv_live_ secret.
    expect(find.byKey(const Key('apikey-secret')), findsOneWidget);
    expect(find.textContaining('only time'), findsOneWidget);
  });
}
