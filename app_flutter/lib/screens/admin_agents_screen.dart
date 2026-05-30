// P15 — Admin · Agents. The agent registry with governance budgets and the
// kill-switch (global) that hard-halts every running agent. Each row shows the
// agent, its tenant, running state, runs today, and a budget bar (spent/budget).
import 'package:flutter/material.dart';
import '../api.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/panel.dart';
import '../widgets/screen_title.dart';

class AdminAgentsScreen extends StatefulWidget {
  const AdminAgentsScreen({super.key});
  @override
  State<AdminAgentsScreen> createState() => _AdminAgentsScreenState();
}

class _AdminAgentsScreenState extends State<AdminAgentsScreen> {
  final Future<List<Agent>> _q = Api.instance.agents();
  bool _killed = false; // global kill-switch engaged

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<Agent>>(
      future: _q,
      builder: (_, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        final agents = snap.data ?? [];
        final running =
            _killed ? 0 : agents.where((a) => a.running).length;
        return ListView(
          key: const Key('agents-list'),
          children: [
            ScreenTitle('Agents',
                sub: '${agents.length} registered · $running running'),
            _killSwitchPanel(running),
            Panel(
              child: Column(
                children: [
                  const Row(children: [
                    SizedBox(width: 150, child: HeaderLabel('AGENT')),
                    SizedBox(width: 100, child: HeaderLabel('TENANT')),
                    SizedBox(width: 95, child: HeaderLabel('STATE')),
                    SizedBox(width: 60, child: HeaderLabel('RUNS')),
                    Expanded(child: HeaderLabel('BUDGET')),
                  ]),
                  const Divider(color: SvColors.border),
                  ...agents.map(_agentRow),
                ],
              ),
            ),
          ],
        );
      },
    );
  }

  Widget _killSwitchPanel(int running) {
    return Panel(
      child: Row(
        children: [
          Icon(_killed ? Icons.dangerous : Icons.power_settings_new,
              color: _killed ? SvColors.phish : SvColors.amber, size: 28),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(_killed ? 'Kill-switch ENGAGED' : 'Global kill-switch',
                    style: TextStyle(
                        color: _killed ? SvColors.phish : SvColors.text,
                        fontSize: 14,
                        fontWeight: FontWeight.bold)),
                Text(
                    _killed
                        ? 'All agents hard-halted. Re-enable to resume.'
                        : 'Hard-halt every running agent across all tenants.',
                    style: const TextStyle(color: SvColors.muted, fontSize: 11)),
              ],
            ),
          ),
          ElevatedButton(
            key: const Key('agents-killswitch'),
            style: ElevatedButton.styleFrom(
                backgroundColor: _killed ? SvColors.benign : SvColors.phish,
                foregroundColor: const Color(0xFF0B0F17)),
            onPressed: () => setState(() => _killed = !_killed),
            child: Text(_killed ? 'Re-enable agents' : 'Engage kill-switch',
                style: const TextStyle(fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  Widget _agentRow(Agent a) {
    final running = a.running && !_killed;
    return Padding(
      key: Key('agent-row-${a.id}'),
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          SizedBox(
              width: 150,
              child: Text(a.name,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                      color: SvColors.text,
                      fontFamily: 'monospace',
                      fontSize: 12,
                      fontWeight: FontWeight.w600))),
          SizedBox(
              width: 100,
              child: Text(a.tenant,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: SvColors.muted, fontSize: 11))),
          SizedBox(
            width: 95,
            child: Row(children: [
              Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                      color: running ? SvColors.benign : SvColors.faint,
                      shape: BoxShape.circle)),
              const SizedBox(width: 6),
              Flexible(
                child: Text(running ? 'running' : 'halted',
                    key: Key('agent-state-${a.id}'),
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                        color: running ? SvColors.benign : SvColors.faint,
                        fontSize: 11)),
              ),
            ]),
          ),
          SizedBox(
              width: 60,
              child: Text('${a.runsToday}',
                  style: const TextStyle(color: SvColors.text, fontSize: 12))),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                    '\$${a.spentUsd.toStringAsFixed(2)} / \$${a.budgetUsd.toStringAsFixed(0)}',
                    style: const TextStyle(color: SvColors.muted, fontSize: 11)),
                const SizedBox(height: 3),
                ClipRRect(
                  borderRadius: BorderRadius.circular(3),
                  child: LinearProgressIndicator(
                    value: a.budgetRatio,
                    minHeight: 5,
                    backgroundColor: SvColors.bg,
                    valueColor: AlwaysStoppedAnimation(
                        a.budgetRatio > 0.8 ? SvColors.amber : SvColors.cyan),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
