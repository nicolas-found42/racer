# Stuck at ~12–13 mph: shift schedule, clutch model, and the 1↔2 oscillation

Scope: read-only source investigation of the live `Simulation`/`PlayFlow` path versus the
headless probes. No build, no test, no source edit. Every number below is either quoted from
the working tree or computed from the quoted constants; anything not recoverable from source
is called out as a missing fixture.

Primary files:

- `src/simulation.cpp` (force model, gearbox, clutch), `src/simulation.h`
- `src/setup.h` (all drivetrain/tyre defaults)
- `src/play_flow.cpp` (live tick path, setup wiring, telemetry)
- `src/main.cpp` (world sampler install, keyboard input, pose placement)
- `experiments/2026-11-09-partial-throttle-stall/probe.cpp`, `vehicle-physics-patches/verification/physics_regression.cpp`, `tests/driving_checks.cpp` (headless probes)

---

## 1. Automatic shift schedule

Decided in `Simulation::integrate`, `src/simulation.cpp:601-621`.

Constants (verbatim, `src/setup.h:53-55`):

```cpp
std::array<double, 6> gearRatios{{3.5, 2.19, 1.52, 1.18, .97, .81}};
double finalDrive = 3.9, reverseRatio = 3.2, drivetrainEfficiency = .92;
double shiftTime = .22, shiftUpRpm = 6200, shiftDownRpm = 2300;
```

Validation bounds (`src/setup.cpp:36-38`): `shiftTime` ∈ [.02, 2], `shiftDownRpm` ∈
[idle+100, redline-400] = [950, 6400], `shiftUpRpm` ∈ [down+200, redline] = [2500, 6800].

The evaluator (`src/simulation.cpp:596-620`):

```cpp
driveWeight[i] = .5 * (i < 2 ? p.frontDriveFraction : 1 - p.frontDriveFraction);
drivenOmega += driveWeight[i] * car.wheels[i].angularVelocity;
...
shiftRemaining_ = std::max(0.0, shiftRemaining_ - h);
if (car.direction > 0 && shiftRemaining_ == 0) {
  const double rpm = engineOmega_ / rpmToRadians;
  const double coupledRpm = drivenOmega *
                            p.gearRatios[std::size_t(car.gear - 1)] *
                            p.finalDrive / rpmToRadians;
  int next = car.gear;
  if (rpm > p.shiftUpRpm && coupledRpm > p.shiftUpRpm * .95 &&
      throttle_ > .15 && next < 6)
    ++next;
  else if (coupledRpm < p.shiftDownRpm && next > 1 &&
           drivenOmega * p.gearRatios[std::size_t(next - 2)] * p.finalDrive /
                   rpmToRadians <
               p.shiftUpRpm * .9)
    --next;
  if (next != car.gear) {
    car.gear = next;
    shiftRemaining_ = p.shiftTime;
  }
}
```

- **Upshift** requires *all* of: engine `rpm > 6200`, wheel speed expressed as
  `coupledRpm > 5890` (`6200*.95`), `throttle_ > .15`, gear < 6 (`src/simulation.cpp:609-610`).
- **Downshift** requires: `coupledRpm < 2300` in the current gear, gear > 1, and the wheel
  speed re-expressed in the lower gear `< 5580` rpm (`6200*.9`) (`src/simulation.cpp:612-616`).
  The lower-gear re-expression is the anti-hunting guard.
- `drivenOmega` is the drive-weight-weighted average wheel angular velocity
  (`src/simulation.cpp:596-599`); the default `frontDriveFraction = 0` (`src/setup.h:57`) means
  only the two rear wheels count.
- `rpm` is the **engine** speed (free or coupled), `coupledRpm` is the **wheel** speed through
  the current ratio. They are different quantities: during clutch slip the engine can be
  hundreds of rpm away from the shaft.

What changes on a shift (`src/simulation.cpp:617-625`): `car.gear` is changed **immediately**
in the same substep, the new gear's ratio is used in the same substep, and `shiftRemaining_`
is set to `.22` s. The shift state then forces the clutch to zero and cuts engine torque:

```cpp
if (shiftRemaining_ > 0)
  throttleTorque *= .15;                                   // :642-643
...
double engagement = (1 - input.clutch) * (shiftRemaining_ > 0 ? 0 : 1);  // :661
```

