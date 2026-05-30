// KPI stat card used on the dashboard. Uses a min-height (not a rigid height) so
// it never overflows when text metrics vary across platforms / text scales.
import 'package:flutter/material.dart';
import '../theme.dart';

class StatCard extends StatelessWidget {
  final String label;
  final String value;
  const StatCard(this.label, this.value, {super.key});

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: '$label $value',
      child: Container(
        width: 150,
        constraints: const BoxConstraints(minHeight: 76),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: SvColors.panel,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: SvColors.border),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label,
                style: const TextStyle(color: SvColors.faint, fontSize: 10)),
            const SizedBox(height: 12),
            Text(
              value,
              style: const TextStyle(
                  color: SvColors.amber, fontSize: 22, fontFamily: 'monospace'),
            ),
          ],
        ),
      ),
    );
  }
}
