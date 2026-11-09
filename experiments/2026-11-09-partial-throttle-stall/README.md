# 2026-11-09-partial-throttle-stall: why does acceleration stall at part throttle?

- Status: completed — root cause diagnosed (below), launch model fixed in `src/simulation.cpp`, regression test added, all 106 ctest targets pass.
- Target/build/platform/architecture: Racer `debug/wheel-clip` at `12033e2`, dirty working tree (the three vehicle-physics patches applied and uncommitted); `build/racer` SHA-256 `6eb13e63d6f5045570a842b3a0bff4fda049851eefe2b0bb27a867167f1d1dc9`; `src/simulation.cpp` SHA-256 `ef31add0ea62790f8e817e4586a466612913bc81a1d72054ed13ce6e9850e0e4`; macOS 27 arm64; Apple clang 21.0.0 (clang-2100.3.34.2); CMake 4.4.4. Headless probe; no SDL/bgfx window.
- Canonical input path, size, SHA-256: the working-tree `src/*` and the 24 ignored descriptors in `assets/local/vehicles/*.vehicle`; probe source retained at `probe.cpp` (4.1 KiB). No external binary analysed.
- Question and expected observation: the user reported acceleration stalling. Does throttle from rest produce monotonic acceleration, and if not, which throttle range and which code path?
- Tool/provider/version: `clang++ -std=c++20 -O2`, `src/simulation.cpp`, `src/setup.cpp`, `src/vehicle_geometry.cpp`, `src/test_session.cpp`; no REA, SDL, bgfx or network.
- Working directory and exact command: from `games/racer`:
  ```sh
  mkdir -p experiments/2026-11-09-partial-throttle-stall/output
  clang++ -std=c++20 -O2 -I src -I tests \
    experiments/2026-11-09-partial-throttle-stall/probe.cpp \
    src/simulation.cpp src/setup.cpp src/vehicle_geometry.cpp src/test_session.cpp \
    -o experiments/2026-11-09-partial-throttle-stall/output/probe
  experiments/2026-11-09-partial-throttle-stall/output/probe \
    > experiments/2026-11-09-partial-throttle-stall/output/probe.log
  ```
- Limits before running: compile ≤ 10 s, run ≤ 10 s, output ≤ 100 KiB; no captures and no simulation beyond 12 s per car (flat default world, away from the 500 m boundary).
- Free space and project/lab output usage before running: 401 GiB free; experiment output 148 KiB after the run.
- Output location: `output/probe.log` (ignored, retained locally) and the numbers below.
- Started/finished and exit result: 2026-11-09; build and run exit 0.

## Observations and evidence

Full throttle (keyboard `Input{1,0,0}`, application wiring `dynamicsFor(geometry)`):

- All 24 installed car descriptors accelerate normally: 4 s ground speed 14.64–17.16 m/s.
- The built-in acceleration test (testRevision 2) is valid for 24/24 cars: 7.34–7.94 s and 109.3–114.1 m to 100 km/h.
- Engine speed never falls below 813 rpm (idle is 850 rpm) in any of the 12 s partial-throttle runs, so this is not an engine cut-out.

10 % throttle held for 12 s:

- All 24 cars reach 1.71–2.63 m/s within 4 s and are still at the same speed at 12 s; measured longitudinal acceleration is 0.000 m/s².
- Engine speed is 860–862 rpm and the clutch reports 0.31–0.34 engagement.
- The Dodge RAM creeps fastest (2.61–2.63 m/s, larger wheel radius); the Mach 1 used by the live session plateaus at 2.11 m/s.

Threshold sweep on the default 2.7 m fixture (all cars share the same engine/drivetrain defaults):

| throttle | v(10 s) | rpm | clutch | aLong |
|---|---|---|---|---|
| 0.18–0.24 | 2.66–2.69 m/s | 873–884 | 0.58–0.59 | 0.00 m/s² |
| 0.25 | 2.93 m/s | 962 | 0.71 | 0.05 m/s² |
| 0.30 | 4.71 m/s | 1541 | 1.00 | 0.42 m/s² |
| 0.35 | 6.82 m/s | 2242 | 1.00 | 0.81 m/s² |

The engine never reaches 0 rpm (minimum 808 rpm in the 6 s traces), so this is not an engine cut-out: the car is held at the idle-creep speed.

