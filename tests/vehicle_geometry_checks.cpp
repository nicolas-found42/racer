#include "vehicle_geometry.h"
#include <bx/math.h>
#include <cmath>
#include <iostream>
#include <limits>
#include <numbers>
#include <stdexcept>

namespace {
int failures = 0;
void check(bool condition, const char *name) {
  if (!condition) { ++failures; std::cerr << "FAIL: " << name << '\n'; }
}
bool near(double a, double b, double tolerance = 1e-5) { return std::abs(a-b) < tolerance; }
template<class F> void rejects(F action, const char *name) {
  bool rejected = false;
  try { action(); } catch (const std::invalid_argument &) { rejected = true; }
  check(rejected, name);
}
// Independent bicycle-to-Ackermann road-wheel angle, geometric (cot) form.
double ackermannAngle(const racer::VehicleGeometry &g, std::size_t wheel, double central) {
  if (wheel >= 2) return 0;
  const double mid = (g.wheels[0].center.x + g.wheels[1].center.x) * .5;
  const double offset = g.wheels[wheel].center.x - mid;
  return std::atan(g.wheelbase() * std::tan(central) /
                   (g.wheelbase() - offset * std::tan(central)));
}
}
int main() {
  using namespace racer;
  constexpr double pi = std::numbers::pi;
  VehicleGeometry geometry;
  std::string reason;
  check(geometry.valid(&reason) && reason.empty(), "default geometry valid");
  check(near(geometry.wheelbase(), 2.7) && near(geometry.frontTrack(), 2) &&
        near(geometry.body.maximum.z-geometry.body.minimum.z, 4.4), "legacy dimensions");
  const auto normalized = normalizeVehiclePoint({110,220,330}, {100,200,300}, .01);
  check(near(normalized.x,.1) && near(normalized.y,.2) && near(normalized.z,.3),
        "explicit model scale and pivot");
  rejects([&] { normalizeVehiclePoint({}, {}, -1); }, "negative source scale rejected");
  auto bad = geometry; bad.wheels[0].radius = 0;
  check(!bad.valid(&reason) && !reason.empty(), "zero tire radius rejected");
  bad = geometry; bad.wheels[0].center.z = -1.35;
  check(!bad.valid(), "misaligned axle rejected");
  bad = geometry; std::swap(bad.wheels[0],bad.wheels[1]);
  check(!bad.valid(), "swapped left/right rejected");
  bad = geometry; bad.body.minimum.x = std::numeric_limits<double>::quiet_NaN();
  check(!bad.valid(), "nonfinite bounds rejected");
  bad = geometry; bad.wheels[0].center.y = 0;
  check(!bad.valid(), "underground tire rejected");
  bad = geometry; bad.body.minimum.z = -1;
  check(!bad.valid(), "axle outside body rejected");
  bad = geometry; std::swap(bad.wheels[0],bad.wheels[2]); std::swap(bad.wheels[1],bad.wheels[3]);
  check(!bad.valid(), "backwards wheelbase rejected");

  // Compare independent math against this checkout's pinned bx rotations, not
  // bx mtxSRT Euler composition (wheel spin must precede steering).
  for (double heading : {0., .7, -1.1, pi/2})
    for (double steering : {-.4, 0., .4})
      for (double spin : {-.8, 0., .8})
        for (std::size_t wheel = 0; wheel < 4; ++wheel) {
          float m[16], rotateX[16], rotateY[16];
          wheelRenderTransform(m, geometry, wheel, heading, 12, -18, steering, spin);
          bx::mtxRotateX(rotateX, float(-spin));
          bx::mtxRotateY(rotateY, float(-heading-ackermannAngle(geometry, wheel, steering)));
          for (int column = 0; column < 3; ++column)
            for (int row = 0; row < 3; ++row) {
              double expected = 0;
              for (int k = 0; k < 3; ++k)
                expected += rotateY[k*4+row] * rotateX[column*4+k];
              check(near(m[column*4+row],expected), "pinned bx composition agreement");
            }
          const auto center = geometry.wheels[wheel].center;
          check(near(m[12],12+std::cos(heading)*center.x+std::sin(heading)*center.z) &&
                near(m[13],center.y) &&
                near(m[14],-18-std::sin(heading)*center.x+std::cos(heading)*center.z),
                "steer/spin keep wheel pivot fixed");
        }
  float m[16];
  wheelRenderTransform(m,geometry,0,0,0,0,.3,0);
  check(m[8] > 0 && near(m[10],std::cos(ackermannAngle(geometry,0,.3))), "front +Z nose steers right");
  // Full Ackermann: the inside wheel turns more than the central angle, the
  // outside wheel less; parallel steering and zero lock are exact.
  const double toRight = wheelSteeringAngle(geometry,1,.3), toLeft = wheelSteeringAngle(geometry,0,.3);
  check(geometry.wheels[1].center.x > geometry.wheels[0].center.x ? toRight > .3 && toLeft < .3
                                                                 : toRight < .3 && toLeft > .3,
        "Ackermann inner/outer wheel angles");
  check(near(wheelSteeringAngle(geometry,0,.3,0),.3) && near(wheelSteeringAngle(geometry,1,.3,0),.3) &&
        near(wheelSteeringAngle(geometry,0,0),0) && near(wheelSteeringAngle(geometry,2,.3),0) &&
        near(wheelSteeringAngle(geometry,3,.3),0), "parallel steer, zero lock and straight rear");
  check(near(wheelSteeringAngle(geometry,0,-.3),-wheelSteeringAngle(geometry,1,.3)),
        "Ackermann mirror symmetry");
  check(near(wheelSteeringAngle(geometry,0,.3),ackermannAngle(geometry,0,.3)) &&
        near(wheelSteeringAngle(geometry,1,.3),ackermannAngle(geometry,1,.3)),
        "Ackermann matches independent geometry");
  wheelRenderTransform(m,geometry,2,0,0,0,.3,0);
  check(near(m[8],0) && near(m[10],1), "rear wheel stays straight");
  wheelRenderTransform(m,geometry,0,0,0,0,0,.2);
  // A tread point initially at the bottom moves toward -Z for forward roll.
  check(-geometry.wheels[0].radius*m[6] < 0, "forward spin contact motion");
  wheelRenderTransform(m,geometry,0,0,0,0,0,-.2);
  check(-geometry.wheels[0].radius*m[6] > 0, "reverse spin contact motion");
  check(near(wheelSpinAfterTravel(.2,-.08,.4),0), "reverse travel unwinds spin");
  float carrier[16],unspun[16];
  wheelRenderTransform(carrier,geometry,0,.4,10,-8,.3,1.7,false);
  wheelRenderTransform(unspun,geometry,0,.4,10,-8,.3,0);
  for(size_t i=0;i<16;++i)check(near(carrier[i],unspun[i]),"caliper carrier steers with axle without rolling");
  check(near(wheelSpinAfterTravel(0,2*pi*.4,.4),0), "one tire circumference");
  wheelRenderTransform(m,geometry,0,0,0,0,0,0);
  check(near(m[0],1) && near(m[5],1) && near(m[10],1) && near(m[6],0), "reset spin/steer identity");
  rejects([&] { wheelRenderTransform(m,geometry,4,0,0,0,0,0); }, "invalid wheel index");
  rejects([&] { wheelSpinAfterTravel(0,1,0); }, "invalid spin radius");

  // The measured geometry changes both axle metrics and contact bounds.
  auto longer = geometry;
  longer.body.minimum.z = -3; longer.body.maximum.z = 3.5;
  for (auto &wheel : longer.wheels) wheel.center.z *= 1.2;
  check(longer.valid() && near(longer.wheelbase(),3.24), "converted axle spacing retained");
  const auto ahead = orientedBoundaryClearance(longer,0);
  check(near(ahead.maxZ,496.5) && near(ahead.minZ,-497), "asymmetric body contact");
  const auto side = orientedBoundaryClearance(longer,pi/2);
  check(near(side.maxX,496.5) && near(side.minX,-497), "body contact rotates with heading");
  for (double heading : {0., .4, pi/2, pi, -2.4}) {
    const auto allowed = orientedBoundaryClearance(longer,heading);
    double x = 600, z = -600;
    check(clampVehicleToBoundary(longer,heading,x,z), "boundary collision detected");
    check(near(x,allowed.maxX) && near(z,allowed.minZ), "boundary clamps origin");
    const auto envelope = longer.collisionBounds();
    for (double px : {envelope.minimum.x,envelope.maximum.x})
      for (double pz : {envelope.minimum.z,envelope.maximum.z}) {
        const double wx=x+std::cos(heading)*px+std::sin(heading)*pz;
        const double wz=z-std::sin(heading)*px+std::cos(heading)*pz;
        check(std::abs(wx) <= 500+1e-9 && std::abs(wz) <= 500+1e-9,
              "whole oriented envelope inside 1000m world");
      }
    check(!clampVehicleToBoundary(longer,heading,x,z), "resting boundary stable");
  }
  const auto envelope = geometry.collisionBounds();
  for (int degree = -90; degree <= 90; ++degree) {
    const double steer = degree*pi/180;
    for (int sample = 0; sample < 360; ++sample) {
      const double around = sample*pi/180;
      for (double sideX : {-geometry.wheels[0].width/2,geometry.wheels[0].width/2}) {
        const double radialZ = geometry.wheels[0].radius*std::cos(around);
        const double x=geometry.wheels[0].center.x+std::cos(steer)*sideX+std::sin(steer)*radialZ;
        const double z=geometry.wheels[0].center.z-std::sin(steer)*sideX+std::cos(steer)*radialZ;
        check(x>=envelope.minimum.x && x<=envelope.maximum.x &&
              z>=envelope.minimum.z && z<=envelope.maximum.z, "tire sweep inside contact envelope");
      }
    }
  }
  rejects([&] { orientedBoundaryClearance(geometry,0,.5); }, "world too small rejected");
  rejects([&] { orientedBoundaryClearance(geometry,std::numeric_limits<double>::infinity()); },
          "invalid heading rejected");
  std::cout << (failures ? "FAIL" : "PASS")
            << ": geometry validation, scale/pivots, bx wheel transforms, steering/spin/reset, oriented boundary and tire sweep\n";
  return failures ? 1 : 0;
}