So each shift is a hard 220 ms of **zero clutch** and 15 % throttle torque.

---

## 2. Clutch model

`src/simulation.cpp:661-703`, defaults `clutchTorque = 450`, `clutchStiffness = 15`
(`src/setup.h:49`), `engineInertia = .25` (`src/setup.h:45`).

```cpp
double engagement = (1 - input.clutch) * (shiftRemaining_ > 0 ? 0 : 1);
engagement *= std::max(
    smooth(1, 4, speed),
    std::clamp((engineOmega_ / rpmToRadians - p.engineIdleRpm + 150) / 1200.0,
               0.0, 1.0));
if (speed < 1 && throttle_ < .02)
  engagement = 0; // Automatic anti-stall clutch.
...
const double efficiency = slip * drivenOmega * ratio < 0
                              ? 1 / p.drivetrainEfficiency
                              : p.drivetrainEfficiency;
const double coupling = p.clutchStiffness * engagement;
const double reciprocalInertia =
    1 / p.engineInertia + ratio * ratio * driveInertia * efficiency;
const double clutch =
    std::clamp(engagement >= .999
                   ? slip / (h * reciprocalInertia)
                   : coupling * slip / (1 + h * coupling * reciprocalInertia),
               -p.clutchTorque * engagement, p.clutchTorque * engagement);
engineOmega_ = std::max(0.0, engineFree - h * clutch / p.engineInertia);
car.clutchEngagement = engagement;
```

Reading of the state machine:

- `car.clutchEngagement` is **not** a physical measure of slip; it is the commanded engagement
  factor (`:703`). It is exactly `0.00` whenever (a) the shift timer is running
  (`shiftRemaining_ > 0`), (b) the clutch input is pressed, or (c) `speed < 1 && throttle_ < .02`
  (anti-stall). A logged `clutch_engagement = 0.00` under full throttle therefore means
  **`shiftRemaining_ > 0`**, i.e. the gearbox was in a shift at that sample.
- At standstill the engagement is *not* zero: the `std::max` takes the rpm term, so at idle
  it is `(850-850+150)/1200 = 0.125` (matches the `/tmp/dbg-tel` live sample: 0.123 at
  846 rpm). This is why the car can launch at all; `smooth(1,4,speed)` only gates the
  low-speed term.
- Capacity is `clutchTorque * engagement` = up to 450 Nm; once `engagement >= .999` the clutch
  behaves as a lock constraint, still clipped at that capacity (`:697-701`).
- **Can a 1↔2 oscillation keep the clutch permanently disengaged (no wheel torque)?**
  Yes as an effect of the code: every `next != car.gear` sets another 220 ms of zero clutch
  (`:617-619`, `:661`). The box re-evaluates only when `shiftRemaining_ == 0` (`:602`), so a
  shift decision taken at the first substep after a shift expires re-arms another 220 ms. A
  long alternation therefore leaves the clutch at exactly 0 for both shift legs, with only a
  1-substep window between them in which `shiftRemaining_ == 0`. Whether the alternation is
  *self-sustaining* is question 3; the source shows the mechanism that would transmit it.
- During a shift the engine is unloaded and `throttleTorque` is multiplied by .15 (`:642-643`).
  Net engine torque at redline under 15 % torque is negative
  (`210*.15 - 35 - .02*712 ≈ -17.8 Nm` at 6800 rpm, `:655-658`, `torqueNm[7]=210`), so a shift
  decays engine speed; the engine only re-reaches ~6800 when it is being driven by the
  driveline (clutch engaged with high wheel speed), not while coasting during a shift.

---

## 3. Is the oscillation stable? rpm-at-speed for the installed cars

`rpm(m/s) = (v / r_rear) * gearRatio * finalDrive * 30/π`, with `finalDrive = 3.9`,
gear 1 = `3.5*3.9 = 13.65`, gear 2 = `2.19*3.9 = 8.541` (`src/setup.h:53-54`). The live
rear radius comes from the vehicle descriptor (rear wheels are the driven pair because
`frontDriveFraction = 0`). Two recoverable values:

- Default fixture geometry: `WheelGeometry.radius = .4` (`src/vehicle_geometry.h:17-20`) →
  `rpm/m/s` = 325.9 in gear 1, 203.9 in gear 2.
