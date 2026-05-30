// Small formatting helpers shared across screens.
import 'package:intl/intl.dart';

String fmtTime(String iso) {
  try {
    return DateFormat('MMM d, HH:mm').format(DateTime.parse(iso).toLocal());
  } catch (_) {
    return iso;
  }
}
