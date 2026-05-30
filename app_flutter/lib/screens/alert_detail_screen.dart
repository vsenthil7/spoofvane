// Alert detail (P06) — the heart of the product: one suspect, ten evidence
// tabs. Each tab is its own small widget so it can be tested independently.
// Tabs (per docs/USER_GUIDE.md §3 P06): Summary, Evidence, Multi-region,
// Verdict trace, MITRE, Kit, Cluster, Deepfake, Takedown, Audit.
import 'package:flutter/material.dart';
import '../models.dart';
import '../theme.dart';
import '../util/format.dart';
import '../widgets/panel.dart';
import '../widgets/verdict_pill.dart';

/// The ten canonical evidence tabs, in spec order.
const List<String> kAlertTabs = [
  'Summary',
  'Evidence',
  'Multi-region',
  'Verdict trace',
  'MITRE',
  'Kit',
  'Cluster',
  'Deepfake',
  'Takedown',
  'Audit',
];

class AlertDetailScreen extends StatelessWidget {
  final Alert alert;
  const AlertDetailScreen({super.key, required this.alert});

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: kAlertTabs.length,
      child: Scaffold(
        backgroundColor: SvColors.bg,
        appBar: AppBar(
          backgroundColor: SvColors.panel2,
          title: Text(alert.url,
              style: const TextStyle(fontFamily: 'monospace', fontSize: 14)),
          actions: [
            Padding(
              padding: const EdgeInsets.all(8),
              child: ElevatedButton(
                key: const Key('takedown-button'),
                style: ElevatedButton.styleFrom(
                    backgroundColor: verdictColor(alert.verdict)),
                onPressed: () => ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Takedown requested (demo)'))),
                child: const Text('Request takedown'),
              ),
            ),
          ],
          bottom: TabBar(
            isScrollable: true,
            indicatorColor: SvColors.cyan,
            labelColor: SvColors.text,
            unselectedLabelColor: SvColors.muted,
            labelStyle: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
            tabs: [for (final t in kAlertTabs) Tab(key: Key('tab-$t'), text: t)],
          ),
        ),
        body: Padding(
          padding: const EdgeInsets.all(24),
          child: TabBarView(
            children: [
              _SummaryTab(alert),
              _EvidenceTab(alert),
              _MultiRegionTab(alert),
              _VerdictTraceTab(alert),
              _MitreTab(alert),
              _KitTab(alert),
              _ClusterTab(alert),
              _DeepfakeTab(alert),
              _TakedownTab(alert),
              _AuditTab(alert),
            ],
          ),
        ),
      ),
    );
  }
}

// --------------------------------------------------------------------------- //
// Shared helpers
// --------------------------------------------------------------------------- //

Widget _kv(String k, String v) => Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
              width: 130,
              child: Text(k,
                  style: const TextStyle(color: SvColors.faint, fontSize: 12))),
          Expanded(
              child: Text(v,
                  style: const TextStyle(
                      color: SvColors.text,
                      fontFamily: 'monospace',
                      fontSize: 12))),
        ],
      ),
    );

Widget _mono(String s, {Color color = SvColors.text}) => Text(s,
    style: TextStyle(color: color, fontFamily: 'monospace', fontSize: 12));

// --------------------------------------------------------------------------- //
// Tab 1 — Summary
// --------------------------------------------------------------------------- //

class _SummaryTab extends StatelessWidget {
  final Alert a;
  const _SummaryTab(this.a);
  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      key: const Key('alert-tab-summary'),
      child: Panel(
        title: 'Summary',
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [VerdictPill(a.verdict)]),
            const SizedBox(height: 12),
            _kv('verdict', a.verdict.name),
            _kv('score', a.composite.toStringAsFixed(2)),
            _kv('brand', a.brandId),
            _kv('family', a.family ?? '—'),
            _kv('kit', a.kit ?? '—'),
            _kv('rendered from', a.renderedFrom ?? '—'),
            _kv('first seen', fmtTime(a.discoveredAt)),
          ],
        ),
      ),
    );
  }
}

// --------------------------------------------------------------------------- //
// Tab 2 — Evidence
// --------------------------------------------------------------------------- //

