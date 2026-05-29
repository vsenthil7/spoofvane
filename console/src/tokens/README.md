# SpoofVane Console — Design Token Parity (v06 Gate 2)

This document maps every `--sv-*` token in `tokens.css` to its canonical
**MeDo** (Track B) source name, so the three convergence tracks share one
design language on paper. SpoofVane is the "command deck" instantiation of the
shared system.

## Parity policy

Token **names** mirror MeDo's canonical scale; token **values** may differ
where SpoofVane's SOC "command deck" aesthetic improves on the shared default.
Any divergence is marked `OVERRIDE (reason)` — never a silent drift. A row with
no OVERRIDE note carries the same value (or an exact translation) as MeDo.

## Color

| SpoofVane token | MeDo source name | Value | Notes |
|---|---|---|---|
| `--sv-bg` | `--md-bg-canvas` | `#0b0f17` | OVERRIDE (deeper slate for 24/7 SOC low-light viewing) |
| `--sv-surface` | `--md-bg-surface` | `#131a26` | OVERRIDE (matches deepened canvas) |
| `--sv-surface-2` | `--md-bg-surface-raised` | `#1b2433` | elevation step 2 |
| `--sv-surface-3` | `--md-bg-surface-overlay` | `#232f42` | elevation step 3 |
| `--sv-border` | `--md-border-default` | `#2c3a52` | hairline divider |
| `--sv-border-strong` | `--md-border-strong` | `#3d4f6e` | focused/active border |
| `--sv-text` | `--md-text-primary` | `#e8edf5` | primary copy |
| `--sv-text-muted` | `--md-text-secondary` | `#93a1b8` | secondary copy |
| `--sv-text-faint` | `--md-text-tertiary` | `#5e6e88` | tertiary/placeholder |
| `--sv-brand` | `--md-accent-primary` | `#ffb020` | OVERRIDE (signal-amber brand vs MeDo blue — threat-domain semantics) |
| `--sv-brand-dim` | `--md-accent-primary-dim` | `#c9871a` | pressed/hover brand |
| `--sv-accent` | `--md-accent-secondary` | `#36c2ce` | secondary accent (cyan) |
| `--sv-phish` | `--md-status-danger` | `#ff4d57` | threat-red (phish verdict) |
| `--sv-phish-bg` | `--md-status-danger-bg` | `#2a1316` | danger surface |
| `--sv-suspicious` | `--md-status-warning` | `#ffb020` | warning (== brand amber by design) |
| `--sv-suspicious-bg` | `--md-status-warning-bg` | `#2a2310` | warning surface |
| `--sv-benign` | `--md-status-success` | `#3ddc84` | benign verdict |
| `--sv-benign-bg` | `--md-status-success-bg` | `#0f2419` | success surface |
| `--sv-info` | `--md-status-info` | `#4d9fff` | informational |

## Typography

| SpoofVane token | MeDo source name | Value | Notes |
|---|---|---|---|
| `--sv-font-display` | `--md-font-display` | `"Space Grotesk", Georgia, serif` | OVERRIDE (geometric display for SOC chrome) |
| `--sv-font-sans` | `--md-font-body` | `"IBM Plex Sans", system-ui, sans-serif` | humanist body |
| `--sv-font-mono` | `--md-font-mono` | `"JetBrains Mono", "SF Mono", monospace` | evidence/IOC text |
| `--sv-fs-xs` | `--md-fs-xs` | `11px` | |
| `--sv-fs-sm` | `--md-fs-sm` | `13px` | |
| `--sv-fs-md` | `--md-fs-base` | `15px` | base body |
| `--sv-fs-lg` | `--md-fs-lg` | `19px` | |
| `--sv-fs-xl` | `--md-fs-xl` | `26px` | |
| `--sv-fs-2xl` | `--md-fs-2xl` | `38px` | |

## Spacing (4px base scale — identical to MeDo)

| SpoofVane token | MeDo source name | Value |
|---|---|---|
| `--sv-s1` | `--md-space-1` | `4px` |
| `--sv-s2` | `--md-space-2` | `8px` |
| `--sv-s3` | `--md-space-3` | `12px` |
| `--sv-s4` | `--md-space-4` | `16px` |
| `--sv-s5` | `--md-space-5` | `24px` |
| `--sv-s6` | `--md-space-6` | `32px` |
| `--sv-s7` | `--md-space-7` | `48px` |
| `--sv-s8` | `--md-space-8` | `64px` |

## Radius

| SpoofVane token | MeDo source name | Value |
|---|---|---|
| `--sv-r-sm` | `--md-radius-sm` | `6px` |
| `--sv-r-md` | `--md-radius-md` | `10px` |
| `--sv-r-lg` | `--md-radius-lg` | `16px` |
| `--sv-r-pill` | `--md-radius-pill` | `999px` |

## Elevation / motion

| SpoofVane token | MeDo source name | Value | Notes |
|---|---|---|---|
| `--sv-shadow-1` | `--md-shadow-sm` | `0 1px 2px rgba(0,0,0,.4)` | |
| `--sv-shadow-2` | `--md-shadow-lg` | `0 8px 24px rgba(0,0,0,.45)` | |
| `--sv-shadow-glow` | `--md-shadow-focus` | `0 0 0 1px brand, 0 0 24px rgba(255,176,32,.15)` | OVERRIDE (amber focus glow vs MeDo blue) |
| `--sv-ease` | `--md-ease-standard` | `cubic-bezier(.2,.7,.2,1)` | |
| `--sv-dur-fast` | `--md-dur-fast` | `120ms` | |
| `--sv-dur` | `--md-dur-base` | `220ms` | |
| `--sv-dur-slow` | `--md-dur-slow` | `420ms` | |

## Coverage

Every token defined in `tokens.css` (19 color, 9 type, 8 spacing, 4 radius,
6 elevation/motion) appears above with a MeDo source name. OVERRIDEs are all in
the threat-domain palette (amber brand, deepened canvas, amber focus glow),
each justified by SOC low-light + threat-semantics use.
