VEHICLE PHYSICS PATCH SERIES
Date: 2026-11-09

DELIVERABLE
Apply all three patches to the exact ten uploaded files. The implementation is
contained entirely in patches to those existing files; no new production header,
third-party physics library, build dependency or source file is required.
The verification directory contains optional test sources, logs and test-only
stand-ins for two project headers that were not supplied.

PATCH ORDER
0001-physical-parameters-and-tyres.patch
  setup.h, setup.cpp, tyre_contact.h
0002-chassis-drivetrain-and-road-contact.patch
  simulation.h, simulation.cpp, vehicle_geometry.h, vehicle_geometry.cpp,
  surface_follow.h
0003-physics-aware-benchmarks.patch
  test_session.h, test_session.cpp

APPLICATION
Patch paths are relative to the folder containing the ten original files.
From that directory, with PATCH_DIR replaced by the extracted package directory:

  git apply --check PATCH_DIR/0001-physical-parameters-and-tyres.patch \
                    PATCH_DIR/0002-chassis-drivetrain-and-road-contact.patch \
                    PATCH_DIR/0003-physics-aware-benchmarks.patch
  git apply PATCH_DIR/0001-physical-parameters-and-tyres.patch \
            PATCH_DIR/0002-chassis-drivetrain-and-road-contact.patch \
            PATCH_DIR/0003-physics-aware-benchmarks.patch

Alternatively use git apply --directory=path/to/source from the repository root.
The package was checked with git apply --check against a clean copy of the exact
uploads, actually applied, and compared byte-for-byte with the tested sources.
SHA256-manifest.json records original, patched and patch-file hashes.

WHAT CHANGED
* The old constant-acceleration, fixed-top-speed, kinematic bicycle update is
  replaced by a six-degree-of-freedom rigid chassis with a normalized quaternion,
  world velocity, angular inertia, gravity and force-generated yaw/sideslip.
* Four independent preloaded spring/damper suspensions provide load transfer,
  bump/rebound damping, bump stops, anti-roll bars, droop and individual loss of
  contact. A coupled implicit normal-force solve checks unilateral contact
  complementarity over at most 16 contact subsets.
* Combined longitudinal/lateral brush tyre forces share one friction budget.
  Parameters include load sensitivity, progressive sliding friction, relaxation
  lengths, camber thrust and pneumatic aligning moment. Camber positive work is
  accounted for as deformation loss. Wheel angular momentum and brake torque are
  integrated using bracketed implicit tyre-force solves with low-speed handling.
* Engine torque curve, engine/wheel inertia, six forward ratios, reverse ratio,
  automatic shifts, a slipping/locking clutch, engine braking, drivetrain losses,
  configurable FWD/RWD/AWD torque split, passive axle limited-slip differentials,
  front brake bias, per-wheel ABS, optional traction control and rear handbrake.
  Idle control and automatic anti-stall clutch are included. The gearbox uses
  shaft speed as well as engine speed to avoid shifts caused by unloaded revs.
* Ackermann steering and finite rack rate; speed-sensitive steering defaults to
  zero so tyre physics determines the high-speed limit. Aerodynamic drag and
  optional downforce replace the artificial road-speed clamp.
* Chassis/road and square-world boundary impulses preserve tangential momentum
  and include rotational response. Tied face contacts are averaged to preserve
  head-on symmetry. These are simplified contact constraints, not a complete
  collision engine for arbitrary track barriers.
* Bounded, independent road queries return no support over gaps. A shared-owner
  adapter connects SurfaceIndex to Simulation. Configurable face winding and
  slope acceptance permit banked roads and avoid selecting overhead bridge decks
  outside the query band.
* Dynamic body and wheel transforms use actual suspension travel and wheel spin.
* Benchmarks replay the complete simulation state to locate speed thresholds,
  measure accumulated path distance, invalidate configuration/contact changes and
  use a measured stop threshold of 0.01 m/s (0.036 km/h). testRevision is now 2.

COMPATIBILITY AND INTEGRATION
The original Input first three fields, Car aggregate prefix and public tick/reset/
rearm APIs remain available. The three persisted VehicleSetup multipliers remain
unchanged. New physical parameters are separate in VehicleDynamics; callers should
use setDynamics for each car's measured handling profile. New structure layouts
require recompiling the application; binary save formats/ABIs were not supplied
or verified. Existing record consumers should honor testRevision=2.

