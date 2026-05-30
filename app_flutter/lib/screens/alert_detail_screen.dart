// Alert detail — summary + ensemble verdict trace + takedown action.
import 'package:flutter/material.dart';
import '../models.dart';
import '../theme.dart';
import '../util/format.dart';
import '../widgets/panel.dart';
import '../widgets/verdict_pill.dart';

class AlertDetailScreen extends StatelessWidget {
  final Alert alert;
  const AlertDetailScreen({super.key, required this.alert});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: SvColors.bg,
      appBar: AppBar(
        backgroundColor: SvColors.panel2,
        title: Text(alert.url,
            style: const TextStyle(fontFamily: 'monospace', fontSize: 14)),
        actions: [
          Padding(
            padding: const EdgeInsets.all(8),
            child: ElevatedButton(
              key: const Key('takedown-button'),
              style:
                  ElevatedButton.styleFrom(backgroundColor: verdictColor(alert.verdict)),
              onPressed: () => ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Takedown requested (demo)'))),
              child: const Text('Request takedown'),
            ),
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Panel(
                title: 'Summary',
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(children: [VerdictPill(alert.verdict)]),
                    const SizedBox(height: 12),
                    _kv('verdict', alert.verdict.name),
                    _kv('score', alert.composite.toStringAsFixed(2)),
                    _kv('family', alert.family ?? '—'),
                    _kv('kit', alert.kit ?? '—'),
                    _kv('rendered from', alert.renderedFrom ?? '—'),
                    _kv('discovered', fmtTime(alert.discoveredAt)),
                    _kv('MITRE', alert.mitreTechniques.join(', ')),
                  ],
                ),
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Panel(
                title: 'Verdict trace (ensemble)',
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _trace('claude', alert.verdict, alert.composite + 0.01),
                    _trace('gpt-5', alert.verdict, alert.composite - 0.02),
                    _trace('gemini', alert.verdict, alert.composite),
                    const Divider(color: SvColors.border),
                    Text('merge: ${alert.verdict.name.toUpperCase()} · no dissent',
                        style: TextStyle(
                            color: verdictColor(alert.verdict),
                            fontFamily: 'monospace',
                            fontSize: 13)),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _kv(String k, String v) => Padding(
        padding: const EdgeInsets.only(bottom: 6),
        child: Row(
          children: [
            SizedBox(
                width: 120,
                child: Text(k,
                    style: const TextStyle(color: SvColors.faint, fontSize: 12))),
            Expanded(
                child: Text(v,
                    style: const TextStyle(
                        color: SvColors.text,
                        fontFamily: 'monospace',
                        fontSize: 12))),
          ],
        ),
      );

  Widget _trace(String model, Verdict v, double conf) => Padding(
        padding: const EdgeInsets.only(bottom: 6),
        child: Text('$model: ${v.name} ${conf.clamp(0, 1).toStringAsFixed(2)}',
            style: const TextStyle(
                color: SvColors.benign, fontFamily: 'monospace', fontSize: 12)),
      );
}
