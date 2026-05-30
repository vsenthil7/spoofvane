// P16 — Admin · Users. RBAC management — the six roles with segregation of
// duties. Lists users with role, MFA status, and last-active. Role is editable
// via a dropdown (demo-local).
import 'package:flutter/material.dart';
import '../api.dart';
import '../models.dart';
import '../roles.dart';
import '../theme.dart';
import '../util/format.dart';
import '../widgets/panel.dart';
import '../widgets/screen_title.dart';

class AdminUsersScreen extends StatefulWidget {
  const AdminUsersScreen({super.key});
  @override
  State<AdminUsersScreen> createState() => _AdminUsersScreenState();
}

class _AdminUsersScreenState extends State<AdminUsersScreen> {
  final Future<List<AdminUser>> _q = Api.instance.adminUsers();
  final Map<String, String> _roleEdits = {};

  String _roleOf(AdminUser u) => _roleEdits[u.id] ?? u.role;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<AdminUser>>(
      future: _q,
      builder: (_, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        final users = snap.data ?? [];
        final noMfa = users.where((u) => !u.mfaEnabled).length;
        return ListView(
          key: const Key('users-list'),
          children: [
            ScreenTitle('Users',
                sub:
                    '${users.length} users · $noMfa without MFA · 6 RBAC roles'),
            Panel(
              child: Column(
                children: [
                  const Row(children: [
                    SizedBox(width: 260, child: HeaderLabel('EMAIL')),
                    SizedBox(width: 140, child: HeaderLabel('ROLE')),
                    SizedBox(width: 70, child: HeaderLabel('MFA')),
                    Expanded(child: HeaderLabel('LAST ACTIVE')),
                  ]),
                  const Divider(color: SvColors.border),
                  ...users.map(_userRow),
                ],
              ),
            ),
          ],
        );
      },
    );
  }

  Widget _userRow(AdminUser u) {
    final role = _roleOf(u);
    return Padding(
      key: Key('user-row-${u.id}'),
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          SizedBox(
              width: 260,
              child: Text(u.email,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                      color: SvColors.text,
                      fontFamily: 'monospace',
                      fontSize: 12))),
          SizedBox(
            width: 140,
            child: DropdownButton<String>(
              key: Key('user-role-${u.id}'),
              value: role,
              isDense: true,
              underline: const SizedBox.shrink(),
              dropdownColor: SvColors.panel2,
              style: const TextStyle(color: SvColors.text, fontSize: 12),
              items: [
                for (final r in Role.values)
                  DropdownMenuItem(value: r.name, child: Text(r.name)),
              ],
              onChanged: (v) => setState(() => _roleEdits[u.id] = v ?? u.role),
            ),
          ),
          SizedBox(
            width: 70,
            child: Icon(u.mfaEnabled ? Icons.lock : Icons.lock_open,
                key: Key('user-mfa-${u.id}'),
                size: 15,
                color: u.mfaEnabled ? SvColors.benign : SvColors.phish),
          ),
          Expanded(
              child: Text(fmtTime(u.lastActive),
                  style: const TextStyle(color: SvColors.muted, fontSize: 11))),
        ],
      ),
    );
  }
}
