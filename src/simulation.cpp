#include "simulation.h"
#include "tyre_contact.h"
#include <algorithm>
#include <cmath>
#include <limits>
#include <numbers>
#include <stdexcept>
#include <utility>

namespace racer {
namespace {
using Vec = GeometryPoint;
using Quat = std::array<double, 4>;
constexpr double gravity = 9.80665;
constexpr double rpmToRadians = std::numbers::pi / 30;
constexpr double physicsStep = 1.0 / 600.0;
Vec add(Vec a, Vec b) { return {a.x + b.x, a.y + b.y, a.z + b.z}; }
Vec sub(Vec a, Vec b) { return {a.x - b.x, a.y - b.y, a.z - b.z}; }
Vec mul(Vec a, double k) { return {a.x * k, a.y * k, a.z * k}; }
double dot(Vec a, Vec b) { return a.x * b.x + a.y * b.y + a.z * b.z; }
Vec cross(Vec a, Vec b) {
  return {a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x};
}
double length(Vec a) { return std::hypot(a.x, a.y, a.z); }
Vec unit(Vec a) {
  const double n = length(a);
  return n > 1e-12 ? mul(a, 1 / n) : Vec{};
}
bool finite(Vec a) {
  return std::isfinite(a.x) && std::isfinite(a.y) && std::isfinite(a.z);
}
Quat product(Quat a, Quat b) {
  return {a[0] * b[0] - a[1] * b[1] - a[2] * b[2] - a[3] * b[3],
          a[0] * b[1] + a[1] * b[0] + a[2] * b[3] - a[3] * b[2],
          a[0] * b[2] - a[1] * b[3] + a[2] * b[0] + a[3] * b[1],
          a[0] * b[3] + a[1] * b[2] - a[2] * b[1] + a[3] * b[0]};
}
Quat normalized(Quat q) {
  const double n = std::hypot(std::hypot(q[0], q[1]), std::hypot(q[2], q[3]));
  for (double &v : q)
    v /= n;
  return q;
}
Quat fromEuler(double heading, double pitch, double roll) {
  return product(product({std::cos(heading / 2), 0, std::sin(heading / 2), 0},
                         {std::cos(pitch / 2), -std::sin(pitch / 2), 0, 0}),
                 {std::cos(roll / 2), 0, 0, -std::sin(roll / 2)});
}
Vec rotate(Quat q, Vec v) {
  const Vec a{q[1], q[2], q[3]};
  return add(v, mul(add(mul(cross(a, v), q[0]), cross(a, cross(a, v))), 2));
}
Vec inverseRotate(Quat q, Vec v) {
  q[1] = -q[1];
  q[2] = -q[2];
  q[3] = -q[3];
  return rotate(q, v);
}
Vec inverseInertia(Quat q, const VehicleDynamics &p, Vec moment) {
  const Vec b = inverseRotate(q, moment);
  return rotate(
      q, {b.x / p.pitchInertia, b.y / p.yawInertia, b.z / p.rollInertia});
}
double inverseEffectiveMass(Quat q, const VehicleDynamics &p, Vec arm,
                            Vec axis) {
  return 1 / p.mass +
         dot(cross(inverseInertia(q, p, cross(arm, axis)), arm), axis);
}
double clean(double v, double lo, double hi) {
  return std::isfinite(v) ? std::clamp(v, lo, hi) : 0;
}
double smooth(double lo, double hi, double v) {
  const double t = std::clamp((v - lo) / (hi - lo), 0.0, 1.0);
  return t * t * (3 - 2 * t);
}
double approach(double from, double to, double amount) {
  return from + std::clamp(to - from, -amount, amount);
}
double brakeWheel(double omega, double impulse) {
  return std::copysign(std::max(0.0, std::abs(omega) - impulse), omega);
}
double torqueAt(const VehicleDynamics &p, double rpm) {
  if (rpm <= p.torqueRpm.front())
    return p.torqueNm.front();
  for (std::size_t i = 1; i < p.torqueRpm.size(); ++i)
    if (rpm <= p.torqueRpm[i]) {
      const double t =
          (rpm - p.torqueRpm[i - 1]) / (p.torqueRpm[i] - p.torqueRpm[i - 1]);
      return p.torqueNm[i - 1] + t * (p.torqueNm[i] - p.torqueNm[i - 1]);
    }
  return p.torqueNm.back();
}
bool finitePose(const Car &c) {
  for (double v : {c.x, c.y, c.z, c.heading, c.pitch, c.roll, c.speed,
                   c.steering, c.velocityX, c.velocityY, c.velocityZ, c.yawRate,
                   c.pitchRate, c.rollRate, c.travel, c.distance})
    if (!std::isfinite(v) || std::abs(v) > 1e12)
      return false;
  return true;
}
std::array<float, 16> matrix(Quat q, Vec origin) {
  const Vec x = rotate(q, {1, 0, 0}), y = rotate(q, {0, 1, 0}),
            z = rotate(q, {0, 0, 1});
  return {float(x.x),      float(x.y),      float(x.z),      0,
          float(y.x),      float(y.y),      float(y.z),      0,
          float(z.x),      float(z.y),      float(z.z),      0,
          float(origin.x), float(origin.y), float(origin.z), 1};
}
} // namespace

const VehicleGeometry &Simulation::effectiveGeometry() const {
  static const VehicleGeometry fallback;
  return geometry_ ? *geometry_ : fallback;
}
Vec Simulation::localCenterOfMass() const {
  const auto &g = effectiveGeometry();
  double bottom = 0;
  for (const auto &w : g.wheels)
    bottom += w.center.y - w.radius;
  return {0, dynamics_.cgHeight + bottom / 4,
          .5 * (g.wheels[2].center.z + g.wheels[3].center.z) +
              g.wheelbase() * dynamics_.frontWeightFraction};
}
bool Simulation::setSetup(const VehicleSetup &setup) {
  if (!setup.valid())
    return false;
  if (setup_ != setup) {
    setup_ = setup;
    ++configurationRevision_;
  }
  return true;
}
bool Simulation::setGeometry(const VehicleGeometry &geometry) {
  if (!geometry.valid() || geometry.wheelbase() < .5 ||
      geometry.wheelbase() > 15 || geometry.frontTrack() < .3 ||
      geometry.frontTrack() > 8 || geometry.rearTrack() < .3 ||
      geometry.rearTrack() > 8 || geometry.body.maximum.y > 50)
    return false;
  for (const auto &w : geometry.wheels)
    if (w.radius < .05 || w.radius > 2 || w.width > 2 || w.center.y > 50)
      return false;
  try {
    orientedBoundaryClearance(geometry, 0);
    orientedBoundaryClearance(geometry, std::numbers::pi / 4);
  } catch (const std::invalid_argument &) {
    return false;
  }
  geometry_ = geometry;
  ++configurationRevision_;
  initialized_ = false;
  return true;
}
bool Simulation::setDynamics(const VehicleDynamics &dynamics) {
  if (!dynamics.valid())
    return false;
  if (dynamics_ != dynamics) {
    dynamics_ = dynamics;
    ++configurationRevision_;
    initialized_ = false;
  }
  return true;
}
void Simulation::setRoadSampler(RoadSampler sampler) {
  road_ = std::move(sampler);
  ++configurationRevision_;
}
double Simulation::groundSpeed() const {
  return std::hypot(car.velocityX, car.velocityZ);
}
std::optional<RoadSample> Simulation::sampleRoad(double x, double z,
                                                 double maxHeight,
                                                 double maxDrop) const {
  std::optional<RoadSample> hit;
  if (road_)
    hit = road_(x, z, maxHeight, maxDrop);
  else if (maxHeight >= 0 && maxHeight - maxDrop <= 0)
    hit = RoadSample{};
  if (!hit || !std::isfinite(hit->height) || hit->height > maxHeight + 1e-8 ||
      hit->height < maxHeight - maxDrop - 1e-8 || !finite(hit->normal) ||
      !std::isfinite(hit->friction) || hit->friction < 0 || hit->friction > 4 ||
      !std::isfinite(hit->rollingResistance) || hit->rollingResistance < 0 ||
      hit->rollingResistance > 10)
    return {};
  hit->normal = unit(hit->normal);
  if (hit->normal.y < .1)
    return {};
  return hit;
}
void Simulation::synchronizeState() {
  if (!finitePose(car))
    return;
  const auto &g = effectiveGeometry();
  const double lock =
      std::min(dynamics_.maxSteeringAngle,
               .95 * std::atan2(g.wheelbase(), g.frontTrack() * .5 + .05));
  car.steering = std::clamp(car.steering, -lock, lock);
  orientation_ = normalized(fromEuler(car.heading, car.pitch, car.roll));
  position_ =
      add({car.x, car.y, car.z}, rotate(orientation_, localCenterOfMass()));
  const Vec forward = rotate(orientation_, {0, 0, 1});
  // Legacy saves and fixtures only initialize signed speed. Explicit vector
  // velocity remains authoritative unless the caller changed that speed.
  if ((initialized_ && car.speed != published_.speed) ||
      (car.velocityX == 0 && car.velocityY == 0 && car.velocityZ == 0)) {
    const Vec v = mul(forward, car.speed);
    car.velocityX = v.x;
    car.velocityY = v.y;
    car.velocityZ = v.z;
  }
  angularVelocity_ =
      rotate(orientation_, {-car.pitchRate, car.yawRate, -car.rollRate});
  car.direction = car.direction < 0 ? -1 : 1;
  car.gear = car.direction < 0 ? -1 : std::clamp(car.gear, 1, 6);
  relaxedLongitudinal_.fill(0);
  relaxedLateral_.fill(0);
  throttle_ = brake_ = shiftRemaining_ = 0;
  const Vec v{car.velocityX, car.velocityY, car.velocityZ};
  for (std::size_t i = 0; i < 4; ++i) {
    auto &w = car.wheels[i];
    w = {};
    w.steeringAngle =
        wheelSteeringAngle(g, i, car.steering, dynamics_.ackermann);
    const Vec f = rotate(orientation_, {std::sin(w.steeringAngle), 0,
                                        std::cos(w.steeringAngle)});
    w.angularVelocity = dot(v, f) / g.wheels[i].radius;
  }
  // Pick a compatible starting gear for a loaded moving pose, not first gear
  // at motorway speed. Thereafter the transmission changes gears dynamically.
  if (car.direction > 0)
    while (car.gear < 6 &&
           std::abs(car.wheels[2].angularVelocity) *
                   dynamics_.gearRatios[std::size_t(car.gear - 1)] *
                   dynamics_.finalDrive / rpmToRadians >
               dynamics_.shiftUpRpm)
      ++car.gear;
  const double ratio =
      (car.direction < 0 ? -dynamics_.reverseRatio
                         : dynamics_.gearRatios[std::size_t(car.gear - 1)]) *
      dynamics_.finalDrive;
  double shaft = 0;
  for (std::size_t i = 0; i < 4; ++i)
    shaft += .5 *
             (i < 2 ? dynamics_.frontDriveFraction
                    : 1 - dynamics_.frontDriveFraction) *
             car.wheels[i].angularVelocity * ratio;
  engineOmega_ = std::max(dynamics_.engineIdleRpm * rpmToRadians, shaft);
  initialized_ = true;
  publish();
}
void Simulation::reset() {
  boundaryContact = chassisContact = false;
  car = {};
  engineOmega_ = dynamics_.engineIdleRpm * rpmToRadians;
  initialized_ = false;
  rearm();
}
void Simulation::rearm() {
  throttleHeld = true;
  brakeHeld = true;
}
void Simulation::publish() {
  const Vec origin = sub(position_, rotate(orientation_, localCenterOfMass()));
  const Vec f = rotate(orientation_, {0, 0, 1}),
            r = rotate(orientation_, {1, 0, 0}),
            u = rotate(orientation_, {0, 1, 0});
  car.x = origin.x;
  car.y = origin.y;
  car.z = origin.z;
  if (std::hypot(f.x, f.z) > 1e-9)
    car.heading = std::atan2(f.x, f.z);
  car.pitch = std::atan2(f.y, std::hypot(f.x, f.z));
  car.roll = std::atan2(-r.y, u.y);
  car.yawRate = dot(angularVelocity_, u);
  car.pitchRate = -dot(angularVelocity_, r);
  car.rollRate = -dot(angularVelocity_, f);
  car.speed = dot({car.velocityX, car.velocityY, car.velocityZ}, f);
  car.engineRpm = engineOmega_ / rpmToRadians;
  published_ = car;
}
std::array<float, 16> Simulation::bodyTransform() const {
  return matrix(initialized_ ? orientation_
                             : fromEuler(car.heading, car.pitch, car.roll),
                {car.x, car.y, car.z});
}
std::array<float, 16> Simulation::wheelTransform(std::size_t wheel,
                                                 bool rolling) const {
  if (wheel >= 4)
    throw std::out_of_range("wheel index");
  const auto &w = car.wheels[wheel];
  const auto q =
      initialized_ ? orientation_ : fromEuler(car.heading, car.pitch, car.roll);
  Vec center = effectiveGeometry().wheels[wheel].center;
  center.y += w.compression;
  const double spin = rolling ? w.rotation : 0;
  const Quat local = product(
      {std::cos(w.steeringAngle / 2), 0, std::sin(w.steeringAngle / 2), 0},
      {std::cos(spin / 2), std::sin(spin / 2), 0, 0});
  return matrix(product(q, local),
                add({car.x, car.y, car.z}, rotate(q, center)));
}
void Simulation::tick(Input in, double dt) {
  if (!std::isfinite(dt) || dt < 0 || dt > 1 || !finitePose(car))
    return;
  boundaryContact = chassisContact = false;
  if (!initialized_ || car.x != published_.x || car.y != published_.y ||
      car.z != published_.z || car.heading != published_.heading ||
      car.pitch != published_.pitch || car.roll != published_.roll ||
      car.speed != published_.speed || car.velocityX != published_.velocityX ||
      car.velocityY != published_.velocityY ||
      car.velocityZ != published_.velocityZ ||
      car.yawRate != published_.yawRate ||
      car.pitchRate != published_.pitchRate ||
      car.rollRate != published_.rollRate || car.gear != published_.gear ||
      car.direction != published_.direction ||
      car.steering != published_.steering)
    synchronizeState();
  for (const auto &w : car.wheels)
    if (!std::isfinite(w.angularVelocity) || !std::isfinite(w.rotation) ||
        !std::isfinite(w.brakePressure) || w.brakePressure < 0 ||
        w.brakePressure > 1)
      return;
  in.throttle = clean(in.throttle, 0, 1);
  in.brake = clean(in.brake, 0, 1);
  in.steer = clean(in.steer, -1, 1);
  in.handbrake = clean(in.handbrake, 0, 1);
  in.clutch = clean(in.clutch, 0, 1);
  const bool t = in.throttle > .05, b = in.brake > .05;
  const bool tp = t && !throttleHeld, bp = b && !brakeHeld;
  throttleHeld = t;
  brakeHeld = b;
  // A direction request is permitted only at actual standstill, never merely
  // when the longitudinal velocity crosses zero during a sideways slide.
  if (groundSpeed() < .03 && std::abs(car.velocityY) < .1 &&
      std::abs(car.yawRate) < .05) {
    if (car.direction == 1 && bp && !t) {
      car.direction = -1;
      car.gear = -1;
    } else if (car.direction == -1 && tp && !b) {
      car.direction = 1;
      car.gear = 1;
    }
  }
  if (dt == 0) {
    published_ = car;
    return;
  }
  // Equal substeps consume the complete supplied interval; no dropped time or
  // acceleration cap tied to render frame rate. 30/60/120 Hz divide
  // identically.
  const unsigned count = unsigned(std::ceil(dt / physicsStep - 1e-10));
  const double h = dt / std::max(1u, count);
  for (unsigned i = 0; i < std::max(1u, count); ++i)
    integrate(in, h);
  publish();
}

void Simulation::integrate(Input input, double h) {
  const auto &p = dynamics_;
  const auto &g = effectiveGeometry();
  const Vec cgLocal = localCenterOfMass();
  const Vec up = rotate(orientation_, {0, 1, 0}),
            forward = rotate(orientation_, {0, 0, 1});
  const Vec right = rotate(orientation_, {1, 0, 0});
  const Vec origin = sub(position_, rotate(orientation_, cgLocal));
  Vec velocity{car.velocityX, car.velocityY, car.velocityZ};
  const Vec oldVelocity = velocity, oldPosition = position_;
  const double drivePedal = car.direction == 1 ? input.throttle : input.brake;
  const double brakePedal = car.direction == 1 ? input.brake : input.throttle;
  throttle_ += (drivePedal - throttle_) * -std::expm1(-p.throttleResponse * h);
  brake_ += (brakePedal - brake_) * -std::expm1(-p.brakeActuationRate * h);
  // A physical rack angle/rate. Optional speed sensitivity defaults OFF;
  // high-speed understeer must come from tyre saturation, not hidden yaw edits.
  const double geometricLimit =
      std::atan2(g.wheelbase(), g.frontTrack() * .5 + .05) * .95;
  const double lock = std::min(p.maxSteeringAngle, geometricLimit);
  const double target =
      input.steer * lock / (1 + p.steeringSpeedSensitivity * length(velocity));
  car.steering =
      approach(car.steering, target, p.steeringRate * setup_.steering * h);

  struct Contact {
    Vec point, normal{0, 1, 0}, longitudinal, lateral, arm;
    double grip = 0, rolling = 0, load = 0, compression = 0,
           compressionRate = 0;
    double vLong = 0, vSide = 0, camber = 0;
    double alignment = 1, damping = 0, stiffness = 0;
    bool hit = false;
  };
  std::array<Contact, 4> contacts;
  // First find each contact independently. A single wheel leaving the road
  // does not discard the other three or fabricate a plane under the vehicle.
  for (std::size_t i = 0; i < 4; ++i) {
    const auto &s = i < 2 ? p.frontSuspension : p.rearSuspension;
    auto &c = contacts[i];
    auto &w = car.wheels[i];
    w.steeringAngle = wheelSteeringAngle(g, i, car.steering, p.ackermann);
    const Vec center = add(origin, rotate(orientation_, g.wheels[i].center));
    const double radius = g.wheels[i].radius;
    const auto road =
        sampleRoad(center.x, center.z, center.y + s.compressionTravel + .04,
                   s.compressionTravel + s.droopTravel + 2 * radius + .12);
    if (road && dot(up, road->normal) > .2) {
      c.normal = road->normal;
      c.alignment = dot(up, c.normal);
      const Vec ground{center.x, road->height, center.z};
      c.compression =
          (radius - dot(c.normal, sub(center, ground))) / dot(c.normal, up);
      if (c.compression >= -s.droopTravel &&
          c.compression <= s.compressionTravel + .25) {
        c.hit = true;
        c.grip = road->friction;
        c.rolling = road->rollingResistance;
        c.point =
            sub(add(center, mul(up, c.compression)), mul(c.normal, radius));
        c.arm = sub(c.point, position_);
        const Vec atContact = add(velocity, cross(angularVelocity_, c.arm));
        c.compressionRate = -dot(atContact, c.normal) / dot(up, c.normal);
        const Vec wheelForward =
            rotate(orientation_,
                   {std::sin(w.steeringAngle), 0, std::cos(w.steeringAngle)});
        c.longitudinal =
            unit(sub(wheelForward, mul(c.normal, dot(wheelForward, c.normal))));
        c.lateral = unit(cross(c.normal, c.longitudinal));
        const Vec axle = rotate(orientation_, {std::cos(w.steeringAngle), 0,
                                               -std::sin(w.steeringAngle)});
        c.camber = -std::asin(std::clamp(dot(axle, c.normal), -1.0, 1.0));
        const std::size_t left = i & ~std::size_t(1);
        const double track =
            g.wheels[left + 1].center.x - g.wheels[left].center.x;
        const double sideFraction = (i % 2 == 0 ? g.wheels[left + 1].center.x
                                                : -g.wheels[left].center.x) /
                                    track;
        const double preload =
            p.mass * gravity *
            (i < 2 ? p.frontWeightFraction : 1 - p.frontWeightFraction) *
            sideFraction;
        const double damper =
            c.compressionRate >= 0 ? s.bumpDamping : s.reboundDamping;
        const double bump =
            std::max(0.0, c.compression - .7 * s.compressionTravel);
        // Nonlinear bump rubber, preloaded springs, asymmetric damping. No
        // duplicated analytic weight-transfer term: force moments create it.
        c.load = preload + s.springRate * c.compression +
                 s.bumpStopRate * bump * bump / (.3 * s.compressionTravel);
        c.damping = damper;
        c.stiffness = s.springRate +
                      2 * s.bumpStopRate * bump / (.3 * s.compressionTravel);
      }
    }
    if (!c.hit) {
      c.compression = -s.droopTravel;
      relaxedLongitudinal_[i] = relaxedLateral_[i] = 0;
    }
  }
  for (std::size_t left : {0u, 2u}) {
    const auto &s = left == 0 ? p.frontSuspension : p.rearSuspension;
    const double antiRoll = s.antiRollRate * (contacts[left].compression -
                                              contacts[left + 1].compression);
    contacts[left].load += antiRoll;
    contacts[left + 1].load -= antiRoll;
  }
  // Implicitly solve the FOUR coupled spring/damper constraints. Computing
  // damper forces explicitly can inject energy for a light chassis, stiff
  // racing springs or a large track even at 600 Hz. The contact Jacobian
  // includes roll/pitch inertia; gravity in the predictor preserves the exact
  // preloaded static equilibrium. Nonnegative active sets prohibit suction.
  double response[4][4]{};
  std::array<double, 4> freeNormal{};
  unsigned hitMask = 0;
  const Vec freeVelocity = add(velocity, {0, -gravity * h, 0});
  for (std::size_t i = 0; i < 4; ++i) {
    const auto &a = contacts[i];
    if (a.hit)
      hitMask |= 1u << i;
    freeNormal[i] =
        dot(add(freeVelocity, cross(angularVelocity_, a.arm)), a.normal);
    for (std::size_t j = 0; j < 4; ++j) {
      const auto &b = contacts[j];
      response[i][j] =
          dot(a.normal, b.normal) / p.mass +
          dot(cross(inverseInertia(orientation_, p, cross(b.arm, b.normal)),
                    a.arm),
              a.normal);
    }
  }
  double full[4][5]{};
  for (std::size_t i = 0; i < 4; ++i) {
    if (!contacts[i].hit) {
      full[i][i] = 1;
      continue;
    }
    const auto &c = contacts[i];
    const std::size_t other = i ^ 1u;
    const auto &s = i < 2 ? p.frontSuspension : p.rearSuspension;
    const double ownRate = c.damping + h * (c.stiffness + s.antiRollRate);
    const double pairedRate = contacts[other].hit ? h * s.antiRollRate : 0;
    full[i][4] = c.load - ownRate * freeNormal[i] / c.alignment +
                 pairedRate * freeNormal[other] / contacts[other].alignment;
    for (std::size_t j = 0; j < 4; ++j)
      full[i][j] =
          (i == j ? c.alignment : 0) +
          h * (ownRate * response[i][j] / c.alignment -
               pairedRate * response[other][j] / contacts[other].alignment);
  }
  std::array<double, 4> normalForces{};
  // Four contacts permit an exact, bounded active-set search (<=16 solves).
  // Removing negative loads once is insufficient: unloading another wheel can
  // require a previously removed wheel to support weight again.
  for (unsigned mask = hitMask;; mask = (mask - 1) & hitMask) {
    double equations[4][5]{};
    for (std::size_t i = 0; i < 4; ++i) {
      if (!(mask & (1u << i))) {
        equations[i][i] = 1;
        continue;
      }
      for (std::size_t j = 0; j < 5; ++j)
        equations[i][j] = full[i][j];
    }
    for (std::size_t k = 0; k < 4; ++k) {
      std::size_t pivot = k;
      for (std::size_t i = k + 1; i < 4; ++i)
        if (std::abs(equations[i][k]) > std::abs(equations[pivot][k]))
          pivot = i;
      for (std::size_t j = 0; j < 5; ++j)
        std::swap(equations[k][j], equations[pivot][j]);
      const double divisor = equations[k][k];
      for (std::size_t j = k; j < 5; ++j)
        equations[k][j] /= divisor;
      for (std::size_t i = 0; i < 4; ++i)
        if (i != k) {
          const double factor = equations[i][k];
          for (std::size_t j = k; j < 5; ++j)
            equations[i][j] -= factor * equations[k][j];
        }
    }
    bool resolved = true;
    for (std::size_t i = 0; i < 4; ++i) {
      normalForces[i] = equations[i][4];
      if (normalForces[i] < -1e-7 || !std::isfinite(normalForces[i]))
        resolved = false;
    }
    for (std::size_t i = 0; i < 4; ++i)
      if ((hitMask & (1u << i)) && !(mask & (1u << i))) {
        double residual = -full[i][4];
        for (std::size_t j = 0; j < 4; ++j)
          residual += full[i][j] * normalForces[j];
        if (residual < -1e-7 * std::max(1.0, std::abs(full[i][4])))
          resolved = false;
      }
    if (resolved || mask == 0)
      break;
  }
  for (std::size_t i = 0; i < 4; ++i)
    contacts[i].load = normalForces[i];
  Vec force{0, -p.mass * gravity, 0}, moment{};
  auto addForce = [&](Vec f, Vec arm) {
    force = add(force, f);
    moment = add(moment, cross(arm, f));
  };
  for (std::size_t i = 0; i < 4; ++i) {
    auto &c = contacts[i];
    auto &w = car.wheels[i];
    // A tyre cannot pull the road. Force cap protects a teleport into geometry;
    // normal impacts are additionally handled by chassis contact constraints.
    c.load = c.hit ? std::clamp(c.load, 0.0, p.mass * gravity * 12) : 0;
    w.grounded = c.hit && c.load > 0;
    w.compression = c.compression;
    w.compressionVelocity = c.compressionRate;
    w.normalLoad = c.load;
    w.contactPoint = c.point;
    w.contactNormal = c.normal;
    w.camber = c.camber;
    addForce(mul(c.normal, c.load), c.arm);
  }
  const double speed = length(velocity);
  addForce(mul(velocity, -.5 * p.airDensity * p.dragArea * speed), {});
  const double downforce = .5 * p.airDensity * p.downforceArea *
                           dot(velocity, forward) * dot(velocity, forward);
  const double rearZ = .5 * (g.wheels[2].center.z + g.wheels[3].center.z);
  const Vec aeroArm =
      rotate(orientation_,
             {0, 0, rearZ + p.aeroFrontFraction * g.wheelbase() - cgLocal.z});
  addForce(mul(up, -downforce), aeroArm);

  // Automatic gearbox and a two-way, slipping, inertia-coupled clutch.
  double drivenOmega = 0, driveInertia = 0;
  std::array<double, 4> driveWeight{}, driveTorque{};
  for (std::size_t i = 0; i < 4; ++i) {
    driveWeight[i] =
        .5 * (i < 2 ? p.frontDriveFraction : 1 - p.frontDriveFraction);
    drivenOmega += driveWeight[i] * car.wheels[i].angularVelocity;
    driveInertia += driveWeight[i] * driveWeight[i] / p.wheelInertia;
  }
  shiftRemaining_ = std::max(0.0, shiftRemaining_ - h);
  if (car.direction > 0 && shiftRemaining_ == 0) {
    const double rpm = engineOmega_ / rpmToRadians;
    const double coupledRpm = drivenOmega *
                              p.gearRatios[std::size_t(car.gear - 1)] *
                              p.finalDrive / rpmToRadians;
    int next = car.gear;
    // Free engine revs during a shift must not trigger another upshift.
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
  const double ratio =
      (car.direction < 0 ? -p.reverseRatio
                         : p.gearRatios[std::size_t(car.gear - 1)]) *
      p.finalDrive;
  // Pedal to torque is concave (throttle plate area and ECU pedal maps are):
  // a held 10 % analog trigger makes ~32 % of the curve's torque, otherwise
  // the request (~15 Nm) cannot even cover rolling resistance and the car sat
  // at the idle-creep equilibrium (2026-11-09 stall diagnosis). sqrt(1)=1, so
  // full throttle and the keyboard path are unchanged.
  double throttleTorque = std::sqrt(throttle_) * setup_.acceleration;
  if (p.tractionControlEnabled) {
    double excess = 0;
    for (std::size_t i = 0; i < 4; ++i)
      if (driveWeight[i] > 0 && car.wheels[i].grounded)
        excess = std::max(excess, car.direction * car.wheels[i].slipRatio -
                                      p.tractionTargetSlip);
    throttleTorque *= std::clamp(1 - 4 * excess, 0.0, 1.0);
  }
  if (engineOmega_ > p.engineRedlineRpm * rpmToRadians)
    throttleTorque = 0;
  if (shiftRemaining_ > 0)
    throttleTorque *= .15;
  const double idle = p.engineIdleRpm * rpmToRadians;
  // Pumping torque scales with engine speed (it is quoted at the redline), so
  // part throttle above idle makes positive net torque and the engine is free
  // to rev against the load. A flat closed-throttle torque pinned every car
  // to the idle-creep equilibrium: at 10 % throttle the 14 Nm requested was
  // below the old 31.5 Nm of braking (2026-11-09 stall diagnosis).
  const double idleBrake =
      p.engineBrakeTorque * (idle / (p.engineRedlineRpm * rpmToRadians));
  const double governor =
      std::clamp((idle - engineOmega_) * 8.0 + idleBrake * (1 - throttle_) +
                     p.engineViscousDrag * idle,
                 0.0, torqueAt(p, p.engineIdleRpm));
  const double netEngine =
      torqueAt(p, engineOmega_ / rpmToRadians) * throttleTorque + governor -
      p.engineBrakeTorque *
          std::clamp(engineOmega_ / (p.engineRedlineRpm * rpmToRadians), 0.0,
                     1.0) *
          (1 - throttle_) -
      p.engineViscousDrag * engineOmega_;
  const double engineFree =
      std::max(0.0, engineOmega_ + h * netEngine / p.engineInertia);
  double engagement = (1 - input.clutch) * (shiftRemaining_ > 0 ? 0 : 1);
  engagement *= std::max(
      smooth(1, 4, speed),
      std::clamp((engineOmega_ / rpmToRadians - p.engineIdleRpm + 150) / 1200.0,
                 0.0, 1.0));
  if (speed < 1 && throttle_ < .02)
    engagement = 0; // Automatic anti-stall clutch.
  double shaftFree = 0;
  for (std::size_t i = 0; i < 4; ++i) {
    const auto &w = car.wheels[i];
    const double radius = g.wheels[i].radius;
    const double resistance =
        brake_ * setup_.brake * p.maxBrakeTorque *
            (i < 2 ? p.frontBrakeBias : 1 - p.frontBrakeBias) * .5 *
            w.brakePressure +
        (i >= 2 ? input.handbrake * p.handbrakeTorque * .5 : 0) +
        p.rollingResistance * contacts[i].rolling * contacts[i].load * radius;
    // Include the preceding tyre reaction in this split-step predictor.
    // Otherwise a locked clutch would couple to bare wheel inertia and ignore
    // the road load, leaving a permanent engine/shaft speed discrepancy.
    const double wheelFree = brakeWheel(
        w.angularVelocity - h * w.longitudinalForce * radius / p.wheelInertia,
        h * resistance / p.wheelInertia);
    shaftFree += driveWeight[i] * wheelFree * ratio;
  }
  const double slip = engineFree - shaftFree;
  // Reverse efficiency on backdrive: multiplying by eta in both directions
  // would create energy when the wheels drive the engine.
  const double efficiency = slip * drivenOmega * ratio < 0
                                ? 1 / p.drivetrainEfficiency
                                : p.drivetrainEfficiency;
  const double coupling = p.clutchStiffness * engagement;
  const double reciprocalInertia =
      1 / p.engineInertia + ratio * ratio * driveInertia * efficiency;
  // A fully engaged friction clutch can lock at any torque inside its static
  // capacity. Partial engagement uses a compliant approach to that constraint.
  const double clutch =
      std::clamp(engagement >= .999
                     ? slip / (h * reciprocalInertia)
                     : coupling * slip / (1 + h * coupling * reciprocalInertia),
                 -p.clutchTorque * engagement, p.clutchTorque * engagement);
  engineOmega_ = std::max(0.0, engineFree - h * clutch / p.engineInertia);
  car.clutchEngagement = engagement;
  for (std::size_t i = 0; i < 4; ++i)
    driveTorque[i] = clutch * ratio * efficiency * driveWeight[i];
  for (std::size_t left : {0u, 2u})
    if (driveWeight[left] > 0) {
      const double difference = car.wheels[left].angularVelocity -
                                car.wheels[left + 1].angularVelocity;
      const double torque = std::copysign(
          std::min({p.differentialMaxTorque,
                    p.differentialPreload +
                        p.differentialLock * std::abs(difference),
                    std::abs(difference) * p.wheelInertia / (2 * h)}),
          difference);
      driveTorque[left] -= torque;
      driveTorque[left + 1] += torque;
    }

  // Predict contact velocity under gravity, suspension and aero before solving
  // tyres. The implicit contact response includes chassis yaw/roll inertia.
  const Vec predictedVelocity = add(velocity, mul(force, h / p.mass));
  const Vec predictedAngular =
      add(angularVelocity_, mul(inverseInertia(orientation_, p, moment), h));
  for (std::size_t i = 0; i < 4; ++i) {
    auto &w = car.wheels[i];
    auto &c = contacts[i];
    const auto &tyre = i < 2 ? p.frontTyre : p.rearTyre;
    const double oldWheelOmega = w.angularVelocity;
    const double radius = g.wheels[i].radius;
    const Vec patchVelocity =
        add(predictedVelocity, cross(predictedAngular, c.arm));
    c.vLong = dot(patchVelocity, c.longitudinal);
    c.vSide = dot(patchVelocity, c.lateral);
    const double denominator = std::max(.5, std::abs(c.vLong));
    const double slipBefore =
        (w.angularVelocity * radius - c.vLong) / denominator;
    const double brakingSlip = -std::copysign(1.0, c.vLong) * slipBefore;
    if (p.absEnabled && brake_ > .01 && std::abs(c.vLong) > 3 && c.load > 0 &&
        brakingSlip > p.absTargetSlip)
      w.brakePressure = std::max(0.0, w.brakePressure - p.absReleaseRate * h);
    else
      w.brakePressure = std::min(1.0, w.brakePressure + p.absApplyRate * h);
    const double brakeTorque =
        brake_ * setup_.brake * p.maxBrakeTorque *
            (i < 2 ? p.frontBrakeBias : 1 - p.frontBrakeBias) * .5 *
            w.brakePressure +
        (i >= 2 ? input.handbrake * p.handbrakeTorque * .5 : 0);
    const double rollingTorque =
        p.rollingResistance * c.rolling * c.load * radius;
    const double brakeImpulse =
        h * (brakeTorque + rollingTorque) / p.wheelInertia;
    auto omegaAfter = [&](double fx) {
      return brakeWheel(w.angularVelocity +
                            h * (driveTorque[i] - fx * radius) / p.wheelInertia,
                        brakeImpulse);
    };
    double fx = 0, fy = 0, mz = 0;
    if (c.load > 0 && c.grip > 0) {
      const double capacity =
          tyrePhysics::frictionCapacity(tyre, c.load, c.grip);
      const double transport =
          std::max(std::abs(c.vLong), std::abs(w.angularVelocity * radius));
      const double transient = smooth(.5, 2, transport);
      const double longAlpha =
          1 - transient * std::exp(-std::max(.5, transport) * h /
                                   tyre.longitudinalRelaxation);
      const double latAlpha =
          1 - transient * std::exp(-std::max(.5, transport) * h /
                                   tyre.lateralRelaxation);
      // At near-zero speed the four constraints share the chassis momentum.
      // A conservative diagonal mass avoids four simultaneous full stop
      // impulses; the transition disappears at ordinary handling speeds.
      const double sharing = 4 - 3 * smooth(.5, 3, std::abs(c.vLong));
      const double invLong =
          sharing *
          inverseEffectiveMass(orientation_, p, c.arm, c.longitudinal);
      const double invSide =
          sharing * inverseEffectiveMass(orientation_, p, c.arm, c.lateral);
      const double camber = c.camber * smooth(.5, 2, std::abs(c.vLong));
      auto trial = [&](double a, double b) {
        const double k =
            (omegaAfter(a) * radius - (c.vLong + h * invLong * a)) /
            denominator;
        const double lateral = (c.vSide + h * invSide * b) / denominator;
        return tyrePhysics::evaluate(
            tyre, c.load, c.grip,
            relaxedLongitudinal_[i] + longAlpha * (k - relaxedLongitudinal_[i]),
            relaxedLateral_[i] + latAlpha * (lateral - relaxedLateral_[i]),
            camber);
      };
      // Coordinate-wise bracketed implicit solve, including combined-slip
      // coupling. Neither a stiff low-speed tyre nor a sliding (falling) force
      // curve is passed to an unguarded explicit/Newton wheel-speed update.
      for (unsigned sweep = 0; sweep < 3; ++sweep) {
        double lo = -capacity, hi = capacity;
        for (unsigned iteration = 0; iteration < 20; ++iteration) {
          const double mid = .5 * (lo + hi);
          const double residual = mid - trial(mid, fy).longitudinal;
          if (std::abs(residual) < 1e-10) {
            lo = hi = mid;
            break;
          }
          if (residual > 0)
            hi = mid;
          else
            lo = mid;
        }
        fx = .5 * (lo + hi);
        lo = -capacity;
        hi = capacity;
        for (unsigned iteration = 0; iteration < 20; ++iteration) {
          const double mid = .5 * (lo + hi);
          const double residual = mid - trial(fx, mid).lateral;
          if (std::abs(residual) < 1e-10) {
            lo = hi = mid;
            break;
          }
          if (residual > 0)
            hi = mid;
          else
            lo = mid;
        }
        fy = .5 * (lo + hi);
      }
      const double forceLength = std::hypot(fx, fy);
      if (forceLength > capacity) {
        fx *= capacity / forceLength;
        fy *= capacity / forceLength;
      }
      const auto evaluated = trial(fx, fy);
      mz = evaluated.aligningMoment;
      const double nextK =
          (omegaAfter(fx) * radius - c.vLong - h * invLong * fx) / denominator;
      const double nextL = (c.vSide + h * invSide * fy) / denominator;
      relaxedLongitudinal_[i] += longAlpha * (nextK - relaxedLongitudinal_[i]);
      relaxedLateral_[i] += latAlpha * (nextL - relaxedLateral_[i]);
    } else
      relaxedLongitudinal_[i] = relaxedLateral_[i] = 0;
    const double nextOmega = omegaAfter(fx);
    w.rotation =
        std::remainder(w.rotation + .5 * (w.angularVelocity + nextOmega) * h,
                       2 * std::numbers::pi);
    w.angularVelocity = nextOmega;
    w.slipRatio = c.hit ? (nextOmega * radius - c.vLong) / denominator : 0;
    w.slipAngle = c.hit ? std::atan2(c.vSide, denominator) : 0;
    w.longitudinalForce = fx;
    w.lateralForce = fy;
    w.aligningMoment = mz;
    addForce(add(mul(c.longitudinal, fx), mul(c.lateral, fy)), c.arm);
    moment = add(moment, mul(c.normal, mz));
    // Camber thrust can do positive work in a simplified brush model. Account
    // for that work as rolling deformation loss rather than a free energy
    // source.
    const double camberPower =
        std::abs(c.camber) > 1e-6
            ? std::max(0.0, fy * c.vSide - fx * (nextOmega * radius - c.vLong))
            : 0;
    if (camberPower > 0 && std::abs(nextOmega) > .5) {
      const double loss =
          h * camberPower / (p.wheelInertia * std::abs(nextOmega));
      w.angularVelocity = brakeWheel(w.angularVelocity, loss);
    }
    // Wheel spin carries angular momentum in addition to the chassis' rigid
    // inertia. Its reaction torque matters during braking and in the air.
    const Vec axle = rotate(orientation_, {std::cos(w.steeringAngle), 0,
                                           -std::sin(w.steeringAngle)});
    moment =
        sub(moment, mul(axle, p.wheelInertia *
                                  (w.angularVelocity - oldWheelOmega) / h));
  }

  // Six-degree-of-freedom rigid body: gravity, contact force moments, Euler's
  // gyroscopic term and a normalized exponential-map orientation update.
  velocity = add(velocity, mul(force, h / p.mass));
  const Vec bodyOmega = inverseRotate(orientation_, angularVelocity_);
  const Vec angularMomentum{p.pitchInertia * bodyOmega.x,
                            p.yawInertia * bodyOmega.y,
                            p.rollInertia * bodyOmega.z};
  const Vec bodyTorque = sub(inverseRotate(orientation_, moment),
                             cross(bodyOmega, angularMomentum));
  const Vec alpha = rotate(orientation_, {bodyTorque.x / p.pitchInertia,
                                          bodyTorque.y / p.yawInertia,
                                          bodyTorque.z / p.rollInertia});
  const Vec oldAngular = angularVelocity_;
  angularVelocity_ = add(angularVelocity_, mul(alpha, h));
  position_ = add(position_, mul(add(oldVelocity, velocity), .5 * h));
  const Vec meanAngular = mul(add(oldAngular, angularVelocity_), .5);
  const double angle = length(meanAngular) * h;
  if (angle > 1e-12) {
    const Vec axis = unit(meanAngular);
    const double sn = std::sin(angle / 2);
    orientation_ = normalized(
        product({std::cos(angle / 2), axis.x * sn, axis.y * sn, axis.z * sn},
                orientation_));
  }

  // Point impulses for chassis-ground and world-wall contact. These preserve
  // tangential motion and angular response; a wall no longer zeros all speed.
  auto impulseAt = [&](Vec point, Vec normal, double penetration,
                       double friction, double restitution) {
    const Vec arm = sub(point, position_);
    Vec contactVelocity = add(velocity, cross(angularVelocity_, arm));
    const double vn = dot(contactVelocity, normal);
    double normalImpulse = 0;
    if (vn < 0) {
      const double bounce = vn < -.5 ? restitution : 0;
      normalImpulse = -(1 + bounce) * vn /
                      inverseEffectiveMass(orientation_, p, arm, normal);
      const Vec j = mul(normal, normalImpulse);
      velocity = add(velocity, mul(j, 1 / p.mass));
      angularVelocity_ =
          add(angularVelocity_, inverseInertia(orientation_, p, cross(arm, j)));
    }
    contactVelocity = add(velocity, cross(angularVelocity_, arm));
    const Vec tangent =
        sub(contactVelocity, mul(normal, dot(contactVelocity, normal)));
    const double vt = length(tangent);
    if (vt > 1e-9 && normalImpulse > 0) {
      const Vec direction = mul(tangent, 1 / vt);
      const double amount =
          std::min(friction * normalImpulse,
                   vt / inverseEffectiveMass(orientation_, p, arm, direction));
      const Vec j = mul(direction, -amount);
      velocity = add(velocity, mul(j, 1 / p.mass));
      angularVelocity_ =
          add(angularVelocity_, inverseInertia(orientation_, p, cross(arm, j)));
    }
    position_ = add(position_, mul(normal, std::max(0.0, penetration)));
  };
  for (unsigned pass = 0; pass < 2; ++pass) {
    for (double x : {g.body.minimum.x, g.body.maximum.x})
      for (double y : {g.body.minimum.y, g.body.maximum.y})
        for (double z : {g.body.minimum.z, g.body.maximum.z}) {
          const Vec point =
              add(position_, rotate(orientation_, sub({x, y, z}, cgLocal)));
          const auto road = sampleRoad(point.x, point.z, point.y + .3, .6);
          if (road) {
            const double depth = (road->height - point.y) * road->normal.y;
            if (depth > 0) {
              chassisContact = true;
              impulseAt(point, road->normal, depth,
                        p.chassisFriction * road->friction,
                        p.chassisRestitution);
            }
          }
        }
  }
  const auto envelope = g.collisionBounds();
  for (unsigned axis = 0; axis < 2; ++axis)
    for (double side : {-1.0, 1.0}) {
      Vec point{};
      double furthest = -std::numeric_limits<double>::infinity();
      unsigned supportCount = 0;
      for (double x : {envelope.minimum.x, envelope.maximum.x})
        for (double y : {envelope.minimum.y, envelope.maximum.y})
          for (double z : {envelope.minimum.z, envelope.maximum.z}) {
            const Vec corner =
                add(position_, rotate(orientation_, sub({x, y, z}, cgLocal)));
            const double projected = side * (axis == 0 ? corner.x : corner.z);
            if (projected > furthest + 1e-8) {
              furthest = projected;
              point = corner;
              supportCount = 1;
            } else if (std::abs(projected - furthest) <= 1e-8) {
              point = add(point, corner);
              ++supportCount;
            }
          }
      if (furthest > worldScale::halfExtent) {
        boundaryContact = true;
        point = mul(point, 1.0 / supportCount);
        impulseAt(point, axis == 0 ? Vec{-side, 0, 0} : Vec{0, 0, -side},
                  furthest - worldScale::halfExtent, p.chassisFriction,
                  p.chassisRestitution);
      }
    }
  // Static brake constraint: only remove microscopic residual motion when the
  // loaded tyres AND applied brake torques can support the gravitational grade.
  // Free coasting/airborne states never receive artificial rest or yaw damping.
  if (drivePedal < .001 && (brakePedal > .05 || input.handbrake > .05) &&
      std::hypot(velocity.x, velocity.z) < .025 &&
      length(angularVelocity_) < .05) {
    Vec averageNormal{};
    double holding = 0;
    unsigned grounded = 0;
    for (std::size_t i = 0; i < 4; ++i)
      if (contacts[i].load > 0) {
        ++grounded;
        averageNormal = add(averageNormal, contacts[i].normal);
        const auto &tyre = i < 2 ? p.frontTyre : p.rearTyre;
        const double torque =
            brake_ * setup_.brake * p.maxBrakeTorque *
                (i < 2 ? p.frontBrakeBias : 1 - p.frontBrakeBias) * .5 +
            (i >= 2 ? input.handbrake * p.handbrakeTorque * .5 : 0);
        holding += std::min(tyrePhysics::frictionCapacity(
                                tyre, contacts[i].load, contacts[i].grip),
                            torque / g.wheels[i].radius);
      }
    const Vec n = unit(averageNormal);
    if (grounded >= 3 &&
        holding > p.mass * gravity * std::sqrt(std::max(0.0, 1 - n.y * n.y)) +
                      p.mass * .1) {
      velocity.x = velocity.z = 0;
      for (auto &w : car.wheels)
        if (w.grounded && std::abs(w.angularVelocity) < 1)
          w.angularVelocity = 0;
      angularVelocity_ =
          sub(angularVelocity_, mul(n, dot(angularVelocity_, n)));
      relaxedLongitudinal_.fill(0);
      relaxedLateral_.fill(0);
    }
  }
  const Vec displacement = sub(position_, oldPosition);
  const double distance = length(displacement);
  car.distance += distance;
  const double longitudinalTravel = dot(displacement, forward);
  if (std::abs(longitudinalTravel) > 1e-12)
    car.travel += std::copysign(distance, longitudinalTravel);
  car.accelerationLongitudinal = dot(sub(velocity, oldVelocity), forward) / h;
  car.accelerationLateral = dot(sub(velocity, oldVelocity), right) / h;
  car.velocityX = velocity.x;
  car.velocityY = velocity.y;
  car.velocityZ = velocity.z;
}
} // namespace racer
