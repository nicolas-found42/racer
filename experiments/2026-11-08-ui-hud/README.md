# 2026-11-08 UI and HUD rebuild against six source games

- Status: completed (this round); open items listed below
- Target/build/platform: Racer, branch `feat/ui-hud-fidelity` (from `main` 2a1913d), macOS Metal, `cmake --build build`, native captures at 1280x720 hidden/isolated profiles
- Canonical inputs (read-only, `games/raw/`): `midnight-club-la`, `mc3.iso`, `gran-turidmo-4.iso`, `juiced-2`, `slrr-221`, `slrr-231` (hashes in `games/INPUTS.json`)
- Question: how far is Racer's UI/HUD from the source games' UI/HUD element by element, and which of their layout/colour/typography rules transfer into a cleaner, more creative HUD without fabricating data the simulation does not provide?
- Limits: native runs 9 s each (`scripts/capture_ui.sh`), ~15 MiB per full capture set, extracts live in the sibling leaf [2026-11-08-ui-source-extracts](../2026-11-08-ui-source-extracts/README.md) (leaf kept under 256 MiB; this leaf ~135 MiB). Free space 383 GiB at start.
- Output: `output/base` (before), `output/cur` + `output/size-*` (final), `output/compare/*.jpg` (element sheets), `output/r1..r13` (iteration rounds). Third-party screenshots are in ignored `references/<game>/` with `manifest.json` (URL, sha256, resolution) per game; they are not redistributed.

## Method

1. Baseline captured from `main` (`output/base`, `base-sheet.png`): every screen was a raw string list (`PlayFlow::lines()`) painted as one text panel; the drive HUD was two flat cards; the gate tag was green debug text.
2. Five research agents (one per game; SLRR 2.2.1/2.3.1 together) mined shipped UI assets and gathered online screenshots of every HUD/UI element (188 reference images: MCLA 39, MC3 31, GT4 47, Juiced 2 25, SLRR 46 - counts from each `manifest.json`).
3. Tools actually used: REA MCP (commit `71f680d`) - MC3: `capture_process_scenario` running `xdvdfs-cli 0.8.3` (evidence `ev_8bc84979...8ede44`); SLRR: Ghidra 12.2 provider (`inspect_pe_imports`, `open_binary`, `search_strings`, `xrefs`, `procedure_pseudo_code`; exe SHA-256 `f44fb88a...fefc2`); MCLA, GT4, Juiced 2: `inspect_byte_entropy` only (`ev_ff403d0f...9685`, `ev_4f05969f...1836a`, `ev_93d9b579...c54e`). GT4 and Juiced 2 UI resources were decoded with project parsers (`scripts/decode_gt4_gpb.py`, `j2_tex.py`), not REA; MCLA used the reviewed LZX decoder. Firecrawl's key was invalid in every agent, so Keenable + plain HTTP were used for screenshots. **The Jev MCP could not run (`OPENROUTER_API_KEY` not set), so no Jev judgment was obtained; design decisions below are reasoned from the cited evidence, not Jev-verified.**
4. Our screens were captured with `scripts/capture_ui.sh` (review scripts drive the menus), compared with `scripts/compare_ui.py` against `compare-spec.json`.

## What was built (all in `src/`, tests pass 102/102)

