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
// Radar target relative to the car (bearing radians, + right; metres).
struct RadarBlip {
  double bearing = 0, distance = 0;
  int kind = 0; // 0 destination, 1 next gate, 2 later gate
};
// Everything the driving HUD shows for one frame.
struct DriveState {
  double mph = 0, throttle = 0, brake = 0, steer = 0, time = 0;
  bool reverse = false;
  std::string vehicle, destination, bearing; // bearing: AHEAD / LEFT / RIGHT
  double distance = 0, bearingRadians = 0;
  bool hasDestination = false;
  double heading = 0; // car heading, radians (rotates the radar compass)
  double carX = 0, carZ = 0; // world position (metres) for the radar street grid
  std::vector<RadarBlip> blips;
  // World-anchored marker in window pixels; `behind` when it projects behind the eye.
  bool markerActive = false, markerBehind = false;
  float markerX = 0, markerY = 0;
  std::string markerLabel;
  double markerDistance = 0;
  std::optional<DriveTest> test;
};
// Street map shown on the event board (world metres; markers and the car).
struct PanelMap {
  struct Marker { double x = 0, z = 0; std::string name; bool selected = false; };
  bool active = false;
  double carX = 0, carZ = 0, heading = 0;
  std::vector<Marker> markers;
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
                 const std::vector<std::string>& lines,bool activeTest,int optionCount=-1,
                 const PanelMap& map=PanelMap{});
  // HUD accent colour (session setting): 0 cyan, 1 green, 2 violet, 3 magenta, 4 ice.
  static constexpr int accentCount=5;
  void setAccent(int index);
  int accentIndex() const;
  // Verification aid (--hud-repaint-audit): repaint each drive frame a second
  // time without the dirty windows and report any pixel the incremental path
  // missed. Off in normal play.
  void setRepaintAudit(bool on);
  void cycleAccent(){setAccent((accentIndex()+1)%accentCount);}
private:
  struct Impl;
  std::unique_ptr<Impl> impl;
};
}
