import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spoofvane_app/models.dart';
import 'package:spoofvane_app/screens/brand_detail_screen.dart';
import 'package:spoofvane_app/theme.dart';
import '../support/pump.dart';

void main() {
  final brand = Brand(
    id: 'b1',
    name: 'Acme Bank',
    loginUrl: 'https://acme.example/login',
    targetCountry: 'GB',
    scoreThreshold: 0.72,
  );

  Future<void> pump(WidgetTester tester) async {
    useDesktopSurface(tester);
    await tester.pumpWidget(MaterialApp(
        theme: buildSvTheme(), home: BrandDetailScreen(brand: brand)));
    await tester.pumpAndSettle();
  }

  testWidgets('shows canonical brand fields', (tester) async {
    await pump(tester);
    expect(find.byKey(const Key('brand-detail-list')), findsOneWidget);
    expect(find.textContaining('acme.example/login'), findsOneWidget);
    expect(find.text('GB'), findsOneWidget);
  });

  testWidgets('shows the escalation threshold', (tester) async {
    await pump(tester);
    expect(find.text('0.72'), findsOneWidget);
    expect(find.textContaining('escalated'), findsOneWidget);
  });

  testWidgets('shows reference asset hashes', (tester) async {
    await pump(tester);
    expect(find.textContaining('Logo hash'), findsOneWidget);
    expect(find.textContaining('sha256:'), findsWidgets);
  });
}
