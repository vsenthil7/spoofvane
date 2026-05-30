import 'package:flutter_test/flutter_test.dart';
import 'package:spoofvane_app/api.dart';
import 'package:spoofvane_app/screens/brands_screen.dart';
import '../support/fake_api.dart';
import '../support/pump.dart';

void main() {
  late ApiClient original;
  setUp(() {
    original = Api.instance;
    Api.instance = FakeApi();
  });
  tearDown(() => Api.instance = original);

  testWidgets('lists brands with login url and threshold', (tester) async {
    await pumpScreen(tester, const BrandsScreen());
    expect(find.text('AcmeBank'), findsOneWidget);
    expect(find.text('Globex'), findsOneWidget);
    expect(find.textContaining('acmebank.com/login'), findsOneWidget);
    expect(find.textContaining('US · thr'), findsOneWidget);
  });
}
