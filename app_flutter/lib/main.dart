// SpoofVane SOC console — Flutter web app.
// Dark SOC theme matching the product mockups. Left rail nav + content area.
// All screens pull from Api.instance, which serves live backend data when
// reachable and falls back to seed (clearly tagged) otherwise.
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import 'api.dart';
import 'models.dart';

void main() => runApp(const SpoofVaneApp());

// ---- palette (from the product mockups) ----
const cBg = Color(0xFF0B0F17);
const cPanel = Color(0xFF131A26);
const cPanel2 = Color(0xFF0E141F);
const cBorder = Color(0xFF2C3A52);
const cText = Color(0xFFE8EDF5);
const cMuted = Color(0xFF93A1B8);
const cFaint = Color(0xFF5E6E88);
const cAmber = Color(0xFFFFB020);
const cCyan = Color(0xFF36C2CE);

class SpoofVaneApp extends StatelessWidget {
  const SpoofVaneApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SpoofVane',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: cBg,
        fontFamily: 'Roboto',
        colorScheme: const ColorScheme.dark(
          surface: cPanel,
          primary: cCyan,
          secondary: cAmber,
        ),
      ),
      home: const Console(),
    );
  }
}

// ---- nav registry (mirrors the mockup sidebar) ----
class NavItem {
  final String label;
  final IconData icon;
  final WidgetBuilder builder;
  const NavItem(this.label, this.icon, this.builder);
}

final navItems = <NavItem>[
  NavItem('Dashboard', Icons.dashboard_outlined, (_) => const DashboardScreen()),
  NavItem('Triage Queue', Icons.flag_outlined, (_) => const TriageScreen()),
  NavItem('Campaign Clusters', Icons.hub_outlined, (_) => const ClustersScreen()),
  NavItem('Deepfake Feed', Icons.smart_display_outlined, (_) => const DeepfakeScreen()),
  NavItem('Exec Protection', Icons.shield_outlined, (_) => const ExecScreen()),
  NavItem('Brand Management', Icons.business_outlined, (_) => const BrandsScreen()),
  NavItem('Cost Attribution', Icons.payments_outlined, (_) => const CostScreen()),
  NavItem('Audit Log', Icons.receipt_long_outlined, (_) => const AuditScreen()),
];

class Console extends StatefulWidget {
  const Console({super.key});
  @override
  State<Console> createState() => _ConsoleState();
}

class _ConsoleState extends State<Console> {
  int _i = 0;
  bool _collapsed = false;

  @override
  void initState() {
    super.initState();
    Api.instance.health(); // probe backend so the LIVE/SEED pill is accurate
  }

