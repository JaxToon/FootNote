# Visual System

## Brand palette (identity surfaces)

| Token | Hex | Use |
|---|---|---|
| Ink Navy | `#111D38` | Primary brand dark |
| Footnote Yellow | `#F3D65B` | Signature accent |
| Paper | `#F4F1E8` | Light surface |
| Signal Coral | `#E56B50` | Secondary emphasis |
| Teal | `#245F59` | Supporting accent |
| Purple | `#5142A0` | Supporting accent |

## Video scene palette (historical source brief)

Navy `#1E2A5A`, dark navy `#0F172A`, purple `#5B3CC4`, teal `#0F766E`, near-black `#111827`, amber `#FFB703`, light blue `#7DD3FC`, green `#4ADE80`, red `#E63946`, light pill `#FFF6E6`, dark pill text `#151A2D`.

## Typography

Historical video tokens: Anton (headings), Poppins 600–700 (captions/body). Brand-board proposal: Space Grotesk (headings), Inter (body), IBM Plex Mono (technical labels). Check installation and licenses; do not bundle font files without permission. Keep typography configurable by profile.

## Motion language
- Clear, purposeful motion; avoid decoration that distracts from the explanation.
- Pop-in and slide-in easing may be used, but animation must be frame-deterministic.
- Lines/arrows may draw on to reveal a process.
- Grain is optional and must not reduce legibility.
- Decorative statistical symbols should remain subtle and never be mistaken for data.

## Short safe area
Reserve approximately the bottom 20% for platform UI. Caption position must be configurable per platform profile. Keep title, data labels, and NODI outside critical UI overlap.

## Data integrity
Charts must be generated from data in the episode spec or derived deterministically. Mark synthetic values as `Ilustrasi`. Units, axes, and labels must agree.
