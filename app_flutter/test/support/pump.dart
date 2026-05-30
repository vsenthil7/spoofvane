// Shared pump helpers. Sets a desktop-sized test surface (1280x800, matching the
// product mockups) so wide SOC layouts don't overflow the default 800x600 test
// window, and wraps screens in MaterialApp for Directionality/theme/Navigator.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spoofvane_app/theme.dart';

const Size kDesktop = Size(1280, 800);

void useDesktopSurface(WidgetTester tester) {
  tester.view.physicalSize = kDesktop;
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

Future<void> pumpScreen(WidgetTester tester, Widget screen) async {
  useDesktopSurface(tester);
  await tester.pumpWidget(MaterialApp(
    theme: buildSvTheme(),
    home: Scaffold(body: screen),
  ));
  await tester.pumpAndSettle();
}
