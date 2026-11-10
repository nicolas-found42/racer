#include "gamepad.h"
#include <iostream>
#include <stdexcept>
void check(bool v, const char *m) {
  if (!v)
    throw std::runtime_error(m);
}
int main() {
  try {
    check(SDL_Init(SDL_INIT_GAMEPAD), SDL_GetError());
    SDL_VirtualJoystickDesc desc{};
    SDL_INIT_INTERFACE(&desc);
    desc.type = SDL_JOYSTICK_TYPE_GAMEPAD;
    desc.naxes = SDL_GAMEPAD_AXIS_COUNT;
    desc.nbuttons = SDL_GAMEPAD_BUTTON_COUNT;
    desc.name = "Racer virtual verification controller";
    desc.axis_mask = (1u << SDL_GAMEPAD_AXIS_COUNT) - 1;
    desc.button_mask = (1u << SDL_GAMEPAD_BUTTON_COUNT) - 1;
    auto id = SDL_AttachVirtualJoystick(&desc);
    check(id != 0, SDL_GetError());
    auto joystick = SDL_OpenJoystick(id);
    auto pad = SDL_OpenGamepad(id);
    check(pad != nullptr, SDL_GetError());
    SDL_SetJoystickVirtualAxis(joystick, SDL_GAMEPAD_AXIS_RIGHT_TRIGGER,
                               -32768);
    SDL_SetJoystickVirtualAxis(joystick, SDL_GAMEPAD_AXIS_LEFT_TRIGGER, -32768);
    SDL_UpdateJoysticks();
    auto in = racer::gamepadInput(pad);
    check(in.throttle == 0 && in.brake == 0 && in.steer == 0,
          "neutral controls");
    // SDL_GetGamepadAxis reports triggers unipolar (0..32767), so raw 1638
    // arrives as 17203 = .525; the trigger remap (axis-.05)/.95 maps it to .5.
    SDL_SetJoystickVirtualAxis(joystick, SDL_GAMEPAD_AXIS_RIGHT_TRIGGER, 1638);
    SDL_SetJoystickVirtualAxis(joystick, SDL_GAMEPAD_AXIS_LEFTX, 16384);
    SDL_UpdateJoysticks();
    in = racer::gamepadInput(pad);
    check(in.throttle > .48 && in.throttle < .53, "analog throttle");
    check(in.steer > .35 && in.steer < .45, "analog steering");
    SDL_SetJoystickVirtualAxis(joystick, SDL_GAMEPAD_AXIS_RIGHT_TRIGGER, 32767);
    SDL_SetJoystickVirtualAxis(joystick, SDL_GAMEPAD_AXIS_LEFT_TRIGGER, 32767);
    SDL_UpdateJoysticks();
    in = racer::gamepadInput(pad);
    check(in.throttle > .99 && in.brake > .99, "full triggers");
    SDL_SetJoystickVirtualButton(joystick, SDL_GAMEPAD_BUTTON_NORTH, true);
    SDL_SetJoystickVirtualButton(joystick, SDL_GAMEPAD_BUTTON_START, true);
    SDL_UpdateJoysticks();
    check(SDL_GetGamepadButton(pad, SDL_GAMEPAD_BUTTON_NORTH) &&
              SDL_GetGamepadButton(pad, SDL_GAMEPAD_BUTTON_START),
          "reset/pause buttons");
    SDL_DetachVirtualJoystick(id);
    SDL_UpdateJoysticks();
    check(!SDL_GamepadConnected(pad), "disconnect");
    SDL_CloseGamepad(pad);
    SDL_CloseJoystick(joystick);
    SDL_Quit();
    std::cout
        << "PASS: virtual SDL gamepad axes, deadzone, buttons and detach\n";
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    SDL_Quit();
    return 1;
  }
}
