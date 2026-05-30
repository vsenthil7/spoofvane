// Dashboard — KPIs, top targeted brands, recent alerts.
import 'package:flutter/material.dart';
import '../api.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/panel.dart';
import '../widgets/screen_title.dart';
import '../widgets/stat_card.dart';
import '../widgets/verdict_pill.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});
  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  late final Future<List<Alert>> _alerts = Api.instance.alerts();

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<Alert>>(
      future: _alerts,
      builder: (_, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        final alerts = snap.data ?? [];
        final open = alerts.where((a) => a.verdict != Verdict.benign).length;
        final df = alerts.where((a) => a.family == 'deepfake').length;
        return ListView(
          key: const Key('dashboard-list'),
          children: [
            const ScreenTitle('Security Dashboard',
                sub: 'Enterprise · Real-time threat visibility'),
            Wrap(
              spacing: 16,
              runSpacing: 16,
              children: [
                StatCard('Total Alerts', '${alerts.length}'),
                StatCard('Open Alerts', '$open'),
                StatCard('Deepfakes 24h', '$df'),
                StatCard('Active Clusters', '2'),
                StatCard('Takedown Rate', '74%'),
              ],
            ),
            const SizedBox(height: 20),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Expanded(
                  child: Panel(
                    title: 'Top Targeted Brands',
                    child: Column(
                      children: [
                        _BarRow('AcmeBank', 0.83, '83'),
                        SizedBox(height: 10),
                        _BarRow('Globex', 0.41, '41'),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Panel(
                    title: 'Recent Alerts',
                    child: Column(
                      children: alerts
                          .take(4)
                          .map((a) => Padding(
                                padding: const EdgeInsets.only(bottom: 8),
                                child: Row(
                                  children: [
                                    VerdictPill(a.verdict),
                                    const SizedBox(width: 10),
                                    Expanded(
                                      child: Text(a.url,
                                          overflow: TextOverflow.ellipsis,
                                          style: const TextStyle(
                                              color: SvColors.text,
                                              fontFamily: 'monospace',
                                              fontSize: 12)),
                                    ),
                                    Text(a.composite.toStringAsFixed(2),
                                        style: const TextStyle(
                                            color: SvColors.muted,
                                            fontFamily: 'monospace',
                                            fontSize: 12)),
                                  ],
                                ),
                              ))
                          .toList(),
                    ),
                  ),
                ),
              ],
            ),
          ],
        );
      },
    );
  }
}

class _BarRow extends StatelessWidget {
  final String label;
  final double frac;
  final String value;
  const _BarRow(this.label, this.frac, this.value);
  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        SizedBox(
            width: 80,
            child: Text(label,
                style: const TextStyle(color: SvColors.text, fontSize: 12))),
        Expanded(
          child: ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: frac,
              minHeight: 8,
              backgroundColor: SvColors.bg,
              valueColor: const AlwaysStoppedAnimation(SvColors.cyan),
            ),
          ),
        ),
        const SizedBox(width: 10),
        Text(value,
            style: const TextStyle(
                color: SvColors.muted, fontFamily: 'monospace', fontSize: 12)),
      ],
    );
  }
}
