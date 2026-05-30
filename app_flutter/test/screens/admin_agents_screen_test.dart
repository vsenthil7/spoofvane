import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spoofvane_app/api.dart';
import 'package:spoofvane_app/screens/admin_agents_screen.dart';
import '../support/fake_api.dart';
import '../support/pump.dart';

void main() {
  late ApiClient original;
  setUp(() {
    original = Api.instance;
    Api.instance = FakeApi();
  });
  tearDown(() => Api.instance = original);

  testWidgets('lists agents with state and runs', (tester) async {
    await pumpScreen(tester, const AdminAgentsScreen());
    expect(find.byKey(const Key('agents-list')), findsOneWidget);
    expect(find.text('discovery'), findsOneWidget);
    expect(find.text('inspector'), findsOneWidget);
    // discovery is running in seed.
    expect(find.byKey(const Key('agent-state-ag_discovery')), findsOneWidget);
  });

  testWidgets('header counts running agents', (tester) async {
    await pumpScreen(tester, const AdminAgentsScreen());
    // 3 of 4 running in seed.
    expect(find.textContaining('4 registered'), findsOneWidget);
    expect(find.textContaining('3 running'), findsOneWidget);
  });

  testWidgets('kill-switch halts all running agents', (tester) async {
    await pumpScreen(tester, const AdminAgentsScreen());
    await tester.tap(find.byKey(const Key('agents-killswitch')));
    await tester.pumpAndSettle();
    expect(find.textContaining('Kill-switch ENGAGED'), findsOneWidget);
    expect(find.textContaining('0 running'), findsOneWidget);
    // A previously-running agent now shows halted.
    expect(find.text('halted'), findsWidgets);
  });

  testWidgets('kill-switch can be re-enabled', (tester) async {
    await pumpScreen(tester, const AdminAgentsScreen());
    await tester.tap(find.byKey(const Key('agents-killswitch')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('agents-killswitch')));
    await tester.pumpAndSettle();
    expect(find.textContaining('3 running'), findsOneWidget);
  });
}
