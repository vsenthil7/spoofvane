// P14 — Compliance. SOC 2 / ISO 27001 / DORA / NIS2 control status and evidence
// — "what auditors read." Controls are grouped by framework; each shows a status
// pill (met / partial / gap / n/a) and a short evidence reference. A per-framework
// readiness bar summarises how many controls are met.
import 'package:flutter/material.dart';
import '../api.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/panel.dart';
import '../widgets/screen_title.dart';

class ComplianceScreen extends StatelessWidget {
  const ComplianceScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<ComplianceControl>>(
      future: Api.instance.compliance(),
      builder: (_, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        final rows = snap.data ?? [];
        final byFramework = <String, List<ComplianceControl>>{};
        for (final c in rows) {
          byFramework.putIfAbsent(c.framework, () => []).add(c);
        }
        final met = rows.where((c) => c.status == ControlStatus.met).length;
        return ListView(
          key: const Key('compliance-list'),
          children: [
            ScreenTitle('Compliance',
                sub:
                    '${byFramework.length} frameworks · $met/${rows.length} controls met'),
            for (final e in byFramework.entries) _frameworkPanel(e.key, e.value),
          ],
        );
      },
    );
  }

  Widget _frameworkPanel(String framework, List<ComplianceControl> controls) {
    final met = controls.where((c) => c.status == ControlStatus.met).length;
    final ratio = controls.isEmpty ? 0.0 : met / controls.length;
    return Panel(
      key: Key('compliance-framework-${framework.replaceAll(' ', '-')}'),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(framework,
                    style: const TextStyle(
                        color: SvColors.text,
                        fontSize: 14,
                        fontWeight: FontWeight.bold)),
              ),
              Text('$met/${controls.length} met',
                  style: const TextStyle(color: SvColors.muted, fontSize: 11)),
            ],
          ),
          const SizedBox(height: 8),
          ClipRRect(
            borderRadius: BorderRadius.circular(3),
            child: LinearProgressIndicator(
              value: ratio,
              minHeight: 6,
              backgroundColor: SvColors.bg,
              valueColor: AlwaysStoppedAnimation(
                  ratio == 1.0 ? SvColors.benign : SvColors.cyan),
            ),
          ),
          const SizedBox(height: 12),
          const Divider(color: SvColors.border),
          ...controls.map(_controlRow),
        ],
      ),
    );
  }

  Widget _controlRow(ComplianceControl c) {
    return Padding(
      key: Key('compliance-control-${c.framework.replaceAll(' ', '-')}-${c.controlId}'),
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
              width: 80,
              child: Text(c.controlId,
                  style: const TextStyle(
                      color: SvColors.text,
                      fontFamily: 'monospace',
                      fontSize: 12,
                      fontWeight: FontWeight.w600))),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(c.title,
                    style: const TextStyle(color: SvColors.text, fontSize: 12)),
                Text(c.evidence,
                    style: const TextStyle(color: SvColors.faint, fontSize: 11)),
              ],
            ),
          ),
          const SizedBox(width: 8),
          _statusPill(c),
        ],
      ),
    );
  }

  Widget _statusPill(ComplianceControl c) {
    final color = controlStatusColor(c.status);
    final label = switch (c.status) {
      ControlStatus.met => 'met',
      ControlStatus.partial => 'partial',
      ControlStatus.gap => 'gap',
      ControlStatus.notApplicable => 'n/a',
    };
    return Container(
      key: Key('compliance-status-${c.framework.replaceAll(' ', '-')}-${c.controlId}'),
      width: 70,
      padding: const EdgeInsets.symmetric(vertical: 3),
      decoration: BoxDecoration(
        color: color.withOpacity(0.14),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: color.withOpacity(0.5)),
      ),
      child: Text(label,
          textAlign: TextAlign.center,
          style:
              TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w600)),
    );
  }
}
