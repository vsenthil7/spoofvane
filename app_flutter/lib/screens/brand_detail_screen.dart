// P04 — Brand detail. Everything about one brand: canonical login URL, target
// region, the score threshold that decides escalation, and reference asset
// hashes (logo + screenshot). Reached by tapping a row on the Brands list.
import 'package:flutter/material.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/panel.dart';

class BrandDetailScreen extends StatelessWidget {
  final Brand brand;
  const BrandDetailScreen({super.key, required this.brand});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: SvColors.bg,
      appBar: AppBar(
        backgroundColor: SvColors.panel2,
        title: Text(brand.name, style: const TextStyle(fontSize: 16)),
      ),
      body: ListView(
        key: const Key('brand-detail-list'),
        padding: const EdgeInsets.all(24),
        children: [
          Panel(
            title: 'Canonical',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _kv('Brand', brand.name),
                _kv('Login URL', brand.loginUrl),
                _kv('Target region', brand.targetCountry),
              ],
            ),
          ),
          Panel(
            title: 'Escalation',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _kv('Score threshold', brand.scoreThreshold.toStringAsFixed(2)),
                const SizedBox(height: 6),
                const Text(
                    'Suspects scoring at or above this threshold are escalated to the triage queue.',
                    style: TextStyle(color: SvColors.faint, fontSize: 11)),
              ],
            ),
          ),
          Panel(
            title: 'Reference assets',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _kv('Logo hash', 'sha256:${_pseudoHash(brand.id, 'logo')}'),
                _kv('Screenshot hash', 'sha256:${_pseudoHash(brand.id, 'shot')}'),
                _kv('Favicon hash', 'sha256:${_pseudoHash(brand.id, 'fav')}'),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _kv(String k, String v) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
                width: 130,
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

  String _pseudoHash(String seed, String salt) {
    final n = (seed + salt)
        .codeUnits
        .fold<int>(0, (acc, c) => (acc * 31 + c) & 0xFFFFFFFF);
    return n.toRadixString(16).padLeft(8, '0') * 4;
  }
}
