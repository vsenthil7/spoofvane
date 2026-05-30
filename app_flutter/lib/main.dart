// SpoofVane SOC console — entrypoint.
import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';
import 'app.dart';

// When built with --dart-define=E2E=true, force-enable the semantics tree so
// Playwright (which drives the DOM) can see widget labels on the CanvasKit
// canvas. No effect on the normal production build.
const _e2e = bool.fromEnvironment('E2E', defaultValue: false);

void main() {
  final binding = WidgetsFlutterBinding.ensureInitialized();
  if (_e2e) {
    // Build the semantic DOM eagerly (and keep it alive) so a DOM-driving E2E
    // harness never has to click the "Enable accessibility" placeholder.
    binding.ensureSemantics();
    // ensureSemantics holds a handle for one frame; re-assert after first paint
    // so the tree persists for the whole session.
    binding.addPostFrameCallback((_) => binding.ensureSemantics());
    SchedulerBinding.instance.scheduleFrame();
  }
  runApp(const SpoofVaneApp());
}