- Example installed descriptor `assets/local/vehicles/2a233c68739f140680e259fa3b3f961a3141cce0bc17c3a2556e909b5fff9e93.vehicle`
  (`wheel RL -0.8199 0.3487 -1.2988 0.3487 0.355`) → rear radius `.355` →
  `rpm/m/s` = 367.3 in gear 1, 229.8 in gear 2.

At **5.5 m/s**:

| car | gear 1 rpm | gear 2 rpm |
|---|---|---|
| default r=.4 | 1792 | 1121 |
| descriptor r=.355 | 2020 | 1264 |

Thresholds in the same units (`src/setup.h:55`, `src/simulation.cpp:609-616`):
upshift needs engine > 6200 and coupled > 5890; downshift needs coupled < 2300.
Derived speed thresholds (no wheel slip), gear 1 / gear 2:

| car | upshift coupled 5890 | upshift engine 6200 | downshift 2300 (gear 2) |
|---|---|---|---|
| r=.4 | 18.07 m/s | 19.02 m/s | 11.28 m/s |
| r=.355 | 16.04 m/s | 16.88 m/s | 9.56 m/s |

Consequences:

1. At 5.5 m/s with the wheels rolling at road speed, gear 1 is ~2000 rpm and gear 2 is
   ~1300 rpm. Gear 2 is **below** the 2300 downshift gate, and the lower-gear re-check
   (~2000 rpm < 5580) permits the downshift. So **gear 2 cannot be held at 5.5 m/s**; the box
   will always request 1.
2. Gear 1 at 5.5 m/s is far below the 6200/5890 upshift gate, so a legitimate 1→2 upshift is
   impossible at that speed.
3. Therefore the observed 1↔2 alternation at ~5.5 m/s **requires that at the upshift instant
   the driven wheels were spinning at ≥ 5890 rpm coupled speed**, i.e.
   `drivenOmega ≥ 5890 / (13.65 * 30/π) = 45.19 rad/s` (same for all cars). At 5.5 m/s ground
   speed that is a wheel-equivalent speed of 45.19*r:
   - r=.355 → 16.04 m/s wheel speed, **slip ratio (16.04-5.5)/5.5 = 1.92**
   - r=.4 → 18.08 m/s, **slip ratio 2.29**

   So the observed gear oscillation **is itself proof of large rear-wheel spin** at the
   upshift instant (or of a non-road-speed wheel state, e.g. airborne/free-spinning wheels).
   A rolling gearbox cannot produce it.
4. In gear 2 immediately after such an upshift, the 220 ms shift lets the spinning wheels
   decelerate under the tyre force; they drop below 45.19 rad/s quickly, so by the time the
   shift expires `coupledRpm < 2300` holds again and the box downshifts. That is a closed
   loop: upshift on spin → clutch 0 → spin dies → downshift → clutch 0 → re-engagement →
   spin. The cycle is self-consistent with the logged gear pattern and with
   `clutch_engagement = 0`.
5. Whether the cycle is **speed-stable** (pins vs slowly escapes) cannot be settled from
   these three channels. Pure kinematics says the car gains a small forward impulse each
   time a spinning tyre is decelerated by the road, so the code does not obviously guarantee a
   hard 5.5 m/s fixed point; an external retarding force (question 4) or an exactly balanced
   duty cycle is needed. The decisive measurements (wheel `angularVelocity`, `slipRatio`,
   chassis `pitch`) are **not in the telemetry**: `PlayFlow::observeDrive` records only
   `requested_throttle/brake/steer`, `speed`, `engine_rpm`, `gear`, `clutch_engagement`,
   `accel_long`, `x`, `z`, `heading`, `boundary_contact` (`src/play_flow.cpp:480-493`).

Caveat on the engine side: the engine is not required to be above the wheel speed for the gate
to fire. At full throttle the compliant clutch settles at a positive slip of roughly
`torque/(clutchStiffness·...)`; with 210 Nm and `clutchStiffness=15` the slip is tens of rad/s
(≈350 rpm, from `clutch ≈ 5.7·slip` for `h=1/600`, `reciprocalInertia≈65`). That is why the
engine reads ~6800 while the wheel-derived `coupledRpm` can sit just above 5890: the gate
window is narrow but reachable.

---

## 4. Slope / terrain / drag terms in the live game

