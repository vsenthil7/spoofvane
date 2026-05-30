import 'package:flutter_test/flutter_test.dart';
import 'package:spoofvane_app/api.dart';
import 'package:spoofvane_app/screens/clusters_screen.dart';
import '../support/fake_api.dart';
import '../support/pump.dart';

void main() {
  late ApiClient original;
  setUp(() {
    original = Api.instance;
    Api.instance = FakeApi();
  });
  tearDown(() => Api.instance = original);

  testWidgets('renders campaigns with members', (tester) async {
    await pumpScreen(tester, const ClustersScreen());
    expect(find.text('Campaign #1'), findsOneWidget);
    expect(find.text('Campaign #2'), findsOneWidget);
    expect(find.textContaining('alert_seed_001'), findsOneWidget);
    expect(find.textContaining('2 members'), findsOneWidget);
  });
}