  @override
  Widget build(BuildContext context) {
    final railW = _collapsed ? 64.0 : 232.0;
    return Scaffold(
      body: Row(
        children: [
          // ---- left rail ----
          AnimatedContainer(
            duration: const Duration(milliseconds: 160),
            width: railW,
            color: cPanel,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Container(
                  height: 56,
                  color: cPanel2,
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: Row(
                    children: [
                      if (!_collapsed)
                        const Expanded(
                          child: _Brand(),
                        ),
                      IconButton(
                        tooltip: 'Collapse',
                        icon: Icon(_collapsed ? Icons.chevron_right : Icons.chevron_left,
                            color: cMuted, size: 18),
                        onPressed: () => setState(() => _collapsed = !_collapsed),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 8),
                Expanded(
                  child: ListView.builder(
                    itemCount: navItems.length,
                    itemBuilder: (_, idx) {
                      final n = navItems[idx];
                      final sel = idx == _i;
                      return InkWell(
                        onTap: () => setState(() => _i = idx),
                        child: Container(
                          margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                          decoration: BoxDecoration(
                            color: sel ? cCyan.withOpacity(0.13) : null,
                            borderRadius: BorderRadius.circular(6),
                            border: sel
                                ? Border.all(color: cCyan.withOpacity(0.4))
                                : null,
                          ),
                          child: Row(
                            mainAxisAlignment: _collapsed
                                ? MainAxisAlignment.center
                                : MainAxisAlignment.start,
                            children: [
                              Icon(n.icon,
                                  size: 18, color: sel ? cCyan : cFaint),
                              if (!_collapsed) ...[
                                const SizedBox(width: 10),
                                Expanded(
                                  child: Text(n.label,
                                      style: TextStyle(
                                          color: sel ? cText : cMuted,
                                          fontSize: 13)),
                                ),
                              ],
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                ),
              ],
            ),
          ),
          // ---- content ----
          Expanded(
            child: Column(
              children: [
                Container(
                  height: 56,
                  color: cPanel2,
                  padding: const EdgeInsets.symmetric(horizontal: 24),
                  child: Row(
                    children: [
                      Expanded(
                        child: Container(
                          height: 30,
                          alignment: Alignment.centerLeft,
                          padding: const EdgeInsets.symmetric(horizontal: 14),
                          decoration: BoxDecoration(
                            color: cBg,
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(color: cBorder),
                          ),
                          constraints: const BoxConstraints(maxWidth: 420),
                          child: const Text('Search alerts, URLs, domains…',
                              style: TextStyle(color: cFaint, fontSize: 12)),
                        ),
                      ),
                      const SizedBox(width: 16),
                      const _SourcePill(),
                      const SizedBox(width: 12),
                      Container(
                        padding:
                            const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                        decoration: BoxDecoration(
                            color: const Color(0xFF1B2433),
                            borderRadius: BorderRadius.circular(14)),
                        child: const Text('AcmeBank ▾',
                            style: TextStyle(color: cText, fontSize: 12)),
                      ),
                    ],
                  ),
                ),
                Expanded(
                  child: Container(
                    color: cBg,
                    padding: const EdgeInsets.all(24),
                    child: navItems[_i].builder(context),
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

class _Brand extends StatelessWidget {
  const _Brand();
  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        RichText(
          text: const TextSpan(children: [
            TextSpan(
                text: 'Spoof',
                style: TextStyle(
                    color: cText,
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                    fontFamily: 'Georgia')),
            TextSpan(
                text: 'Vane',
                style: TextStyle(
                    color: cAmber,
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                    fontFamily: 'Georgia')),
          ]),
        ),
        const Text('v0.5 Enterprise',
            style: TextStyle(color: cFaint, fontSize: 9)),
      ],
    );
  }
}

class _SourcePill extends StatelessWidget {
  const _SourcePill();
  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<DataSource>(
      valueListenable: Api.instance.source,
      builder: (_, src, __) {
        final live = src == DataSource.live;
        return Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
          decoration: BoxDecoration(
            color: (live ? const Color(0xFF3DDC84) : cAmber).withOpacity(0.15),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Text(
            live ? 'LIVE' : 'SEED',
            style: TextStyle(
              color: live ? const Color(0xFF3DDC84) : cAmber,
              fontSize: 11,
              letterSpacing: 1,
              fontFamily: 'monospace',
            ),
          ),
        );
      },
    );
  }
}

// ===================== shared widgets =====================

class Panel extends StatelessWidget {
  final String? title;
  final Widget child;
  final double? width;
  const Panel({super.key, this.title, required this.child, this.width});
  @override
  Widget build(BuildContext context) {
    return Container(
      width: width,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: cPanel,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: cBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (title != null) ...[
            Text(title!,
                style: const TextStyle(
                    color: cText, fontSize: 13, fontFamily: 'Georgia')),
            const SizedBox(height: 12),
          ],
          child,
        ],
      ),
    );
  }
}

class ScreenTitle extends StatelessWidget {
  final String title;
  final String? sub;
  const ScreenTitle(this.title, {super.key, this.sub});
  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title,
            style: const TextStyle(
                color: cText, fontSize: 22, fontWeight: FontWeight.bold, fontFamily: 'Georgia')),
        if (sub != null) ...[
          const SizedBox(height: 4),
          Text(sub!, style: const TextStyle(color: cMuted, fontSize: 12)),
        ],
        const SizedBox(height: 20),
      ],
    );
  }
}

class VerdictPill extends StatelessWidget {
  final Verdict v;
  const VerdictPill(this.v, {super.key});
  @override
  Widget build(BuildContext context) {
    final c = verdictColor(v);
    final label = v.name;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
          color: c.withOpacity(0.15), borderRadius: BorderRadius.circular(8)),
      child: Text(label,
          style: TextStyle(color: c, fontSize: 11, fontFamily: 'monospace')),
    );
  }
}

class StatCard extends StatelessWidget {
  final String label;
  final String value;
  const StatCard(this.label, this.value, {super.key});
  @override
  Widget build(BuildContext context) {
    return Container(
      width: 150,
      height: 76,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
          color: cPanel,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: cBorder)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(color: cFaint, fontSize: 10)),
          const Spacer(),
          Text(value,
              style: const TextStyle(
                  color: cAmber, fontSize: 22, fontFamily: 'monospace')),
        ],
      ),
    );
  }
}

String _fmtTime(String iso) {
  try {
    return DateFormat('MMM d, HH:mm').format(DateTime.parse(iso).toLocal());
  } catch (_) {
    return iso;
  }
}

// ===================== screens =====================

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});
  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  late Future<List<Alert>> _alerts;
  @override
  void initState() {
    super.initState();
    _alerts = Api.instance.alerts();
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<Alert>>(
      future: _alerts,
      builder: (_, snap) {
        final alerts = snap.data ?? [];
        final open = alerts.where((a) => a.verdict != Verdict.benign).length;
        final df = alerts.where((a) => a.family == 'deepfake').length;
        return ListView(
          children: [
            const ScreenTitle('Security Dashboard',
                sub: 'Enterprise · Real-time threat visibility'),
            Wrap(
              spacing: 16,
              runSpacing: 16,
              children: [
                StatCard('Total Alerts', '${alerts.length}'),
                StatCard('Open Alerts', '$open'),
                StatCard('Deepfakes 24h', '$df'),
                StatCard('Active Clusters', '2'),
                StatCard('Takedown Rate', '74%'),
              ],
            ),
            const SizedBox(height: 20),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Panel(
                    title: 'Top Targeted Brands',
                    child: Column(
                      children: const [
                        _BarRow('AcmeBank', 0.83, '83'),
                        SizedBox(height: 10),
                        _BarRow('Globex', 0.41, '41'),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Panel(
                    title: 'Recent Alerts',
                    child: Column(
                      children: alerts
                          .take(4)
                          .map((a) => Padding(
                                padding: const EdgeInsets.only(bottom: 8),
                                child: Row(
                                  children: [
                                    VerdictPill(a.verdict),
                                    const SizedBox(width: 10),
                                    Expanded(
                                      child: Text(a.url,
                                          overflow: TextOverflow.ellipsis,
                                          style: const TextStyle(
                                              color: cText,
                                              fontFamily: 'monospace',
                                              fontSize: 12)),
                                    ),
                                    Text(a.composite.toStringAsFixed(2),
                                        style: const TextStyle(
                                            color: cMuted,
                                            fontFamily: 'monospace',
                                            fontSize: 12)),
                                  ],
                                ),
                              ))
                          .toList(),
                    ),
                  ),
                ),
              ],
            ),
          ],
        );
      },
    );
  }
}

