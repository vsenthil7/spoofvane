// Review queue (P12) — the reviewer's human-in-the-loop surface. Each row is a
// consequential action awaiting approval. Segregation of duties is enforced in
// the UI: if the current reviewer is the same actor who raised the item, the
// approve/deny controls are disabled with an SoD notice (the backend enforces
// this too — this surfaces it to the reviewer).
import 'package:flutter/material.dart';
import '../api.dart';
import '../models.dart';
import '../theme.dart';
import '../util/format.dart';
import '../widgets/panel.dart';
import '../widgets/screen_title.dart';
import '../widgets/verdict_pill.dart';

class ReviewQueueScreen extends StatefulWidget {
  /// The actor viewing the queue. SoD: cannot approve items they raised.
  final String currentReviewer;
  const ReviewQueueScreen({super.key, this.currentReviewer = 'reviewer.osei'});

  @override
  State<ReviewQueueScreen> createState() => _ReviewQueueScreenState();
}

class _ReviewQueueScreenState extends State<ReviewQueueScreen> {
  final Future<List<ReviewItem>> _q = Api.instance.reviewQueue();
  final Map<String, String> _decisions = {}; // id -> approved|denied

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<ReviewItem>>(
      future: _q,
      builder: (_, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        final rows = snap.data ?? [];
        return ListView(
          key: const Key('review-list'),
          children: [
            ScreenTitle('Review Queue',
                sub: '${rows.length} actions awaiting approval'),
            Panel(
              child: Column(
                children: [
                  const Row(
                    children: [
                      SizedBox(width: 90, child: HeaderLabel('VERDICT')),
                      Expanded(child: HeaderLabel('ACTION / TARGET')),
                      SizedBox(width: 120, child: HeaderLabel('RAISED BY')),
                      SizedBox(width: 180, child: HeaderLabel('DECISION')),
                    ],
                  ),
                  const Divider(color: SvColors.border),
                  ...rows.map(_row),
                ],
              ),
            ),
          ],
        );
      },
    );
  }

  Widget _row(ReviewItem r) {
    final isSelf = r.raisedBy == widget.currentReviewer;
    final decided = _decisions[r.id];
    return Padding(
      key: Key('review-row-${r.id}'),
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(width: 90, child: VerdictPill(r.verdict)),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(r.action,
                    style: const TextStyle(
                        color: SvColors.text, fontSize: 12, fontWeight: FontWeight.w600)),
                Text(r.targetUrl,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                        color: SvColors.muted, fontFamily: 'monospace', fontSize: 11)),
                Text(fmtTime(r.ts),
                    style: const TextStyle(color: SvColors.faint, fontSize: 10)),
              ],
            ),
          ),
          SizedBox(
              width: 120,
              child: Text(r.raisedBy,
                  style: const TextStyle(color: SvColors.muted, fontSize: 11))),
          SizedBox(width: 180, child: _decisionCell(r, isSelf, decided)),
        ],
      ),
    );
  }

  Widget _decisionCell(ReviewItem r, bool isSelf, String? decided) {
    if (decided != null) {
      final ok = decided == 'approved';
      return Text(ok ? '✓ Approved' : '✕ Denied',
          key: Key('review-decision-${r.id}'),
          style: TextStyle(
              color: ok ? SvColors.benign : SvColors.phish,
              fontSize: 12,
              fontWeight: FontWeight.bold));
    }
    if (isSelf) {
      // Segregation of duties: cannot approve your own raised action.
      return Row(
        key: Key('review-sod-${r.id}'),
        children: const [
          Icon(Icons.block, size: 14, color: SvColors.faint),
          SizedBox(width: 6),
          Expanded(
            child: Text('Blocked — you raised this (SoD)',
                style: TextStyle(color: SvColors.faint, fontSize: 10.5)),
          ),
        ],
      );
    }
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        TextButton(
          key: Key('review-approve-${r.id}'),
          onPressed: () => setState(() => _decisions[r.id] = 'approved'),
          style: TextButton.styleFrom(
              foregroundColor: SvColors.benign,
              padding: const EdgeInsets.symmetric(horizontal: 8),
              minimumSize: const Size(0, 32),
              tapTargetSize: MaterialTapTargetSize.shrinkWrap),
          child: const Text('Approve', style: TextStyle(fontSize: 11)),
        ),
        TextButton(
          key: Key('review-deny-${r.id}'),
          onPressed: () => setState(() => _decisions[r.id] = 'denied'),
          style: TextButton.styleFrom(
              foregroundColor: SvColors.phish,
              padding: const EdgeInsets.symmetric(horizontal: 8),
              minimumSize: const Size(0, 32),
              tapTargetSize: MaterialTapTargetSize.shrinkWrap),
          child: const Text('Deny', style: TextStyle(fontSize: 11)),
        ),
      ],
    );
  }
}
