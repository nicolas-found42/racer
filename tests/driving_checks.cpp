#include "simulation.h"
#include "vehicle_fixtures.h"
#include "vehicle_tuning.h"
#include <cmath>
#include <iostream>
#include <memory>
#include <string>
#include <stdexcept>
using namespace racer;
void check(bool v, const char *m) {
  if (!v)
    throw std::runtime_error(m);
}
// The simulation is a force-based rigid body (see vehicle-physics-patches).
// Speeds and distances are therefore bracketed by physics, not pinned to the
// constants of the retired kinematic model (100 km/h at exactly 8 s, hard
// 40 m stop, 30 km/h reverse and 160 km/h clamps).
constexpr double stopped = .01; // m/s, the same threshold benchmarks use.
int main(int argc, char **argv) {
  try {
    Simulation s;
    for (int i = 0; i < 960; i++)
      s.tick({1, 0, 0});
    std::cout << "Eight second speed: " << s.car.speed * 3.6 << " km/h\n";
    // Default road-sports-car profile reaches 100 km/h in about 7.9 s.
    check(s.car.speed * 3.6 > 95 && s.car.speed * 3.6 < 106, "acceleration");
    check(s.car.gear >= 2, "automatic gearbox upshifted");
    check(std::abs(s.groundSpeed() - s.car.speed) < .05, "straight ground speed");
    double start = s.car.z;
    const double entry = s.car.speed;
    for (int i = 0; i < 600; i++)
      s.tick({0, 1, 0});
    const double braking = s.car.z - start;
    std::cout << "Braking distance: " << braking << " m\n";
    // v^2/(2 mu g) with mu=1.05 is 38 m: a stop cannot beat the tyre limit.
    check(braking > entry * entry / (2 * 1.05 * 9.80665) - .5 && braking < 50,
          "stopping distance");
    check(std::abs(s.car.speed) < stopped, "held brake stays stopped");
    s.tick({});
    s.tick({0, 1, 0});
    check(s.car.direction == -1, "fresh press selects reverse");
    for (int i = 0; i < 1000; i++)
      s.tick({0, 1, 0});
    check(s.car.speed < -5 / 3.6 && s.car.gear == -1, "reverse");
    for (int i = 0; i < 1000; i++)
      s.tick({1, 0, 0});
    check(std::abs(s.car.speed) < stopped, "forward pedal stops reverse");
    s.tick({});
    s.tick({1, 0, 0});
    check(s.car.direction == 1, "fresh forward");
    s.reset();
    check(s.car.x == 0 && s.car.z == 0 && s.car.speed == 0 &&
              s.car.heading == 0,
          "reset");
    s.tick({});
    for (int i = 0; i < 480; i++)
      s.tick({1, 0, .7});
    check(std::abs(s.car.x) > 2 && std::abs(s.car.heading) > .2, "turning");
    {
      // Steering is positive toward +X with force-generated yaw and sideslip.
      Simulation right, left;
      for (int i = 0; i < 360; i++) {
        right.tick({.5, 0, 0});
        left.tick({.5, 0, 0});
      }
      for (int i = 0; i < 240; i++) {
        right.tick({.3, 0, .4});
        left.tick({.3, 0, -.4});
      }
      check(right.car.heading > .3 && right.car.x > 1, "positive steer turns +X");
      check(left.car.heading < -.3 && left.car.x < -1, "negative steer turns -X");
      check(std::abs(right.car.heading + left.car.heading) < 1e-6,
            "mirrored steering is symmetric");
      check(right.car.yawRate > 0 && right.car.accelerationLateral > 0,
            "steering produces tyre-force yaw and lateral acceleration");
    }
    s.reset();
    s.tick({});
    s.car.x = 490;
    s.car.heading = 1.57079632679;
    for (int i = 0; i < 1500; i++)
      s.tick({1, 0, 0});
    // The oriented collision envelope (not a fixed 497.5 m centre limit) stops
    // the nose at the 500 m wall and the rest of the speed is removed by it.
    check(s.boundaryContact && s.car.x > 497 && s.car.x <= 498.1 &&
              std::abs(s.car.speed) < .05,
          "boundary");
    double reference = 0;
    for (int fps : {30, 60, 144}) {
      Simulation a;
      double accumulator = 0;
      for (int f = 0; f < fps * 8; f++) {
        accumulator += 1.0 / fps;
        while (accumulator + 1e-10 >= step) {
          a.tick({1, 0, 0});
          accumulator -= step;
        }
      }
      if (fps == 30)
        reference = a.car.speed;
      check(std::abs(a.car.speed - reference) < 1e-6 &&
                std::abs(a.car.speed * 3.6 - 100.8) < 1.5,
            "frame-rate independence");
    }
    // No artificial road-speed clamp: the car passes the old 160 km/h limit's
    // neighbourhood still accelerating, limited by gearing, drag and the wall.
    Simulation cap;
    double previous = 0;
    for (int i = 0; i < 1560; i++) {
      cap.tick({1, 0, 0});
      if (i == 1559 - 120)
        previous = cap.car.speed;
    }
    check(cap.car.speed * 3.6 > 130 && cap.car.speed > previous &&
              cap.car.gear >= 3,
          "uncapped acceleration");
    Simulation offroad;
    offroad.car.x = 50;
    for (int i = 0; i < 960; i++)
      offroad.tick({1, 0, 0});
    // The default world is one flat uniform-grip plane, so position is neutral.
    check(std::abs(offroad.car.speed * 3.6 - 100.8) < 1.5, "offroad traction");
    // Every synthetic car (and real descriptor when a directory is given) with
    // the application's clearance-aware dynamics, at several headings.
    constexpr double pi = 3.14159265358979323846;
    const auto cars = allCars(argc, argv);
    for (const auto &car : cars) {
      auto fail = [&](const std::string &why) { throw std::runtime_error(car.name + ": " + why); };
      auto configured = [&] {
        auto sim = std::make_unique<Simulation>();
        if (!sim->setGeometry(car.geometry) || !sim->setDynamics(dynamicsFor(car.geometry))) fail("configure");
        return sim;
      };
      auto drive = configured();
      for (int i = 0; i < 960; ++i) drive->tick({1, 0, 0});
      const double kmh = drive->car.speed * 3.6;
      if (kmh < 95 || kmh > 125 || drive->car.gear < 2) fail("eight second speed " + std::to_string(kmh));
      const double entry = drive->car.speed, from = drive->car.z;
      for (int i = 0; i < 600; ++i) drive->tick({0, 1, 0});
      const double stop = drive->car.z - from;
      if (stop < entry * entry / (2 * 1.1 * 9.80665) - .5 || stop > 55 || std::abs(drive->car.speed) > .01 ||
          drive->chassisContact)
        fail("braking distance " + std::to_string(stop));
      auto right = configured(), left = configured();
      for (int i = 0; i < 360; ++i) {
        right->tick({.5, 0, 0});
        left->tick({.5, 0, 0});
      }
      for (int i = 0; i < 240; ++i) {
        right->tick({.3, 0, .4});
        left->tick({.3, 0, -.4});
      }
      if (!(right->car.heading > .25 && right->car.x > .8 && right->car.yawRate > 0 && right->car.accelerationLateral > 0) ||
          std::abs(right->car.heading + left->car.heading) > 1e-3 || std::abs(right->car.x + left->car.x) > 1e-3)
        fail("mirrored steering heading " + std::to_string(right->car.heading) + "/" + std::to_string(left->car.heading));
      // Walls from several headings (axis-aligned, oblique, reverse): the
      // oriented envelope stops the car inside the world and it does not tunnel.
      for (const double degrees : {0., 90., 180., 270., 30., 60., 135., 225.}) {
        const double heading = degrees * pi / 180, dx = std::sin(heading), dz = std::cos(heading);
        const double reach = 500 / std::max(std::abs(dx), std::abs(dz));
        auto wall = configured();
        wall->car.x = dx * (reach - 25);
        wall->car.z = dz * (reach - 25);
        wall->car.heading = heading;
        wall->tick({}, 0);
        bool touched = false;
        double deepest = 0;
        for (int i = 0; i < 1500; ++i) {
          wall->tick({1, 0, 0});
          touched = touched || wall->boundaryContact;
          // Penetration of the oriented envelope past the wall, every tick.
          const auto clearance = orientedBoundaryClearance(car.geometry, wall->car.heading);
          const auto &c = wall->car;
          deepest = std::max({deepest, c.x - clearance.maxX, clearance.minX - c.x, c.z - clearance.maxZ,
                              clearance.minZ - c.z});
        }
        const std::string at = " at " + std::to_string(int(degrees)) + " deg";
        if (!touched) fail("never reached the wall" + at);
        if (deepest > .25) fail("tunnelled " + std::to_string(deepest) + " m through the wall" + at);
      }
    }
    std::cout << cars.size() << " cars x 8 wall headings checked\n";
    std::cout << "PASS: acceleration, braking, direction changes, uncapped "
                 "speed, steering, reset, boundary, 30/60/144 Hz\n";
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
