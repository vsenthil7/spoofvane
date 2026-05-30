// P17 — Admin · Tenants. Multi-tenant management, including each tenant's
// data-residency region, plan, seats, and active status. Owner-only.
import 'package:flutter/material.dart';
import '../api.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/panel.dart';
import '../widgets/screen_title.dart';

class AdminTenantsScreen extends StatelessWidget {
  const AdminTenantsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<Tenant>>(
      future: Api.instance.tenants(),
      builder: (_, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        final tenants = snap.data ?? [];
        final active = tenants.where((t) => t.active).length;
        final seats = tenants.fold<int>(0, (s, t) => s + t.seats);
        return ListView(
          key: const Key('tenants-list'),
          children: [
            ScreenTitle('Tenants',
                sub: '${tenants.length} tenants · $active active · $seats seats'),
            Panel(
              child: Column(
                children: [
                  const Row(children: [
                    SizedBox(width: 160, child: HeaderLabel('TENANT')),
                    SizedBox(width: 120, child: HeaderLabel('PLAN')),
                    SizedBox(width: 120, child: HeaderLabel('REGION')),
                    SizedBox(width: 80, child: HeaderLabel('SEATS')),
                    Expanded(child: HeaderLabel('STATUS')),
                  ]),
                  const Divider(color: SvColors.border),
                  ...tenants.map(_tenantRow),
                ],
              ),
            ),
          ],
        );
      },
    );
  }

  Widget _tenantRow(Tenant t) {
    return Padding(
      key: Key('tenant-row-${t.id}'),
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          SizedBox(
              width: 160,
              child: Text(t.name,
                  style: const TextStyle(
                      color: SvColors.text,
                      fontSize: 13,
                      fontWeight: FontWeight.w600))),
          SizedBox(
              width: 120,
              child: Text(t.plan,
                  style: const TextStyle(color: SvColors.amber, fontSize: 12))),
          SizedBox(
              width: 120,
              child: Text(t.region,
                  style: const TextStyle(
                      color: SvColors.muted,
                      fontFamily: 'monospace',
                      fontSize: 12))),
          SizedBox(
              width: 80,
              child: Text('${t.seats}',
                  style: const TextStyle(color: SvColors.text, fontSize: 12))),
          Expanded(
            child: Row(children: [
              Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                      color: t.active ? SvColors.benign : SvColors.faint,
                      shape: BoxShape.circle)),
              const SizedBox(width: 6),
              Text(t.active ? 'active' : 'suspended',
                  key: Key('tenant-status-${t.id}'),
                  style: TextStyle(
                      color: t.active ? SvColors.benign : SvColors.faint,
                      fontSize: 11)),
            ]),
          ),
        ],
      ),
    );
  }
}
