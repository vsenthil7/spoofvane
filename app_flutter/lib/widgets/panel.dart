// A bordered content panel with an optional title. Used across all screens.
import 'package:flutter/material.dart';
import '../theme.dart';

class Panel extends StatelessWidget {
  final String? title;
  final Widget child;
  final double? width;
  const Panel({super.key, this.title, required this.child, this.width});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: width,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: SvColors.panel,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: SvColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (title != null) ...[
            Text(
              title!,
              style: const TextStyle(
                  color: SvColors.text, fontSize: 13, fontFamily: 'Georgia'),
            ),
            const SizedBox(height: 12),
          ],
          child,
        ],
      ),
    );
  }
}
