import 'package:flutter_test/flutter_test.dart';
import 'package:spoofvane_app/api.dart';
import 'package:spoofvane_app/app.dart';
import 'package:spoofvane_app/widgets/source_pill.dart';
import 'support/fake_api.dart';
import 'support/pump.dart';

void main() {
  late ApiClient original;
  setUp(() {
    original = Api.instance;
    Api.instance = FakeApi();
  });
  tearDown(() => Api.instance = original);

  testWidgets('boots on the dashboard with brand + LIVE pill', (tester) async {
    useDesktopSurface(tester);
    await tester.pumpWidget(const SpoofVaneApp());
    await tester.pumpAndSettle();
    expect(find.text('Security Dashboard'), findsOneWidget);
    expect(find.text('Dashboard'), findsWidgets); // nav rail label
    expect(find.byType(SourcePill), findsOneWidget);
    expect(find.text('LIVE'), findsOneWidget);
  });

  testWidgets('nav switches to the triage screen', (tester) async {
    useDesktopSurface(tester);
    await tester.pumpWidget(const SpoofVaneApp());
    await tester.pumpAndSettle();
    await tester.tap(find.text('Triage Queue'));
    await tester.pumpAndSettle();
    expect(find.text('3 alerts'), findsOneWidget);
  });

  testWidgets('SEED source renders the SEED pill', (tester) async {
    useDesktopSurface(tester);
    Api.instance = FakeApi(forcedSource: DataSource.seed);
    await tester.pumpWidget(const SpoofVaneApp());
    await tester.pumpAndSettle();
    expect(find.text('SEED'), findsOneWidget);
  });

  testWidgets('nav rail collapses and expands', (tester) async {
    useDesktopSurface(tester);
    await tester.pumpWidget(const SpoofVaneApp());
    await tester.pumpAndSettle();
    // Expanded: full label visible.
    expect(find.text('Campaign Clusters'), findsOneWidget);
    await tester.tap(find.byTooltip('Collapse'));
    await tester.pumpAndSettle();
    // Collapsed: labels leave the tree (icons only).
    expect(find.text('Campaign Clusters'), findsNothing);
    // Toggle back open.
    await tester.tap(find.byTooltip('Expand'));
    await tester.pumpAndSettle();
    expect(find.text('Campaign Clusters'), findsOneWidget);
  });
}
