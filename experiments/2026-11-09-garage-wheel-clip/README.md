# Garage tyres clip into the floor

- Target: `build/racer` at `95dc4d2` (main, PR #2 merged), Acura NSX '04 (vehicle 0), Metal, 1280x720.
- Question: why do the wheels clip through the floor in the garage, and does the game do it too?
- Method: temporary env-driven orbit camera (not committed) plus per-layer hide mask; screenshots at several angles/zooms; tyre-bottom row measured against the analytic projection of y=0 (scan down from hub to first floor-bright pixel; 1 px ~ 2.5 mm at 1.73 m).
- Evidence (real frames, not code reading):
  - `wheel_geometry` diagnostics: every tyre bottom (centre.y - radius) is 0.000 m for vehicles 0-16 (<= 0.5 cm). Vehicles 17-23 emitted no wheel events and were not checked.
  - Garage floor stack sits above y=0: studio floor .03, plate .05, rim .06, veil .052, contact blob .075; blob/plate/floor write depth, so they depth-hide the tyre bottoms.
  - Buried tyre height, close side view: baseline 7.6/7.8 cm (front/rear); blob hidden 5.1/5.3; +plate hidden 3.1/3.3; +studio floor hidden 1.1/0.8 (noise floor). Steps match the layer heights.
  - Floor-level horizon camera with all layers hidden: tyres are round and end on the horizon row, so the meshes and wheel transform are fine.
  - Driving mode, stationary, floor-level camera: luma profile through the tyre contact rows identical to the all-layers-hidden garage control (zero burial).
- Cause: garage stage geometry was authored in a plane above the tyre contact plane (y=0).
- Fix: `showroomFloorDrop = .08f` lowers all stage layers (floor, gloss, blob, plate, veil, redrawn blob) below y=0 in `src/main.cpp`. After: 1.1/0.8 cm (noise floor); frames show round, grounded tyres and the reflection intact. `ctest`: 102/102.
- Not verified: driving at speed (the scripted run was declined and not retried); vehicles 17-23; other garage screens beyond the default showroom camera.
- Retention: frames and scripts were in the session scratchpad only; none retained. The debug camera patch was removed.
- Next: re-run the measurement for vehicles 17-23 and an at-speed drive capture if desired.
