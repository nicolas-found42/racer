# 2026-11-09-vehicle-physics-patches: apply the force-based vehicle physics patch series

- Status: completed; committed on branch `feat/vehicle-physics` (PR pending). Patches applied, project and renderer wired, verified headless over 29 cars and live (renderer wiring section below). No subjective drive test by a person.
- Target/build/platform/architecture: Racer `debug/wheel-clip` at `12033e2`, macOS arm64, Apple clang 21.0.0, CMake 4.4.4, Release build in `build/`.
- Canonical input: `vehicle-physics-patches/` (untracked, kept): `0001-physical-parameters-and-tyres.patch` 9d1469d5…7f, `0002-chassis-drivetrain-and-road-contact.patch` 276e0572…83, `0003-physics-aware-benchmarks.patch` 97b0225d…bf, `SHA256-manifest.json`, `README.txt`, `verification/`. All ten original `src/` files matched the manifest's `original_sha256` before applying; all ten match `patched_sha256` after (rechecked after every later edit).
- Question and expected observation: do the three patches apply cleanly, and does the project (build, 103 ctest suites, live app checks) work with the new model? Expected from the series README: clean apply, 30/30 isolated scenarios; unknown: effect on the existing project.
- Tool/provider/version: git apply, cmake/ninja, clang++ -std=c++20, the series' `verification/run_tests.sh` (plain and `SANITIZE=1`: `-fsanitize=address,undefined`). Jev `typesafe/jev-1.14-20261014` via `jev_gate` (source diff of the integration changes only). REA not used (source project).
- Working directory and exact commands (from `games/racer`):
  - `git apply --directory=src --check|apply vehicle-physics-patches/000{1,2,3}-*.patch` (from the repo root. Running `git apply` from inside `src/` silently matches nothing: no error, no change.)
  - `bash vehicle-physics-patches/verification/run_tests.sh $PWD/src` and `SANITIZE=1 …`
  - `cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=/opt/homebrew && cmake --build build -j 8; ctest --test-dir build -j 6`
  - `./build/racer --verify-controls --profile /tmp/racer-vc-new/profile.txt`, `--verify-garage keyboard|gamepad --profile …`, `--smoke 14 --benchmark --autodrive`
- Limits before running: builds ≤ a few minutes, ctest ≈ 7 s, each live check ≤ 150 s timeout; no large outputs (381 GiB free, `build/` is ignored). Isolated profiles under `/tmp` so the real profile was not written (its files keep their 2026-11-06/09 mtimes).
- Output location: `build/` (ignored), the source/test edits in the working tree (uncommitted at evidence time; now committed on `feat/vehicle-physics`), and `evidence/` (contact sheets, scripts, generated ramp mesh, about 1.4 MB).
- Started/finished and exit result: 2026-11-09; all checks exit 0 (final run below).

## Observations and evidence

- Patches apply cleanly and byte-for-byte reproduce the series' patched sources. Isolated suite: 30/30 (also ASan+UBSan), default profile 0-100 km/h 7.91646 s over 110.45 m, 100-0 in 2.918 s over 41.816 m.
- Baseline (patched files stashed): 103/103. Patches alone: **10 of 103 failed**. Causes, all in code that encoded the retired kinematic model:
  1. Tests: exact 100 km/h at 8 s, 160/30 km/h clamps, 40 m stop, exact `speed == 0`, 497.5 m centre boundary (now the oriented body envelope hits the 500 m wall at centre 497.8 m), Ackermann-corrected front wheel angles, banked ≤60° faces now supported by default (old limit .9 normal), `wheelbase` ratio of one-tick heading.
  2. **Real integration defects (fixed in source):**
     - `src/profile.cpp` rejected `testRevision != 1`, so every revision-2 benchmark result was silently dropped (no record, no best). Now 1 and 2 are valid; old records still load; `comparable()` never mixes them.
     - `src/presentation.cpp` queried best results with `testRevision` 1, so the comparison screen showed "No comparable result". Now uses the current revision.
     - `src/performance_class.h` predicted time as `8/acceleration`; replaced by the measured table (acc .8 → 10.02 s … 1.0 → 7.916 s … 1.2 → 6.591 s). Class bands D/C/B/A unchanged.
     - `src/live_checks.h` required `car.speed == 0` after a menu resume; physics leaves ≈1e-5 m/s settling. A parked car drifts ≈1e-8 m/s (0.5 µm in 140 s). Now `< 0.01 m/s`.
     - `PlayFlow::configureVehicle` now also calls `setDynamics(dynamicsFor(geometry))`. With generic 12 cm suspension travel, the real Juiced 2 CCX (8.6 cm clearance, two descriptors) and Ford GT (10.3 cm) fail the **braking benchmark with "Chassis contact"**. Travel is limited to `min(.12, .6 × body clearance)`. Probe over all 25 `assets/local/vehicles/*.vehicle` (3 first failed, then all 25 valid): acceleration 7.34–7.94 s, braking 40.5–41.3 m. New regression: `tests/vehicle_asset_checks.cpp` (bare generic suspension bottoms out on a low car; `configureVehicle` limits travel and the benchmark completes).
