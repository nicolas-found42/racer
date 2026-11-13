# Incremental HUD repaint

Question: the drive HUD dominates frame cost even when almost nothing on it
changes. Can it repaint only the windows whose inputs changed, with pixel
identical results and the same visible behaviour?

## Target and build

- Checkout `games/racer`, `main` at `eecaf09` (world/night sky attribution) plus
  the working-tree HUD change described here. Baseline binary: `git archive HEAD`
  extracted to `/tmp/racer-base` with `assets/local`, `assets/visual-local` and
  `.deps` linked, built with the same CMake Release configuration.
- App: `build/racer`, Metal backend, Release (`-O3`), 1920x1080 Metal drawable
  (`--benchmark`), vsync + MSAA x4, 120 Hz display.
- Host: Apple Silicon, macOS 27.0.1; the machine was shared during measurement
  (load average 16-28 on 18 cores), so wall-clock FPS is noisy and CPU time per
  frame is the primary metric.

## Baseline observation

`sample` of the 1080p autodrive run, before the change:

| thread | self/total samples | dominant frame |
|---|---|---|
| main | 992 | `DriveHud::draw` 765 (77 % of the main thread) |
| render | 992 | `flushTextureUpdateBatch` 248, of which `TextureMtl::update` 213 |

Per frame the HUD cleared the whole 1280x720 RGBA canvas, re-rasterised every
widget (shadow blurs, radial gradients, CoreText runs) and uploaded the complete
3.5 MiB texture, which the render thread then converted tile by tile.

Whole-frame CPU (`/usr/bin/time -l`, user+sys over measured frames, interleaved
A/B) put the HUD at roughly 3.3 ms of the 8.33 ms frame budget: the largest
single cost in the frame at 1080p/120 Hz, and the source of the missed-vsync
frames observed under load.

## Change

`src/hud_repaint.h` (new) maps a sanitised `DriveState` change to the widget
groups it can affect and owns the conservative canvas windows for the widgets
whose ink does not depend on measured text. `src/drive_hud.mm` repaints only
those windows:

- clear each dirty window, clip to their union, re-run the *complete* paint
  pipeline into the clip (same order, blending and antialiasing as a full
  repaint), then `updateTexture2D` each window's packed rows only;
- the waypoint and announcement banner report ink bounds from the same code that
  draws them (the label/plate width is measured once per frame), so their
  windows follow the real geometry instead of a guess;
- the banner is painted at the midpoint of its quantised animation step
  (90 steps over 1.9 s, unchanged) so any window repaint draws the same banner
  frame the rest of the canvas holds; painting the continuous phase per window
  would leave a patchwork of banner positions;
- compact layout, menus and any layout/scale/accent change still repaint in
  full, as before;
- a second iteration skips the widgets whose ink window cannot reach the dirty
  set at all: clipping alone hides their pixels but still pays each draw's setup
  (CoreText runs, gradient and shadow state) on every window repaint, which is
  most of a repaint that only moves the waypoint. The waypoint and banner
  geometry is now measured once per frame and reused by the dirty set, the
  paint and the audit instead of being measured twice.

`--hud-repaint-audit` (verification switch) paints each drive frame a second
time into an unclipped scratch canvas and reports any pixel the incremental path
missed. `tests/hud_repaint_checks.cpp` covers the change mapping and window
bookkeeping; `tests/hud_repaint_audit_checks.py` runs the audit over free drive
and the handling course.

## Results

Primary metric: CPU time per measured frame (`user+sys` over the frames the
benchmark reports), because vsync caps the frame rate at 120 Hz and the host was
shared during the runs. Reproduction:

```sh
scripts/measure_frame_cost.sh baseline=/tmp/racer-base/build/racer final=./build/racer
```

Each build runs the normal 1080p workload (`--smoke 12 --benchmark --autodrive`)
alternately, five times, so a busy host perturbs both sides equally. Canonical
run (load average 16-28 on 18 cores; absolute numbers move with host load, the
paired ratio does not):

