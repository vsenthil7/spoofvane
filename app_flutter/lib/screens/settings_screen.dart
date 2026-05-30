// P19 — Settings. Your profile, MFA enrolment, and API keys. This is the
// current user's own settings surface: state is local to the screen (demo), so
// there's no backend fetch — toggles and key reveal/rotate act on local state.
import 'package:flutter/material.dart';
import '../theme.dart';
import '../widgets/panel.dart';
import '../widgets/screen_title.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});
  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  bool _mfaEnabled = true;
  bool _emailAlerts = true;
  bool _keyRevealed = false;
  String _apiKey = 'sv_live_8f2c…a91b';

  @override
  Widget build(BuildContext context) {
    return ListView(
      key: const Key('settings-list'),
      children: [
        const ScreenTitle('Settings', sub: 'Profile, security and API access'),
        _profilePanel(),
        _securityPanel(),
        _apiKeysPanel(),
      ],
    );
  }

  Widget _profilePanel() {
    return Panel(
      title: 'Profile',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _kv('Name', 'Demo Analyst'),
          _kv('Email', 'analyst.kim@demotenant.io'),
          _kv('Tenant', 'DemoTenant'),
          _kv('Role', 'analyst'),
        ],
      ),
    );
  }

  Widget _securityPanel() {
    return Panel(
      title: 'Security',
      child: Column(
        children: [
          SwitchListTile(
            key: const Key('settings-mfa'),
            contentPadding: EdgeInsets.zero,
            activeColor: SvColors.benign,
            title: const Text('Multi-factor authentication (TOTP)',
                style: TextStyle(color: SvColors.text, fontSize: 13)),
            subtitle: Text(_mfaEnabled ? 'Enrolled' : 'Not enrolled',
                style: TextStyle(
                    color: _mfaEnabled ? SvColors.benign : SvColors.amber,
                    fontSize: 11)),
            value: _mfaEnabled,
            onChanged: (v) => setState(() => _mfaEnabled = v),
          ),
          SwitchListTile(
            key: const Key('settings-email-alerts'),
            contentPadding: EdgeInsets.zero,
            activeColor: SvColors.benign,
            title: const Text('Email me on new phish verdicts',
                style: TextStyle(color: SvColors.text, fontSize: 13)),
            value: _emailAlerts,
            onChanged: (v) => setState(() => _emailAlerts = v),
          ),
        ],
      ),
    );
  }

  Widget _apiKeysPanel() {
    return Panel(
      title: 'API keys',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                    _keyRevealed ? 'sv_live_8f2c0d4471e2a91b' : _apiKey,
                    key: const Key('settings-apikey'),
                    style: const TextStyle(
                        color: SvColors.text,
                        fontFamily: 'monospace',
                        fontSize: 13)),
              ),
              TextButton(
                key: const Key('settings-reveal-key'),
                onPressed: () => setState(() => _keyRevealed = !_keyRevealed),
                child: Text(_keyRevealed ? 'Hide' : 'Reveal',
                    style: const TextStyle(color: SvColors.cyan, fontSize: 12)),
              ),
              TextButton(
                key: const Key('settings-rotate-key'),
                onPressed: () => setState(() {
                  _apiKey = 'sv_live_4b7e…32cf';
                  _keyRevealed = false;
                  ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
                      content: Text('API key rotated (demo)')));
                }),
                child: const Text('Rotate',
                    style: TextStyle(color: SvColors.amber, fontSize: 12)),
              ),
            ],
          ),
          const SizedBox(height: 6),
          const Text(
              'Keep this secret. Rotating immediately invalidates the old key.',
              style: TextStyle(color: SvColors.faint, fontSize: 11)),
        ],
      ),
    );
  }

  Widget _kv(String k, String v) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Row(
          children: [
            SizedBox(
                width: 120,
                child: Text(k,
                    style: const TextStyle(color: SvColors.faint, fontSize: 12))),
            Text(v,
                style: const TextStyle(color: SvColors.text, fontSize: 13)),
          ],
        ),
      );
}
