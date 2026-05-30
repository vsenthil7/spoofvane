import 'package:flutter_test/flutter_test.dart';
import 'package:spoofvane_app/api.dart';
import 'package:spoofvane_app/screens/cost_screen.dart';
import '../support/fake_api.dart';
import '../support/pump.dart';

void main() {
  late ApiClient original;
  setUp(() {
    original = Api.instance;
    Api.instance = FakeApi();
  });
  tearDown(() => Api.instance = original);

  testWidgets('renders per-product spend and total vs envelope', (tester) async {
    await pumpScreen(tester, const CostScreen());
    expect(find.text('Cost Attribution'), findsOneWidget);
    expect(find.text('serp'), findsOneWidget);
    expect(find.text('scraping_browser'), findsOneWidget);
    // total of seed cost rows = 4.21+9.84+12.50+6.10 = 32.65
    expect(find.textContaining('\$32.65 / \$500.00'), findsOneWidget);
  });
}
