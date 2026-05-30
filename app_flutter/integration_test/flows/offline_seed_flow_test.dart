// E2E flow: when the backend is unreachable the app still renders every screen
// from seed data and the SEED pill is shown — the honest offline-demo path.
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:spoofvane_app/api.dart';

import '../support/harness.dart';
import '../pages/console_pages.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('offline (SEED) mode renders all surfaces with the SEED pill',
      (tester) async {
    await bootApp(tester, source: DataSource.seed);
    final shell = ConsoleShell(tester);

    expect(shell.isSeed, isTrue);
    expect(DashboardPage().title, findsOneWidget);

    await shell.navigateTo('Triage Queue');
    expect(TriagePage(tester).root, findsOneWidget);
    // Still SEED after navigation.
    expect(shell.isSeed, isTrue);

    await shell.navigateTo('Cost Attribution');
    expect(CostPage().total, findsOneWidget);
  });
}
