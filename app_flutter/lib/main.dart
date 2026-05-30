// SpoofVane SOC console — entrypoint.
import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'app.dart';

// When built with --dart-define=E2E=true, force-enable the semantics tree so
// Playwright (which drives the DOM) can see widget labels on the CanvasKit
// canvas. No effect on the normal production build.
const _e2e = bool.fromEnvironment('E2E', defaultValue: false);

void main() {
  if (_e2e) {
    SemanticsBinding.instance.ensureSemantics();
  }
  runApp(const SpoofVaneApp());
}