- Gravity is world-down: `constexpr double gravity = 9.80665;` (`src/simulation.cpp:14`).
  There is no synthetic "slope force" term; a grade acts only through the contact normal
  returned by the road sampler and through gravity.
- Road sampler: `Simulation::sampleRoad` (`src/simulation.cpp:177-190`). With an **empty**
  callback the fallback is a flat Y=0 plane (`:183-184`), which is the default city world
  ("the default city world has no road mesh", `experiments/2026-11-09-vehicle-physics-patches/README.md:38`).
  The live game installs a real sampler only with `--follow-ground` and a world mesh
  (`src/main.cpp:1314-1315`, `src/surface_follow.h:191-198`). `Limits::minimumNormalY = .5`
  admits grades up to ~60° (`src/surface_follow.h:32-35`).
- Aerodynamic drag: `addForce(mul(velocity, -.5*p.airDensity*p.dragArea*speed), {})`
  (`src/simulation.cpp:582-583`); defaults `dragArea = .66`, `airDensity = 1.225`,
  `downforceArea = 0` (`src/setup.h:78-80`). At 5.5 m/s this is
  `0.5*1.225*.66*5.5² ≈ 12 N` — negligible.
- Rolling resistance: `p.rollingResistance * contacts[i].rolling * contacts[i].load * radius`
  (`src/simulation.cpp:674-676`, applied again in the wheel solve at `:735-738`);
  `rollingResistance = .013` (`src/setup.h:80`). At static load ≈ 14217 N this is ≈185 N —
  about `0.13 m/s²` of deceleration, not enough to pin a full-throttle car.
- Chassis-ground and world-wall impulses (`src/simulation.cpp:900-960`): the wall is at
  `worldScale::halfExtent` (500 m, `src/world_scale.h`); a car pressed on the wall reports
  `boundaryContact`. The static-brake hold only runs when `drivePedal < .001`
  (`src/simulation.cpp:984-1006`), so it cannot hold a throttled car.

Equilibrium check for a *gearbox-healthy* car pinned at 5.5 m/s in gear 2: at 1264 rpm the
torque curve gives ≈170 Nm; wheel force ≈ `170*8.541*.92/.355 ≈ 3762 N`; to hold that needs
`sin θ ≈ 3762/14217 ≈ 0.265`, i.e. a ~15.3° (28 %) grade. City roads do not have that.

Equilibrium check for the **shift-cycling** car: with the clutch at 0 for both 220 ms legs,
the drive duty is small (only the instants between shifts). A grade of only a few degrees
(1450 kg → ~250 N per degree of sin) can then balance the average traction. So the
observation is consistent with **either** (a) a real grade plus the shift cycle, or (b) an
otherwise unexplained retarding force of order 0.1–0.5 m/s². The source alone does not
identify which; the live world sampler and chassis pitch are not in the retained telemetry.

---

## 5. Why the headless full-throttle probe passes while the live game can pin

The probe and the live free-drive path use the same `Simulation` code and the same 120 Hz
step, but they differ in wiring:

