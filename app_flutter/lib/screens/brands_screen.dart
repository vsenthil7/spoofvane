// Brand management — protected brands + thresholds.
import 'package:flutter/material.dart';
import '../api.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/panel.dart';
import '../widgets/screen_title.dart';

class BrandsScreen extends StatefulWidget {
  const BrandsScreen({super.key});
  @override
  State<BrandsScreen> createState() => _BrandsScreenState();
}

class _BrandsScreenState extends State<BrandsScreen> {
  late final Future<List<Brand>> _b = Api.instance.brands();

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<Brand>>(
      future: _b,
      builder: (_, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        final brands = snap.data ?? [];
        return ListView(
          key: const Key('brands-list'),
          children: [
            const ScreenTitle('Brand Management'),
            ...brands.map((b) => Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Panel(
                    child: Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(b.name,
                                  style: const TextStyle(
                                      color: SvColors.text, fontSize: 14)),
                              const SizedBox(height: 4),
                              Text(b.loginUrl,
                                  style: const TextStyle(
                                      color: SvColors.muted,
                                      fontFamily: 'monospace',
                                      fontSize: 12)),
                            ],
                          ),
                        ),
                        Text('${b.targetCountry} · thr ${b.scoreThreshold}',
                            style: const TextStyle(
                                color: SvColors.faint, fontSize: 12)),
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
