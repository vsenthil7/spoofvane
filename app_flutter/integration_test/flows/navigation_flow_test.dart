// E2E flow: navigate every surface in the rail and assert each renders.
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

import '../support/harness.dart';
import '../pages/console_pages.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('every rail destination renders its screen', (tester) async {
    await bootApp(tester);
    final shell = ConsoleShell(tester);

    await shell.navigateTo('Campaign Clusters');
    expect(ClustersPage().root, findsOneWidget);

    await shell.navigateTo('Deepfake Feed');
    expect(DeepfakePage().root, findsOneWidget);

    await shell.navigateTo('Exec Protection');
    expect(ExecPage().root, findsOneWidget);

    await shell.navigateTo('Brand Management');
    expect(BrandsPage().root, findsOneWidget);
    expect(BrandsPage().brand('AcmeBank'), findsOneWidget);

    await shell.navigateTo('Cost Attribution');
    expect(CostPage().root, findsOneWidget);
    expect(CostPage().total, findsOneWidget);

    await shell.navigateTo('Audit Log');
    expect(AuditPage().root, findsOneWidget);
    expect(AuditPage().action('alert.triage'), findsOneWidget);

    // Rail collapse/expand works mid-session.
    await shell.collapseRail();
    expect(find.text('Audit Log'), findsNothing);
    await shell.expandRail();
    expect(find.text('Audit Log'), findsWidgets);
  });
}
