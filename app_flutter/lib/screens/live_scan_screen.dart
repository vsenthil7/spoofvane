// P26 — Live Scan. The surface that proves SpoofVane works LIVE end-to-end:
// paste a suspect URL, Bright Data live-fetches it, and a MULTI-LLM ENSEMBLE
// (Claude + GPT, plus Gemini when its key is active) each score it; a
// disagreement-aware merger picks the final verdict. The result shows each
// model's individual vote + which BD product + latency + tokens + cost, so it
// is visibly a real multi-model decision, not seed data.
//
// A live/demo toggle lets a presenter show a canned sample (no spend, no
// network) vs the real billable live ensemble. Demo results are clearly tagged.
import 'package:flutter/material.dart';
import '../api.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/screen_title.dart';
import '../widgets/verdict_pill.dart';

class LiveScanScreen extends StatefulWidget {
  const LiveScanScreen({super.key});
  @override
  State<LiveScanScreen> createState() => _LiveScanScreenState();
}

class _LiveScanScreenState extends State<LiveScanScreen> {
  final _url = TextEditingController(text: 'https://example.com');
  final _brand = TextEditingController(text: 'AcmeBank');
  bool _running = false;
  bool _demoMode = false; // false = live (billable), true = canned sample
  ScanResult? _result;

  Future<void> _scan() async {
    setState(() {
      _running = true;
      _result = null;
    });
    final res =
        await Api.instance.scan(_url.text.trim(), _brand.text.trim(), demo: _demoMode);
    if (!mounted) return;
    setState(() {
      _running = false;
      _result = res;
    });
  }

