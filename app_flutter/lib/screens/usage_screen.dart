// P24 — Usage. Metered consumption this billing period against plan allowances,
// with progress bars, overage flags, and an unlimited indicator. The kind of
// page every metered SaaS shows so customers can see where they stand.
import 'package:flutter/material.dart';
import '../api.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/panel.dart';
import '../widgets/screen_title.dart';

class UsageScreen extends StatelessWidget {
  const UsageScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<UsageMetric>>(
      future: Api.instance.usage(),
      builder: (_, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        final metrics = snap.data ?? [];
        final overages = metrics.where((m) => m.overage).length;
        return ListView(
          key: const Key('usage-list'),
          children: [
            ScreenTitle('Usage',
                sub:
                    'Current billing period · ${metrics.length} metered resources${overages > 0 ? ' · $overages over limit' : ''}'),
            Panel(
              child: Column(
                children: [
                  for (final m in metrics) _metricRow(m),
                ],
              ),
            ),
            const SizedBox(height: 8),
            const Text(
                'Usage resets at the start of each billing period. Overages on metered resources are billed at your plan rate.',
                style: TextStyle(color: SvColors.faint, fontSize: 11)),
          ],
        );
      },
    );
  }

  Widget _metricRow(UsageMetric m) {
    final pct = (m.ratio * 100).round();
    final barColor = m.overage
        ? SvColors.phish
        : m.ratio > 0.8
            ? SvColors.amber
            : SvColors.cyan;
    String fmt(double v) =>
        m.unit == 'USD' ? '\$${v.toStringAsFixed(2)}' : v.toStringAsFixed(0);
    final allowance = m.unlimited ? 'unlimited' : fmt(m.included);
    return Padding(
      key: Key('usage-row-${m.name.replaceAll(' ', '-')}'),
      padding: const EdgeInsets.symmetric(vertical: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(m.name,
                    style: const TextStyle(color: SvColors.text, fontSize: 13)),
              ),
              Text('${fmt(m.used)} / $allowance',
                  style: TextStyle(
                      color: m.overage ? SvColors.phish : SvColors.muted,
                      fontSize: 12,
                      fontWeight: FontWeight.w600)),
              if (m.overage) ...[
                const SizedBox(width: 8),
                const Text('OVER',
                    style: TextStyle(
                        color: SvColors.phish,
                        fontSize: 9,
                        fontWeight: FontWeight.bold)),
              ],
              if (m.unlimited) ...[
                const SizedBox(width: 8),
                const Icon(Icons.all_inclusive, size: 14, color: SvColors.benign),
              ],
            ],
          ),
          const SizedBox(height: 6),
          ClipRRect(
            borderRadius: BorderRadius.circular(3),
            child: LinearProgressIndicator(
              value: m.unlimited ? 0.04 : m.ratio,
              minHeight: 6,
              backgroundColor: SvColors.bg,
              valueColor: AlwaysStoppedAnimation(
                  m.unlimited ? SvColors.benign : barColor),
            ),
          ),
          if (!m.unlimited) ...[
            const SizedBox(height: 3),
            Text('$pct% of allowance used',
                style: const TextStyle(color: SvColors.faint, fontSize: 10)),
          ],
        ],
      ),
    );
  }
}
