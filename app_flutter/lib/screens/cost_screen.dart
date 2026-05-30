// Cost attribution — Bright Data spend by product vs envelope.
import 'package:flutter/material.dart';
import '../api.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/panel.dart';
import '../widgets/screen_title.dart';

class CostScreen extends StatefulWidget {
  const CostScreen({super.key});
  @override
  State<CostScreen> createState() => _CostScreenState();
}

class _CostScreenState extends State<CostScreen> {
  late final Future<List<CostRow>> _c = Api.instance.cost();

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<CostRow>>(
      future: _c,
      builder: (_, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        final rows = snap.data ?? [];
        final total = rows.fold<double>(0, (s, r) => s + r.usd);
        return ListView(
          key: const Key('cost-list'),
          children: [
            const ScreenTitle('Cost Attribution',
                sub: 'Bright Data spend by product · \$500 monthly envelope'),
            Panel(
              child: Column(
                children: [
                  ...rows.map((r) => Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: Row(
                          children: [
                            SizedBox(
                                width: 160,
                                child: Text(r.product,
                                    style: const TextStyle(
                                        color: SvColors.text, fontSize: 13))),
                            Expanded(
                              child: ClipRRect(
                                borderRadius: BorderRadius.circular(4),
                                child: LinearProgressIndicator(
                                  value: (r.usd / 20).clamp(0, 1),
                                  minHeight: 8,
                                  backgroundColor: SvColors.bg,
                                  valueColor:
                                      const AlwaysStoppedAnimation(SvColors.cyan),
                                ),
                              ),
                            ),
                            const SizedBox(width: 12),
                            Text('\$${r.usd.toStringAsFixed(2)}',
                                style: const TextStyle(
                                    color: SvColors.muted,
                                    fontFamily: 'monospace',
                                    fontSize: 12)),
                          ],
                        ),
                      )),
                  const Divider(color: SvColors.border),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text('Total',
                          style: TextStyle(color: SvColors.text, fontSize: 13)),
                      Text('\$${total.toStringAsFixed(2)} / \$500.00',
                          style: const TextStyle(
                              color: SvColors.amber,
                              fontFamily: 'monospace',
                              fontSize: 13)),
                    ],
                  ),
                ],
              ),
            ),
          ],
        );
      },
    );
  }
}
