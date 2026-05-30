// P10 — Takedowns. Multi-channel takedown status: registrar (Cloudflare /
// GoDaddy / Namecheap) and hosting-abuse (AWS / GCP / Hetzner / OVH / Hostinger)
// channels, each with a state pill, provider reference id, and a manual override
// so an analyst can mark a channel resolved/rejected when a provider replies out
// of band. Grouped by target URL.
import 'package:flutter/material.dart';
import '../api.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/panel.dart';
import '../widgets/screen_title.dart';

class TakedownsScreen extends StatefulWidget {
  const TakedownsScreen({super.key});
  @override
  State<TakedownsScreen> createState() => _TakedownsScreenState();
}

class _TakedownsScreenState extends State<TakedownsScreen> {
  final Future<List<Takedown>> _q = Api.instance.takedowns();
  // Local manual overrides keyed by takedown id.
  final Map<String, TakedownState> _overrides = {};

  TakedownState _stateOf(Takedown t) => _overrides[t.id] ?? t.state;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<Takedown>>(
      future: _q,
      builder: (_, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        final rows = snap.data ?? [];
        // Group by target URL.
        final byTarget = <String, List<Takedown>>{};
        for (final t in rows) {
          byTarget.putIfAbsent(t.targetUrl, () => []).add(t);
        }
        final resolved =
            rows.where((t) => _stateOf(t) == TakedownState.resolved).length;
        return ListView(
          key: const Key('takedowns-list'),
          children: [
            ScreenTitle('Takedowns',
                sub:
                    '${byTarget.length} targets · ${rows.length} channels · $resolved resolved'),
            for (final entry in byTarget.entries) _targetPanel(entry.key, entry.value),
          ],
        );
      },
    );
  }

  Widget _targetPanel(String target, List<Takedown> channels) {
    return Panel(
      key: Key('takedown-target-${channels.first.id}'),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(target,
              style: const TextStyle(
                  color: SvColors.text,
                  fontFamily: 'monospace',
                  fontSize: 13,
                  fontWeight: FontWeight.w600)),
          const SizedBox(height: 4),
          const Divider(color: SvColors.border),
          const Row(
            children: [
              SizedBox(width: 120, child: HeaderLabel('CHANNEL')),
              SizedBox(width: 90, child: HeaderLabel('KIND')),
              Expanded(child: HeaderLabel('REFERENCE')),
              SizedBox(width: 130, child: HeaderLabel('STATE')),
              SizedBox(width: 110, child: HeaderLabel('OVERRIDE')),
            ],
          ),
          const SizedBox(height: 4),
          ...channels.map(_channelRow),
        ],
      ),
    );
  }

  Widget _channelRow(Takedown t) {
    final state = _stateOf(t);
    return Padding(
      key: Key('takedown-row-${t.id}'),
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          SizedBox(
              width: 120,
              child: Text(t.channel,
                  style: const TextStyle(color: SvColors.text, fontSize: 12))),
          SizedBox(
              width: 90,
              child: Text(t.channelKind,
                  style: const TextStyle(color: SvColors.muted, fontSize: 11))),
          Expanded(
              child: Text(t.referenceId,
                  style: const TextStyle(
                      color: SvColors.muted,
                      fontFamily: 'monospace',
                      fontSize: 11))),
          SizedBox(width: 130, child: _statePill(t, state)),
          SizedBox(width: 110, child: _overrideMenu(t, state)),
        ],
      ),
    );
  }

  Widget _statePill(Takedown t, TakedownState state) {
    final c = takedownStateColor(state);
    return Container(
      key: Key('takedown-state-${t.id}'),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: c.withOpacity(0.14),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: c.withOpacity(0.5)),
      ),
      child: Text(state.name,
          textAlign: TextAlign.center,
          style: TextStyle(color: c, fontSize: 11, fontWeight: FontWeight.w600)),
    );
  }

  Widget _overrideMenu(Takedown t, TakedownState current) {
    return PopupMenuButton<TakedownState>(
      key: Key('takedown-override-${t.id}'),
      tooltip: 'Manual override',
      color: SvColors.panel2,
      onSelected: (s) => setState(() => _overrides[t.id] = s),
      itemBuilder: (_) => [
        for (final s in TakedownState.values)
          PopupMenuItem(
            value: s,
            child: Text(s.name,
                style: const TextStyle(color: SvColors.text, fontSize: 12)),
          ),
      ],
      child: const Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.edit_outlined, size: 14, color: SvColors.cyan),
          SizedBox(width: 4),
          Text('Override',
              style: TextStyle(color: SvColors.cyan, fontSize: 11)),
        ],
      ),
    );
  }
}
