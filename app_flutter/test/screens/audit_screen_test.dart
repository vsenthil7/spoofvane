import 'package:flutter_test/flutter_test.dart';
import 'package:spoofvane_app/api.dart';
import 'package:spoofvane_app/screens/audit_screen.dart';
import '../support/fake_api.dart';
import '../support/pump.dart';

void main() {
  late ApiClient original;
  setUp(() {
    original = Api.instance;
    Api.instance = FakeApi();
  });
  tearDown(() => Api.instance = original);

  testWidgets('renders hash-chain rows', (tester) async {
    await pumpScreen(tester, const AuditScreen());
    expect(find.text('Audit Log'), findsOneWidget);
    expect(find.textContaining('alert.triage'), findsOneWidget);
    expect(find.textContaining('takedown.approve'), findsOneWidget);
    expect(find.textContaining('a1b2c3d4'), findsOneWidget);
  });
}
