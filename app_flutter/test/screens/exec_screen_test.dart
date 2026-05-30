import 'package:flutter_test/flutter_test.dart';
import 'package:spoofvane_app/screens/exec_screen.dart';
import '../support/pump.dart';

void main() {
  testWidgets('renders exec dossiers with risk + exposed items', (tester) async {
    await pumpScreen(tester, const ExecScreen());
    expect(find.text('Executive Protection'), findsOneWidget);
    expect(find.textContaining('Jane Powell'), findsOneWidget);
    expect(find.textContaining('home_address'), findsOneWidget);
    expect(find.text('0.74'), findsOneWidget);
  });
}
