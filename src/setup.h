#pragma once
#include <array>
#include <cstddef>
namespace racer {
struct VehicleSetup {
  double acceleration = 1, brake = 1, steering = 1;
  bool valid() const;
  bool operator==(const VehicleSetup &) const = default;
};

// Handling data is deliberately separate from the three persisted garage
// multipliers above. Model dimensions cannot identify a real car's mass,
// tyre compound or torque curve. These are editable, uncalibrated road-car
// defaults; lengths are metres, angles radians, forces newtons and torques Nm.
struct TyreParameters {
  double referenceLoad = 3500;
  double friction = 1.05, slidingFrictionRatio = .82, loadSensitivity = .12;
  // Small-slip slopes at referenceLoad: N per slip ratio / N per tan(alpha).
  double longitudinalStiffness = 85000, corneringStiffness = 65000;
  double camberStiffness =
      7500; // N/rad; positive camber thrust points +wheel X.
  double longitudinalRelaxation = .3, lateralRelaxation = .45;
  double pneumaticTrail = .055;
  bool valid() const;
  bool operator==(const TyreParameters &) const = default;
};
struct AxleSuspension {
  // Wheel rates, already including suspension motion ratio; each spring and
  // damper belongs to ONE wheel. Anti-roll rate acts on left-right deflection.
  double springRate = 34000, bumpDamping = 2600, reboundDamping = 3800;
  double compressionTravel = .12, droopTravel = .12;
  double antiRollRate = 14000, bumpStopRate = 180000;
  bool valid() const;
  bool operator==(const AxleSuspension &) const = default;
};
struct VehicleDynamics {
  double mass = 1450, frontWeightFraction = .54, cgHeight = .53;
  // Principal inertias about the CG: yaw (+Y), pitch (+X), roll (+Z), kg m^2.
  double yawInertia = 2500, pitchInertia = 2600, rollInertia = 650;
  AxleSuspension frontSuspension;
  AxleSuspension rearSuspension{32000, 2400, 3500, .12, .12, 10000, 180000};
  TyreParameters frontTyre, rearTyre;
  double wheelInertia = 1.4; // Per wheel, including tyre and brake disc.

  double engineInertia = .25, engineIdleRpm = 850, engineRedlineRpm = 6800;
  // Closed-throttle pumping torque quoted at the redline; the simulation
  // scales it with engine speed (see engineBrakeTorqueAt in simulation.cpp).
  double engineBrakeTorque = 35, engineViscousDrag = .02;
  double clutchTorque = 450, clutchStiffness = 15;
  std::array<double, 8> torqueRpm{
      {850, 1500, 2200, 3000, 3800, 4600, 5800, 6800}};
  std::array<double, 8> torqueNm{{140, 190, 225, 260, 282, 290, 265, 210}};
  std::array<double, 6> gearRatios{{3.5, 2.19, 1.52, 1.18, .97, .81}};
  double finalDrive = 3.9, reverseRatio = 3.2, drivetrainEfficiency = .92;
  double shiftTime = .22, shiftUpRpm = 6200, shiftDownRpm = 2300;
  // 0 = rear drive; 1 = front drive; intermediate values = fixed AWD split.
  double frontDriveFraction = 0;
  // Passive axle LSD coupling: preload Nm + lock Nm/(rad/s), bounded by max.
  double differentialPreload = 25, differentialLock = 12;
  double differentialMaxTorque = 300;

  double maxBrakeTorque = 6500, frontBrakeBias = .64; // Total over FOUR wheels.
  double handbrakeTorque = 2500; // Total over TWO rear wheels.
  bool absEnabled = true, tractionControlEnabled = false;
  double absTargetSlip = .15, tractionTargetSlip = .12;
  double absReleaseRate = 15, absApplyRate = 5;
  double brakeActuationRate = 12, throttleResponse = 10; // Reciprocal seconds.
  double maxSteeringAngle = .6, steeringRate = 1.8;
  double ackermann = 1, steeringSpeedSensitivity = 0;
  double dragArea = .66, downforceArea = 0, aeroFrontFraction = .5;
  double airDensity = 1.225, rollingResistance = .013;
  double chassisFriction = .45, chassisRestitution = .05;
  bool valid() const;
  bool operator==(const VehicleDynamics &) const = default;
};
class GarageState {
public:
  std::array<VehicleSetup, 3> applied{};
  std::size_t selected = 0;
  VehicleSetup draft;
  bool dirty() const;
  bool apply();
  void discard();
  void defaults();
  // Dirty drafts require an explicit apply or discard before selection changes.
  bool select(std::size_t slot);
  bool valid() const;
};
} // namespace racer