| # | Probe / test | Live PlayFlow | Why it matters |
|---|---|---|---|
| 1 | `sim.setRoadSampler({})` — flat Y=0 (`probe.cpp:30`) | sampler installed only with `--follow-ground` + world mesh (`main.cpp:1314-1315`) | no grade, no curb/crest, no launch/landing transient in the probe |
| 2 | `VehicleSetup setup;` with `acceleration = 1` (`probe.cpp:44-48`) | `effectiveSetup = clamp(garage*parts, .8, 1.2)` (`play_flow.cpp:132-139`) | up to 1.2× engine torque; wheelspin threshold is torque/grip, so the live car can spin where the probe does not (or spin less at 0.8×) |
| 3 | starts at the origin with a level pose (`probe.cpp:31-32`) | `resetPose()` then `placeOnGround()` sets `y`, `pitch`, `roll`, zeroes velocity, then `sim.tick({},0)` (`play_flow.cpp:66-71`, `main.cpp:1318-1350`) | starting on a graded/pitched surface changes load transfer and the gravity component from the first substep |
| 4 | full-throttle runs are 4 s (`probe.cpp:40-41`), 8 s (`tests/driving_checks.cpp:22`), 13 s (`:112-118`) | the reported pin ran ~20 s | the probe never covers the 20 s window; the 13 s test asserts >130 km/h and is healthy |
| 5 | `Input{1,0,0}` (`probe.cpp:41`) | keyboard aggregate sets only throttle/brake/steer; `handbrake` and `clutch` default 0 (`simulation.h:14-17`, `main.cpp:1621-1625`) | inputs are byte-identical for a pure keyboard W drive; a gamepad replaces the keyboard when any trigger > .05 (`main.cpp:1628-1634`), so a pad could inject brake/steer |
| 6 | free drive `sim.tick(input, dt)` (`probe.cpp:41`) | `PlayFlow::tick` → `sim.tick(input)` (`play_flow.cpp:409-439`), gated by `paused/rearming`; the rearm handshake requires neutral input before the first step (`main.cpp:1662-1673`) | equal after release, but the live path can start a frame with `input = {}` and `dt = 0` |
| 7 | `TestSession` free-run test forces `Input{1,0,0}` per substep and resets the car to `Car{0,-350,...}` (`test_session.cpp:101-105`, `:157-162`) | free drive does not use `TestSession` | `session.tick` is not the path under test in a human drive |
| 8 | probe iterates all 24 local descriptors with `dynamicsFor(geometry)` (`probe.cpp:38`, `vehicle_tuning.h:15-31`) | one live descriptor + saved garage slot are not recorded in the repo | geometry is covered; the **exact** live car/setup multiplier is a missing pin |

Headless tests that *should* have caught a hunting bug and pass:

- `physics_regression.cpp:141-160` `gearbox_full_throttle_does_not_hunt`: 1440 ticks (12 s)
  at `{1,0,0}`, asserts zero downshifts after 3 s and no upshift into a lugging gear.
- `tests/driving_checks.cpp:112-119` `cap`: 13 s full throttle, asserts speed >130 km/h,
  still accelerating, gear ≥3.
- `tests/driving_checks.cpp:142-148`: every descriptor, 8 s full throttle, 95–125 km/h.

None of these set a road sampler (`physics_regression`'s `fresh()` is
`sim.reset(); sim.tick({},0)` at `:27`, i.e. flat fallback), and none logs wheel slip or gear
sequence, so none would detect a *spin-triggered* hunt that only starts on a graded/blocked
surface. The probe's `fullThrottle` reports only `v4` (`probe.cpp:40-42`); a transient 1↔2
hunt during launch would not be visible if the car has recovered by 4 s.

---

## Ranked mechanisms for the 12–13 mph full-throttle pin

### 1. Spin-triggered 1↔2 shift hunting with the clutch forced to 0 (most plausible)

Mechanism: at ~5.5 m/s gear 2 is below the 2300 rpm downshift gate and gear 1 is far below the
6200 upshift gate (computed above). The only way to be in gear 2 at that speed is an upshift
taken while the rear wheels are spinning at ≥45.19 rad/s (slip ratio ≥1.92/2.29). Once in gear
2, the 220 ms shift lets the spin die, the wheel-derived rpm falls below 2300, and the box
downshifts (`simulation.cpp:612-619`); each shift is 220 ms of exact zero clutch
(`:661`) and 15 % torque (`:642`). Repeated alternation therefore leaves the car with almost
no drive torque and the engine free-revving near redline during the shifts, matching
`engine_rpm ≈ 6800`, `clutch_engagement = 0.00`, gear 1↔2.

Falsifier: log `car.wheels[2].angularVelocity*radius` and `slipRatio` at each upshift. If the
rear-wheel equivalent speed is ≈ vehicle speed at every 1→2 transition (slip ≈ 0), this
mechanism is false; then the oscillation must come from a non-wheel-speed state (airborne/
chassis contact) or from outside `Simulation`.

### 2. Grade/terrain retarding force balancing the shift cycle's low drive duty

Mechanism: a few-degree grade (or a curb/step the chassis rests on) supplies 0.1–0.5 m/s² of
retardation, enough to hold a car whose clutch is at 0 for most of each 440 ms cycle. A
gearbox-healthy car needs ~15° to be held in gear 2 at 5.5 m/s, so this only works **together
with** mechanism 1. `--follow-ground` is the only way a grade enters physics
(`main.cpp:1314-1315`); the default city is flat (`simulation.cpp:183-184`).

