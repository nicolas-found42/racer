# Racer transmission fix

This package contains complete source replacements for the uploaded code, a
dedicated transmission regression suite, and reproducible headless verification.
It is an overlay for the existing Racer project, not a complete game repository.

## Install

1. Copy `src/`, `tests/`, and `experiments/` into the corresponding directories in
   your project. The uploaded `setup(1).cpp`, `setup(1).h`, `simulation(1).cpp`, and
   `simulation(1).h` have their normal project names: `setup.cpp`, `setup.h`,
   `simulation.cpp`, and `simulation.h`.
2. Rebuild the application. `Car` and `VehicleDynamics` have additional fields,
   so all translation units using those types must be recompiled together.
3. Run the supplied headless checks and your project's application/integration
   checks. `verification/` contains isolated test support; do not copy its
   adapters or reference headers over production headers.

The existing public input prefix, six forward ratios, reverse controls, garage
setup multipliers, and default traction-control setting are preserved.

## Diagnosis from the supplied recordings

The recordings show a repeated first/second-gear cycle with the clutch open,
despite full throttle and no brake or steering request in the measured windows.

| Recording | Window from recorder start | Gear changes observed | Clutch exactly zero | Signed speed range |
| --- | --- | --- | --- | --- |
| `1794266128267257-57542.jsonl` | 21.570–24.079 s | 11 | 24 of 25 samples | 4.987–6.251 m/s |
| `1794266412218877-58161.jsonl` | 28.604–30.804 s | 10 | 22 of 22 samples | 5.413–6.346 m/s |

Both recordings report keyboard input, no connected controller, no loaded world
surface source, an acceleration multiplier of 1.0, no boundary contacts, and no
dropped telemetry records. The logged wheels have a radius of 0.299 m and a
wheelbase of approximately 2.623 m. The persistent cycle follows hard cornering.

The old scheduler could mistake driven-wheel spin for sufficient road speed to
upshift. During its 0.22-second clutch-open shift, the wheels slowed; the newly
selected ratio then requested a downshift and opened the clutch again. The logs
did not contain wheel angular velocity or tyre slip, so the wheelspin mechanism
was inferred from the source and reproduced separately in the physics tests.

## Transmission changes

- Calculate a road-coupled RPM estimate from chassis velocity at each driven
  wheel's contact point. Use it alongside engine and driven-wheel RPM when
  deciding whether an upshift is justified.
- Require adequate driven-wheel support. Free-revving airborne wheels cannot
  independently advance the automatic gearbox.
- Check the RPM that the next gear would produce, with a margin above its
  downshift threshold, before opening the clutch.
- Confirm a shift request over a short interval and hold the selected gear after
  clutch reconnection. An immediate opposite shift cannot continuously reopen
  the clutch.
- Reconnect clutch capacity and engine torque progressively after the shift.
- Blend the upshift schedule with throttle demand and derive downshift hysteresis
  from adjacent gear ratios, including the large first-to-second ratio change.
- Anticipate rising driver demand when choosing the shift schedule. A newly
  loaded moving car receiving full throttle must not briefly use the light-pedal
  schedule while its torque-response filter catches up.
- Require current pedal demand for an upshift, so a released throttle cannot
  trigger a shift merely because the pedal filter is still decaying.
- Select first safely at a completed stop, and check both road and shaft speeds
  before a downshift. Reset pending shifts and filtered pedals when switching
  direction.
- Initialize a loaded moving vehicle using its configured drive split rather
  than assuming that the left rear wheel represents the drivetrain.

No tyre-force, suspension-force, or engine-power increase is used to conceal the
transmission defect. Traction control remains disabled by default.

### New tuning fields

These fields are appended to `VehicleDynamics`; `setDynamics()` validates them
transactionally. Times are seconds and engine speeds are RPM.

