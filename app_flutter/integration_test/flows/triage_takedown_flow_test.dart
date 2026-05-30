// E2E flow: analyst triages an alert end-to-end.
// Dashboard -> Triage queue -> open a phishing alert -> inspect ensemble verdict
// -> request takedown -> return to the queue.
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

import '../support/harness.dart';
import '../pages/console_pages.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('analyst triages a phishing alert and requests takedown',
      (tester) async {
    await bootApp(tester);
    final shell = ConsoleShell(tester);
    final dashboard = DashboardPage();
    final triage = TriagePage(tester);
    final detail = AlertDetailPage(tester);

    // Lands on the dashboard, backend reachable.
    expect(dashboard.title, findsOneWidget);
    expect(shell.isLive, isTrue);

    // Go to the triage queue.
    await shell.navigateTo('Triage Queue');
    expect(triage.root, findsOneWidget);

    // Open the top phishing alert and inspect the verdict trace.
    await triage.openAlert('alert_seed_001');
    expect(detail.summary, findsOneWidget);
    expect(detail.ensembleTrace, findsOneWidget);

    // Request a takedown -> confirmation surfaces.
    await detail.requestTakedown();
    expect(find.textContaining('Takedown requested'), findsOneWidget);

    // Back to the queue.
    await detail.back();
    expect(triage.root, findsOneWidget);
  });
}
