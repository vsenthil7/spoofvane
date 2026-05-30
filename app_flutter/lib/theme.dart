// SpoofVane SOC palette + theme. Single source of truth for colours so screens
// and widgets never hard-code hex values.
import 'package:flutter/material.dart';

class SvColors {
  SvColors._();
  // Palette aligned to the MeDo reference screenshots (design_refs/): sampled
  // dominant colours — content bg #1A1E28, darker sidebar #101219, panels
  // #1E222C, borders #2B2F3B, near-white text #F7F9FC, accent green #25A777,
  // sign-in blue #3C83F6. Single source of truth; screens never hard-code hex.
  static const bg = Color(0xFF1A1E28); // content background (MeDo)
  static const sidebar = Color(0xFF101219); // darker nav rail (MeDo)
  static const panel = Color(0xFF1E222C); // card / panel surface (MeDo)
  static const panel2 = Color(0xFF13151B); // inset / deeper surface (MeDo)
  static const border = Color(0xFF2B2F3B); // hairline borders (MeDo)
  static const text = Color(0xFFF7F9FC); // primary text (MeDo)
  static const muted = Color(0xFF93A1B8);
  static const faint = Color(0xFF5E6E88);
  static const amber = Color(0xFFFFB020);
  static const cyan = Color(0xFF36C2CE);
  static const blue = Color(0xFF3C83F6); // MeDo primary action blue
  static const phish = Color(0xFFFF4D57);
  static const benign = Color(0xFF25A777); // MeDo green
  static const chipDanger = Color(0xFF2A1316);
  static const chip = Color(0xFF242833); // MeDo chip / hover surface
  static const node = Color(0xFF232F42);
}

ThemeData buildSvTheme() => ThemeData(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: SvColors.bg,
      fontFamily: 'Roboto',
      colorScheme: const ColorScheme.dark(
        surface: SvColors.panel,
        primary: SvColors.blue,
        secondary: SvColors.cyan,
        error: SvColors.phish,
      ),
    );
