#pragma once
#include "setup.h"
#include "vehicle_geometry.h"
#include <array>
#include <cstdint>
#include <functional>
#include <optional>

namespace racer {
constexpr double step = 1.0 / 120.0;
struct Input {
  double throttle = 0, brake = 0, steer = 0;
  double handbrake = 0, clutch = 0; // Clutch pedal: 1 = disconnected.
};
struct WheelState {
  double angularVelocity = 0, rotation = 0, steeringAngle = 0;
  double compression = 0, compressionVelocity = 0, normalLoad = 0;
  double longitudinalForce = 0, lateralForce = 0, aligningMoment = 0;
  double slipRatio = 0, slipAngle = 0, camber = 0;
  double brakePressure = 1;
  GeometryPoint contactPoint, contactNormal{0, 1, 0};
  bool grounded = false;
};
struct Car {
  // Preserve the original aggregate prefix and coordinate convention. speed
  // is SIGNED body-forward velocity; use groundSpeed() for a speedometer.
  double x = 0, z = 0, heading = 0, speed = 0, steering = 0;
  int direction = 1;
  double travel = 0;
  // Model-origin elevation, CG world velocity, and measured path length (m).
  double y = 0, velocityX = 0, velocityY = 0, velocityZ = 0, distance = 0;
  // Radians: positive pitch = nose up; positive roll = right side down.
  double pitch = 0, roll = 0, yawRate = 0, pitchRate = 0, rollRate = 0;
  double accelerationLongitudinal = 0, accelerationLateral = 0;
  double engineRpm = 850, clutchEngagement = 0;
  int gear = 1; // -1 = reverse; 1..6 = forward automatic transmission.
  std::array<WheelState, 4> wheels{}; // FL, FR, RL, RR.
};

struct RoadSample {
  double height = 0;
  GeometryPoint normal{0, 1, 0};
  double friction = 1, rollingResistance = 1; // Multipliers, not coefficients.
};
// Query the highest support in [maxHeight-maxDrop, maxHeight]. A missing hit
// means air, NEVER an extrapolated ground plane. Keep queries deterministic
// and side-effect-free: benchmark event location copies/replays Simulation.
using RoadSampler = std::function<std::optional<RoadSample>(
    double x, double z, double maxHeight, double maxDrop)>;

class Simulation {
public:
  Car car;
  bool boundaryContact = false;
  bool chassisContact = false;
  bool setSetup(const VehicleSetup &setup);
  const VehicleSetup &setup() const { return setup_; }
  bool setGeometry(const VehicleGeometry &geometry);
  double wheelbase() const { return geometry_ ? geometry_->wheelbase() : 2.7; }
  const VehicleGeometry *geometry() const { return geometry_ ? &*geometry_ : nullptr; }
  bool setDynamics(const VehicleDynamics &dynamics);
  const VehicleDynamics &dynamics() const { return dynamics_; }
  // An empty callback restores the legacy flat world at Y=0. Installing a
  // callback changes support immediately; it does not teleport the vehicle.
  void setRoadSampler(RoadSampler sampler);
  std::uint64_t configurationRevision() const { return configurationRevision_; }
  double groundSpeed() const;
  // Explicit initialization for teleports, loaded saves, or test fixtures.
  // Resets tyre/drivetrain history. Ordinary integration never calls this.
  void synchronizeState();
  // Exact dynamic transforms. Use these instead of the visual fit() plane
  // and travel/radius spin when displaying suspension, slides or wheelspin.
  std::array<float, 16> bodyTransform() const;
  std::array<float, 16> wheelTransform(std::size_t wheel, bool rolling = true) const;
  // Invalid/non-finite dt, dt<0 or dt>1 is a no-op. dt==0 only synchronizes
  // external pose edits and pedal latches. All elapsed time is substepped.
  void tick(Input in, double dt = step);
  void reset();
  void rearm();

private:
  VehicleSetup setup_;
  VehicleDynamics dynamics_;
  std::optional<VehicleGeometry> geometry_;
  RoadSampler road_;
  std::uint64_t configurationRevision_ = 0;
  bool throttleHeld = false, brakeHeld = false, initialized_ = false;
  // Quaternion (w,x,y,z), CG world position and world angular velocity.
  std::array<double, 4> orientation_{{1, 0, 0, 0}};
  GeometryPoint position_, angularVelocity_;
  Car published_;
  std::array<double, 4> relaxedLongitudinal_{}, relaxedLateral_{};
  double throttle_ = 0, brake_ = 0, engineOmega_ = 0, shiftRemaining_ = 0;
  void integrate(Input input, double dt);
  void publish();
  GeometryPoint localCenterOfMass() const;
  const VehicleGeometry &effectiveGeometry() const;
  std::optional<RoadSample> sampleRoad(double x, double z, double maxHeight,
                                        double maxDrop) const;
};
} // namespace racer
