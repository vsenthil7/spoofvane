// App root: theme, the Console shell (nav rail + top bar + content), and the
// nav registry that maps each rail entry to its screen.
import 'package:flutter/material.dart';

import 'api.dart';
import 'theme.dart';
import 'widgets/nav_rail.dart';
import 'widgets/source_pill.dart';
import 'screens/dashboard_screen.dart';
import 'screens/triage_screen.dart';
import 'screens/clusters_screen.dart';
import 'screens/deepfake_screen.dart';
import 'screens/exec_screen.dart';
import 'screens/brands_screen.dart';
import 'screens/cost_screen.dart';
import 'screens/audit_screen.dart';

class SpoofVaneApp extends StatelessWidget {
  const SpoofVaneApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SpoofVane',
      debugShowCheckedModeBanner: false,
      theme: buildSvTheme(),
      home: const Console(),
    );
  }
}

/// One nav entry: rail metadata + the screen builder it routes to.
class ConsolePage {
  final NavEntry nav;
  final WidgetBuilder builder;
  const ConsolePage(this.nav, this.builder);
}

final consolePages = <ConsolePage>[
  ConsolePage(const NavEntry('Dashboard', Icons.dashboard_outlined),
      (_) => const DashboardScreen()),
  ConsolePage(const NavEntry('Triage Queue', Icons.flag_outlined),
      (_) => const TriageScreen()),
  ConsolePage(const NavEntry('Campaign Clusters', Icons.hub_outlined),
      (_) => const ClustersScreen()),
  ConsolePage(const NavEntry('Deepfake Feed', Icons.smart_display_outlined),
      (_) => const DeepfakeScreen()),
  ConsolePage(const NavEntry('Exec Protection', Icons.shield_outlined),
      (_) => const ExecScreen()),
  ConsolePage(const NavEntry('Brand Management', Icons.business_outlined),
      (_) => const BrandsScreen()),
  ConsolePage(const NavEntry('Cost Attribution', Icons.payments_outlined),
      (_) => const CostScreen()),
  ConsolePage(const NavEntry('Audit Log', Icons.receipt_long_outlined),
      (_) => const AuditScreen()),
];

class Console extends StatefulWidget {
  const Console({super.key});
  @override
  State<Console> createState() => _ConsoleState();
}

class _ConsoleState extends State<Console> {
  int _selected = 0;
  bool _collapsed = false;

  @override
  void initState() {
    super.initState();
    // Probe the backend so the LIVE/SEED pill reflects reality on first paint.
    Api.instance.health();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Row(
        children: [
          NavRail(
            items: consolePages.map((p) => p.nav).toList(),
            selected: _selected,
            collapsed: _collapsed,
            onSelect: (i) => setState(() => _selected = i),
            onToggle: () => setState(() => _collapsed = !_collapsed),
          ),
          Expanded(
            child: Column(
              children: [
                _TopBar(),
                Expanded(
                  child: Container(
                    color: SvColors.bg,
                    padding: const EdgeInsets.all(24),
                    child: consolePages[_selected].builder(context),
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

class _TopBar extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      height: 56,
      color: SvColors.panel2,
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Row(
        children: [
          Expanded(
            child: Container(
              height: 30,
              alignment: Alignment.centerLeft,
              padding: const EdgeInsets.symmetric(horizontal: 14),
              constraints: const BoxConstraints(maxWidth: 420),
              decoration: BoxDecoration(
                color: SvColors.bg,
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: SvColors.border),
              ),
              child: const Text('Search alerts, URLs, domains…',
                  style: TextStyle(color: SvColors.faint, fontSize: 12)),
            ),
          ),
          const SizedBox(width: 16),
          const SourcePill(),
          const SizedBox(width: 12),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
            decoration: BoxDecoration(
                color: SvColors.chip, borderRadius: BorderRadius.circular(14)),
            child: const Text('AcmeBank ▾',
                style: TextStyle(color: SvColors.text, fontSize: 12)),
          ),
        ],
      ),
    );
  }
}