class _EvidenceTab extends StatelessWidget {
  final Alert a;
  const _EvidenceTab(this.a);
  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      key: const Key('alert-tab-evidence'),
      child: Panel(
        title: 'Evidence',
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _kv('captured URL', a.url),
            _kv('screenshot', 'sha256:${_pseudoHash(a.id, 'shot')}'),
            _kv('DOM snapshot', 'sha256:${_pseudoHash(a.id, 'dom')}'),
            _kv('favicon', 'sha256:${_pseudoHash(a.id, 'fav')}'),
            const SizedBox(height: 12),
            Container(
              height: 140,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: SvColors.bg,
                border: Border.all(color: SvColors.border),
                borderRadius: BorderRadius.circular(6),
              ),
              child: const Text('[ rendered screenshot ]',
                  style: TextStyle(color: SvColors.faint, fontSize: 12)),
            ),
          ],
        ),
      ),
    );
  }
}

// --------------------------------------------------------------------------- //
// Tab 3 — Multi-region (cloaking)
// --------------------------------------------------------------------------- //

class _MultiRegionTab extends StatelessWidget {
  final Alert a;
  const _MultiRegionTab(this.a);
  @override
  Widget build(BuildContext context) {
    // Demonstrate cloaking: the phishing payload renders for some regions,
    // a benign holding page for others.
    final regions = {
      'US': a.verdict,
      'GB': a.verdict,
      'DE': Verdict.benign,
      'SG': a.verdict,
      'BR': Verdict.benign,
    };
    final cloaked = regions.values.toSet().length > 1;
    return SingleChildScrollView(
      key: const Key('alert-tab-multi-region'),
      child: Panel(
        title: 'Multi-region render',
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(cloaked ? 'Cloaking detected' : 'Consistent across regions',
                style: TextStyle(
                    color: cloaked ? SvColors.amber : SvColors.benign,
                    fontSize: 13,
                    fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            for (final e in regions.entries)
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(children: [
                  SizedBox(width: 60, child: _mono(e.key)),
                  VerdictPill(e.value),
                ]),
              ),
          ],
        ),
      ),
    );
  }
}

// --------------------------------------------------------------------------- //
// Tab 4 — Verdict trace (ensemble)
// --------------------------------------------------------------------------- //

class _VerdictTraceTab extends StatelessWidget {
  final Alert a;
  const _VerdictTraceTab(this.a);
  @override
  Widget build(BuildContext context) {
    Widget trace(String model, double conf) => Padding(
          padding: const EdgeInsets.only(bottom: 6),
          child: _mono('$model: ${a.verdict.name} ${conf.clamp(0, 1).toStringAsFixed(2)}',
              color: SvColors.benign),
        );
    return SingleChildScrollView(
      key: const Key('alert-tab-verdict-trace'),
      child: Panel(
        title: 'Verdict trace (ensemble)',
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            trace('claude', a.composite + 0.01),
            trace('gpt-5', a.composite - 0.02),
            trace('gemini', a.composite),
            const Divider(color: SvColors.border),
            _mono('merge: ${a.verdict.name.toUpperCase()} · no dissent',
                color: verdictColor(a.verdict)),
          ],
        ),
      ),
    );
  }
}

// --------------------------------------------------------------------------- //
// Tab 5 — MITRE
// --------------------------------------------------------------------------- //

class _MitreTab extends StatelessWidget {
  final Alert a;
  const _MitreTab(this.a);
  @override
  Widget build(BuildContext context) {
    final techniques = a.mitreTechniques.isNotEmpty
        ? a.mitreTechniques
        : const ['T1566.002', 'T1583.001'];
    return SingleChildScrollView(
      key: const Key('alert-tab-mitre'),
      child: Panel(
        title: 'MITRE ATT&CK',
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            for (final t in techniques) _kv(t, _mitreName(t)),
            const Divider(color: SvColors.border),
            _kv('D3FEND', 'D3-DNSAL · D3-UA'),
          ],
        ),
      ),
    );
  }
}

// --------------------------------------------------------------------------- //
// Tab 6 — Kit
// --------------------------------------------------------------------------- //

class _KitTab extends StatelessWidget {
  final Alert a;
  const _KitTab(this.a);
  @override
  Widget build(BuildContext context) {
    final kit = a.kit;
    return SingleChildScrollView(
      key: const Key('alert-tab-kit'),
      child: Panel(
        title: 'Phishing kit',
        child: kit == null
            ? const Text('No kit fingerprint matched.',
                style: TextStyle(color: SvColors.muted, fontSize: 13))
            : Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _kv('matched kit', kit),
                  _kv('match basis', 'DOM template + JS bundle hash'),
                  _kv('confidence', (a.composite).clamp(0, 1).toStringAsFixed(2)),
                ],
              ),
      ),
    );
  }
}

