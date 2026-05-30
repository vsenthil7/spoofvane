// P18 — Admin · Demo health. Internal screen showing seed completeness and the
// 21-page coverage status. Each row is a check with an ok/fail badge + detail.
import 'package:flutter/material.dart';
import '../api.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/panel.dart';
import '../widgets/screen_title.dart';

class AdminDemoHealthScreen extends StatelessWidget {
  const AdminDemoHealthScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<DemoHealthRow>>(
      future: Api.instance.demoHealth(),
      builder: (_, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        final rows = snap.data ?? [];
        final ok = rows.where((r) => r.ok).length;
        return ListView(
          key: const Key('demo-health-list'),
          children: [
            ScreenTitle('Demo health',
                sub: '$ok/${rows.length} checks passing'),
            Panel(
              child: Column(
                children: [
                  for (final r in rows) _checkRow(r),
                ],
              ),
            ),
          ],
        );
      },
    );
  }

  Widget _checkRow(DemoHealthRow r) {
    return Padding(
      key: Key('demo-health-row-${r.check.replaceAll(' ', '-')}'),
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          Icon(r.ok ? Icons.check_circle : Icons.cancel,
              size: 16, color: r.ok ? SvColors.benign : SvColors.amber),
          const SizedBox(width: 10),
          SizedBox(
              width: 220,
              child: Text(r.check,
                  style: const TextStyle(color: SvColors.text, fontSize: 13))),
          Expanded(
              child: Text(r.detail,
                  style: const TextStyle(color: SvColors.muted, fontSize: 12))),
        ],
      ),
    );
  }
}
