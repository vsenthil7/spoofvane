// Deepfake feed — multimodal detection review with confirm/override.
import 'package:flutter/material.dart';
import '../api.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/panel.dart';
import '../widgets/screen_title.dart';
import '../widgets/verdict_pill.dart';

class DeepfakeScreen extends StatefulWidget {
  const DeepfakeScreen({super.key});
  @override
  State<DeepfakeScreen> createState() => _DeepfakeScreenState();
}

class _DeepfakeScreenState extends State<DeepfakeScreen> {
  late final Future<List<Alert>> _d = Api.instance.deepfakes();

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<Alert>>(
      future: _d,
      builder: (_, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        final rows = snap.data ?? [];
        return ListView(
          key: const Key('deepfake-list'),
          children: [
            const ScreenTitle('Deepfake Feed',
                sub: 'Multimodal real-time detection · liveness · C2PA provenance'),
            ...rows.map((a) => Padding(
                  padding: const EdgeInsets.only(bottom: 16),
                  child: Panel(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(children: [
                          const Text('CEO impersonation clip',
                              style: TextStyle(
                                  color: SvColors.text,
                                  fontSize: 13,
                                  fontFamily: 'Georgia')),
                          const SizedBox(width: 12),
                          VerdictPill(a.verdict),
                        ]),
                        const SizedBox(height: 12),
                        const Text(
                            'face dist 0.81 · lip-sync 0.74 · voiceprint match 0.03',
                            style: TextStyle(
                                color: SvColors.muted,
                                fontFamily: 'monospace',
                                fontSize: 12)),
                        const SizedBox(height: 6),
                        const Text('C2PA ✗ invalid',
                            style: TextStyle(
                                color: SvColors.phish,
                                fontFamily: 'monospace',
                                fontSize: 12)),
                        const SizedBox(height: 10),
                        Text(
                            'multimodal verdict: ${a.verdict.name.toUpperCase()} ${a.composite.toStringAsFixed(2)}',
                            style: TextStyle(
                                color: verdictColor(a.verdict),
                                fontFamily: 'monospace',
                                fontSize: 14)),
                        const SizedBox(height: 12),
                        Row(children: [
                          ElevatedButton(
                              style: ElevatedButton.styleFrom(
                                  backgroundColor: SvColors.amber),
                              onPressed: () {},
                              child: const Text('Confirm',
                                  style: TextStyle(color: Color(0xFF1A1300)))),
                          const SizedBox(width: 10),
                          OutlinedButton(
                              onPressed: () {}, child: const Text('Override')),
                        ]),
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
