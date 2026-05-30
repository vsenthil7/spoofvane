// P26 — Registration (public sign-up). Standard SaaS account-creation form:
// work email, company, password + strength, plan pre-select, and demo SSO sign-up
// options. This is a DEMO flow — it does not create a real account or perform
// real auth; "Create account" proceeds to onboarding.
import 'package:flutter/material.dart';
import '../theme.dart';
import 'onboarding_screen.dart';
import 'login_screen.dart';

class RegisterScreen extends StatefulWidget {
  final String? plan; // optional plan pre-selected from Pricing
  const RegisterScreen({super.key, this.plan});
  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _email = TextEditingController();
  final _company = TextEditingController();
  final _password = TextEditingController();
  bool _agreed = false;

  double get _strength {
    final p = _password.text;
    var s = 0.0;
    if (p.length >= 8) s += 0.34;
    if (RegExp(r'[A-Z]').hasMatch(p) && RegExp(r'[a-z]').hasMatch(p)) s += 0.33;
    if (RegExp(r'[0-9!@#\$%^&*]').hasMatch(p)) s += 0.33;
    return s.clamp(0, 1);
  }

  bool get _canSubmit =>
      _email.text.contains('@') &&
      _company.text.isNotEmpty &&
      _strength >= 0.67 &&
      _agreed;

  void _register() {
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(builder: (_) => const OnboardingScreen()),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: SvColors.bg,
      body: Center(
        child: SingleChildScrollView(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Container(
              key: const Key('register-card'),
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
                  const Text('Create your account',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                          color: SvColors.text,
                          fontFamily: 'Georgia',
                          fontWeight: FontWeight.bold,
                          fontSize: 22)),
                  const SizedBox(height: 4),
                  Text(
                      widget.plan != null
                          ? 'Starting your ${widget.plan} plan trial'
                          : 'Start your 14-day free trial. No card required.',
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: SvColors.muted, fontSize: 12)),
                  const SizedBox(height: 20),

                  // Demo SSO sign-up options.
                  _SsoButton(
                      key: const Key('register-google'),
                      label: 'Sign up with Google (demo)',
                      icon: Icons.g_mobiledata,
                      color: const Color(0xFF4285F4),
                      onTap: _register),
                  const SizedBox(height: 8),
                  _SsoButton(
                      key: const Key('register-microsoft'),
                      label: 'Sign up with Microsoft (demo)',
                      icon: Icons.window,
                      color: const Color(0xFF00A4EF),
                      onTap: _register),
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

                  _field(const Key('register-email'), _email, 'Work email', false),
                  const SizedBox(height: 8),
                  _field(const Key('register-company'), _company, 'Company', false),
                  const SizedBox(height: 8),
                  _field(const Key('register-password'), _password, 'Password',
                      true),
                  const SizedBox(height: 8),
                  // Password strength meter.
                  ClipRRect(
                    borderRadius: BorderRadius.circular(3),
                    child: LinearProgressIndicator(
                      value: _strength,
                      minHeight: 5,
                      backgroundColor: SvColors.bg,
                      valueColor: AlwaysStoppedAnimation(_strength >= 0.67
                          ? SvColors.benign
                          : _strength >= 0.34
                              ? SvColors.amber
                              : SvColors.phish),
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                      _strength >= 0.67
                          ? 'Strong password'
                          : 'Use 8+ chars with mixed case and a number/symbol',
                      key: const Key('register-strength'),
                      style: const TextStyle(color: SvColors.faint, fontSize: 10)),
                  const SizedBox(height: 12),

                  CheckboxListTile(
                    key: const Key('register-terms'),
                    contentPadding: EdgeInsets.zero,
                    controlAffinity: ListTileControlAffinity.leading,
                    activeColor: SvColors.amber,
                    value: _agreed,
                    onChanged: (v) => setState(() => _agreed = v ?? false),
                    title: const Text('I agree to the Terms and Privacy Policy',
                        style: TextStyle(color: SvColors.muted, fontSize: 12)),
                  ),
                  const SizedBox(height: 8),

                  ElevatedButton(
                    key: const Key('register-submit'),
                    style: ElevatedButton.styleFrom(
                        backgroundColor:
                            _canSubmit ? SvColors.amber : SvColors.chip,
                        foregroundColor: _canSubmit
                            ? const Color(0xFF1A1300)
                            : SvColors.faint,
                        padding: const EdgeInsets.symmetric(vertical: 14)),
                    onPressed: _canSubmit ? _register : null,
                    child: const Text('Create account',
                        style: TextStyle(fontWeight: FontWeight.bold)),
                  ),
                  const SizedBox(height: 12),
                  Center(
                    child: TextButton(
                      key: const Key('register-to-login'),
                      onPressed: () => Navigator.of(context).pushReplacement(
                          MaterialPageRoute(builder: (_) => const LoginScreen())),
                      child: const Text('Already have an account? Sign in',
                          style: TextStyle(color: SvColors.cyan, fontSize: 12)),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _field(Key key, TextEditingController c, String hint, bool obscure) =>
      TextField(
        key: key,
        controller: c,
        obscureText: obscure,
        onChanged: (_) => setState(() {}),
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

class _SsoButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final Color color;
  final VoidCallback onTap;
  const _SsoButton({
    super.key,
    required this.label,
    required this.icon,
    required this.color,
    required this.onTap,
  });
  @override
  Widget build(BuildContext context) => OutlinedButton.icon(
        onPressed: onTap,
        style: OutlinedButton.styleFrom(
          foregroundColor: SvColors.text,
          backgroundColor: SvColors.panel2,
          side: const BorderSide(color: SvColors.border),
          padding: const EdgeInsets.symmetric(vertical: 12),
          alignment: Alignment.centerLeft,
        ),
        icon: Icon(icon, color: color, size: 20),
        label: Text(label,
            style: const TextStyle(fontSize: 13, color: SvColors.text)),
      );
}
