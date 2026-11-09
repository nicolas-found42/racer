// The simulation driven over the real SurfaceIndex through makeRoadSampler (the
// wiring the application installs for --world-mesh/--follow-ground), for every
// synthetic car and, when a directory is given, every real local descriptor,
// each approaching the ramp at several headings.
#include "simulation.h"
#include "surface_follow.h"
#include "vehicle_fixtures.h"
#include "vehicle_tuning.h"
#include <cmath>
#include <iostream>
#include <memory>
#include <string>
using namespace racer;
namespace {
int failures = 0;
void check(bool ok, const std::string &car, const std::string &why) {
  if (!ok) {
    ++failures;
    std::cerr << "FAIL [" << car << "]: " << why << '\n';
  }
}
constexpr double pi = 3.14159265358979323846;
const double slope = std::tan(12 * pi / 180);
double ramp(double z) { // flat to z=30, 12 degree incline to z=70, plateau after
  return z < 30 ? 0 : z < 70 ? (z - 30) * slope : 40 * slope;
}
AssetVertex vertex(double x, double y, double z) {
  return AssetVertex{float(x), float(y), float(z), 0xffffffff};
}
void strip(MeshAsset &asset, double z0, double z1, double x = 200) {
  asset.triangles.insert(asset.triangles.end(),
      {vertex(-x, ramp(z0), z0), vertex(-x, ramp(z1), z1), vertex(x, ramp(z1), z1),
       vertex(-x, ramp(z0), z0), vertex(x, ramp(z1), z1), vertex(x, ramp(z0), z0)});
}
std::shared_ptr<const surfaceFollow::SurfaceIndex> index(MeshAsset asset) {
  AssetSection section;
  section.count = uint32_t(asset.triangles.size());
  asset.sections.push_back(section);
  surfaceFollow::SurfaceIndex::Builder builder;
  builder.add(asset, surfaceFollow::identity);
  return std::make_shared<const surfaceFollow::SurfaceIndex>(builder.finish());
}
double wheelBottom(const VehicleGeometry &g) {
  double bottom = 0;
  for (const auto &w : g.wheels) bottom += (w.center.y - w.radius) / 4;
  return bottom;
}
bool configure(Simulation &sim, const VehicleGeometry &g) {
  return sim.setGeometry(g) && sim.setDynamics(dynamicsFor(g));
}
bool allGrounded(const Simulation &sim) {
  for (const auto &w : sim.car.wheels)
    if (!w.grounded) return false;
  return true;
}
} // namespace
int main(int argc, char **argv) {
  const auto cars = allCars(argc, argv);
  std::cout << cars.size() << " cars\n";
  MeshAsset rampMesh, gapMesh;
  strip(rampMesh, -120, 30);
  strip(rampMesh, 30, 70);
  strip(rampMesh, 70, 200);
  strip(gapMesh, -120, 10);
  strip(gapMesh, 22, 200); // 12 m hole at the same height
  const auto rampIndex = index(rampMesh), gapIndex = index(gapMesh);
  for (const auto &car : cars) {
    const auto &g = car.geometry;
    const std::string &name = car.name;
    {
      // Flat default world (no sampler): rests at its ride height, grounded.
      Simulation sim;
      check(configure(sim, g), name, "geometry/dynamics accepted");
      for (int i = 0; i < 720; ++i) sim.tick({});
      check(allGrounded(sim) && std::abs(sim.car.y + wheelBottom(g)) < .02 &&
                sim.groundSpeed() < .01 && !sim.chassisContact,
            name, "rests on the default flat road at its static ride height");
    }
    for (const double degrees : {0., 25., -25., 50., -50.}) {
      const double heading = degrees * pi / 180;
      const std::string label = name + " @" + std::to_string(int(degrees)) + " deg";
      Simulation sim;
      sim.setRoadSampler(surfaceFollow::makeRoadSampler(rampIndex));
      check(configure(sim, g), label, "geometry/dynamics accepted");
      // The application places the chassis on the road under a teleport.
      sim.car.x = -std::sin(heading) * 0 - 25 * std::sin(heading);
      sim.car.z = -25 * std::cos(heading);
      sim.car.heading = heading;
      sim.car.y = ramp(sim.car.z) - wheelBottom(g);
      sim.tick({}, 0);
      int chassisTicks = 0;
      for (int i = 0; i < 6000 && sim.car.z < 52; ++i) {
        sim.tick({.7, 0, 0});
        chassisTicks += sim.chassisContact;
      }
      check(sim.car.z >= 52, label, "drives up the ramp");
      // Low bodies may scrape the sharp flat-to-12-degree kink for a moment
      // (measured worst case 35 ticks = 0.29 s, always over before the top):
      // bound it at half a second, and it must not persist.
      check(chassisTicks <= 60 && !sim.chassisContact, label,
            "chassis scrape at the kink is brief: " + std::to_string(chassisTicks) +
                " ticks, in contact at end " + std::to_string(sim.chassisContact));
      check(allGrounded(sim), label, "all four wheels on the slope");
      // Body attitude follows the plane: body up equals the ground normal.
      const auto body = sim.bodyTransform();
      const double nl = std::sqrt(1 + slope * slope), ny = 1 / nl, nz = -slope / nl;
      const double dot = body[5] * ny + body[6] * nz;
      check(std::acos(std::clamp(dot, -1., 1.)) < 4 * pi / 180, label,
            "body up vector matches the ground normal within 4 degrees");
      // Analytic world roll/pitch of a rigid body lying on this plane.
      const double expectedPitch = std::atan(slope * std::cos(heading));
      const double expectedRoll = std::atan(slope * std::sin(heading)); // + = right side down
      check(std::abs(sim.car.pitch - expectedPitch) < 3 * pi / 180, label,
            "pitch matches the slope along the heading");
      check(std::abs(sim.car.roll - expectedRoll) < 3 * pi / 180, label,
            "roll sign and size match the slope across the heading");
      check(sim.car.wheels[0].contactNormal.z < -.15 && sim.car.wheels[3].contactPoint.y > .5, label,
            "contact points and normals describe the elevated slope");
      check(std::abs(sim.car.y - (ramp(sim.car.z) - wheelBottom(g))) < .1 + .25 * std::abs(std::sin(heading)),
            label, "chassis rides at the local ground height plus ride height");
    }
    {
      // A hole in the mesh is air, never an extrapolated ground plane.
      Simulation sim;
      sim.setRoadSampler(surfaceFollow::makeRoadSampler(gapIndex));
      check(configure(sim, g), name, "geometry/dynamics accepted");
      sim.car.z = -60;
      sim.car.y = -wheelBottom(g);
      sim.tick({}, 0);
      bool airborne = false;
      double lowest = 0;
      for (int i = 0; i < 2400 && sim.car.z < 40; ++i) {
        sim.tick({.8, 0, 0});
        bool any = false;
        for (const auto &w : sim.car.wheels) any = any || w.grounded;
        airborne = airborne || !any;
        lowest = std::min(lowest, sim.car.y);
      }
      check(airborne, name, "all four wheels leave the road over the gap");
      check(lowest < -.5, name, "the car falls instead of being held up by a phantom plane");
    }
    {
      // The dynamic wheel transform keeps each wheel centre where suspension
      // compression puts it, while cornering (so steering and roll are active).
      Simulation sim;
      check(configure(sim, g), name, "geometry/dynamics accepted");
      for (int i = 0; i < 480; ++i) sim.tick({.6, 0, 0});
      for (int i = 0; i < 180; ++i) sim.tick({.2, 0, .5});
      const auto body = sim.bodyTransform();
      for (std::size_t i = 0; i < 4; ++i) {
        const auto wheel = sim.wheelTransform(i, true), still = sim.wheelTransform(i, false);
        const auto local = g.wheels[i].center;
        const double compression = sim.car.wheels[i].compression;
        const double expected[3] = {
            body[12] + body[0] * local.x + body[4] * (local.y + compression) + body[8] * local.z,
            body[13] + body[1] * local.x + body[5] * (local.y + compression) + body[9] * local.z,
            body[14] + body[2] * local.x + body[6] * (local.y + compression) + body[10] * local.z};
        bool placed = true;
        for (int k = 0; k < 3; ++k)
          placed = placed && std::abs(wheel[12 + k] - expected[k]) < 1e-4 &&
                   std::abs(still[12 + k] - expected[k]) < 1e-4;
        check(placed, name, "wheel transform follows suspension travel (wheel " + std::to_string(i) + ")");
        check(std::abs(wheel[0] - still[0]) < 1e-5 && std::abs(wheel[1] - still[1]) < 1e-5 &&
                  std::abs(wheel[2] - still[2]) < 1e-5,
              name, "spin leaves the axle direction unchanged");
      }
      // Front wheels steer with Ackermann: inner wheel turns more; rears stay straight.
      const auto &fl = sim.car.wheels[0], &fr = sim.car.wheels[1];
      check(sim.car.steering > 0 && fr.steeringAngle > fl.steeringAngle && fl.steeringAngle > 0 &&
                sim.car.wheels[2].steeringAngle == 0 && sim.car.wheels[3].steeringAngle == 0,
            name, "Ackermann inner/outer front angles, straight rears");
      check(sim.groundSpeed() >= std::abs(sim.car.speed) - 1e-6 &&
                std::abs(sim.groundSpeed() - std::hypot(sim.car.velocityX, sim.car.velocityZ)) < 1e-12,
            name, "ground speed is the horizontal velocity magnitude");
    }
  }
  if (failures) {
    std::cerr << failures << " failure(s)\n";
    return 1;
  }
  std::cout << "PASS: road sampler over a real SurfaceIndex (ramp at 5 headings, gap, flat), dynamic transforms and "
               "Ackermann, for "
            << cars.size() << " cars\n";
}
