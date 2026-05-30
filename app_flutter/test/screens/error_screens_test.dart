import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spoofvane_app/screens/error_screens.dart';
import '../support/pump.dart';

void main() {
  testWidgets('404 screen shows not-found copy', (tester) async {
    await pumpScreen(tester, const NotFoundScreen());
    expect(find.byKey(const Key('notfound-screen')), findsOneWidget);
    expect(find.text('404'), findsOneWidget);
    expect(find.text('Page not found'), findsOneWidget);
  });

  testWidgets('403 screen shows forbidden copy', (tester) async {
    await pumpScreen(tester, const ForbiddenScreen());
    expect(find.byKey(const Key('forbidden-screen')), findsOneWidget);
    expect(find.text('403'), findsOneWidget);
    expect(find.text('Access forbidden'), findsOneWidget);
    expect(find.textContaining('role does not have access'), findsOneWidget);
  });
}