- Final: `ctest` **103/103** (same count as baseline; no suites added, `vehicle_asset_checks`, `setup_checks`, `surface_follow_checks`, `vehicle_geometry_checks`, `driving_checks` gained assertions). `--verify-controls`, `--verify-garage keyboard`, `--verify-garage gamepad` PASS; smoke autodrive 1561 frames, 120.0 FPS, longest frame 8.5 ms.
- Jev `jev_gate` (final source diff, claims vs ctest/hash/probe logs): `escalate`, no claim contradicted; 5 of 7 claims verified (live checks 0.97, hashes 0.92, patches-alone-10-failures 0.89, main.cpp unchanged 1.0), real-car claim 0.74 verified at confidence 0.61, sanitizer claim unsupported (my evidence omitted the flag names), patch review safe_to_apply 0.53 with `test_gap` the limiting rubric (0.26). I added the regression test above; the sanitizer flags (`-fsanitize=address,undefined`) are in `vehicle-physics-patches/verification/run_tests.sh:16`. Treated as signals, not proof.

## Conclusion and limits

- The patch series is applied, builds, and passes all project checks. Defects found by the project's own checks are fixed as above.
- Not done / unverified:
  - Reverse gear is no longer capped: default reverse reaches ≈82 km/h; forward top speed is drag/gearing limited (137 km/h at 13 s). Decide whether that matches intended behaviour.
  - Handling is generic and uncalibrated (README of the series); `dynamicsFor` (`src/vehicle_tuning.h`) is a heuristic for suspension travel and spring/anti-roll stiffness only. Garage multipliers' meaning changed (acceleration scales engine torque; brake strength saturates at the tyre limit: 1.2× brakes → −3% stop distance, 0.8× → +14%).
  - Old revision-1 records in existing profiles are retained but are never compared with revision-2 results.
  - The default city world has no road mesh, so on the default scene the car still drives on the flat Y=0 plane (body pitch/roll/heave and wheel travel are rendered, terrain support only exists with `--world-mesh --follow-ground`). Traffic and parked cars are unchanged (not physics-driven).
  - The far-teleport ground search in `placeOnGround` (`src/main.cpp`) has no unit test (only the screenshots and `restingPose` are covered).
  - Debug-time probe sources lived in the session scratchpad only and were not retained (regenerate from the commands above).

## Renderer wiring and multi-car verification (user request: several cars, several angles, screenshots)