Falsifier: the retained telemetry has no `pitch`; re-run and log `car.pitch`, `heading`,
`x/z`, `boundary_contact`, and the world sampler. If the drive was on the default flat city
(no `--follow-ground`), or the pose is level (|pitch| ≈ 0) while the car stays at 5.5 m/s,
this mechanism is false.

### 3. Vehicle held against geometry (wall/crest/step) while the wheels spin

Mechanism: if the chassis or a wheel is blocked, full throttle lets the driveline accelerate to
the upshift gate in gear 1 with the car barely moving; the shift cycle then repeats as in
mechanism 1. The 500 m boundary is the only built-in wall (`simulation.cpp:940-960`), and
`boundaryContact` is logged (`play_flow.cpp:490`).

Falsifier: `boundary_contact` true with `|speed|` well below the wheel speed, or a slope so
steep that the car cannot climb; if `boundary_contact = false` and the car is level on the flat
default world, reject.

### 4. Excess full-throttle torque from the saved garage/parts multiplier causing spin the probe doesn't have

Mechanism: live torque is `sqrt(throttle)*effectiveSetup.acceleration` with
`effectiveSetup.acceleration` up to 1.2× (`play_flow.cpp:135-136`, `simulation.cpp:631`).
More torque lowers the speed at which rear grip saturates and makes the spin-triggered upshift
reachable; conversely 0.8× can make the headless-equivalent launch clean. The probe uses 1.0
(`probe.cpp:44-48`).

Falsifier: read `applied_accel`/`effective_accel` from the live `state` event
(`play_flow.cpp:545-550`). If it is 1.0 and the same descriptor was tested by the probe, this
is not the differentiator.

### 5. Input/controller state differing from `Input{1,0,0}`

Mechanism: a gamepad replaces the keyboard when any axis exceeds .05 (`main.cpp:1628-1634`);
a pad left stick or trigger would add steer/brake, and the telemetry only shows `requested_*`
(the value passed to the sim), so a nonzero `requested_brake` would directly explain a hold.
Keyboard `W` alone is exactly `Input{1,0,0,0,0}` (`main.cpp:1621-1625`).

Falsifier: the live `drive_sample` `requested_brake`/`requested_steer` channels. If they are
nonzero the mechanism is confirmed; if zero (as the reported keyboard-only drive implies),
reject.

---

## Missing fixtures (cannot be computed from this checkout)

- The live `drive_sample` JSONL for the reported 20 s drive is **not in the repo**; the only
  retained diagnostics under `~/Library/Application Support/Racer/Racer/diagnostics` are
  capture/garage runs with no `drive_sample` events, and the debug copies under `/tmp`
  (`/tmp/dbg-tel`, `/tmp/dbg-tel2`) contain one-shot samples only.
- The live command line (`--world-mesh`, `--follow-ground`, `--start-at`, `--vehicle`,
  `--vehicle-library`, `--benchmark/--background`) and the saved garage slot
  (`applied_accel/brake/steer`) are not recorded in the repo.
- `PlayFlow::observeDrive` does not log wheel speeds, slip, `chassisContact`, or `pitch`
  (`src/play_flow.cpp:480-493`); without those, "no wheel torque" and "wheelspin" are
  indistinguishable from the retained telemetry. Adding those fields is the single cheapest
  step that would falsify mechanisms 1–3.

## Exact computed reference values

- `rpmToRadians = π/30` (`src/simulation.cpp:15`); `coupledRpm = ω_wheel * gearRatio * 3.9 / (π/30)`.
- Gear 1 total ratio `13.65`, gear 2 `8.541` (`src/setup.h:53-54`).
- Upshift coupled gate: `6200*.95 = 5890` rpm → `drivenOmega = 45.19 rad/s` for every car.
- Upshift engine gate: `6200` rpm; downshift: `2300` rpm; downshift lower-gear guard:
  `6200*.9 = 5580` rpm; throttle gate `throttle_ > .15` (`src/simulation.cpp:609-616`).
- Gate speeds at 5.5 m/s: default r=.4 → gear1 1792 rpm / gear2 1121 rpm; descriptor r=.355 →
  gear1 2020 rpm / gear2 1264 rpm. Both gear-2 values are below 2300; both gear-1 values are
  below 5890/6200.
