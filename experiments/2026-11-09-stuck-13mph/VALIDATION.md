# Validation results

## Reproduce the checks

From the extracted package directory, with a C++20 compiler and Python 3:

```sh
bash verification/run_checks.sh
SANITIZE=1 bash verification/run_checks.sh
python3 verification/gamepad/run.py
python3 verification/gamepad/run.py --sanitize
```

Set `CXX` to select a compiler if necessary. The headless runner compiles the
current `src/simulation.cpp` and `src/setup.cpp` with the reference geometry,
tyre, and benchmark implementation. It uses strict warnings:
`-std=c++20 -O2 -Wall -Wextra -Wpedantic -Werror`.

Both runners build in temporary directories. The reference/stub headers stay
inside the verification build and are not production replacements. See the
scope section below before interpreting a successful check as an application
build.

## The new regressions fail on the uploaded implementation

The original simulation/setup files were compiled unchanged with the same
recovered physics dependencies and the new test source. Two independent checks
demonstrated the defect:

1. A supported, low-speed wheelspin fixture triggered an inappropriate upshift
   in the original implementation. It holds the correct gear in the updated
   implementation for rear-, front-, and all-wheel drive.
2. A natural hard-corner fixture generated repeated first/second-gear changes
   and long interruptions of transmitted torque in the original code. This
   fixture applies no artificial wheel-speed forcing.

The recorded baseline commands, source hashes, expected failing assertions, and
exit statuses are in `verification/baseline_failures.log`.

### Severe-corner comparison

Both implementations start at 16 m/s using the wheel measurements from recording
`58161`, with the default body envelope and dynamics. After two seconds of full
steering/full throttle, the steering is released while full throttle is held for
another eight seconds. Traction control is disabled.

| Measurement over the eight-second straight-steering interval | Uploaded code | Final updated code |
| --- | ---: | ---: |
| Gear changes | 25 | 0 |
| Time with clutch engagement below 0.001 | 5.350 s | 0 s |
| Longest uninterrupted clutch-open period | 0.442 s | 0 s |
| End ground speed | 6.336 m/s | 3.038 m/s |

The last row matters: holding full throttle during this extreme skid still
sustains power oversteer in the final model. The gearbox now holds second with
the clutch engaged and drive torque transmitted; the vehicle is no longer
cycling gears and repeatedly disconnecting the engine. A three-second hard-turn
variant also has zero gear changes and zero open-clutch time during the next
eight seconds. Both left and right turns are checked.

An additional recovery check lifts the throttle for one second to regain grip,
then reapplies power. It reaches **22.764 m/s (81.95 km/h), third gear, and
essentially zero yaw rate** in both mirrored runs. This checks useful recovery
without assuming that a sustained full-throttle skid must straighten itself.

An earlier implementation briefly treated a loaded moving car's full-throttle
request as light throttle while its torque filter ramped up. The final code
corrects this and has a specific moving-pose regression. Results above are from
the final source, not that intermediate implementation.

## Final headless coverage

The dedicated transmission suite covers:

- Low-road-speed wheelspin for RWD, AWD, and FWD.
- Airborne wheelspin without unwanted automatic shifts.
- Full-throttle acceleration at garage multipliers 0.8, 1.0, and 1.2.
- Different road-grip multipliers and flat/6% uphill surfaces.
- Partial-throttle launches at 5%, 10%, and 25% pedal demand.
- Loaded moving poses receiving immediate full-throttle demand.
- Clutch-pedal override, reverse, reset, and explicit synchronization.
- Hard cornering, continued drive during a skid, and recovery after a lift.
- Braking from a higher gear to a stop and relaunching in first.
- Smooth clutch reconnection, diagnostic consistency, and zero-time updates.
- Transactional rejection of invalid transmission tuning.
- Equivalent 30 Hz/120 Hz time partitioning and invalid-timestep rejection.

The previous comprehensive physics regression also passes **30/30**. It covers
acceleration, braking, coasting, load transfer, mirrored steering, collision
boundaries, reverse input latches, low grip, combined tyre-force limits,
airborne motion, independent wheel support, grades, multilevel surfaces,
configuration invalidation, deterministic replay, and malformed input.

Measured generic default-profile results from the final source:

| Measurement | Result |
| --- | ---: |
| 0–100 km/h | 7.91037 s |
| Distance to 100 km/h | 111.220 m |
| 100 km/h to the benchmark's stopped threshold | 2.91365 s |
| Braking distance | 42.088 m |
| Speed after six seconds at full throttle | 22.055 m/s |

These are generic simulation-profile measurements, not calibration claims for
the real car represented by a visual model. The full optimized run is recorded
in `verification/checks.log`, including the exact source hashes.

## Controller mapping

The controller runner compiles the actual current `src/gamepad.cpp` against an
explicitly test-only SDL/input adapter. It exhaustively checks all 65,536 raw
values for each of three axes: **196,608 mappings**.

Checks cover finite and monotonic output, bounds, signed steering endpoints,
negative trigger readings, deadzone continuity, full trigger travel, neutral
input, and null controllers. The adapter is in `verification/gamepad/stubs/`;
it must not replace the application's `gamepad.h`.

## Sanitizers

The sanitizer mode enables AddressSanitizer and UndefinedBehaviorSanitizer.
LeakSanitizer is disabled by default because the hosted/traced execution
environment cannot reliably perform its process inspection. No leak-check
claim is made. Final sanitizer results are recorded alongside the optimized
verification logs.

## What was not executable from the supplied files

This is isolated translation-unit and behavior verification, not a complete
SDL/bgfx application build. The renderer, real SDL devices, full application
headers/build configuration, and the complete vehicle-descriptor/asset collection
were not supplied.

The original `driving_checks.cpp` is retained unchanged. Its default-vehicle
portion was checked separately; its complete descriptor sweep requires the
project's `vehicle_fixtures.h`, `vehicle_tuning.h`, and actual descriptors.
The longer descriptor probe and `workflow_observation_checks.cpp` are included
for integration testing in the full project. PlayFlow/main changes were reviewed
but their complete application executables were not built here.

`verification/reference/` contains geometry, tyre, benchmark, and surface code
reconstructed from the earlier uploaded originals and physics patches. The
only mesh/world stand-ins are in `verification/stubs/`. None of these reference
files replaces a production header in this package's `src/` directory.

The sampled recordings do not retain every exact input edge or the live physical
body envelope. Their wheel measurements are used directly; their whole-mesh
visual bounds are not substituted for the collision envelope. No exact replay
of the original live drives is claimed.