Code path (`src/simulation.cpp`, working tree):

- `throttleTorque = throttle_ * setup_.acceleration` (line 457) multiplies the torque curve linearly; at idle rpm `torqueAt(850) = 140 Nm`, so 10 % throttle requests 14 Nm.
- Engine braking is `engineBrakeTorque * (1 - throttle_)` (lines 468–472), i.e. 31.5 Nm at 10 % and 33.6 Nm at 4 % against a 35 Nm closed-throttle value.
- The idle governor `(idle - engineOmega_) * 8` (line 468) is a proportional speed controller clamped to `torqueAt(idleRpm)`; below ~24 % throttle it finds an equilibrium within about +40 rpm of idle (measured +10..34 rpm).
- The automatic clutch is already engaged at idle: `(rpm - idle + 150) / 1200 = 0.125`, multiplied by the speed term to 0.31–0.59 (`src/simulation.cpp:475`). It therefore couples the driveline to the governed idle speed; the car's speed is the wheel speed that back-drives the engine at that rpm in first gear (2.1–2.7 m/s depending on wheel radius).
- The automatic anti-stall disconnect only applies when `throttle_ < .02` (line 476), so it cannot release the engine at 5–24 % throttle.
- Above ~24 % throttle the engine torque at the top of the governor band exceeds friction and viscous loss, the governor clamps to zero, engine speed and clutch engagement rise, and the launch proceeds.

Exploratory (scratch copy, not retained): removing `engineBrakeTorque` removed the hard plateau but 10 % throttle still reached only 2.59 m/s in 6 s, because the idle-referenced clutch engagement still pins the engine near idle; a square-root throttle map alone improved but did not eliminate the low-throttle bog. Both indicate that fixing only one of the three terms is insufficient.

## Conclusion and limits

- The reported stall is real but throttle-dependent: an analog trigger (gamepad right trigger is `axis/32767`, `src/gamepad.cpp`) held between 5 % and ~24 % leaves the car at 1.7–2.7 m/s (≈6–10 km/h) with 0.000 m/s² and idle rpm. Full throttle, the keyboard path and the acceleration test are healthy.
- Root cause is the interaction of (a) a linear throttle→torque map whose low-throttle torque is below engine friction, (b) the fixed closed-throttle braking torque, (c) the idle governor's proportional hold near idle, and (d) an automatic clutch already 12.5 % engaged at idle that locks the car to the governed engine speed. The governor cannot raise engine speed because the tiny surplus is consumed by rolling resistance at the idle-gear creep speed.
- Not verified: the live SDL/bgfx loop and a physical gamepad (no controller exercised here), partial throttle under `--world-mesh --follow-ground` grades, and heat/altitude-style parameter variation. The probe uses the same `dynamicsFor` wiring as the application but not `PlayFlow`.
- The live session at diagnosis time was in the focus-loss pause menu; no game input reached the simulation.

## Retention

Keep `probe.cpp` (tracked), `output/probe.log` (pre-fix run, ignored, ~50 KiB) and `output/probe-after-fix.log` (post-fix run, ignored; regenerate both with the command above). The probe binary in `output/` is disposable. No source, profiles or assets were modified.

## Code review — 2026-11-09 (implement-skill mandate, two axes on f1d0c97)

Standards (smell baseline; the repo documents no code standard): brake law written twice with divergent shaping → extracted `engineBrakeTorqueAt` (anonymous namespace, `simulation.cpp`) and reused for both the governor compensation and the net-torque term; `engineBrakeTorque` meaning change now documented at its declaration in `src/setup.h`; part-throttle test constants named (`idleCreepMax`, `governorFloor`). Not taken: renaming the pre-existing `throttleTorque` (churn beyond the diff), collapsing the five pin sites into one shared measurement header (pre-existing repo pattern; recorded here as future work for the next model change).