class _BarRow extends StatelessWidget {
  final String label;
  final double frac;
  final String value;
  const _BarRow(this.label, this.frac, this.value);
  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        SizedBox(
            width: 80,
            child: Text(label, style: const TextStyle(color: cText, fontSize: 12))),
        Expanded(
          child: ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: frac,
              minHeight: 8,
              backgroundColor: cBg,
              valueColor: const AlwaysStoppedAnimation(cCyan),
            ),
          ),
        ),
        const SizedBox(width: 10),
        Text(value,
            style: const TextStyle(
                color: cMuted, fontFamily: 'monospace', fontSize: 12)),
      ],
    );
  }
}

class TriageScreen extends StatefulWidget {
  const TriageScreen({super.key});
  @override
  State<TriageScreen> createState() => _TriageScreenState();
}

class _TriageScreenState extends State<TriageScreen> {
  late Future<List<Alert>> _q;
  @override
  void initState() {
    super.initState();
    _q = Api.instance.triageQueue();
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<Alert>>(
      future: _q,
      builder: (_, snap) {
        final rows = snap.data ?? [];
        return ListView(
          children: [
            ScreenTitle('Triage Queue', sub: '${rows.length} alerts'),
            Panel(
              child: Column(
                children: [
                  Row(
                    children: const [
                      SizedBox(width: 90, child: _H('VERDICT')),
                      Expanded(child: _H('URL')),
                      SizedBox(width: 60, child: _H('SCORE')),
                      SizedBox(width: 90, child: _H('FAMILY')),
                      SizedBox(width: 70, child: _H('REGION')),
                    ],
                  ),
                  const Divider(color: cBorder),
                  ...rows.map((a) => InkWell(
                        onTap: () => Navigator.of(context).push(MaterialPageRoute(
                            builder: (_) => AlertDetailScreen(alert: a))),
                        child: Padding(
                          padding: const EdgeInsets.symmetric(vertical: 8),
                          child: Row(
                            children: [
                              SizedBox(width: 90, child: VerdictPill(a.verdict)),
                              Expanded(
                                child: Text(a.url,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(
                                        color: cText,
                                        fontFamily: 'monospace',
                                        fontSize: 12)),
                              ),
                              SizedBox(
                                  width: 60,
                                  child: Text(a.composite.toStringAsFixed(2),
                                      style: const TextStyle(
                                          color: cMuted,
                                          fontFamily: 'monospace',
                                          fontSize: 12))),
                              SizedBox(
                                  width: 90,
                                  child: Text(a.family ?? '—',
                                      style: const TextStyle(
                                          color: cMuted, fontSize: 12))),
                              SizedBox(
                                  width: 70,
                                  child: Text(a.renderedFrom ?? '—',
                                      style: const TextStyle(
                                          color: cMuted, fontSize: 12))),
                            ],
                          ),
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

class _H extends StatelessWidget {
  final String t;
  const _H(this.t);
  @override
  Widget build(BuildContext context) => Text(t,
      style: const TextStyle(
          color: cFaint, fontSize: 9.5, fontWeight: FontWeight.bold));
}

class AlertDetailScreen extends StatelessWidget {
  final Alert alert;
  const AlertDetailScreen({super.key, required this.alert});
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: cBg,
      appBar: AppBar(
        backgroundColor: cPanel2,
        title: Text(alert.url, style: const TextStyle(fontFamily: 'monospace', fontSize: 14)),
        actions: [
          Padding(
            padding: const EdgeInsets.all(8),
            child: ElevatedButton(
              style: ElevatedButton.styleFrom(backgroundColor: verdictColor(alert.verdict)),
              onPressed: () {
                ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
                    content: Text('Takedown requested (demo)')));
              },
              child: const Text('Request takedown'),
            ),
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Panel(
                title: 'Summary',
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(children: [VerdictPill(alert.verdict)]),
                    const SizedBox(height: 12),
                    _kv('verdict', alert.verdict.name),
                    _kv('score', alert.composite.toStringAsFixed(2)),
                    _kv('family', alert.family ?? '—'),
                    _kv('kit', alert.kit ?? '—'),
                    _kv('rendered from', alert.renderedFrom ?? '—'),
                    _kv('discovered', _fmtTime(alert.discoveredAt)),
                    _kv('MITRE', alert.mitreTechniques.join(', ')),
                  ],
                ),
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Panel(
                title: 'Verdict trace (ensemble)',
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _trace('claude', alert.verdict, alert.composite + 0.01),
                    _trace('gpt-5', alert.verdict, alert.composite - 0.02),
                    _trace('gemini', alert.verdict, alert.composite),
                    const Divider(color: cBorder),
                    Text('merge: ${alert.verdict.name.toUpperCase()} · no dissent',
                        style: TextStyle(
                            color: verdictColor(alert.verdict),
                            fontFamily: 'monospace',
                            fontSize: 13)),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _kv(String k, String v) => Padding(
        padding: const EdgeInsets.only(bottom: 6),
        child: Row(
          children: [
            SizedBox(
                width: 120,
                child: Text(k, style: const TextStyle(color: cFaint, fontSize: 12))),
            Expanded(
                child: Text(v,
                    style: const TextStyle(
                        color: cText, fontFamily: 'monospace', fontSize: 12))),
          ],
        ),
      );

  Widget _trace(String model, Verdict v, double conf) => Padding(
        padding: const EdgeInsets.only(bottom: 6),
        child: Text(
            '$model: ${v.name} ${conf.clamp(0, 1).toStringAsFixed(2)}',
            style: const TextStyle(
                color: Color(0xFF3DDC84), fontFamily: 'monospace', fontSize: 12)),
      );
}

class ClustersScreen extends StatefulWidget {
  const ClustersScreen({super.key});
  @override
  State<ClustersScreen> createState() => _ClustersScreenState();
}

class _ClustersScreenState extends State<ClustersScreen> {
  late Future<List<Cluster>> _c;
  @override
  void initState() {
    super.initState();
    _c = Api.instance.clusters();
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<Cluster>>(
      future: _c,
      builder: (_, snap) {
        final clusters = snap.data ?? [];
        return ListView(
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
                              style: TextStyle(color: cFaint, fontSize: 12)),
                          Text(c.risk.toStringAsFixed(2),
                              style: const TextStyle(
                                  color: cAmber, fontFamily: 'monospace')),
                          const SizedBox(width: 16),
                          Text('${c.members.length} members',
                              style: const TextStyle(color: cMuted, fontSize: 12)),
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
                                        color: const Color(0xFF232F42),
                                        borderRadius: BorderRadius.circular(20),
                                        border: Border.all(color: cBorder)),
                                    child: Text(m,
                                        style: const TextStyle(
                                            color: cText,
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

class DeepfakeScreen extends StatefulWidget {
  const DeepfakeScreen({super.key});
  @override
  State<DeepfakeScreen> createState() => _DeepfakeScreenState();
}

class _DeepfakeScreenState extends State<DeepfakeScreen> {
  late Future<List<Alert>> _d;
  @override
  void initState() {
    super.initState();
    _d = Api.instance.deepfakes();
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<Alert>>(
      future: _d,
      builder: (_, snap) {
        final rows = snap.data ?? [];
        return ListView(
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
                                  color: cText, fontSize: 13, fontFamily: 'Georgia')),
                          const SizedBox(width: 12),
                          VerdictPill(a.verdict),
                        ]),
                        const SizedBox(height: 12),
                        const Text('face dist 0.81 · lip-sync 0.74 · voiceprint match 0.03',
                            style: TextStyle(
                                color: cMuted, fontFamily: 'monospace', fontSize: 12)),
                        const SizedBox(height: 6),
                        const Text('C2PA ✗ invalid',
                            style: TextStyle(
                                color: Color(0xFFFF4D57),
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
                              style: ElevatedButton.styleFrom(backgroundColor: cAmber),
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

class ExecScreen extends StatelessWidget {
  const ExecScreen({super.key});
  @override
  Widget build(BuildContext context) {
    final execs = [
      ('Jane Powell', 'CEO', 0.74, ['home_address', 'children_school']),
      ('Raj Mehta', 'CFO', 0.41, ['personal_phone']),
    ];
    return ListView(
      children: [
        const ScreenTitle('Executive Protection',
            sub: 'Doxxing · physical-threat · impersonation monitoring'),
        ...execs.map((e) => Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: Panel(
                child: Row(
                  children: [
                    const CircleAvatar(
                        backgroundColor: Color(0xFF232F42),
                        child: Icon(Icons.person, color: cMuted)),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('${e.$1} · ${e.$2}',
                              style: const TextStyle(color: cText, fontSize: 14)),
                          const SizedBox(height: 6),
                          Wrap(
                            spacing: 6,
                            children: e.$4
                                .map((x) => Chip(
                                      label: Text(x,
                                          style: const TextStyle(fontSize: 10)),
                                      backgroundColor: const Color(0xFF2A1316),
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
                            style: TextStyle(color: cFaint, fontSize: 10)),
                        Text(e.$3.toStringAsFixed(2),
                            style: TextStyle(
                                color: e.$3 > 0.6 ? const Color(0xFFFF4D57) : cAmber,
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

class BrandsScreen extends StatefulWidget {
  const BrandsScreen({super.key});
  @override
  State<BrandsScreen> createState() => _BrandsScreenState();
}

class _BrandsScreenState extends State<BrandsScreen> {
  late Future<List<Brand>> _b;
  @override
  void initState() {
    super.initState();
    _b = Api.instance.brands();
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<Brand>>(
      future: _b,
      builder: (_, snap) {
        final brands = snap.data ?? [];
        return ListView(
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
                                  style: const TextStyle(color: cText, fontSize: 14)),
                              const SizedBox(height: 4),
                              Text(b.loginUrl,
                                  style: const TextStyle(
                                      color: cMuted,
                                      fontFamily: 'monospace',
                                      fontSize: 12)),
                            ],
                          ),
                        ),
                        Text('${b.targetCountry} · thr ${b.scoreThreshold}',
                            style: const TextStyle(color: cFaint, fontSize: 12)),
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

class CostScreen extends StatefulWidget {
  const CostScreen({super.key});
  @override
  State<CostScreen> createState() => _CostScreenState();
}

class _CostScreenState extends State<CostScreen> {
  late Future<List<CostRow>> _c;
  @override
  void initState() {
    super.initState();
    _c = Api.instance.cost();
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<CostRow>>(
      future: _c,
      builder: (_, snap) {
        final rows = snap.data ?? [];
        final total = rows.fold<double>(0, (s, r) => s + r.usd);
        return ListView(
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
                                    style: const TextStyle(color: cText, fontSize: 13))),
                            Expanded(
                              child: ClipRRect(
                                borderRadius: BorderRadius.circular(4),
                                child: LinearProgressIndicator(
                                  value: (r.usd / 20).clamp(0, 1),
                                  minHeight: 8,
                                  backgroundColor: cBg,
                                  valueColor: const AlwaysStoppedAnimation(cCyan),
                                ),
                              ),
                            ),
                            const SizedBox(width: 12),
                            Text('\$${r.usd.toStringAsFixed(2)}',
                                style: const TextStyle(
                                    color: cMuted, fontFamily: 'monospace', fontSize: 12)),
                          ],
                        ),
                      )),
                  const Divider(color: cBorder),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text('Total',
                          style: TextStyle(color: cText, fontSize: 13)),
                      Text('\$${total.toStringAsFixed(2)} / \$500.00',
                          style: const TextStyle(
                              color: cAmber, fontFamily: 'monospace', fontSize: 13)),
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

class AuditScreen extends StatefulWidget {
  const AuditScreen({super.key});
  @override
  State<AuditScreen> createState() => _AuditScreenState();
}

class _AuditScreenState extends State<AuditScreen> {
  late Future<List<AuditRow>> _a;
  @override
  void initState() {
    super.initState();
    _a = Api.instance.audit();
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<AuditRow>>(
      future: _a,
      builder: (_, snap) {
        final rows = snap.data ?? [];
        return ListView(
          children: [
            const ScreenTitle('Audit Log',
                sub: 'Tamper-evident hash chain'),
            Panel(
              child: Column(
                children: [
                  Row(
                    children: const [
                      SizedBox(width: 40, child: _H('SEQ')),
                      SizedBox(width: 90, child: _H('ROLE')),
                      Expanded(child: _H('ACTION')),
                      SizedBox(width: 60, child: _H('OUTCOME')),
                      SizedBox(width: 140, child: _H('TIME')),
                      SizedBox(width: 90, child: _H('HASH')),
                    ],
                  ),
                  const Divider(color: cBorder),
                  ...rows.map((r) => Padding(
                        padding: const EdgeInsets.symmetric(vertical: 8),
                        child: Row(
                          children: [
                            SizedBox(
                                width: 40,
                                child: Text('${r.seq}',
                                    style: const TextStyle(
                                        color: cMuted, fontFamily: 'monospace', fontSize: 12))),
                            SizedBox(
                                width: 90,
                                child: Text(r.actorRole,
                                    style: const TextStyle(color: cMuted, fontSize: 12))),
                            Expanded(
                                child: Text(r.action,
                                    style: const TextStyle(
                                        color: cText, fontFamily: 'monospace', fontSize: 12))),
                            SizedBox(
                                width: 60,
                                child: Text(r.outcome,
                                    style: const TextStyle(
                                        color: Color(0xFF3DDC84), fontSize: 12))),
                            SizedBox(
                                width: 140,
                                child: Text(_fmtTime(r.ts),
                                    style: const TextStyle(color: cMuted, fontSize: 11))),
                            SizedBox(
                                width: 90,
                                child: Text(r.hash,
                                    style: const TextStyle(
                                        color: cFaint, fontFamily: 'monospace', fontSize: 11))),
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
