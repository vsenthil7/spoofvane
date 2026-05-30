// Triage queue — clickable alert rows that open the detail screen.
import 'package:flutter/material.dart';
import '../api.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/panel.dart';
import '../widgets/screen_title.dart';
import '../widgets/verdict_pill.dart';
import 'alert_detail_screen.dart';

class TriageScreen extends StatefulWidget {
  const TriageScreen({super.key});
  @override
  State<TriageScreen> createState() => _TriageScreenState();
}

class _TriageScreenState extends State<TriageScreen> {
  late final Future<List<Alert>> _q = Api.instance.triageQueue();

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<Alert>>(
      future: _q,
      builder: (_, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        final rows = snap.data ?? [];
        return ListView(
          key: const Key('triage-list'),
          children: [
            ScreenTitle('Triage Queue', sub: '${rows.length} alerts'),
            Panel(
              child: Column(
                children: [
                  Row(
                    children: const [
                      SizedBox(width: 90, child: HeaderLabel('VERDICT')),
                      Expanded(child: HeaderLabel('URL')),
                      SizedBox(width: 60, child: HeaderLabel('SCORE')),
                      SizedBox(width: 90, child: HeaderLabel('FAMILY')),
                      SizedBox(width: 70, child: HeaderLabel('REGION')),
                    ],
                  ),
                  const Divider(color: SvColors.border),
                  ...rows.map((a) => InkWell(
                        key: Key('alert-row-${a.id}'),
                        onTap: () => Navigator.of(context).push(MaterialPageRoute(
                            builder: (_) => AlertDetailScreen(alert: a))),
                        child: Padding(
                          padding: const EdgeInsets.symmetric(vertical: 8),
                          child: Row(
                            children: [
                              SizedBox(width: 90, child: VerdictPill(a.verdict)),
                              Expanded(
                                child: Text(a.url,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(
                                        color: SvColors.text,
                                        fontFamily: 'monospace',
                                        fontSize: 12)),
                              ),
                              SizedBox(
                                  width: 60,
                                  child: Text(a.composite.toStringAsFixed(2),
                                      style: const TextStyle(
                                          color: SvColors.muted,
                                          fontFamily: 'monospace',
                                          fontSize: 12))),
                              SizedBox(
                                  width: 90,
                                  child: Text(a.family ?? '—',
                                      style: const TextStyle(
                                          color: SvColors.muted, fontSize: 12))),
                              SizedBox(
                                  width: 70,
                                  child: Text(a.renderedFrom ?? '—',
                                      style: const TextStyle(
                                          color: SvColors.muted, fontSize: 12))),
                            ],
                          ),
                        ),
                      )),
                ],
              ),
            ),
          ],
        );
      },
    );
  }
}