Spec (the diagnosis README's next action): the regression test now encodes the spec's literal criterion — 10 % must exceed the old 2.7 m/s idle-creep plateau within 4 s — and covers the band's lower edge (5 %, worst measured v12 6.55 m/s at rpm 2137 across all 29 descriptors); hub-checker PASS and the retained `output/probe-after-fix.log` are recorded in the Fix section below. Judgement calls accepted: rpm-scaled engine braking is a global closed-throttle change, not one of the three offered launch models — justified by diagnosed term (b) and labelled as softer coasting feel, an open human-judgement item; the concurrent whole-file clang-format reformat rides in the same commit (whitespace only, verified). Hand drive remains unexecuted and is labelled, not claimed.

## Fix — 2026-11-09 (same day, this branch)

Original next action at diagnosis time (superseded by this section, kept for chronology):

> Choose a launch model before changing physics: either a non-linear part-throttle torque map (or measured part-throttle curve), a throttle-following idle/stall-speed target, or a proper launch clutch/torque-converter characteristic that lets the engine rev while the car is stationary. Whichever is chosen needs a regression test (e.g. 10 % throttle from rest must exceed the idle-creep speed within 4 s) and a hand drive with the analog trigger; then re-run ctest and the hub checker.

Chosen model: two coordinated terms (the diagnosis predicted one term alone is insufficient):

1. **rpm-proportional engine braking** in `src/simulation.cpp`: `engineBrakeTorque` is now quoted at the redline and scales with `clamp(engineOmega/redlineOmega, 0, 1)` instead of being a flat 35 Nm above idle. At 850 rpm the closed-throttle torque is 4.4 Nm, not 35 Nm, so part-throttle net torque is positive immediately above idle and the engine is free to rev against the load; the idle-governor compensation term was rescaled to match (`idleBrake`). Coasting engine braking is correspondingly softer below ~3000 rpm (full value retained at the redline); the braking benchmark moves 41.8 → 42.4 m, inside every existing band.
2. **Concave pedal map**: `throttleTorque = sqrt(throttle) * setup.acceleration`. Throttle-plate area and ECU pedal maps are concave; a linear map gives 14 Nm at 10 %, below the ~15 Nm crank-equivalent of rolling resistance alone. `sqrt(1)=1`, so full throttle, the keyboard path and steady-state benchmark physics are unchanged; the only full-throttle movement is the ~0.2 s pedal-filter ramp at launch (0-100 times shift ~0.05 s).

Not chosen: throttle-following governor target (pins a hard speed ceiling per throttle in gear 1) and a slip-reworked launch clutch (the existing compliant clutch launches correctly once net engine torque is positive).

Regression test (red → green, `tests/driving_checks.cpp`, per car over all synthetic + local descriptors; strengthened in the code-review pass to encode the spec's literal criteria and the band's lower edge): 10 % throttle must exceed the old 2.7 m/s idle-creep plateau within 4 s and keep accelerating to 12 s with the engine off the governor (`rpm > 1200`); 5 % held for 12 s must keep accelerating (worst measured: v12 6.55 m/s, rpm 2137); 25 % for 8 s must exceed 3.5 m/s. Before the fix: `v6=2.615 v12=2.615 rpm=860` (fail); after: e.g. default car 10 % gives v12 ≈ 11-13 m/s at 0.9-1.1 m/s². Post-fix probe sweep: no STALL flags on any of the 29 descriptors; threshold sweep monotonic from 18 % up (was a hard plateau below ~24 %).

Full-throttle pins re-measured under the new model (repo convention: `performance_class.h` documents re-measurement on model change; a throwaway probe replicated each measurement path exactly): performance table 9.981110/9.349068/8.794632/8.305135/7.869522/7.480605/7.132100/6.819413/6.542811 s at multipliers .8-1.2 (class bands D/C/B/A unchanged); default braking 42.3776 m / 2.9523 s; imported-fixture benchmark 7.297325 s; presentation delta text now "−1.327 s better than A". Updated in `src/performance_class.h`, `tests/session_checks.cpp`, `tests/presentation_checks.cpp`, `tests/vehicle_asset_checks.cpp`, `tests/vehicle_config_checks.cpp`.

Verification: `ctest` 106/106; stall probe re-run with 0 STALL flags on all 29 descriptors, retained at `output/probe-after-fix.log` (gitignored, regenerate with the probe command above; the pre-fix log remains `output/probe.log`); hub checker `python3 ../../tools/check.py` PASS. Limits: no human/analog-trigger drive yet (AFK user); at light throttle the automatic box still holds gear 1 to high rpm (shift gate is `throttle_>.15`), so 10 % pedal revs out first gear — low-throttle upshift scheduling is a separate, unmodelled item; coasting engine-brake feel below 3000 rpm is softer.
