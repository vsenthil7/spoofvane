import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spoofvane_app/api.dart';
import 'package:spoofvane_app/screens/brands_screen.dart';
import 'package:spoofvane_app/screens/brand_detail_screen.dart';
import '../support/fake_api.dart';
import '../support/pump.dart';

void main() {
  late ApiClient original;
  setUp(() {
    original = Api.instance;
    Api.instance = FakeApi();
  });
  tearDown(() => Api.instance = original);

  testWidgets('lists brands with login url and threshold', (tester) async {
    await pumpScreen(tester, const BrandsScreen());
    expect(find.text('AcmeBank'), findsOneWidget);
    expect(find.text('Globex'), findsOneWidget);
    expect(find.textContaining('acmebank.com/login'), findsOneWidget);
    expect(find.textContaining('US · thr'), findsOneWidget);
  });

  testWidgets('tapping a brand opens its detail', (tester) async {
    await pumpScreen(tester, const BrandsScreen());
    await tester.tap(find.byKey(const Key('brand-row-brand_acmebank')));
    await tester.pumpAndSettle();
    expect(find.byType(BrandDetailScreen), findsOneWidget);
    expect(find.textContaining('Score threshold'), findsOneWidget);
  });
}