Changes (uncommitted at evidence time; now committed on `feat/vehicle-physics`): `src/main.cpp` (road sampler from the loaded `SurfaceIndex`, `placeOnGround` teleport placement, per-frame `Simulation visual` copy advanced by the leftover frame time so the car is drawn from `bodyTransform()`/`wheelTransform()` at any refresh rate, contact frame for shadow/footprints/camera from the simulation's wheel contacts, skid marks and smoke from simulated tyre slip, HUD speed from `groundSpeed()`; the fitted-plane `fit()` path and its `surface_follow_uncovered` abort are gone from the drive view, the flat kinematic path stays for the prototype car), `src/vehicle_tuning.h` (new), `src/tyre_contact.h` (`tyreLowestAlongNormal`), `src/surface_follow.h` (`restingPose`).

Defects found by the multi-car checks and fixed:
- **Low cars scraped in the cornering handling course** (Juiced 2 CCX, 8.6 cm): a travel cap alone is not enough because load transfer overruns the bump stop. `dynamicsFor` now also scales spring and anti-roll rates by the travel reduction (damping by its square root). All 29 cars then complete acceleration, braking and the driven handling course (0-100 7.16–7.94 s, 100-0 40.6–41.8 m).
- **Teleporting a car onto a slope with pitch=roll=0 wedged it into the road** (the uphill wheels fall outside the suspension query band; a long truck on 12° ended 0.7 m below the road). Placement now uses the fitted road plane (`restingPose`), with pitch and roll.
- **`placeOnGround` only searched 0.75 m around the previous ground height**, so `--start-at` onto a slope at y≈10 m left the car buried and invisible. It now falls back to the highest road under the point after a far teleport.
- A "no sustained chassis contact" claim was too strong: a low body scrapes the sharp flat-to-12° kink for up to 35 ticks (0.29 s); the test bounds it at 0.5 s and requires no contact at the end.

Tests added/extended (all in ctest, now **106/106**; each takes the 5 synthetic cars — default, 8.6 cm low sports, 1.84 m compact, 3.57 m truck, wide estate — plus the real descriptors in `assets/local/vehicles` when present, 29 in total):
- `terrain_physics_checks`: real `SurfaceIndex` through `makeRoadSampler`, 12° ramp at headings 0, ±25°, ±50°: all wheels grounded, body up within 4° of the ground normal, pitch and roll within 3° of the analytic values (roll sign from the heading), brief scrape only, mesh gap → airborne and falling, flat default world at static ride height, dynamic wheel transform follows suspension travel, Ackermann inner/outer front angles.
- `vehicle_benchmark_checks`: acceleration, braking and the driven handling course through `PlayFlow::configureVehicle`.
- `driving_checks`: acceleration/braking/mirrored steering and no tunnelling through the world wall from 8 headings (0, 90, 180, 270, 30, 60, 135, 225°), every tick, per car.
- `tyre_slope_checks` (17 real vehicles, their actual tyre meshes): 272 wheel placements on a 12° slope at 4 headings using the renderer's rule (`tyreLowestAlongNormal`) then every vertex of the rolling meshes against the analytic plane: worst lowest-point error **0.0013 mm**, largest renderer shift 3.7 mm. This replaces an unmeasured "pixel-level" claim (Jev's gate returned `verified` at 0.19 confidence for that claim although my evidence said the opposite; I treated it as unsupported).

Screenshots (`evidence/`, from `run_matrix.sh`, `run_matrix2.sh`, `sheets.py`, `brake.script`, `corner.script`, generated 12° `ramp.gltf`; 54 + 6 captures, 0 failures): `sheet-ramp.jpg` (6 cars × rear/left/front/elevated climbing the ramp), `sheet-brake.jpg` (6 cars × left/front, scripted full throttle then full brake, nose dive and front tyre smoke at 32–37 mph), `sheet-corner.jpg` (6 cars × rear/right/elevated, scripted steering, tyre marks visible in the elevated views), `sheet-slope-start.jpg` (NSX, RAM, Ford GT started on the slope, nose-up). Cars: Acura NSX '04, Mustang 1973, Dodge RAM 1500, Daihatsu Midget, Ford GT, Juiced 2 CCX (clearances 8.6–22.3 cm). Caveats: judged at thumbnail scale; heavy wheelspin smoke on the ramp now hides the rear camera for some cars (it comes from real slip, `|slipRatio| > .2`); autodrive's sustained steer at speed now ends in a slide, so the scripted inputs were used instead.

Jev `jev_gate` on the renderer diff: `escalate`, 0 contradicted, 3 verified at auto, `test_gap` limiting; after it I added `tyre_slope_checks` and found the two placement defects above. Final run: ctest 106/106; `--verify-controls`, `--verify-garage keyboard|gamepad` PASS; smoke autodrive 1560 frames at 119.9 FPS.