Default behavior runs on an infinite flat Y=0 road within the existing square
world boundary. Terrain and dynamic rendering require connecting the new APIs
in the application call sites, which were not supplied:

  // trackIndex is a shared_ptr<const surfaceFollow::SurfaceIndex>.
  simulation.setRoadSampler(surfaceFollow::makeRoadSampler(trackIndex));

  // Use these as the body's and each wheel's render transforms.
  const auto body = simulation.bodyTransform();
  const auto wheel = simulation.wheelTransform(wheelIndex);
  const auto nonRollingWheelParts = simulation.wheelTransform(wheelIndex, false);

Use groundSpeed() for a speedometer. car.speed remains the signed body-forward
component for existing callers; car.distance is accumulated path length.
Use car.wheels[i].rotation and the dynamic wheel transform for visual wheelspin.
Using the previous visual fit() plane or deriving all spin from car.travel hides
physical heave, roll, pitch, individual wheelspin and suspension movement.
After an external pose edit or loaded save, synchronizeState() explicitly resets
wheel/drivetrain history; tick also recognizes edits to legacy public pose fields.

RoadSampler queries must be deterministic and side-effect-free for benchmark
replay. An empty callback restores flat ground. An installed callback returning
nullopt means airborne. RoadSample friction/rollingResistance are multipliers.
For consistently outward/upward-wound collision meshes, set Limits.twoSided=false
when building SurfaceIndex to exclude downward-facing undersides. Imported meshes
with mixed winding default to two-sided acceptance; this projected index cannot
infer solid volume or distinguish an underside solely from a two-sided triangle.

VALIDATION ON THE EXACT PATCHED SOURCES
* C++20: -O2 -Wall -Wextra -Wpedantic -Werror.
* 30/30 behavioral scenarios passed; source and output are in verification/.
* The same 30 scenarios passed AddressSanitizer and UndefinedBehaviorSanitizer.
  LeakSanitizer is disabled because the hosted execution environment prevents its
  process inspection. No claim of a leak check is made.
* 3,630 tyre load/grip/slip combinations checked force bounds, signs and symmetry;
  additional tyre tests cover load sensitivity, combined grip, camber, relaxation,
  malformed mesh ranges and empty rim data.
* Dynamic transform, arbitrary airborne orientation and separated 0 m/4 m bridge
  support checks passed. Head-on and mirrored oblique wall response was checked.
* The observed stiff-suspension energy-injection defect has a regression: a
  250 kg chassis with 8 m track, low roll inertia, high spring/damping rates and
  1e-6 rad initial roll settles without generating a jump or chassis collision.
* Tests use clearly marked minimal stand-ins for mesh_asset.h and world_scale.h,
  which were absent from the uploads. Production source files were not replaced
  with stubs. This is isolated translation-unit verification, not an application
  build, renderer integration test or real-vehicle calibration.

MEASURED GENERIC DEFAULT PROFILE (NOT A CLAIM ABOUT A PARTICULAR REAL CAR)
0-100 km/h:                    7.91646082763 s
Distance to 100 km/h:          110.446544503 m
100 km/h to 0.01 m/s:          2.91824994399 s
Braking distance:             41.8160450815 m
Static total wheel load:      14219.6425 N = 1450 kg * 9.80665 m/s^2
Full-throttle shifts in 12 s:  2 upshifts, no downshift hunting

REPRODUCE THE ISOLATED VERIFICATION
  bash verification/run_tests.sh /absolute/path/to/patched/source/directory
  SANITIZE=1 bash verification/run_tests.sh /absolute/path/to/patched/source/directory

The runner copies those ten files into a temporary directory and adds only the
verification stubs there. It does not edit the application or install stubs into it.

PRACTICAL FIDELITY LIMITS
The defaults are uncalibrated road-sports-car parameters. Matching an actual car
requires measured mass/inertia, centre of gravity, torque/gearing, tyres, brakes,
spring/damper/motion-ratio curves and comparison with telemetry from that car.
Suspension is a force-element/raycast model with no separate unsprung-mass DOFs;
wheel contact uses a rigid radius/point-plane approximation. Detailed suspension
linkages, measured tyre force tables, temperature/pressure/wear, deformable tyres
and terrain, full track collision manifolds, powertrain component compliance,
manual gear selection and force-feedback hardware integration are not implemented
by these supplied-file patches. A live application drive test is still required
for input/renderer integration and subjective handling assessment.

MODEL REFERENCES
NVIDIA PhysX vehicle force/suspension/tyre architecture:
https://nvidia-omniverse.github.io/PhysX/physx/5.6.1/docs/Vehicles.html
Project Chrono handling tyre models and their limitations:
https://api.projectchrono.org/development/wheeled_tire.html
The implementation is original code using these general modeling principles;
it does not import or embed either physics engine.