| metric | baseline (HEAD) | final |
|---|---|---|
| CPU per frame, median | 12.95 ms | 6.16 ms |
| main-thread `user` per frame | 9.63 ms | 4.54 ms |
| kernel `sys` per frame | 3.32 ms | 1.64 ms |
| frames over 16.67 ms, median | 45 | 17 |
| FPS, median (vsync capped) | 108.2 | 114.7 |

Three independent interleaved windows (5, 5 and 6 pairs) give a paired
CPU-per-frame ratio of **0.57, 0.57 and 0.58**: the HUD's cost fell by about
**42 %** of the whole frame's CPU. `sys` time (the render thread's tile
conversion of the per-frame texture upload) fell by 41-45 %.

Attribution, same window per row:

| measurement | baseline | final |
|---|---|---|
| CPU per frame, HUD drawn | 8.26 ms | 4.89 ms |
| CPU per frame, `--hide-hud` | 2.73 ms | 2.62 ms |
| HUD-attributable | 5.5 ms | 2.3 ms |

The scene floor is unchanged within noise (paired ratio 0.95, spans 0.77-1.00),
so the gain is confined to the HUD path; the HUD itself is ~2.4x cheaper. The
second iteration (widget skipping + single geometry measurement) measured
0.915 of the first iteration's CPU per frame (paired median over 5 pairs,
spread 0.74-1.11), i.e. a further ~8 %.

What a player sees: at 120 Hz with vsync, baseline frames that missed the 8.33 ms
budget inside a 16.67 ms interval were 45 per 12 s run (median) and now are 17;
the median FPS rose from 108 to 115 under the same host load. On an unloaded
machine both builds sit at the 120 Hz cap, and the remaining headroom is what
keeps busy scenes from dropping frames.

## Verification

- `hud_repaint_checks` (unit) and `hud_repaint_audit_checks` (native audit) pass;
  the audit reports `failing_frames=0 over_slack=0 max_delta<=2` on both
  scenarios, with a few pixels per frame differing by at most two 8-bit steps
  (CoreGraphics applies the clip mask to gradient dithering and glyph/curve
  antialiasing; the pre-change full repaint had no clip).
- Full `ctest` on an isolated worktree of the committed revision: **109/109
  pass** (107 targets before this change; the two new ones are
  `hud_repaint_checks` and `hud_repaint_audit_checks`). The live checkout runs
  110/110 because it also carries another session's uncommitted taillight suite,
  which this commit does not include.
- Static requirement: no new dependency, no change to the HUD canvas size,
  texture format, shader, draw order, text, colours or timings of any widget.
- Visible equivalence on a parked deterministic frame
  (`--smoke 4 --post-neutral --screenshot`, 1920x1080): two runs of the same
  binary are pixel identical, and baseline versus final differ in a single
  28x4-pixel scene sliver (max delta 44) that is reproduced identically with
  `--hide-hud`, so it is a frame-timing dependent scene element, not HUD
  content; every HUD widget window (identity, controls, radar, dial) is
  byte-identical.

## Limitations

- The clip-mask rounding above means "pixel identical" is measured as "no
  difference beyond two 8-bit steps"; stale or missing widget content is orders
  of magnitude larger and is rejected by the audit.
- Menus/panels and the compact layout are unchanged (still full repaints); they
  are not on the driving hot path.
- Wall-clock FPS on the shared host is not a reliable comparator; CPU time per
  frame is reported instead, with the shared-host caveat.

## Next

- The HUD still costs ~2.3 ms per frame at 1080p. Of that, the waypoint window
  (its position changes on most frames) measures 0.33 ms when drawn unclipped;
  the reset is the per-repaint setup the clip cannot remove (CoreText runs,
  gradient/shadow state), the ~42k-pixel clear, the packed-row copy and the
  texture update. A cached static background layer (identity/controls/radar/dial
  baked once, composited under the waypoint and banner) would remove the setup
  work for waypoint-only frames, at the cost of a second canvas and an extra
  composite; it is the next candidate, not yet attempted.
- Iteration 2's widget skipping is verified but its win is small (~8 % of the
  HUD path); a workload that changes only the dial (e.g. a throttle-only probe)
  would show its best case more clearly than the autodrive mix does.
