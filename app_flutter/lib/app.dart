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
  String _tenant = 'AcmeBank';

  late final List<PageMeta> _pages = navPagesFor(widget.role);

  // Demo tenants the account menu can switch between.
  static const _tenants = ['AcmeBank', 'GlobalPay', 'NorthVault', 'DemoTenant'];

  void _switchRole(Role r) {
    if (r == widget.role) return;
    // Re-enter the console as the new role so the rail re-gates.
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(builder: (_) => Console(role: r)),
    );
  }

  void _switchTenant(String t) => setState(() => _tenant = t);

  void _logout() {
    // Clear the whole stack and return to the login screen so there is no
    // "back" path into the authenticated console.
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const LoginScreen()),
      (route) => false,
    );
  }

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
                _TopBar(
                  role: widget.role,
                  tenant: _tenant,
                  tenants: _tenants,
                  onSwitchRole: _switchRole,
                  onSwitchTenant: _switchTenant,
                  onLogout: _logout,
                ),
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
  final String tenant;
  final List<String> tenants;
  final void Function(Role) onSwitchRole;
  final void Function(String) onSwitchTenant;
  final VoidCallback onLogout;
  const _TopBar({
    required this.role,
    required this.tenant,
    required this.tenants,
    required this.onSwitchRole,
    required this.onSwitchTenant,
    required this.onLogout,
  });

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
          // Account menu: current user/role/tenant + switch role + switch tenant
          // + log out. Replaces the previous display-only chips.
          _AccountMenu(
            role: role,
            tenant: tenant,
            tenants: tenants,
            onSwitchRole: onSwitchRole,
            onSwitchTenant: onSwitchTenant,
            onLogout: onLogout,
          ),
        ],
      ),
    );
  }
}

/// The top-right account menu. A single tappable chip (role · tenant · avatar)
/// opens a popup with: switch role (6 roles), switch tenant, and Log out.
class _AccountMenu extends StatelessWidget {
  final Role role;
  final String tenant;
  final List<String> tenants;
  final void Function(Role) onSwitchRole;
  final void Function(String) onSwitchTenant;
  final VoidCallback onLogout;
  const _AccountMenu({
    required this.role,
    required this.tenant,
    required this.tenants,
    required this.onSwitchRole,
    required this.onSwitchTenant,
    required this.onLogout,
  });

  @override
  Widget build(BuildContext context) {
    return PopupMenuButton<String>(
      key: const Key('account-menu'),
      tooltip: 'Account',
      offset: const Offset(0, 44),
      color: SvColors.panel2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(8),
        side: const BorderSide(color: SvColors.border),
      ),
      onSelected: (value) {
        if (value == 'logout') {
          onLogout();
        } else if (value.startsWith('role:')) {
          onSwitchRole(roleFromString(value.substring(5)));
        } else if (value.startsWith('tenant:')) {
          onSwitchTenant(value.substring(7));
        }
      },
      itemBuilder: (context) => [
        PopupMenuItem<String>(
          enabled: false,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('demo.user@$tenant.io'.toLowerCase(),
                  style: const TextStyle(color: SvColors.text, fontSize: 12)),
              const SizedBox(height: 2),
              Text('${roleLabel(role)} · $tenant',
                  style: const TextStyle(color: SvColors.faint, fontSize: 11)),
            ],
          ),
        ),
        const PopupMenuDivider(),
        PopupMenuItem<String>(
          enabled: false,
          child: Text('Switch role',
              style: TextStyle(
                  color: SvColors.faint,
                  fontSize: 10,
                  letterSpacing: 0.5,
                  fontWeight: FontWeight.w600)),
        ),
        for (final r in Role.values)
          PopupMenuItem<String>(
            key: Key('account-role-${r.name}'),
            value: 'role:${r.name}',
            child: Row(
              children: [
                Icon(r == role ? Icons.check : Icons.person_outline,
                    size: 16,
                    color: r == role ? SvColors.benign : SvColors.faint),
                const SizedBox(width: 10),
                Text(roleLabel(r),
                    style: const TextStyle(color: SvColors.text, fontSize: 13)),
              ],
            ),
          ),
        const PopupMenuDivider(),
        PopupMenuItem<String>(
          enabled: false,
          child: Text('Switch tenant',
              style: TextStyle(
                  color: SvColors.faint,
                  fontSize: 10,
                  letterSpacing: 0.5,
                  fontWeight: FontWeight.w600)),
        ),
        for (final t in tenants)
          PopupMenuItem<String>(
            key: Key('account-tenant-$t'),
            value: 'tenant:$t',
            child: Row(
              children: [
                Icon(t == tenant ? Icons.check : Icons.business_outlined,
                    size: 16,
                    color: t == tenant ? SvColors.benign : SvColors.faint),
                const SizedBox(width: 10),
                Text(t,
                    style: const TextStyle(color: SvColors.text, fontSize: 13)),
              ],
            ),
          ),
        const PopupMenuDivider(),
        PopupMenuItem<String>(
          key: const Key('account-logout'),
          value: 'logout',
          child: Row(
            children: const [
              Icon(Icons.logout, size: 16, color: SvColors.phish),
              SizedBox(width: 10),
              Text('Log out',
                  style: TextStyle(color: SvColors.phish, fontSize: 13)),
            ],
          ),
        ),
      ],
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
            color: SvColors.chip, borderRadius: BorderRadius.circular(14)),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(roleLabel(role),
                style: const TextStyle(color: SvColors.cyan, fontSize: 11)),
            const SizedBox(width: 8),
            Container(width: 1, height: 12, color: SvColors.border),
            const SizedBox(width: 8),
            Text(tenant,
                style: const TextStyle(color: SvColors.text, fontSize: 12)),
            const Icon(Icons.arrow_drop_down, color: SvColors.muted, size: 18),
          ],
        ),
      ),
    );
  }
}
