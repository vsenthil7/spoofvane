// Honest placeholder for canonical pages whose full screen is not yet built.
// It renders the page title + a "planned" note so the 21-page structure is
// fully navigable today without pretending the screen is complete.
import 'package:flutter/material.dart';
import '../theme.dart';
import '../widgets/screen_title.dart';

class PlaceholderScreen extends StatelessWidget {
  final String title;
  final String pageId;
  const PlaceholderScreen({super.key, required this.title, required this.pageId});

  @override
  Widget build(BuildContext context) {
    return Column(
      key: Key('placeholder-$pageId'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        ScreenTitle(title),
        const SizedBox(height: 24),
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: SvColors.panel,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: SvColors.border),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.construction_outlined,
                  color: SvColors.amber, size: 18),
              const SizedBox(width: 10),
              Text('$pageId — screen planned. Structure is in place; '
                  'full UI lands in an upcoming build.',
                  style: const TextStyle(color: SvColors.muted, fontSize: 13)),
            ],
          ),
        ),
      ],
    );
  }
}
