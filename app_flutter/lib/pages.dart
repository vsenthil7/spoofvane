// The canonical 21-page registry (P01–P21), the Flutter analogue of
// console/src/lib/pages.ts. The shell's nav rail, routing, and role-gating all
// read this single list so "21 pages" lives in one place and stays aligned with
// the React/convergence registry. Screens not yet built map to PlaceholderScreen
// (honest "planned"), so the full structure is navigable today.
import 'package:flutter/material.dart';

import 'roles.dart';
import 'screens/dashboard_screen.dart';
import 'screens/triage_screen.dart';
import 'screens/clusters_screen.dart';
import 'screens/deepfake_screen.dart';
import 'screens/exec_screen.dart';
import 'screens/brands_screen.dart';
import 'screens/cost_screen.dart';
import 'screens/audit_screen.dart';
import 'screens/review_queue_screen.dart';
import 'screens/takedowns_screen.dart';
import 'screens/compliance_screen.dart';
import 'screens/admin_agents_screen.dart';
import 'screens/admin_users_screen.dart';
import 'screens/admin_tenants_screen.dart';
import 'screens/admin_demo_health_screen.dart';
import 'screens/login_screen.dart';
import 'screens/placeholder_screen.dart';

/// One console page: registry metadata + the screen builder it routes to.
class PageMeta {
  final String id; // P01..P21
  final String route; // /triage, /alerts/:id, *
  final String title;
  final Role minRole;
  final bool nav; // appears in the rail?
  final IconData icon;
  final WidgetBuilder builder;
  final bool built; // true = real screen, false = placeholder

  const PageMeta({
    required this.id,
    required this.route,
    required this.title,
    required this.minRole,
    required this.nav,
    required this.icon,
    required this.builder,
    this.built = true,
  });
}

PageMeta _planned({
  required String id,
  required String route,
  required String title,
  required Role minRole,
  required bool nav,
  required IconData icon,
}) =>
    PageMeta(
      id: id,
      route: route,
      title: title,
      minRole: minRole,
      nav: nav,
      icon: icon,
      built: false,
      builder: (_) => PlaceholderScreen(title: title, pageId: id),
    );

/// All 21 canonical pages, in spec order.
final List<PageMeta> kPages = <PageMeta>[
  PageMeta(id: 'P01', route: '/login', title: 'Sign in', minRole: Role.viewer, nav: false, icon: Icons.login_outlined, builder: (_) => const LoginScreen()),
  PageMeta(id: 'P02', route: '/', title: 'Dashboard', minRole: Role.viewer, nav: true, icon: Icons.dashboard_outlined, builder: (_) => const DashboardScreen()),
  PageMeta(id: 'P03', route: '/brands', title: 'Brands', minRole: Role.analyst, nav: true, icon: Icons.business_outlined, builder: (_) => const BrandsScreen()),
  _planned(id: 'P04', route: '/brands/:id', title: 'Brand detail', minRole: Role.analyst, nav: false, icon: Icons.business_outlined),
  PageMeta(id: 'P05', route: '/triage', title: 'Triage Queue', minRole: Role.analyst, nav: true, icon: Icons.flag_outlined, builder: (_) => const TriageScreen()),
  _planned(id: 'P06', route: '/alerts/:id', title: 'Alert detail', minRole: Role.analyst, nav: false, icon: Icons.warning_amber_outlined),
  PageMeta(id: 'P07', route: '/clusters', title: 'Campaign Clusters', minRole: Role.analyst, nav: true, icon: Icons.hub_outlined, builder: (_) => const ClustersScreen()),
  PageMeta(id: 'P08', route: '/deepfakes', title: 'Deepfake Feed', minRole: Role.analyst, nav: true, icon: Icons.smart_display_outlined, builder: (_) => const DeepfakeScreen()),
  PageMeta(id: 'P09', route: '/exec-protection', title: 'Exec Protection', minRole: Role.analyst, nav: true, icon: Icons.shield_outlined, builder: (_) => const ExecScreen()),
  PageMeta(id: 'P10', route: '/takedowns', title: 'Takedowns', minRole: Role.analyst, nav: true, icon: Icons.content_cut_outlined, builder: (_) => const TakedownsScreen()),
  PageMeta(id: 'P11', route: '/audit', title: 'Audit Log', minRole: Role.auditor, nav: true, icon: Icons.receipt_long_outlined, builder: (_) => const AuditScreen()),
  PageMeta(id: 'P12', route: '/review', title: 'Review queue', minRole: Role.reviewer, nav: true, icon: Icons.check_circle_outline, builder: (_) => const ReviewQueueScreen()),
  PageMeta(id: 'P13', route: '/cost', title: 'Cost Attribution', minRole: Role.admin, nav: true, icon: Icons.payments_outlined, builder: (_) => const CostScreen()),
  PageMeta(id: 'P14', route: '/compliance', title: 'Compliance', minRole: Role.auditor, nav: true, icon: Icons.gavel_outlined, builder: (_) => const ComplianceScreen()),
  PageMeta(id: 'P15', route: '/admin/agents', title: 'Agents', minRole: Role.admin, nav: true, icon: Icons.settings_suggest_outlined, builder: (_) => const AdminAgentsScreen()),
  PageMeta(id: 'P16', route: '/admin/users', title: 'Users', minRole: Role.admin, nav: true, icon: Icons.group_outlined, builder: (_) => const AdminUsersScreen()),
  PageMeta(id: 'P17', route: '/admin/tenants', title: 'Tenants', minRole: Role.owner, nav: true, icon: Icons.apartment_outlined, builder: (_) => const AdminTenantsScreen()),
  PageMeta(id: 'P18', route: '/admin/demo-health', title: 'Demo health', minRole: Role.admin, nav: true, icon: Icons.favorite_outline, builder: (_) => const AdminDemoHealthScreen()),
  _planned(id: 'P19', route: '/settings', title: 'Settings', minRole: Role.viewer, nav: true, icon: Icons.settings_outlined),
  _planned(id: 'P20', route: '*', title: 'Not found', minRole: Role.viewer, nav: false, icon: Icons.close),
  _planned(id: 'P21', route: '/403', title: 'Forbidden', minRole: Role.viewer, nav: false, icon: Icons.block),
];

/// Must equal 21 (asserted in tests, mirrors PAGE_COUNT in pages.ts).
final int kPageCount = kPages.length;

/// Pages that appear in the rail for [role] (nav==true and role-allowed).
List<PageMeta> navPagesFor(Role role) =>
    kPages.where((p) => p.nav && roleAllows(role, p.minRole)).toList();
