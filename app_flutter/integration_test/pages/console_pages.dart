// Page objects for the SpoofVane console E2E flows. Each object encapsulates the
// finders + actions for one surface, so flow specs stay declarative and don't
// hard-code widget lookups. Navigation goes through the rail like a real user.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

/// Shell-level actions: rail navigation + the LIVE/SEED pill.
class ConsoleShell {
  final WidgetTester tester;
  ConsoleShell(this.tester);

  Future<void> navigateTo(String navLabel) async {
    await tester.tap(find.text(navLabel).first);
    await tester.pumpAndSettle();
  }

  Future<void> collapseRail() async {
    await tester.tap(find.byTooltip('Collapse'));
    await tester.pumpAndSettle();
  }

  Future<void> expandRail() async {
    await tester.tap(find.byTooltip('Expand'));
    await tester.pumpAndSettle();
  }

  bool get isLive => find.text('LIVE').evaluate().isNotEmpty;
  bool get isSeed => find.text('SEED').evaluate().isNotEmpty;
}

class DashboardPage {
  Finder get root => find.byKey(const Key('dashboard-list'));
  Finder get title => find.text('Security Dashboard');
  Finder statCard(String label) => find.text(label);
}

class TriagePage {
  final WidgetTester tester;
  TriagePage(this.tester);

  Finder get root => find.byKey(const Key('triage-list'));
  Finder row(String alertId) => find.byKey(Key('alert-row-$alertId'));

  Future<void> openAlert(String alertId) async {
    await tester.tap(row(alertId));
    await tester.pumpAndSettle();
  }
}

class AlertDetailPage {
  final WidgetTester tester;
  AlertDetailPage(this.tester);

  Finder get summary => find.text('Summary');
  Finder get ensembleTrace => find.text('Verdict trace (ensemble)');
  Finder get takedownButton => find.byKey(const Key('takedown-button'));

  Future<void> requestTakedown() async {
    await tester.tap(takedownButton);
    await tester.pump();
  }

  Future<void> back() async {
    await tester.pageBack();
    await tester.pumpAndSettle();
  }
}

class ClustersPage {
  Finder get root => find.byKey(const Key('clusters-list'));
  Finder campaign(int id) => find.text('Campaign #$id');
}

class DeepfakePage {
  Finder get root => find.byKey(const Key('deepfake-list'));
  Finder get confirm => find.text('Confirm');
  Finder get override => find.text('Override');
}

class CostPage {
  Finder get root => find.byKey(const Key('cost-list'));
  Finder get total => find.textContaining('/ \$500.00');
}

class AuditPage {
  Finder get root => find.byKey(const Key('audit-list'));
  Finder action(String action) => find.textContaining(action);
}

class BrandsPage {
  Finder get root => find.byKey(const Key('brands-list'));
  Finder brand(String name) => find.text(name);
}

class ExecPage {
  Finder get root => find.byKey(const Key('exec-list'));
}
