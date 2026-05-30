// Smoke test: the console boots and shows the brand + nav.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spoofvane_app/main.dart';

void main() {
  testWidgets('console renders nav and brand', (tester) async {
    await tester.pumpWidget(const SpoofVaneApp());
    await tester.pump();
    expect(find.text('Dashboard'), findsWidgets);
    expect(find.text('Triage Queue'), findsWidgets);
    expect(find.text('Vane'), findsWidgets);
  });
}
