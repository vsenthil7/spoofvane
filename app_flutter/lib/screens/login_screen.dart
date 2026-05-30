// P01 — Login. Demo-friendly sign-in: a "Continue with Google" demo button plus
// similar demo options (Microsoft / SSO-OIDC / SAML), an email+password form,
// and a role selector so the demo can show how the console menu is gated per
// role. Every option is a DEMO entry (no real auth) — it just opens the Console
// shell as the chosen role. Mirrors the MeDo sign-in design (design_refs/).
import 'package:flutter/material.dart';
import '../app.dart';
import '../roles.dart';
import '../theme.dart';
import 'register_screen.dart';
import 'pricing_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});
  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  Role _role = Role.analyst;

  void _enter() {
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(builder: (_) => Console(role: _role)),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: SvColors.bg,
      body: Center(
        child: SingleChildScrollView(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 400),
            child: Container(
              key: const Key('login-card'),
              margin: const EdgeInsets.all(24),
              padding: const EdgeInsets.all(28),
              decoration: BoxDecoration(
                color: SvColors.panel,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: SvColors.border),
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Brand mark.
                  RichText(
                    textAlign: TextAlign.center,
                    text: const TextSpan(children: [
                      TextSpan(
                          text: '⬡ Spoof',
                          style: TextStyle(
                              color: SvColors.text,
                              fontFamily: 'Georgia',
                              fontWeight: FontWeight.bold,
                              fontSize: 24)),
                      TextSpan(
                          text: 'Vane',
                          style: TextStyle(
                              color: SvColors.amber,
                              fontFamily: 'Georgia',
                              fontWeight: FontWeight.bold,
                              fontSize: 24)),
                    ]),
                  ),
                  const SizedBox(height: 6),
                  const Text('Sign in to the SOC console',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: SvColors.muted, fontSize: 12)),
                  const SizedBox(height: 24),

                  // Demo SSO buttons — Google + similar options.
                  _DemoButton(
                      key: const Key('login-google'),
                      label: 'Continue with Google (demo)',
                      icon: Icons.g_mobiledata,
                      iconColor: const Color(0xFF4285F4),
                      onTap: _enter),
                  const SizedBox(height: 8),
                  _DemoButton(
                      key: const Key('login-microsoft'),
                      label: 'Continue with Microsoft (demo)',
                      icon: Icons.window,
                      iconColor: const Color(0xFF00A4EF),
                      onTap: _enter),
                  const SizedBox(height: 8),
                  _DemoButton(
                      key: const Key('login-sso'),
                      label: 'Continue with SSO / OIDC (demo)',
                      icon: Icons.vpn_key_outlined,
                      iconColor: SvColors.cyan,
                      onTap: _enter),
                  const SizedBox(height: 8),
                  _DemoButton(
                      key: const Key('login-saml'),
                      label: 'Continue with SAML (demo)',
                      icon: Icons.security_outlined,
                      iconColor: SvColors.cyan,
                      onTap: _enter),

                  const SizedBox(height: 16),
                  const Row(children: [
                    Expanded(child: Divider(color: SvColors.border)),
                    Padding(
                      padding: EdgeInsets.symmetric(horizontal: 10),
                      child: Text('or',
                          style: TextStyle(color: SvColors.faint, fontSize: 11)),
                    ),
                    Expanded(child: Divider(color: SvColors.border)),
                  ]),
                  const SizedBox(height: 16),

                  // Email + password (demo — not validated).
                  _field(const Key('login-email'), 'email', false),
                  const SizedBox(height: 8),
                  _field(const Key('login-password'), 'password', true),
                  const SizedBox(height: 16),

                  // Role selector — demo can show each role's gated menu.
                  const Text('Demo role',
                      style: TextStyle(color: SvColors.faint, fontSize: 11)),
                  const SizedBox(height: 6),
                  DropdownButtonFormField<Role>(
                    key: const Key('login-role'),
                    value: _role,
                    dropdownColor: SvColors.panel2,
                    decoration: InputDecoration(
                      filled: true,
                      fillColor: SvColors.bg,
                      contentPadding:
                          const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(6),
                        borderSide: const BorderSide(color: SvColors.border),
                      ),
                    ),
                    style: const TextStyle(color: SvColors.text, fontSize: 13),
                    items: [
                      for (final r in Role.values)
                        DropdownMenuItem(
                            value: r, child: Text(roleLabel(r))),
                    ],
                    onChanged: (r) => setState(() => _role = r ?? Role.analyst),
                  ),
                  const SizedBox(height: 16),

                  ElevatedButton(
                    key: const Key('login-signin'),
                    style: ElevatedButton.styleFrom(
                        backgroundColor: SvColors.amber,
                        foregroundColor: const Color(0xFF1A1300),
                        padding: const EdgeInsets.symmetric(vertical: 14)),
                    onPressed: _enter,
                    child: const Text('Sign in',
                        style: TextStyle(fontWeight: FontWeight.bold)),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Flexible(
                        child: TextButton(
                          key: const Key('login-to-register'),
                          style: TextButton.styleFrom(
                              padding: const EdgeInsets.symmetric(horizontal: 8),
                              tapTargetSize: MaterialTapTargetSize.shrinkWrap),
                          onPressed: () => Navigator.of(context).push(
                              MaterialPageRoute(
                                  builder: (_) => const RegisterScreen())),
                          child: const Text('Create account',
                              style: TextStyle(color: SvColors.cyan, fontSize: 12)),
                        ),
                      ),
                      const Text('·',
                          style: TextStyle(color: SvColors.faint, fontSize: 12)),
                      Flexible(
                        child: TextButton(
                          key: const Key('login-to-pricing'),
                          style: TextButton.styleFrom(
                              padding: const EdgeInsets.symmetric(horizontal: 8),
                              tapTargetSize: MaterialTapTargetSize.shrinkWrap),
                          onPressed: () => Navigator.of(context).push(
                              MaterialPageRoute(
                                  builder: (_) => const PricingScreen())),
                          child: const Text('View pricing',
                              style: TextStyle(color: SvColors.cyan, fontSize: 12)),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _field(Key key, String hint, bool obscure) => TextField(
        key: key,
        obscureText: obscure,
        style: const TextStyle(color: SvColors.text, fontSize: 13),
        decoration: InputDecoration(
          hintText: hint,
          hintStyle: const TextStyle(color: SvColors.faint, fontSize: 13),
          filled: true,
          fillColor: SvColors.bg,
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(6),
            borderSide: const BorderSide(color: SvColors.border),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(6),
            borderSide: const BorderSide(color: SvColors.border),
          ),
        ),
      );
}

class _DemoButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final Color iconColor;
  final VoidCallback onTap;
  const _DemoButton({
    super.key,
    required this.label,
    required this.icon,
    required this.iconColor,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return OutlinedButton.icon(
      onPressed: onTap,
      style: OutlinedButton.styleFrom(
        foregroundColor: SvColors.text,
        backgroundColor: SvColors.panel2,
        side: const BorderSide(color: SvColors.border),
        padding: const EdgeInsets.symmetric(vertical: 12),
        alignment: Alignment.centerLeft,
      ),
      icon: Icon(icon, color: iconColor, size: 20),
      label: Text(label,
          style: const TextStyle(fontSize: 13, color: SvColors.text)),
    );
  }
}
