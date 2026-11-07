#include "simulation.h"
#include <cmath>
#include <iostream>
#include <stdexcept>
using namespace racer;
void check(bool v, const char *m) {
  if (!v)
    throw std::runtime_error(m);
}
int main() {
  try {
    Simulation s;
    for (int i = 0; i < 960; i++)
      s.tick({1, 0, 0});
    std::cout << "Eight second speed: " << s.car.speed * 3.6 << " km/h\n";
    check(std::abs(s.car.speed * 3.6 - 100) < .2, "acceleration");
    double start = s.car.z;
    for (int i = 0; i < 600; i++)
      s.tick({0, 1, 0});
    std::cout << "Braking distance: " << s.car.z - start << " m\n";
    check(std::abs(s.car.z - start - 40) < 2, "stopping distance");
    check(s.car.speed == 0, "held brake stays stopped");
    s.tick({});
    s.tick({0, 1, 0});
    check(s.car.speed < 0, "fresh press reverses");
    for (int i = 0; i < 1000; i++)
      s.tick({0, 1, 0});
    check(std::abs(s.car.speed + 30 / 3.6) < .01, "reverse cap");
    for (int i = 0; i < 1000; i++)
      s.tick({1, 0, 0});
    check(s.car.speed == 0, "forward pedal stops reverse");
    s.tick({});
    s.tick({1, 0, 0});
    check(s.car.speed > 0, "fresh forward");
    s.reset();
    check(s.car.x == 0 && s.car.z == 0 && s.car.speed == 0 &&
              s.car.heading == 0,
          "reset");
    s.tick({});
    for (int i = 0; i < 480; i++)
      s.tick({1, 0, .7});
    check(std::abs(s.car.x) > 2 && std::abs(s.car.heading) > .2, "turning");
    s.reset();
    s.tick({});
    s.car.x = 490;
    s.car.heading = 1.57079632679;
    for (int i = 0; i < 1500; i++)
      s.tick({1, 0, 0});
    check(s.car.x <= 497.5 && s.car.speed == 0, "boundary");
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
      check(std::abs(a.car.speed * 3.6 - 100) < .2, "frame-rate independence");
    }
    Simulation cap;
    for (int i = 0; i < 1560; i++)
      cap.tick({1, 0, 0});
    check(std::abs(cap.car.speed - 160 / 3.6) < .01, "forward cap");
    Simulation offroad;
    offroad.car.x = 50;
    for (int i = 0; i < 960; i++)
      offroad.tick({1, 0, 0});
    check(std::abs(offroad.car.speed * 3.6 - 100) < .2, "offroad traction");
    std::cout << "PASS: acceleration, braking, direction changes, caps, "
                 "steering, reset, boundary, 30/60/144 Hz\n";
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
