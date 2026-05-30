// Executive protection — per-exec doxxing/physical risk dossiers.
import 'package:flutter/material.dart';
import '../theme.dart';
import '../widgets/panel.dart';
import '../widgets/screen_title.dart';

class _Exec {
  final String name, role;
  final double risk;
  final List<String> exposed;
  const _Exec(this.name, this.role, this.risk, this.exposed);
}

class ExecScreen extends StatelessWidget {
  const ExecScreen({super.key});

  static const _execs = <_Exec>[
    _Exec('Jane Powell', 'CEO', 0.74, ['home_address', 'children_school']),
    _Exec('Raj Mehta', 'CFO', 0.41, ['personal_phone']),
  ];

  @override
  Widget build(BuildContext context) {
    return ListView(
      key: const Key('exec-list'),
      children: [
        const ScreenTitle('Executive Protection',
            sub: 'Doxxing · physical-threat · impersonation monitoring'),
        ..._execs.map((e) => Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: Panel(
                child: Row(
                  children: [
                    const CircleAvatar(
                        backgroundColor: SvColors.node,
                        child: Icon(Icons.person, color: SvColors.muted)),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('${e.name} · ${e.role}',
                              style: const TextStyle(
                                  color: SvColors.text, fontSize: 14)),
                          const SizedBox(height: 6),
                          Wrap(
                            spacing: 6,
                            children: e.exposed
                                .map((x) => Chip(
                                      label: Text(x,
                                          style: const TextStyle(fontSize: 10)),
                                      backgroundColor: SvColors.chipDanger,
                                      side: BorderSide.none,
                                    ))
                                .toList(),
                          ),
                        ],
                      ),
                    ),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        const Text('overall risk',
                            style: TextStyle(color: SvColors.faint, fontSize: 10)),
                        Text(e.risk.toStringAsFixed(2),
                            style: TextStyle(
                                color: e.risk > 0.6
                                    ? SvColors.phish
                                    : SvColors.amber,
                                fontSize: 20,
                                fontFamily: 'monospace')),
                      ],
                    ),
                  ],
                ),
              ),
            )),
      ],
    );
  }
}
