#pragma once
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

namespace racer {
// Construct after bgfx initialization and destroy before bgfx shutdown.
// Aspect-correct safe areas retain the normal canvas and a cropped compact layout.
class DriveHud {
public:
  DriveHud();
  ~DriveHud();
  DriveHud(const DriveHud&)=delete;
  DriveHud& operator=(const DriveHud&)=delete;
  void draw(uint16_t width,uint16_t height,double mph,bool reverse,
            const std::string& vehicle,const std::string& destination,
            double distance,const std::string& bearing);
  void drawPanel(uint16_t width,uint16_t height,
                 const std::vector<std::string>& lines,bool activeTest);
private:
  struct Impl;
  std::unique_ptr<Impl> impl;
};
}
