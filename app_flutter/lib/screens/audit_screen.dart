// Audit log — tamper-evident hash-chain rows.
import 'package:flutter/material.dart';
import '../api.dart';
import '../models.dart';
import '../theme.dart';
import '../util/format.dart';
import '../widgets/panel.dart';
import '../widgets/screen_title.dart';

class AuditScreen extends StatefulWidget {
  const AuditScreen({super.key});
  @override
  State<AuditScreen> createState() => _AuditScreenState();
}

class _AuditScreenState extends State<AuditScreen> {
  late final Future<List<AuditRow>> _a = Api.instance.audit();

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<AuditRow>>(
      future: _a,
      builder: (_, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        final rows = snap.data ?? [];
        return ListView(
          key: const Key('audit-list'),
          children: [
            const ScreenTitle('Audit Log', sub: 'Tamper-evident hash chain'),
            Panel(
              child: Column(
                children: [
                  Row(
                    children: const [
                      SizedBox(width: 40, child: HeaderLabel('SEQ')),
                      SizedBox(width: 90, child: HeaderLabel('ROLE')),
                      Expanded(child: HeaderLabel('ACTION')),
                      SizedBox(width: 60, child: HeaderLabel('OUTCOME')),
                      SizedBox(width: 140, child: HeaderLabel('TIME')),
                      SizedBox(width: 90, child: HeaderLabel('HASH')),
                    ],
                  ),
                  const Divider(color: SvColors.border),
                  ...rows.map((r) => Padding(
                        padding: const EdgeInsets.symmetric(vertical: 8),
                        child: Row(
                          children: [
                            SizedBox(
                                width: 40,
                                child: Text('${r.seq}',
                                    style: const TextStyle(
                                        color: SvColors.muted,
                                        fontFamily: 'monospace',
                                        fontSize: 12))),
                            SizedBox(
                                width: 90,
                                child: Text(r.actorRole,
                                    style: const TextStyle(
                                        color: SvColors.muted, fontSize: 12))),
                            Expanded(
                                child: Text(r.action,
                                    style: const TextStyle(
                                        color: SvColors.text,
                                        fontFamily: 'monospace',
                                        fontSize: 12))),
                            SizedBox(
                                width: 60,
                                child: Text(r.outcome,
                                    style: const TextStyle(
                                        color: SvColors.benign, fontSize: 12))),
                            SizedBox(
                                width: 140,
                                child: Text(fmtTime(r.ts),
                                    style: const TextStyle(
                                        color: SvColors.muted, fontSize: 11))),
                            SizedBox(
                                width: 90,
                                child: Text(r.hash,
                                    style: const TextStyle(
                                        color: SvColors.faint,
                                        fontFamily: 'monospace',
                                        fontSize: 11))),
                          ],
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
