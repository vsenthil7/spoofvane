import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spoofvane_app/models.dart';
import 'package:spoofvane_app/theme.dart';
import 'package:spoofvane_app/widgets/verdict_pill.dart';

Future<void> _pump(WidgetTester t, Widget w) =>
    t.pumpWidget(MaterialApp(theme: buildSvTheme(), home: Scaffold(body: w)));

void main() {
  testWidgets('shows the verdict name', (tester) async {
    await _pump(tester, const VerdictPill(Verdict.phish));
    expect(find.text('phish'), findsOneWidget);
  });

  testWidgets('colour differs by verdict', (tester) async {
    expect(verdictColor(Verdict.phish), isNot(verdictColor(Verdict.benign)));
    expect(verdictColor(Verdict.suspicious), isNot(verdictColor(Verdict.unknown)));
  });

  test('verdictFrom parses all known strings + fallback', () {
    expect(verdictFrom('phish'), Verdict.phish);
    expect(verdictFrom('SUSPICIOUS'), Verdict.suspicious);
    expect(verdictFrom('benign'), Verdict.benign);
    expect(verdictFrom('garbage'), Verdict.unknown);
    expect(verdictFrom(null), Verdict.unknown);
  });
}
