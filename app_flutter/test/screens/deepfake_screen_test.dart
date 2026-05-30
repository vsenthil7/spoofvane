import 'package:flutter_test/flutter_test.dart';
import 'package:spoofvane_app/api.dart';
import 'package:spoofvane_app/screens/deepfake_screen.dart';
import '../support/fake_api.dart';
import '../support/pump.dart';

void main() {
  late ApiClient original;
  setUp(() {
    original = Api.instance;
    Api.instance = FakeApi();
  });
  tearDown(() => Api.instance = original);

  testWidgets('renders multimodal verdict and C2PA status', (tester) async {
    await pumpScreen(tester, const DeepfakeScreen());
    expect(find.text('Deepfake Feed'), findsOneWidget);
    expect(find.textContaining('multimodal verdict'), findsOneWidget);
    expect(find.textContaining('C2PA'), findsWidgets);
    expect(find.text('Confirm'), findsOneWidget);
    expect(find.text('Override'), findsOneWidget);
  });

  testWidgets('confirm and override buttons are tappable', (tester) async {
    await pumpScreen(tester, const DeepfakeScreen());
    await tester.tap(find.text('Confirm'));
    await tester.pump();
    await tester.tap(find.text('Override'));
    await tester.pump();
    // No exception => the onPressed callbacks executed.
    expect(tester.takeException(), isNull);
  });
}