| Piece | Where | Source-game evidence behind it |
|---|---|---|
| UI view model: classifies existing `lines()` rows into option/slider/field/tiles/warning/notice, icons, key hints (pure, `tests/ui_model_checks.cpp`) | `ui_model.h` | GT4 row template + tooltip; SLRR dual-column specs |
| CoreGraphics primitives (gradients, skew, arcs, vector icons, keycaps, DIN/Avenir Next Condensed type) | `ui_paint.h` | MC3/J2 skewed plates, GT4 one-accent rule |
| 270 deg arc speedometer with speed-tinted arc, lit ticks, gear chip, real pedal bars | `drive_hud.mm` | MC3 250 deg dial, SLRR 31%-of-height corner dial, MCLA state tint |
| Heading-up radar with authored 100 m street grid, rotating compass rim, destination/gate blips | `drive_hud.mm` | MC3/MCLA/J2 round minimap bottom-left, rim as compass |
| World waypoint marker with beacon column, edge arrow + name chip when off-screen (replaces green posts, debug gate text, and a redundant top strip) | `drive_hud.mm`, `main.cpp` | MCLA yellow beacon + arrow, MC3 edge arrow |
| Active-test HUD: timer plate, gate counter + guidance arrow, 0->100 / 100->0 progress bar, countdown ring with per-second pop, GO and gate-cleared banners with echo | `drive_hud.mm` | MC3 countdown scale/fade, J2 echo banners |
| Menus: left rail with skewed selection, icons, tuning sliders, adjustable chevrons, alternating tint, `n of N`, info card (stat tiles, key/value, hero result, warnings/notices, hint callout), keycap footer | `drive_hud.mm` | GT4 alternating rows/help bar, MC3 single-colour selection, J2 darken-only-half |
| Showroom: slow turntable camera framed right of the menu, ring plate; event board street map | `main.cpp`, `drive_hud.mm` | MC3/MCLA/J2 live garage car, J2 turntable ring, MC3 Nav System |
| Compact/medium windows: structured menus down to 0.75 scale; compact canvas rebuilt on the same model (scrolling rows, warnings pinned) | `hud_layout.h`, `drive_hud.mm` | - |
| Career event rows now use the same two-space option prefix as every other flow | `career_flow.cpp` | - |

Deliberately not built: an RPM tach / gear model. The simulation exposes only speed, steering and pedal input; a tach would be fabricated telemetry. Pedal bars, speed, heading, positions and the street grid are real data.

## Element comparison (observed from `output/compare/*.jpg`, strict-reviewer verdicts)

| Element | Verdict after changes | Remaining gap vs best reference |
|---|---|---|
| Speedometer | cleaner and more legible than all six games' | no analogue needle or redline (no RPM data) |
| Minimap/radar | street grid + blips + compass; matches placement/size of MC3/MCLA/J2 | no building/parks texture; roads are the authored grid only |
| Waypoint marker | beacon + diamond + chip, comparable to MCLA/MC3 | no GPS ribbon |
| Pause menu | cleaner than MC3/SLRR/J2; icons + glow selection | static (no slide-in animation) |
| Garage list/tuning | above GT4/SLRR/MCLA lists for clarity; live turntable car | showroom is the dark street; MC3/MCLA/J2 garages are lit interiors |
| Results | hero numeral + stat tiles; clearer than SLRR/MCLA/J2 tables | no medal/cup art, no results table of rivals (no rival data) |
| Countdown/GO | ring + pop + banner | no coloured GO ring per outcome |
| Race timer/gate HUD | clearer than MC3/MCLA; lacks lap/position (single-car tests) | - |
| Footer hints | keycaps; closest peer GT4 help bar | - |
| Event board | map + tiles | map has no district art |
| Compact (<0.75) | now same language | text-only info cards omitted by design |

## Adversarial-review ledger (strict UI/HUD persona, manual; no Jev gate)

Closed this round: raw text walls everywhere; unaligned values; no selection affordance; debug-green gate tag; green posts and amber strips at screen edges in menus; redundant destination info in three places; menus unreadable below 1280x720; compact HUD plates; garage with no car view; no hierarchy in results; sliders without range cue.
Open: lit garage interior / car-on-turntable lighting; HUD colour option; lap/position elements (no race mode yet); minimap texture; pause slide-in animation; canvas is 1280x720 upscaled (no hi-DPI canvas); world-art defects outside the UI (flat neon sign blocks, tree cards) are not addressed here.

## Evidence / retention

Keep: all `output/` sheets and comparison JPEGs, `compare-spec.json`, scripts. Referenced screenshots are third-party and local only. Round directories `r1..r13` are intermediate evidence (small, kept). Per-game extraction outputs moved to the sibling leaf to respect the 256 MiB bound (moves only; no deletion).
Regeneration: `scripts/capture_ui.sh experiments/2026-11-08-ui-hud/output/cur 1280 720` then `scripts/compare_ui.py experiments/2026-11-08-ui-hud/compare-spec.json experiments/2026-11-08-ui-hud/output/cur experiments/2026-11-08-ui-hud/output/compare`.

## Next action

Lit garage interior (floor/backdrop geometry with a key light) so the turntable car reads like the MC3/MCLA/J2 garages; then a HUD colour setting in the garage.
