import 'package:flutter_test/flutter_test.dart';
import 'package:spoofvane_app/api.dart';
import 'package:spoofvane_app/screens/dashboard_screen.dart';
import '../support/fake_api.dart';
import '../support/pump.dart';

void main() {
  late ApiClient original;
  setUp(() {
    original = Api.instance;
    Api.instance = FakeApi();
  });
  tearDown(() => Api.instance = original);

  testWidgets('renders KPIs and recent alerts from the API', (tester) async {
    await pumpScreen(tester, const DashboardScreen());
    expect(find.text('Security Dashboard'), findsOneWidget);
    expect(find.text('Total Alerts'), findsOneWidget);
    // 4 seed alerts -> total card shows 4.
    expect(find.text('4'), findsWidgets);
    // A known seed URL appears in the recent-alerts panel.
    expect(find.textContaining('acmebank-secure-login.top'), findsWidgets);
  });
}
