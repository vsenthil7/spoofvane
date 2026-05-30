// App root: theme, the Console shell (nav rail + top bar + content), and the
// page registry (lib/pages.dart) that maps each rail entry to its screen with
// role-gating.
import 'package:flutter/material.dart';

import 'api.dart';
import 'pages.dart';
import 'roles.dart';
import 'theme.dart';
import 'widgets/nav_rail.dart';
import 'widgets/source_pill.dart';
import 'screens/login_screen.dart';

class SpoofVaneApp extends StatelessWidget {
  const SpoofVaneApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SpoofVane',
      debugShowCheckedModeBanner: false,
      theme: buildSvTheme(),
      home: const LoginScreen(),
    );
  }
}

class Console extends StatefulWidget {
  /// Role the console renders for (drives nav visibility). Defaults to analyst
  /// for the demo; a real login (P01) would set this.
  final Role role;
  const Console({super.key, this.role = Role.analyst});
  @override
  State<Console> createState() => _ConsoleState();
}

class _ConsoleState extends State<Console> {
  int _selected = 0;
  bool _collapsed = false;

  late final List<PageMeta> _pages = navPagesFor(widget.role);

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
            items: _pages
                .map((p) => NavEntry(p.title, p.icon))
                .toList(),
            selected: _selected,
            collapsed: _collapsed,
            onSelect: (i) => setState(() => _selected = i),
            onToggle: () => setState(() => _collapsed = !_collapsed),
          ),
          Expanded(
            child: Column(
              children: [
                _TopBar(role: widget.role),
                Expanded(
                  child: Container(
                    color: SvColors.bg,
                    padding: const EdgeInsets.all(24),
                    child: _pages[_selected].builder(context),
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
  final Role role;
  const _TopBar({required this.role});
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
          // Current role chip (surfaces the role the console is gated to).
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
                color: SvColors.chip, borderRadius: BorderRadius.circular(14)),
            child: Text(roleLabel(role),
                style: const TextStyle(color: SvColors.cyan, fontSize: 11)),
          ),
          const SizedBox(width: 8),
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
