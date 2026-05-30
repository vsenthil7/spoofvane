// Driver entrypoint for `flutter drive` browser runs of the integration_test
// flows. Run against Chrome with:
//
//   flutter drive \
//     --driver=test_driver/integration_test.dart \
//     --target=integration_test/flows/<flow>_test.dart \
//     -d chrome
//
// (Requires chromedriver on PATH, started with: chromedriver --port=4444)
import 'package:integration_test/integration_test_driver.dart';

Future<void> main() => integrationDriver();
