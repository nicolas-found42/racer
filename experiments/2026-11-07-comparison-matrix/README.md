# 2026-11-07 comparison matrix: many Racer frames against many raw-game frames

**Why:** the earlier comparisons used about five reference/Racer pairs, which the user judged too few. This experiment builds a large, systematic comparison: a fixed matrix of actual native Racer captures (times of day, camera views, close-ups, speed, braking) paired by scene category with a much larger set of console/PC reference screenshots from the five raw games, so visible gaps can be listed per category rather than anecdotally.

## Target
Branch `feat/improve-racer-visual-fidelity`, executable built from the working tree on 2026-11-07 (frozen into `output/base` by `scripts/capture_visual_review.py --traffic-vehicle 2 7 9 12 --camera-distance 9`; hashes in `output/base/manifest.json`). Captures: `scripts/capture_matrix.py output/base output/matrix` (37 scenarios, 1280x720, HUD hidden, default effects). References: `../2026-11-07-asset-mining/references/web` (52) and `references/web2` (agent-gathered), plus the earlier MCLA/GT4/MC3/Juiced frames in `../2026-11-05-city-scale/output/reference-images` and `/private/tmp/racer-visual-remainingrefs`. Reference screenshots are copyrighted third-party images kept local and gitignored.

## Method
1. `capture_matrix.py` writes one PNG per scenario plus `matrix.json` (arguments, description, category).
2. References carry a category from their manifest; Jev (`jev_classify`) cross-checks those labels from the descriptions, and `jev_rerank` picks the best-matching Racer scenario for each reference by meaning.
3. Side-by-side sheets (reference left, Racer right) are built per pair and as category grids; every grid is read by the author and gaps are written down below as observations, separate from inference.


## Results (first round, 2026-11-07)
- Racer: 37 scenario PNGs + garage/course UI captures = 39 frames, all 39 used.
- References: 62 distinct images (52 web captures across all five raw games plus PGR4, GRID, Forza Horizon, Burnout, NFS and 12 canonical MCLA frames); 69 pairs in 7 category sheets (`output/grids/{night,dusk,day,smoke,motion,closeup,garage}-NN.jpg`, 14 sheets, built by `scripts/build_comparison_grids.py` from `pairs.json`, which `scripts/make_comparison_pairs.py` writes). `jev_rerank` ordered Racer scenarios per category; the top matches were used and cycled.
- Every sheet was opened and read. Observations below are things visible in those sheets. Inference and unknowns are labelled.
- The agent-gathered `references/web2` set (target >= 120) had not landed when this round was written; a second round will add it.

### Observed gaps (per category)
**Night (17 pairs).** References (GT4 Hong Kong, MC3, Juiced 2, PGR4, GRID, NFS Most Wanted 2012, MCLA) show dense lit facades with readable signage, wet-road reflections of lights, bloom around lamps, lit car interiors and headlight pools on geometry. Racer shows: (a) flat-shaded violet/pink walls with no window pattern at the street level, (b) neon as flat saturated cyan/magenta rectangles with no sign content, (c) a dark sky with speckled stars that read as noise rather than a night city glow, (d) no road reflection of lamps at the camera distance, (e) a dim, grey headlight pool on the road that is the only strongly lit area, (f) green lane-guide markers dominating the foreground of rear/front frames.
**Dusk (10 pairs).** References show a warm, saturated sunset grade with long cast shadows, detailed trees (MCLA, SLRR, Juiced 2 PS3) and lens bloom. Racer dusk is a desaturated brown-grey grade; trees are low-resolution leaf cards; building walls are untextured planes; a soft yellow lens ghost sits low in frame. The sky is the most convincing part.
**Day (16 pairs).** References have dense, varied architecture, signage, vegetation and traffic. Racer day: sparse low-rise buildings with flat walls, bare long road, few props, the lane-guide markers, and large dark rectangular puddle/crack patches with hard edges visible on the speed frames (`speed-day-10s/14s`). Sky and clouds are comparable to the lower-end references; the world around the road is not.
**Tyre smoke (8 pairs).** References show wispy, lit, directional smoke with tyre marks and sparks; Racer rear-braking smoke is an opaque, symmetrical white/blue cotton ball that hides the road and the car (`brake-day-rear`, `brake-night-rear`); side views are closer to the references but remain a single soft blob. Skid marks are thin dark lines and are hard to see from the chase camera.
**Motion (8 pairs).** References show motion blur concentrated on the nearest geometry and wheels, with the car sharp (MCLA, NFS). Racer applies radial streaks that read as scattered particles/lines at the edges (`speed-night-10s/14s` shows white dashes in the sky) and the car stays tiny in frame; no per-object blur on the near road surface.
**Close-up / paint (6 pairs).** Racer has no true close-up; the `closeup-*` and `paint-*` frames are the same side camera at about 3 m, with the car cropped at the bottom edge. References show a car filling the frame with detailed wheels, reflections of the environment, interior and lights. Racer shows a recognisable body shape and a spoked wheel but no environment reflection, no visible interior, and headlights that do not light the car's surroundings.
**Garage / UI (4 pairs).** References show a lit garage/showroom interior as the backdrop. Racer's garage screen is a text menu over a darkened street; there is no garage scene.

### Cross-category findings
1. The largest visible gap is world content (facades, signage, props, vegetation density), not post effects.
2. Lighting at night has no environment: lamps do not light walls or the road beyond the car, and windows/signs carry no detail.
3. Smoke needs shaping (wisps, lighting, ground contact), not just density.
4. Close-up presentation (camera, reflections, interior, garage backdrop) is missing, so the car itself cannot be compared fairly at reference scale.
5. Racer is far from "indistinguishable"; this round only enlarges the evidence base. It does not close any gap.

### Not established
- Whether any reference's look (grade, bloom, shadow filtering) is recoverable numerically from the raw games; the MCLA/MC3/GT4 comparisons used only names and authored values.
- Reference resolutions differ (640x480 to 1920x1080) and some carry compression and watermarks, so fine-detail comparisons are limited to what the sheets show at 480x270 per cell.

## Retention
`output/base` (42 MiB, frozen build), `output/matrix` (42 MiB, PNGs), `output/grids` (4 MiB, JPEG sheets): total 89 MiB, under the 256 MiB bound. All are local and gitignored; reference images and Racer frames rendered with extracted assets are not published, except the selection placed on the evidence-only branch (see PR #1).
