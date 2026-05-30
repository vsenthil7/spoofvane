// Page heading + optional subtitle, consistent across screens.
import 'package:flutter/material.dart';
import '../theme.dart';

class ScreenTitle extends StatelessWidget {
  final String title;
  final String? sub;
  const ScreenTitle(this.title, {super.key, this.sub});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: const TextStyle(
            color: SvColors.text,
            fontSize: 22,
            fontWeight: FontWeight.bold,
            fontFamily: 'Georgia',
          ),
        ),
        if (sub != null) ...[
          const SizedBox(height: 4),
          Text(sub!, style: const TextStyle(color: SvColors.muted, fontSize: 12)),
        ],
        const SizedBox(height: 20),
      ],
    );
  }
}

/// Column-header label for tables.
class HeaderLabel extends StatelessWidget {
  final String text;
  const HeaderLabel(this.text, {super.key});
  @override
  Widget build(BuildContext context) => Text(
        text,
        style: const TextStyle(
            color: SvColors.faint, fontSize: 9.5, fontWeight: FontWeight.bold),
      );
}
