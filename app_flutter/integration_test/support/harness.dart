// Shared harness for integration_test flows. Boots the real SpoofVaneApp with an
// injected FakeApi (deterministic, no network) and a desktop-sized surface, so
// E2E flows exercise the genuine widget tree + navigation without a backend.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spoofvane_app/api.dart';
import 'package:spoofvane_app/app.dart';

// Reuse the unit-test FakeApi via a relative import into the test tree.
import '../../test/support/fake_api.dart';

const Size kDesktop = Size(1280, 800);

/// Boot the app for an E2E flow. [source] controls the LIVE/SEED pill.
Future<void> bootApp(WidgetTester tester,
    {DataSource source = DataSource.live}) async {
  Api.instance = FakeApi(forcedSource: source);
  tester.view.physicalSize = kDesktop;
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(const SpoofVaneApp());
  await tester.pumpAndSettle();
}
