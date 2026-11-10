#include "simulation.h"
#include "test_session.h"
#include <cstdio>
using namespace racer;
int main() {
  for (double m : {.8, .85, .9, .95, 1.0, 1.05, 1.1, 1.15, 1.2}) {
    Simulation sim; TestSession test;
    test.start(TestKind::Acceleration, 0, VehicleSetup{m, 1, 1}, sim);
    for (int i = 0; i < 2400 && test.active(); ++i) test.tick(sim, {});
    std::printf("mult=%.2f seconds=%.6f valid=%d\n", m, test.result().seconds, (int)test.result().valid);
  }
  // Braking baseline (session_checks pins).
  { Simulation sim; TestSession t;
    t.start(TestKind::Braking, 0, VehicleSetup{1,1,1}, sim);
    for (int i = 0; i < 2400 && t.active(); ++i) t.tick(sim, {0,1,1});
    std::printf("braking dist=%.4f sec=%.4f\n", t.result().distance, t.result().seconds); }
  // Acceleration baseline distance.
  { Simulation sim; TestSession t;
    t.start(TestKind::Acceleration, 0, VehicleSetup{1,1,1}, sim);
    for (int i = 0; i < 2400 && t.active(); ++i) t.tick(sim, {0,1,1});
    std::printf("accel1.0 dist=%.4f sec=%.6f\n", t.result().distance, t.result().seconds); }
  return 0;
}
