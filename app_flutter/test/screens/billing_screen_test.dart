import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spoofvane_app/api.dart';
import 'package:spoofvane_app/screens/billing_screen.dart';
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

  testWidgets('shows current plan, payment method and invoices', (tester) async {
    await pumpScreen(tester, const BillingScreen());
    expect(find.byKey(const Key('billing-list')), findsOneWidget);
    expect(find.text('Business'), findsOneWidget);
    expect(find.textContaining('Visa'), findsOneWidget);
    expect(find.text('INV-2026-0042'), findsOneWidget);
  });

  testWidgets('invoices show paid status and a PDF action', (tester) async {
    await pumpScreen(tester, const BillingScreen());
    expect(find.text('paid'), findsWidgets);
    expect(find.byKey(const Key('invoice-download-INV-2026-0042')), findsOneWidget);
  });

  testWidgets('change plan opens the pricing screen', (tester) async {
    await pumpScreen(tester, const BillingScreen());
    await tester.tap(find.byKey(const Key('billing-change-plan')));
    await tester.pumpAndSettle();
    expect(find.byType(PricingScreen), findsOneWidget);
  });
}