| Field | Default | Purpose |
| --- | ---: | --- |
| `shiftConfirmTime` | 0.06 | Require a sustained shift request |
| `shiftReengagementTime` | 0.12 | Ramp clutch reconnection after the open shift |
| `minimumGearHoldTime` | 0.55 | Hold the gear after clutch reconnection |
| `partThrottleShiftUpRpm` | 2800 | Light-pedal upshift point, blended toward `shiftUpRpm` |

The original `shiftTime` remains 0.22 seconds by default. The hold interval does
not expire while the clutch is still in its open/reconnection phase.

## Related refinements

### Controller handling

`gamepad.cpp` now handles null controllers, normalizes both signed stick endpoints
correctly, and applies a continuous 5% trigger deadzone. The remaining trigger
travel still maps to the full `[0, 1]` range. `main.cpp` gives an active keyboard
command precedence over a connected controller and tries additional controllers
if opening the first device fails.

These fixes prevent unwanted controller input from overriding keyboard driving;
controller input was not the cause of the two recorded failures.

### Diagnostics

`drive_sample` retains its 10 Hz cadence and adds:

- Vehicle/configuration identity, direction, ground speed, pitch, roll, vertical
  velocity, and chassis contact.
- Requested clutch and handbrake inputs.
- Gearbox input RPM, road-coupled RPM, clutch slip RPM, clutch torque, shift time
  remaining, time until another shift may be considered, and shift state.
- All four wheels' angular velocity, longitudinal slip ratio, slip angle,
  normal load, and grounded state.

`drive_gear_change` records gear changes independently of the sample limiter.
Resetting the vehicle or starting a benchmark resets the observation baseline.
Telemetry remains optional and cannot interrupt simulation on an exception.

RPM channels are in revolutions per minute, wheel angular velocity in radians
per second, slip angles/pitch/roll in radians, normal load in newtons, clutch
torque in newton-metres, and speeds in metres per second. Positive/negative
clutch torque distinguishes drive from engine braking. `shifting` includes the
clutch reconnection ramp; `shift_remaining` covers the open-clutch phase.

Wheel-pose diagnostics now use the wheel's simulated rotation and Ackermann
steering angle, matching the rendered dynamic transform.

## Files

| Location | Role |
| --- | --- |
| `src/simulation.cpp`, `src/simulation.h` | Transmission scheduling, clutch transitions, initialization, diagnostics |
| `src/setup.cpp`, `src/setup.h` | Transmission tuning and validation |
| `src/play_flow.cpp`, `src/play_flow.h` | Live transmission/wheel telemetry and gear-change events |
| `src/gamepad.cpp`, `src/main.cpp` | Controller mapping, input ownership, accurate wheel-pose diagnostics |
| `tests/transmission_checks.cpp` | Focused transmission and recovery regressions |
| `tests/workflow_observation_checks.cpp` | Extended integration assertions for diagnostic channels |
| `tests/driving_checks.cpp` | Supplied existing driving suite, retained unchanged |
| `experiments/2026-11-09-partial-throttle-stall/probe.cpp` | Longer transmission/grip probe and shift diagnostics |
| `verification/` | Reproducible checks, support files, and validation evidence |

## Validation scope

See `VALIDATION.md` for exact before/after results, commands, and coverage.

The headless build exercises the actual updated simulation, setup, geometry,
tyre, and benchmark implementations. Geometry/tyre/benchmark dependencies were
recovered from the earlier physics patch package; the absent mesh/world headers
are represented by explicitly labelled verification-only adapters.

The full SDL/bgfx application, native controller devices, the project's complete
vehicle-descriptor collection, and the PlayFlow integration executable cannot be
built or run from this source subset. The unchanged driving integration suite
and updated live telemetry assertions are included for execution in the full
project. The long descriptor probe likewise requires that project's existing
`vehicle_fixtures.h`, `vehicle_tuning.h`, and assets.

The cornering fixtures use the recorded wheel measurements with the default
body envelope and dynamics. Whole-mesh visual bounds do not establish the live
collision envelope; these fixtures are not claimed to be exact replays of the
10 Hz recordings or real-car calibration.