  @override
  void dispose() {
    _url.dispose();
    _brand.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const ScreenTitle('Live Scan',
              sub: 'Paste a suspect URL — Bright Data fetches it live and a '
                  'multi-LLM ensemble (Claude + GPT + Gemini) scores it in real '
                  'time, then votes on a verdict. Not seed data.'),
          _inputCard(),
          const SizedBox(height: 16),
          if (_running) _runningCard(),
          if (_result != null) _resultCard(_result!),
        ],
      ),
    );
  }

  Widget _inputCard() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: SvColors.panel,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: SvColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                flex: 3,
                child: _field(_url, 'Suspect URL', const Key('scan-url')),
              ),
              const SizedBox(width: 12),
              Expanded(
                flex: 2,
                child: _field(_brand, 'Target brand', const Key('scan-brand')),
              ),
              const SizedBox(width: 12),
              ElevatedButton.icon(
                key: const Key('scan-run'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: SvColors.blue,
                  foregroundColor: Colors.white,
                  padding:
                      const EdgeInsets.symmetric(horizontal: 22, vertical: 16),
                ),
                onPressed: _running ? null : _scan,
                icon: const Icon(Icons.radar, size: 18),
                label: Text(_running ? 'Scanning…' : 'Scan'),
              ),
            ],
          ),
          const SizedBox(height: 14),
          // Live / demo toggle.
          Row(
            children: [
              _modeToggle(),
              const SizedBox(width: 14),
              Expanded(
                child: Text(
                  _demoMode
                      ? 'Demo mode: shows a canned sample ensemble result — no '
                          'network, no spend.'
                      : 'Live mode: one real Bright Data request + one real call '
                          'per LLM (billable).',
                  style: const TextStyle(color: SvColors.faint, fontSize: 11),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _modeToggle() {
    return Container(
      key: const Key('scan-mode-toggle'),
      decoration: BoxDecoration(
        color: SvColors.panel2,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: SvColors.border),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        _modeButton('Live', !_demoMode, const Key('scan-mode-live'),
            () => setState(() => _demoMode = false)),
        _modeButton('Demo', _demoMode, const Key('scan-mode-demo'),
            () => setState(() => _demoMode = true)),
      ]),
    );
  }

  Widget _modeButton(String label, bool active, Key key, VoidCallback onTap) {
    return InkWell(
      key: key,
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          color: active ? SvColors.blue : Colors.transparent,
          borderRadius: BorderRadius.circular(7),
        ),
        child: Text(label,
            style: TextStyle(
                color: active ? Colors.white : SvColors.muted,
                fontSize: 12,
                fontWeight: FontWeight.w600)),
      ),
    );
  }

  Widget _field(TextEditingController c, String hint, Key key) => TextField(
        key: key,
        controller: c,
        style: const TextStyle(color: SvColors.text, fontSize: 13),
        decoration: InputDecoration(
          hintText: hint,
          hintStyle: const TextStyle(color: SvColors.faint, fontSize: 13),
          filled: true,
          fillColor: SvColors.bg,
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 12, vertical: 14),
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

  Widget _runningCard() {
    return Container(
      key: const Key('scan-running'),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: SvColors.panel,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: SvColors.border),
      ),
      child: Row(
        children: const [
          SizedBox(
              width: 18,
              height: 18,
              child: CircularProgressIndicator(strokeWidth: 2)),
          SizedBox(width: 14),
          Expanded(
            child: Text(
                'Bright Data is fetching the page, then Claude + GPT + Gemini '
                'each score it and vote…',
                style: TextStyle(color: SvColors.muted, fontSize: 13)),
          ),
        ],
      ),
    );
  }

  Widget _resultCard(ScanResult r) {
    if (r.mode == 'error') {
      return Container(
        key: const Key('scan-error'),
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: SvColors.chipDanger,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: SvColors.phish),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: const [
              Icon(Icons.error_outline, color: SvColors.phish, size: 18),
              SizedBox(width: 8),
              Text('Live scan could not run',
                  style: TextStyle(
                      color: SvColors.phish,
                      fontSize: 14,
                      fontWeight: FontWeight.bold)),
            ]),
            const SizedBox(height: 8),
            Text('Stage: ${r.stage.isEmpty ? "unknown" : r.stage}',
                style: const TextStyle(color: SvColors.muted, fontSize: 12)),
            const SizedBox(height: 4),
            Text(r.error,
                style: const TextStyle(color: SvColors.text, fontSize: 12)),
            const SizedBox(height: 8),
            const Text(
                'No mock fallback is shown for a live scan — this is the real '
                'reason it failed.',
                style: TextStyle(color: SvColors.faint, fontSize: 11)),
          ],
        ),
      );
    }

    final isDemo = r.mode == 'demo';
    return Container(
      key: const Key('scan-result'),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: SvColors.panel,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: SvColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              VerdictPill(r.verdict),
              const SizedBox(width: 12),
              Flexible(
                child: Text(r.host,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                        color: SvColors.text,
                        fontSize: 16,
                        fontWeight: FontWeight.bold)),
              ),
              const Spacer(),
              isDemo ? _demoBadge() : _liveBadge(),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            'Ensemble confidence ${(r.confidence * 100).toStringAsFixed(0)}% · '
            'severity ${r.severity} · suggested: ${r.suggestedAction}'
            '${r.dissent ? " · models DISAGREED → escalated to human" : " · models agreed"}',
            style: TextStyle(
                color: r.dissent ? SvColors.amber : SvColors.muted,
                fontSize: 12),
          ),
          const Divider(color: SvColors.border, height: 28),

          // Per-model votes — the proof it's a real multi-LLM ensemble.
          const Text('Model votes (multi-LLM ensemble)',
              style: TextStyle(
                  color: SvColors.faint,
                  fontSize: 10,
                  letterSpacing: 0.5,
                  fontWeight: FontWeight.w600)),
          const SizedBox(height: 10),
          for (final m in r.members) _memberRow(m),
          if (r.skipped.isNotEmpty) ...[
            const SizedBox(height: 8),
            for (final s in r.skipped)
              Padding(
                padding: const EdgeInsets.only(bottom: 4),
                child: Row(children: [
                  const Icon(Icons.remove_circle_outline,
                      size: 14, color: SvColors.faint),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text('Skipped — $s',
                        style: const TextStyle(
                            color: SvColors.faint, fontSize: 11)),
                  ),
                ]),
              ),
          ],
          const SizedBox(height: 16),

          // The proof row: real BD product + latency + cost.
          Wrap(spacing: 10, runSpacing: 10, children: [
            _proofChip(Icons.cloud_download, 'Fetch', r.fetchProduct),
            _proofChip(Icons.http, 'HTTP', '${r.fetchStatus} · ${r.htmlLen}B'),
            _proofChip(Icons.groups, 'Models',
                r.modelsUsed.isEmpty ? '—' : r.modelsUsed.join(' + ')),
            if (r.ranAsAgent)
              _proofChip(
                  r.agentAuditVerified ? Icons.verified_user : Icons.smart_toy,
                  'Agent',
                  '${r.agentName} · ${r.agentState}'
                      '${r.agentAuditVerified ? " · audit ✓" : ""}'),
            _proofChip(Icons.timer, 'Total latency', '${r.totalLatencyMs} ms'),
            _proofChip(Icons.attach_money, 'Total cost',
                '\$${r.totalCostUsd.toStringAsFixed(4)}'),
          ]),
          const SizedBox(height: 18),

          const Text('Evidence (from the winning models)',
              style: TextStyle(
                  color: SvColors.faint,
                  fontSize: 10,
                  letterSpacing: 0.5,
                  fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          for (final e in r.evidence)
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Text('•  ',
                    style: TextStyle(color: SvColors.cyan, fontSize: 13)),
                Expanded(
                    child: Text(e,
                        style: const TextStyle(
                            color: SvColors.text, fontSize: 13))),
              ]),
            ),
        ],
      ),
    );
  }

  Widget _memberRow(ScanMember m) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: SvColors.panel2,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: SvColors.border),
      ),
      child: Row(
        children: [
          SizedBox(
            width: 64,
            child: Text(m.name,
                style: const TextStyle(
                    color: SvColors.text,
                    fontSize: 13,
                    fontWeight: FontWeight.w600)),
          ),
          VerdictPill(m.verdict),
          const SizedBox(width: 10),
          Text('${(m.confidence * 100).toStringAsFixed(0)}%',
              style: const TextStyle(color: SvColors.muted, fontSize: 12)),
          const Spacer(),
          Text(
              '${m.model}  ·  ${m.latencyMs} ms  ·  '
              '${m.tokensIn}/${m.tokensOut} tok  ·  '
              '\$${m.costUsd.toStringAsFixed(4)}',
              style: const TextStyle(color: SvColors.faint, fontSize: 10.5)),
        ],
      ),
    );
  }

  Widget _liveBadge() => _badge('LIVE', SvColors.benign);
  Widget _demoBadge() => _badge('DEMO', SvColors.amber);

  Widget _badge(String label, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(
            color: c.withOpacity(0.15),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: c)),
        child: Text(label,
            style: TextStyle(
                color: c,
                fontSize: 10,
                fontWeight: FontWeight.bold,
                letterSpacing: 1)),
      );

  Widget _proofChip(IconData icon, String label, String value) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
            color: SvColors.panel2,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: SvColors.border)),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(icon, size: 14, color: SvColors.muted),
          const SizedBox(width: 8),
          Text('$label: ',
              style: const TextStyle(color: SvColors.faint, fontSize: 11)),
          Text(value,
              style: const TextStyle(color: SvColors.text, fontSize: 11)),
        ]),
      );
}