// --------------------------------------------------------------------------- //
// Tab 7 — Cluster
// --------------------------------------------------------------------------- //

class _ClusterTab extends StatelessWidget {
  final Alert a;
  const _ClusterTab(this.a);
  @override
  Widget build(BuildContext context) {
    final linked = [
      a.url,
      a.url.replaceFirst(RegExp(r'https?://'), 'https://mirror-'),
    ];
    return SingleChildScrollView(
      key: const Key('alert-tab-cluster'),
      child: Panel(
        title: 'Linked domains (campaign)',
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _kv('campaign size', '${linked.length}'),
            const SizedBox(height: 8),
            for (final m in linked) Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: _mono(m, color: SvColors.muted),
            ),
          ],
        ),
      ),
    );
  }
}

// --------------------------------------------------------------------------- //
// Tab 8 — Deepfake
// --------------------------------------------------------------------------- //

class _DeepfakeTab extends StatelessWidget {
  final Alert a;
  const _DeepfakeTab(this.a);
  @override
  Widget build(BuildContext context) {
    final isDeepfake = (a.family ?? '').toLowerCase().contains('deepfake');
    return SingleChildScrollView(
      key: const Key('alert-tab-deepfake'),
      child: Panel(
        title: 'Deepfake / synthetic media',
        child: isDeepfake
            ? Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _kv('face swap', '0.88'),
                  _kv('lip-sync drift', '0.74'),
                  _kv('voiceprint match', '0.12'),
                  _kv('C2PA', 'absent (unsigned)'),
                ],
              )
            : const Text('No synthetic media in this alert.',
                style: TextStyle(color: SvColors.muted, fontSize: 13)),
      ),
    );
  }
}

// --------------------------------------------------------------------------- //
// Tab 9 — Takedown
// --------------------------------------------------------------------------- //

class _TakedownTab extends StatelessWidget {
  final Alert a;
  const _TakedownTab(this.a);
  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      key: const Key('alert-tab-takedown'),
      child: Panel(
        title: 'Takedown packet',
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _kv('target', a.url),
            _kv('provider', 'Cloudflare (registrar abuse)'),
            _kv('status', 'draft — awaiting analyst submit'),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: SvColors.bg,
                border: Border.all(color: SvColors.border),
                borderRadius: BorderRadius.circular(6),
              ),
              child: _mono(
                  'To: abuse@cloudflare.com\nRe: phishing — ${a.url}\n'
                  'Evidence pack attached (screenshot, DOM, verdict trace).',
                  color: SvColors.muted),
            ),
          ],
        ),
      ),
    );
  }
}

// --------------------------------------------------------------------------- //
// Tab 10 — Audit
// --------------------------------------------------------------------------- //

class _AuditTab extends StatelessWidget {
  final Alert a;
  const _AuditTab(this.a);
  @override
  Widget build(BuildContext context) {
    final rows = [
      ('alert.create', 'system'),
      ('alert.triage', 'analyst'),
      ('takedown.draft', 'analyst'),
    ];
    return SingleChildScrollView(
      key: const Key('alert-tab-audit'),
      child: Panel(
        title: 'Audit trail (hash-chained)',
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            for (var i = 0; i < rows.length; i++)
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: _mono(
                    '#${i + 1}  ${rows[i].$1.padRight(16)} ${rows[i].$2.padRight(9)} '
                    'sha:${_pseudoHash(a.id, 'audit$i').substring(0, 12)}',
                    color: SvColors.muted),
              ),
          ],
        ),
      ),
    );
  }
}

// --------------------------------------------------------------------------- //
// Local helpers
// --------------------------------------------------------------------------- //

String _pseudoHash(String seed, String salt) {
  // Deterministic display-only hex from the alert id (NOT a security hash).
  final n = (seed + salt).codeUnits.fold<int>(0, (acc, c) => (acc * 31 + c) & 0xFFFFFFFF);
  return n.toRadixString(16).padLeft(8, '0') * 4;
}

String _mitreName(String t) {
  const names = {
    'T1566.002': 'Phishing: Spearphishing Link',
    'T1583.001': 'Acquire Infrastructure: Domains',
    'T1656': 'Impersonation',
  };
  return names[t] ?? 'technique';
}
