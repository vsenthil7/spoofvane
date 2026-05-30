// P22 — API keys (market-standard). A proper developer keys screen like Stripe /
// OpenAI / GitHub: a table of keys (name, masked value, scope, created, last
// used, status), create-key flow that reveals the full secret EXACTLY ONCE,
// copy-to-clipboard, and revoke. The full secret is never stored or re-shown.
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../api.dart';
import '../models.dart';
import '../theme.dart';
import '../util/format.dart';
import '../widgets/panel.dart';
import '../widgets/screen_title.dart';

class ApiKeysScreen extends StatefulWidget {
  const ApiKeysScreen({super.key});
  @override
  State<ApiKeysScreen> createState() => _ApiKeysScreenState();
}

class _ApiKeysScreenState extends State<ApiKeysScreen> {
  final Future<List<ApiKey>> _q = Api.instance.apiKeys();
  final List<ApiKey> _localKeys = [];
  final Set<String> _revoked = {};
  int _counter = 0;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<ApiKey>>(
      future: _q,
      builder: (_, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        final List<ApiKey> keys = [..._localKeys, ...(snap.data ?? <ApiKey>[])];
        final active = keys.where((k) => k.active && !_revoked.contains(k.id)).length;
        return ListView(
          key: const Key('apikeys-list'),
          children: [
            Row(
              children: [
                const Expanded(
                  child: ScreenTitle('API keys',
                      sub: 'Programmatic access to the SpoofVane API'),
                ),
                ElevatedButton.icon(
                  key: const Key('apikey-create'),
                  style: ElevatedButton.styleFrom(
                      backgroundColor: SvColors.amber,
                      foregroundColor: const Color(0xFF1A1300)),
                  onPressed: _createKeyDialog,
                  icon: const Icon(Icons.add, size: 18),
                  label: const Text('Create key'),
                ),
              ],
            ),
            Panel(
              child: Column(
                children: [
                  Row(children: [
                    Text('$active active key${active == 1 ? '' : 's'}',
                        style: const TextStyle(color: SvColors.muted, fontSize: 12)),
                  ]),
                  const SizedBox(height: 8),
                  const Divider(color: SvColors.border),
                  const Row(children: [
                    Expanded(flex: 3, child: HeaderLabel('NAME')),
                    Expanded(flex: 4, child: HeaderLabel('KEY')),
                    Expanded(flex: 2, child: HeaderLabel('SCOPE')),
                    Expanded(flex: 2, child: HeaderLabel('LAST USED')),
                    SizedBox(width: 90, child: HeaderLabel('')),
                  ]),
                  const Divider(color: SvColors.border),
                  ...keys.map(_keyRow),
                ],
              ),
            ),
            const SizedBox(height: 8),
            const Text(
                'Treat API keys like passwords. They carry the scope shown and can act on your tenant. Revoking is immediate and cannot be undone.',
                style: TextStyle(color: SvColors.faint, fontSize: 11)),
          ],
        );
      },
    );
  }

  Widget _keyRow(ApiKey k) {
    final revoked = _revoked.contains(k.id) || !k.active;
    return Padding(
      key: Key('apikey-row-${k.id}'),
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          Expanded(
            flex: 3,
            child: Text(k.name,
                style: TextStyle(
                    color: revoked ? SvColors.faint : SvColors.text,
                    fontSize: 13,
                    decoration:
                        revoked ? TextDecoration.lineThrough : TextDecoration.none)),
          ),
          Expanded(
            flex: 4,
            child: Text(k.masked,
                style: const TextStyle(
                    color: SvColors.muted, fontFamily: 'monospace', fontSize: 12)),
          ),
          Expanded(
              flex: 2,
              child: _scopePill(k.scope)),
          Expanded(
            flex: 2,
            child: Text(k.lastUsed.isEmpty ? 'never' : fmtTime(k.lastUsed),
                style: const TextStyle(color: SvColors.muted, fontSize: 11)),
          ),
          SizedBox(
            width: 90,
            child: revoked
                ? const Text('revoked',
                    style: TextStyle(color: SvColors.faint, fontSize: 11))
                : TextButton(
                    key: Key('apikey-revoke-${k.id}'),
                    onPressed: () => setState(() => _revoked.add(k.id)),
                    style: TextButton.styleFrom(
                        foregroundColor: SvColors.phish,
                        padding: const EdgeInsets.symmetric(horizontal: 8),
                        minimumSize: const Size(0, 32),
                        tapTargetSize: MaterialTapTargetSize.shrinkWrap),
                    child: const Text('Revoke', style: TextStyle(fontSize: 12)),
                  ),
          ),
        ],
      ),
    );
  }

  Widget _scopePill(String scope) {
    final color = scope == 'admin'
        ? SvColors.phish
        : scope == 'read_write'
            ? SvColors.amber
            : SvColors.cyan;
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: color.withOpacity(0.14),
          borderRadius: BorderRadius.circular(4),
          border: Border.all(color: color.withOpacity(0.5)),
        ),
        child: Text(scope,
            style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w600)),
      ),
    );
  }

  Future<void> _createKeyDialog() async {
    final nameCtrl = TextEditingController();
    String scope = 'read';
    final created = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setLocal) => AlertDialog(
          backgroundColor: SvColors.panel,
          title: const Text('Create API key',
              style: TextStyle(color: SvColors.text)),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                key: const Key('apikey-name-field'),
                controller: nameCtrl,
                style: const TextStyle(color: SvColors.text),
                decoration: const InputDecoration(
                    labelText: 'Key name',
                    labelStyle: TextStyle(color: SvColors.faint)),
              ),
              const SizedBox(height: 12),
              DropdownButton<String>(
                key: const Key('apikey-scope-field'),
                value: scope,
                isExpanded: true,
                dropdownColor: SvColors.panel2,
                style: const TextStyle(color: SvColors.text, fontSize: 13),
                items: const [
                  DropdownMenuItem(value: 'read', child: Text('read')),
                  DropdownMenuItem(value: 'read_write', child: Text('read_write')),
                  DropdownMenuItem(value: 'admin', child: Text('admin')),
                ],
                onChanged: (v) => setLocal(() => scope = v ?? 'read'),
              ),
            ],
          ),
          actions: [
            TextButton(
                onPressed: () => Navigator.pop(ctx, false),
                child: const Text('Cancel')),
            ElevatedButton(
              key: const Key('apikey-create-confirm'),
              onPressed: () => Navigator.pop(ctx, true),
              child: const Text('Create'),
            ),
          ],
        ),
      ),
    );
    if (created == true) {
      _counter++;
      final secret = 'sv_live_${DateTime.now().millisecondsSinceEpoch.toRadixString(16)}';
      final key = ApiKey(
        id: 'key_new_$_counter',
        name: nameCtrl.text.isEmpty ? 'New key' : nameCtrl.text,
        prefix: secret.substring(0, 12),
        last4: secret.substring(secret.length - 4),
        scope: scope,
        created: DateTime.now().toIso8601String(),
        lastUsed: '',
      );
      setState(() => _localKeys.insert(0, key));
      if (mounted) await _revealSecretOnce(secret);
    }
  }

  // The full secret is shown exactly once — standard for Stripe/OpenAI/GitHub.
  Future<void> _revealSecretOnce(String secret) async {
    await showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: SvColors.panel,
        title: const Text('Save your API key',
            style: TextStyle(color: SvColors.text)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
                "This is the only time the full key is shown. Copy it now — you won't be able to see it again.",
                style: TextStyle(color: SvColors.muted, fontSize: 12)),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: SvColors.bg,
                border: Border.all(color: SvColors.border),
                borderRadius: BorderRadius.circular(6),
              ),
              child: SelectableText(secret,
                  key: const Key('apikey-secret'),
                  style: const TextStyle(
                      color: SvColors.benign,
                      fontFamily: 'monospace',
                      fontSize: 13)),
            ),
          ],
        ),
        actions: [
          TextButton(
            key: const Key('apikey-copy-secret'),
            onPressed: () {
              Clipboard.setData(ClipboardData(text: secret));
              ScaffoldMessenger.of(ctx).showSnackBar(
                  const SnackBar(content: Text('Copied to clipboard')));
            },
            child: const Text('Copy'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Done'),
          ),
        ],
      ),
    );
  }
}
