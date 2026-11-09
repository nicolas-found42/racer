#pragma once
#include <cstdint>
#include <memory>
#include <optional>
#include <string>
#include <vector>

namespace racer {
// Live data for an active driving test (countdown, timer, gate guidance).
struct DriveTest {
  int kind = 0; // 0 acceleration, 1 braking, 2 handling
  std::string name, note;
  bool countdown = false, measuring = true, automatic = false;
  double countdownSeconds = 0, elapsed = 0, distance = 0, speedKmh = 0;
  int gate = 0, gates = 0;
  double gateDistance = 0, bearing = 0; // bearing radians, + is to the right
  std::string turn;
};
// Everything the driving HUD shows for one frame.
struct DriveState {
  double mph = 0, throttle = 0, brake = 0, steer = 0, time = 0;
  bool reverse = false;
  std::string vehicle, destination, bearing; // bearing: AHEAD / LEFT / RIGHT
  double distance = 0, bearingRadians = 0;
  bool hasDestination = false;
  // World-anchored marker in window pixels; `behind` when it projects behind the eye.
  bool markerActive = false, markerBehind = false;
  float markerX = 0, markerY = 0;
  std::string markerLabel;
  double markerDistance = 0;
  std::optional<DriveTest> test;
};
// Construct after bgfx initialization and destroy before bgfx shutdown.
// Aspect-correct safe areas retain the normal canvas and a cropped compact layout.
class DriveHud {
public:
  DriveHud();
  ~DriveHud();
  DriveHud(const DriveHud&)=delete;
  DriveHud& operator=(const DriveHud&)=delete;
  void draw(uint16_t width,uint16_t height,const DriveState& state);
  // optionCount: selectable entries (PlayFlow::menuCount); -1 when unknown.
  void drawPanel(uint16_t width,uint16_t height,
                 const std::vector<std::string>& lines,bool activeTest,int optionCount=-1);
private:
  struct Impl;
  std::unique_ptr<Impl> impl;
};
}
