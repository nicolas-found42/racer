#include "gamepad.h"
#include <algorithm>
#include <cmath>
namespace racer {
Input gamepadInput(SDL_Gamepad *pad) {
  if (!pad)
    return {};
  auto axis = [&](SDL_GamepadAxis a) {
    const auto value = SDL_GetGamepadAxis(pad, a);
    // Signed stick axes have one more negative value than positive values.
    return value / (value < 0 ? 32768.0 : 32767.0);
  };
  auto trigger = [&](SDL_GamepadAxis a) {
    // Keep an idle trigger from applying a brake or taking over the keyboard.
    // Remap the usable range continuously so the pedal still reaches 1.0.
    constexpr double deadzone = .05;
    return std::clamp((axis(a) - deadzone) / (1 - deadzone), 0.0, 1.0);
  };
  double steering = axis(SDL_GAMEPAD_AXIS_LEFTX);
  steering = std::abs(steering) < .15
                 ? 0
                 : std::copysign((std::abs(steering) - .15) / .85, steering);
  return {trigger(SDL_GAMEPAD_AXIS_RIGHT_TRIGGER),
          trigger(SDL_GAMEPAD_AXIS_LEFT_TRIGGER),
          std::clamp(steering, -1.0, 1.0)};
}
} // namespace racer
