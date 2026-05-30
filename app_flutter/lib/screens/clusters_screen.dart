// Campaign clusters — shared-infrastructure correlation groups.
import 'package:flutter/material.dart';
import '../api.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/panel.dart';
import '../widgets/screen_title.dart';

class ClustersScreen extends StatefulWidget {
  const ClustersScreen({super.key});
  @override
  State<ClustersScreen> createState() => _ClustersScreenState();
}

class _ClustersScreenState extends State<ClustersScreen> {
  late final Future<List<Cluster>> _c = Api.instance.clusters();

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<Cluster>>(
      future: _c,
      builder: (_, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        final clusters = snap.data ?? [];
        return ListView(
          key: const Key('clusters-list'),
          children: [
            const ScreenTitle('Campaign Clusters',
                sub: 'Shared-infrastructure correlation (threat-actor graph)'),
            ...clusters.map((c) => Padding(
                  padding: const EdgeInsets.only(bottom: 16),
                  child: Panel(
                    title: 'Campaign #${c.id}',
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(children: [
                          const Text('risk ',
                              style: TextStyle(color: SvColors.faint, fontSize: 12)),
                          Text(c.risk.toStringAsFixed(2),
                              style: const TextStyle(
                                  color: SvColors.amber, fontFamily: 'monospace')),
                          const SizedBox(width: 16),
                          Text('${c.members.length} members',
                              style: const TextStyle(
                                  color: SvColors.muted, fontSize: 12)),
                        ]),
                        const SizedBox(height: 10),
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: c.members
                              .map((m) => Container(
                                    padding: const EdgeInsets.symmetric(
                                        horizontal: 10, vertical: 6),
                                    decoration: BoxDecoration(
                                        color: SvColors.node,
                                        borderRadius: BorderRadius.circular(20),
                                        border: Border.all(color: SvColors.border)),
                                    child: Text(m,
                                        style: const TextStyle(
                                            color: SvColors.text,
                                            fontFamily: 'monospace',
                                            fontSize: 11)),
                                  ))
                              .toList(),
                        ),
                      ],
                    ),
                  ),
                )),
          ],
        );
      },
    );
  }
}
