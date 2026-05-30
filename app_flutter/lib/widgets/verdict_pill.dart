// Verdict badge — colour-coded phish / suspicious / benign / unknown.
import 'package:flutter/material.dart';
import '../models.dart';

class VerdictPill extends StatelessWidget {
  final Verdict v;
  const VerdictPill(this.v, {super.key});

  @override
  Widget build(BuildContext context) {
    final c = verdictColor(v);
    return Semantics(
      label: 'verdict ${v.name}',
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: c.withOpacity(0.15),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Text(
          v.name,
          style: TextStyle(color: c, fontSize: 11, fontFamily: 'monospace'),
        ),
      ),
    );
  }
}