## Chase camera and tyre smoke retune

Question: the default chase camera looked down too steeply and tyre smoke filled the screen. Target: `build/racer` from this working tree (then-uncommitted `src/main.cpp`, now committed), pre-change binary kept for comparison.

References looked up (web search, then the images viewed in the browser pane; third-party frames are not stored here): Assetto Corsa chase presets that mimic other games give camera pitch below the horizon of 3.4° (Gran Turismo-style, 2.8 m back, 1.3 m up), 7° near and 10° far (Forza Motorsport 7-style, 3.5/1.8 m and 4/2.5 m), 3° (Forza Horizon-style, 4.9 m, 1.58 m), and AC's own default of 0.2° far and 14° near. Frames viewed for Forza Horizon 5, Gran Turismo 7, NFS Heat, Burnout Paradise and Juiced 2 (eyeballed, not measured) put the horizon near 40–45% from the top with the car in the lower middle; Juiced 2 sits more elevated. These are community approximations of the games' cameras, not recovered constants.

Changes in `src/main.cpp`:
- The default (`rear`) chase camera now aims by pitch: `--camera-pitch` degrees below the horizon, default 5 (range 0-30). The old aim-at-the-body camera looked about 11° down. At 55° vertical FOV, 5° puts the horizon about 42% from the top (old: about 31%). Distance and height are unchanged (about 3 m behind the bumper, 1.7 m up for the NSX), already inside the reference range. Other review views, hood and showroom are unchanged.
- Tyre smoke: emission 130 → 42 puffs/s per rear wheel (launch 34 → 14), life 1.2–1.8 s → 0.55–0.8 s, start size 0.6 → 0.30 m, growth ×4.2 → ×2.5 with a 0.7 m cap, peak opacity 0.62 → 0.27, quad lift 0.9 → 0.55 of size (lower to the road), initial rise 0.3 → 0.1 m/s, tyre-smoke particles capped at 260, and a fade to nothing as a puff comes within 1.5 m of the lens (full strength beyond 5 m), so smoke cannot cover the view. Exhaust wisps and sparks are unchanged.

Evidence (`evidence/`): `chase-camera-before-after.jpg` (cruise and braking, 4 cars: NSX, Mustang '73, Dodge RAM, Juiced 2 CCX, before and after), `tyre-smoke-before-after.jpg` (launch and sustained slide), `tyre-smoke-stress.jpg` (after only: full-throttle full-lock donut and a hard sustained slide). `run_camera_matrix.sh` runs the matrix with `--background` (hidden Metal window, nothing is activated, so no focus-loss pause), 960×540, four captures in parallel with separate profile files: 32 captures in 83 s, against about 15 min serially. Earlier visible runs paused the game on focus loss (two Dodge RAM captures showed the pause menu). A non-zero exit from these runs is expected (the app leaves at the smoke limit); only a missing image is a failure.

Result: 100% of captures produced; smoke now stays a small wisp behind the tyres in all four cars, including the stress runs; the car sits lower in frame with more road and horizon above it. Checks after the final build: ctest 106/106, `--verify-controls`, `--verify-garage keyboard|gamepad` PASS, autodrive smoke 1561 frames at 120 FPS with 0 slow frames. Limits: before/after speeds differ between captures because parallel hidden runs start at different real times (compare framing and smoke, not speed); no human drove it; reference comparison is by eye from search-result frames; the pitch default is chosen by me inside the 3–10° range, not matched to one game; skid-mark brightness was not changed.

## Retention

Keep `vehicle-physics-patches/` (canonical input; tracked in git since commit `218ecdb`, previously kept untracked on disk). `build/` is ignored and regenerable. No other outputs.

## Next action

Drive it by hand (keyboard or gamepad) in the default city and on a `--world-mesh --follow-ground` slope; decide the reverse-speed limit and whether 5° chase pitch and the light smoke feel right (`--camera-pitch` to try others); then merge the `feat/vehicle-physics` PR (source, tests and evidence are committed there).
