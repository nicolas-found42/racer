#include "setup.h"
#include <cmath>
namespace racer {
namespace {
bool inRange(double value, double low, double high) {
  return std::isfinite(value) && value >= low && value <= high;
}
}

bool TyreParameters::valid() const {
  return inRange(referenceLoad, 100, 100000) && inRange(friction, .05, 3) &&
         inRange(slidingFrictionRatio, .25, 1) && inRange(loadSensitivity, 0, .4) &&
         inRange(longitudinalStiffness, 1000, 1000000) &&
         inRange(corneringStiffness, 1000, 1000000) &&
         inRange(camberStiffness, 0, 50000) &&
         inRange(longitudinalRelaxation, .01, 5) &&
         inRange(lateralRelaxation, .01, 5) && inRange(pneumaticTrail, 0, .3);
}
bool AxleSuspension::valid() const {
  return inRange(springRate, 5000, 300000) &&
         inRange(bumpDamping, 100, 30000) && inRange(reboundDamping, 100, 40000) &&
         inRange(compressionTravel, .02, .5) && inRange(droopTravel, .02, .5) &&
         inRange(antiRollRate, 0, 200000) && inRange(bumpStopRate, 10000, 2000000);
}
bool VehicleDynamics::valid() const {
  if (!inRange(mass, 250, 8000) || !inRange(frontWeightFraction, .2, .8) ||
      !inRange(cgHeight, .15, 2) || !inRange(yawInertia, 100, 100000) ||
      !inRange(pitchInertia, 100, 100000) || !inRange(rollInertia, 50, 50000) ||
      !frontSuspension.valid() || !rearSuspension.valid() ||
      !frontTyre.valid() || !rearTyre.valid() || !inRange(wheelInertia, .2, 20) ||
      !inRange(engineInertia, .05, 5) || !inRange(engineIdleRpm, 400, 2000) ||
      !inRange(engineRedlineRpm, 2500, 15000) ||
      !inRange(engineBrakeTorque, 0, 500) || !inRange(engineViscousDrag, 0, 2) ||
      !inRange(clutchTorque, 50, 3000) || !inRange(clutchStiffness, .1, 200) ||
      !inRange(finalDrive, 1, 10) || !inRange(reverseRatio, .5, 8) ||
      !inRange(drivetrainEfficiency, .5, 1) || !inRange(shiftTime, .02, 2) ||
      !inRange(shiftDownRpm, engineIdleRpm + 100, engineRedlineRpm - 400) ||
      !inRange(shiftUpRpm, shiftDownRpm + 200, engineRedlineRpm) ||
      !inRange(frontDriveFraction, 0, 1) ||
      !inRange(differentialPreload, 0, 1000) ||
      !inRange(differentialLock, 0, 200) ||
      !inRange(differentialMaxTorque, differentialPreload, 3000) ||
      !inRange(maxBrakeTorque, 500, 50000) || !inRange(frontBrakeBias, .3, .85) ||
      !inRange(handbrakeTorque, 0, 30000) ||
      !inRange(absTargetSlip, .03, .4) || !inRange(tractionTargetSlip, .03, .4) ||
      !inRange(absReleaseRate, .1, 100) || !inRange(absApplyRate, .1, 100) ||
      !inRange(brakeActuationRate, .1, 100) || !inRange(throttleResponse, .1, 100) ||
      !inRange(maxSteeringAngle, .1, 1) || !inRange(steeringRate, .1, 10) ||
      !inRange(ackermann, 0, 1) || !inRange(steeringSpeedSensitivity, 0, .1) ||
      !inRange(dragArea, .05, 5) || !inRange(downforceArea, 0, 10) ||
      !inRange(aeroFrontFraction, 0, 1) || !inRange(airDensity, .5, 2) ||
      !inRange(rollingResistance, 0, .1))
    return false;
  if (!inRange(chassisFriction, 0, 2) || !inRange(chassisRestitution, 0, .5) ||
      !inRange(shiftReengagementTime, .02, 2) ||
      !inRange(minimumGearHoldTime, .1, 5) ||
      !inRange(shiftConfirmTime, .01, .5) ||
      !inRange(partThrottleShiftUpRpm, engineIdleRpm + 300, shiftUpRpm))
    return false;
  for (std::size_t i = 0; i < torqueRpm.size(); ++i) {
    if (!inRange(torqueRpm[i], 0, 20000) || !inRange(torqueNm[i], 0, 3000) ||
        (i && torqueRpm[i] <= torqueRpm[i - 1]))
      return false;
  }
  if (torqueRpm.front() > engineIdleRpm || torqueRpm.back() < engineRedlineRpm)
    return false;
  for (std::size_t i = 0; i < gearRatios.size(); ++i)
    if (!inRange(gearRatios[i], .2, 8) || (i && gearRatios[i] >= gearRatios[i - 1]))
      return false;
  return true;
}

bool VehicleSetup::valid() const {
  for (double value : {acceleration, brake, steering})
    if (!std::isfinite(value) || value < .8 || value > 1.2)
      return false;
  return true;
}
bool GarageState::valid() const {
  if (selected >= applied.size() || !draft.valid())
    return false;
  for (const auto &setup : applied)
    if (!setup.valid())
      return false;
  return true;
}
bool GarageState::dirty() const {
  return selected >= applied.size() || draft != applied[selected];
}
bool GarageState::apply() {
  if (selected >= applied.size() || !draft.valid())
    return false;
  applied[selected] = draft;
  return true;
}
void GarageState::discard() {
  if (selected < applied.size())
    draft = applied[selected];
}
void GarageState::defaults() { draft = {}; }
bool GarageState::select(std::size_t slot) {
  if (slot >= applied.size() || dirty())
    return false;
  selected = slot;
  discard();
  return true;
}
} // namespace racer
