import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spoofvane_app/api.dart';
import 'package:spoofvane_app/screens/pricing_screen.dart';
import '../support/fake_api.dart';
import '../support/pump.dart';

void main() {
  late ApiClient original;
  setUp(() {
    original = Api.instance;
    Api.instance = FakeApi();
  });
  tearDown(() => Api.instance = original);

  testWidgets('renders all four plan cards', (tester) async {
    await pumpScreen(tester, const PricingScreen());
    expect(find.byKey(const Key('pricing-card-free')), findsOneWidget);
    expect(find.byKey(const Key('pricing-card-pro')), findsOneWidget);
    expect(find.byKey(const Key('pricing-card-business')), findsOneWidget);
    expect(find.byKey(const Key('pricing-card-enterprise')), findsOneWidget);
  });

  testWidgets('business is the highlighted most-popular plan', (tester) async {
    await pumpScreen(tester, const PricingScreen());
    expect(find.text('MOST POPULAR'), findsOneWidget);
  });

  testWidgets('shows annual price by default and toggles to monthly',
      (tester) async {
    await pumpScreen(tester, const PricingScreen());
    // Pro annual = $499/mo.
    expect(find.text('\$499'), findsOneWidget);
    await tester.tap(find.byKey(const Key('pricing-toggle-monthly')));
    await tester.pumpAndSettle();
    // Pro monthly = $599/mo.
    expect(find.text('\$599'), findsOneWidget);
  });

  testWidgets('enterprise is custom-priced with contact CTA', (tester) async {
    await pumpScreen(tester, const PricingScreen());
    expect(find.text('Custom'), findsOneWidget);
    expect(find.byKey(const Key('pricing-cta-enterprise')), findsOneWidget);
    expect(find.text('Contact sales'), findsOneWidget);
  });
}
