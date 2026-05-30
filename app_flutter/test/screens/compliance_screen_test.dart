import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spoofvane_app/api.dart';
import 'package:spoofvane_app/screens/compliance_screen.dart';
import '../support/fake_api.dart';
import '../support/pump.dart';

void main() {
  late ApiClient original;
  setUp(() {
    original = Api.instance;
    Api.instance = FakeApi();
  });
  tearDown(() => Api.instance = original);

  testWidgets('groups controls by framework', (tester) async {
    await pumpScreen(tester, const ComplianceScreen());
    expect(find.byKey(const Key('compliance-list')), findsOneWidget);
    expect(find.text('SOC 2'), findsOneWidget);
    expect(find.text('ISO 27001'), findsOneWidget);
    expect(find.text('DORA'), findsOneWidget);
    expect(find.text('NIS2'), findsOneWidget);
  });

  testWidgets('renders control ids, titles and evidence', (tester) async {
    await pumpScreen(tester, const ComplianceScreen());
    expect(find.text('CC6.1'), findsOneWidget);
    expect(find.text('Logical access controls'), findsOneWidget);
    expect(find.textContaining('RBAC + SSO'), findsOneWidget);
  });

  testWidgets('shows status pills incl. a gap', (tester) async {
    await pumpScreen(tester, const ComplianceScreen());
    expect(find.text('met'), findsWidgets);
    expect(find.text('partial'), findsWidgets);
    expect(find.text('gap'), findsOneWidget); // NIS2 Art.21
  });

  testWidgets('header summarises frameworks and controls met', (tester) async {
    await pumpScreen(tester, const ComplianceScreen());
    // 4 frameworks; 5 of 8 controls met in seed.
    expect(find.textContaining('4 frameworks'), findsOneWidget);
    expect(find.textContaining('5/8 controls met'), findsOneWidget);
  });
}
