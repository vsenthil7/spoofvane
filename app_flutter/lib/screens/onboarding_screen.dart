// P27 — Onboarding wizard. First-run setup after registration: company details →
// add your first protected brand → invite your team → done. A stepper that ends
// by entering the console as an admin. Demo flow — no data is persisted.
import 'package:flutter/material.dart';
import '../app.dart';
import '../roles.dart';
import '../theme.dart';

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});
  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  int _step = 0;

  final _company = TextEditingController(text: 'DemoTenant');
  final _domain = TextEditingController(text: 'demotenant.io');
  final _brand = TextEditingController();
  final _brandUrl = TextEditingController();
  final _invite = TextEditingController();
  final List<String> _invited = [];

  static const _titles = ['Company', 'First brand', 'Invite team', 'Done'];

  void _next() {
    if (_step < _titles.length - 1) {
      setState(() => _step++);
    } else {
      _finish();
    }
  }

  void _back() {
    if (_step > 0) setState(() => _step--);
  }

  void _finish() {
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(builder: (_) => const Console(role: Role.admin)),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: SvColors.bg,
      body: Center(
        child: SingleChildScrollView(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 520),
            child: Container(
              key: const Key('onboarding-card'),
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
                  _stepIndicator(),
                  const SizedBox(height: 20),
                  _stepBody(),
                  const SizedBox(height: 24),
                  Row(
                    children: [
                      if (_step > 0)
                        TextButton(
                          key: const Key('onboarding-back'),
                          onPressed: _back,
                          child: const Text('Back',
                              style: TextStyle(color: SvColors.muted)),
                        ),
                      const Spacer(),
                      ElevatedButton(
                        key: const Key('onboarding-next'),
                        style: ElevatedButton.styleFrom(
                            backgroundColor: SvColors.amber,
                            foregroundColor: const Color(0xFF1A1300),
                            padding: const EdgeInsets.symmetric(
                                horizontal: 24, vertical: 12)),
                        onPressed: _next,
                        child: Text(
                            _step == _titles.length - 1
                                ? 'Enter console'
                                : 'Continue',
                            style: const TextStyle(fontWeight: FontWeight.bold)),
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

  Widget _stepIndicator() {
    return Row(
      children: [
        for (var i = 0; i < _titles.length; i++) ...[
          CircleAvatar(
            radius: 13,
            backgroundColor: i <= _step ? SvColors.amber : SvColors.chip,
            child: i < _step
                ? const Icon(Icons.check, size: 14, color: Color(0xFF1A1300))
                : Text('${i + 1}',
                    style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        color: i <= _step
                            ? const Color(0xFF1A1300)
                            : SvColors.faint)),
          ),
          if (i < _titles.length - 1)
            Expanded(
              child: Container(
                  height: 2,
                  color: i < _step ? SvColors.amber : SvColors.border),
            ),
        ],
      ],
    );
  }

  Widget _stepBody() {
    switch (_step) {
      case 0:
        return _companyStep();
      case 1:
        return _brandStep();
      case 2:
        return _inviteStep();
      default:
        return _doneStep();
    }
  }

  Widget _companyStep() {
    return Column(
      key: const Key('onboarding-step-company'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Tell us about your company',
            style: TextStyle(
                color: SvColors.text, fontSize: 18, fontWeight: FontWeight.bold)),
        const SizedBox(height: 12),
        _field(const Key('onboarding-company'), _company, 'Company name'),
        const SizedBox(height: 8),
        _field(const Key('onboarding-domain'), _domain, 'Primary domain'),
      ],
    );
  }

  Widget _brandStep() {
    return Column(
      key: const Key('onboarding-step-brand'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Add your first protected brand',
            style: TextStyle(
                color: SvColors.text, fontSize: 18, fontWeight: FontWeight.bold)),
        const SizedBox(height: 4),
        const Text('We will start monitoring lookalikes for this brand.',
            style: TextStyle(color: SvColors.muted, fontSize: 12)),
        const SizedBox(height: 12),
        _field(const Key('onboarding-brand'), _brand, 'Brand name'),
        const SizedBox(height: 8),
        _field(const Key('onboarding-brand-url'), _brandUrl,
            'Canonical login URL'),
      ],
    );
  }

  Widget _inviteStep() {
    return Column(
      key: const Key('onboarding-step-invite'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Invite your team',
            style: TextStyle(
                color: SvColors.text, fontSize: 18, fontWeight: FontWeight.bold)),
        const SizedBox(height: 4),
        const Text('Optional — you can do this later from Admin · Users.',
            style: TextStyle(color: SvColors.muted, fontSize: 12)),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
                child: _field(
                    const Key('onboarding-invite'), _invite, 'teammate@company.com')),
            const SizedBox(width: 8),
            ElevatedButton(
              key: const Key('onboarding-invite-add'),
              style: ElevatedButton.styleFrom(
                  backgroundColor: SvColors.chip, foregroundColor: SvColors.text),
              onPressed: () {
                if (_invite.text.contains('@')) {
                  setState(() {
                    _invited.add(_invite.text);
                    _invite.clear();
                  });
                }
              },
              child: const Text('Add'),
            ),
          ],
        ),
        const SizedBox(height: 12),
        ..._invited.map((e) => Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Row(children: [
                const Icon(Icons.mail_outline, size: 14, color: SvColors.cyan),
                const SizedBox(width: 8),
                Text(e, style: const TextStyle(color: SvColors.text, fontSize: 12)),
                const Spacer(),
                const Text('invited',
                    style: TextStyle(color: SvColors.benign, fontSize: 11)),
              ]),
            )),
      ],
    );
  }

  Widget _doneStep() {
    return Column(
      key: const Key('onboarding-step-done'),
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        const Icon(Icons.check_circle, color: SvColors.benign, size: 48),
        const SizedBox(height: 12),
        const Text("You're all set",
            style: TextStyle(
                color: SvColors.text, fontSize: 20, fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        Text(
            '${_company.text} is ready. ${_brand.text.isEmpty ? 'Your brand' : _brand.text} is now monitored and ${_invited.length} teammate(s) invited.',
            textAlign: TextAlign.center,
            style: const TextStyle(color: SvColors.muted, fontSize: 13)),
      ],
    );
  }

  Widget _field(Key key, TextEditingController c, String hint) => TextField(
        key: key,
        controller: c,
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
