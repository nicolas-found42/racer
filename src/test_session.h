#pragma once
#include "simulation.h"
#include <optional>
#include <string>
#include <vector>
namespace racer {
enum class TestKind { Acceleration, Braking, Handling };
enum class TestPhase { Idle, Countdown, Running, Result, Invalid };
const char *testId(TestKind kind);
const char *testName(TestKind kind);
struct Gate {
  double x, z, nx, nz, width;
};
struct Course {
  Car start;
  int revision;
  std::vector<Gate> gates;
};
const Course &handlingCourse();
std::optional<double> gateCrossing(const Gate &, const Car &before,
                                   const Car &after);
struct TestResult {
  TestKind kind = TestKind::Acceleration;
  int slot = 0;
  VehicleSetup setup;
  double seconds = 0, distance = 0, initialSpeed = 0;
  bool valid = false;
  std::string reason;
  int testRevision = 1, handlingRevision = 1;
  std::string carId = "prototype";
};
class TestSession {
public:
  bool start(TestKind, int slot, const VehicleSetup &, Simulation &,
             const std::string &carId = "prototype",int modelRevision = 1);
  void tick(Simulation &, Input player, double dt = step);
  // Shared measurement path, also useful for deterministic course checks.
  void observeMotion(const Car &before, const Car &after, double dt,
                     bool boundaryContact = false);
  void invalidate(std::string reason);
  void cancel() { invalidate("Cancelled - no record saved"); }
  TestPhase phase() const { return phase_; }
  bool active() const {
    return phase_ == TestPhase::Countdown || phase_ == TestPhase::Running;
  }
  const TestResult &result() const { return result_; }
  double countdownRemaining() const { return countdown_; }
  bool measuringBraking() const { return braking_; }
  double distance() const { return distance_; }
  double elapsed() const { return measured_; }
  size_t nextGate() const { return nextGate_; }
  double timeout =
      60; // Bounded automatic benchmark, seconds of simulation time.
private:
  TestPhase phase_ = TestPhase::Idle;
  TestResult result_;
  double countdown_ = 0, total_ = 0, measured_ = 0, distance_ = 0;
  size_t nextGate_ = 0;
  bool braking_ = false;
  void finish(double seconds, double distance);
};
} // namespace racer
