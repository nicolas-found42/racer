#include "gamepad.h"
#include <cmath>
namespace racer {
Input gamepadInput(SDL_Gamepad *pad) {
  auto axis = [&](SDL_GamepadAxis a) {
    return SDL_GetGamepadAxis(pad, a) / 32767.0;
  };
  double steering = axis(SDL_GAMEPAD_AXIS_LEFTX);
  steering = std::abs(steering) < .15
                 ? 0
                 : std::copysign((std::abs(steering) - .15) / .85, steering);
  return {std::max(0.0, axis(SDL_GAMEPAD_AXIS_RIGHT_TRIGGER)),
          std::max(0.0, axis(SDL_GAMEPAD_AXIS_LEFT_TRIGGER)),
          std::clamp(steering, -1.0, 1.0)};
}
} // namespace racer
