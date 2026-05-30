// P23 — Pricing (public). Four-tier plan comparison with a monthly/annual
// billing toggle, a highlighted "most popular" plan, feature lists, and a CTA
// per plan. Prices are set from market norms for brand-protection / anti-phishing
// SaaS (see seedPricing). Reachable from the login screen and in-app.
import 'package:flutter/material.dart';
import '../api.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/screen_title.dart';

class PricingScreen extends StatefulWidget {
  const PricingScreen({super.key});
  @override
  State<PricingScreen> createState() => _PricingScreenState();
}

class _PricingScreenState extends State<PricingScreen> {
  final Future<List<PricingPlan>> _q = Api.instance.pricing();
  bool _annual = true;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<PricingPlan>>(
      future: _q,
      builder: (_, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        final plans = snap.data ?? [];
        return Scaffold(
          backgroundColor: SvColors.bg,
          body: ListView(
            key: const Key('pricing-list'),
            padding: const EdgeInsets.all(24),
            children: [
            const Center(
              child: ScreenTitle('Plans & pricing',
                  sub: 'Defend your brand at any scale. Cancel anytime.'),
            ),
            _billingToggle(),
            const SizedBox(height: 20),
            LayoutBuilder(builder: (_, c) {
              // In a bounded layout maxWidth is the viewport; guard against an
              // unbounded constraint (e.g. pushed route in tests) by capping.
              final maxW = c.maxWidth.isFinite && c.maxWidth < 4000
                  ? c.maxWidth
                  : 1200.0;
              final wide = maxW > 900;
              final cardW = wide ? (maxW - 48) / 4 : maxW;
              return Wrap(
                alignment: WrapAlignment.center,
                spacing: 16,
                runSpacing: 16,
                children: [
                  for (final p in plans)
                    SizedBox(
                      width: cardW,
                      child: _planCard(p),
                    ),
                ],
              );
            }),
            const SizedBox(height: 16),
            const Center(
              child: Text(
                  'All plans include phishing & lookalike detection, court-ready evidence, and the human-in-the-loop review gate.',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: SvColors.faint, fontSize: 11)),
            ),
            ],
          ),
        );
      },
    );
  }

  Widget _billingToggle() {
    return Center(
      child: Container(
        padding: const EdgeInsets.all(4),
        decoration: BoxDecoration(
          color: SvColors.panel2,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: SvColors.border),
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          _toggleBtn('Monthly', !_annual, () => setState(() => _annual = false)),
          _toggleBtn('Annual (save ~20%)', _annual, () => setState(() => _annual = true)),
        ]),
      ),
    );
  }

  Widget _toggleBtn(String label, bool active, VoidCallback onTap) {
    return InkWell(
      key: Key('pricing-toggle-${label.split(' ').first.toLowerCase()}'),
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          color: active ? SvColors.amber : Colors.transparent,
          borderRadius: BorderRadius.circular(6),
        ),
        child: Text(label,
            style: TextStyle(
                color: active ? const Color(0xFF1A1300) : SvColors.muted,
                fontSize: 12,
                fontWeight: FontWeight.w600)),
      ),
    );
  }

  Widget _planCard(PricingPlan p) {
    final price = _annual ? p.priceMonthly : p.priceMonthlyMonthly;
    return Container(
      key: Key('pricing-card-${p.id}'),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: p.highlighted ? SvColors.panel : SvColors.panel2,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
            color: p.highlighted ? SvColors.amber : SvColors.border,
            width: p.highlighted ? 2 : 1),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (p.highlighted)
            Container(
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(
                  color: SvColors.amber, borderRadius: BorderRadius.circular(4)),
              child: const Text('MOST POPULAR',
                  style: TextStyle(
                      color: Color(0xFF1A1300),
                      fontSize: 9,
                      fontWeight: FontWeight.bold)),
            ),
          Text(p.name,
              style: const TextStyle(
                  color: SvColors.text,
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  fontFamily: 'Georgia')),
          const SizedBox(height: 4),
          SizedBox(
            height: 52,
            child: Text(p.tagline,
                style: const TextStyle(color: SvColors.muted, fontSize: 11)),
          ),
          const SizedBox(height: 8),
          if (p.isCustom)
            const Text('Custom',
                style: TextStyle(
                    color: SvColors.text,
                    fontSize: 28,
                    fontWeight: FontWeight.bold))
          else
            Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text('\$${price.toStringAsFixed(0)}',
                    style: const TextStyle(
                        color: SvColors.text,
                        fontSize: 28,
                        fontWeight: FontWeight.bold)),
                const Padding(
                  padding: EdgeInsets.only(bottom: 5, left: 2),
                  child: Text('/mo',
                      style: TextStyle(color: SvColors.muted, fontSize: 12)),
                ),
              ],
            ),
          const SizedBox(height: 4),
          Text(
              p.isCustom
                  ? 'Billed annually'
                  : (_annual ? 'Billed annually' : 'Billed monthly'),
              style: const TextStyle(color: SvColors.faint, fontSize: 10)),
          const SizedBox(height: 14),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              key: Key('pricing-cta-${p.id}'),
              style: ElevatedButton.styleFrom(
                backgroundColor: p.highlighted ? SvColors.amber : SvColors.chip,
                foregroundColor:
                    p.highlighted ? const Color(0xFF1A1300) : SvColors.text,
              ),
              onPressed: () => ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('${p.cta} — ${p.name} (demo)'))),
              child: Text(p.cta),
            ),
          ),
          const SizedBox(height: 14),
          ...p.features.map((f) => Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.check, size: 14, color: SvColors.benign),
                    const SizedBox(width: 8),
                    Expanded(
                        child: Text(f,
                            style: const TextStyle(
                                color: SvColors.muted, fontSize: 12))),
                  ],
                ),
              )),
        ],
      ),
    );
  }
}
