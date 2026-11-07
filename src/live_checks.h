#pragma once
#include "simulation.h"
#include <SDL3/SDL.h>
#include <iostream>
#include <stdexcept>
#include "diagnostics.h"
// Optional live verification drives SDL's virtual hardware through the real
// event loop.
class LiveChecks {
  racer::Diagnostics *diagnostics = nullptr;
  int stage = 0;
  SDL_JoystickID id = 0;
  SDL_Joystick *joystick = nullptr;
  void require(bool ok, const char *message) {
    if (!ok) {
      if (diagnostics) diagnostics->event("check_failed", {{"check", std::string(message).starts_with("live") || std::string(message).starts_with("background") || std::string(message).starts_with("pause") ? message : "device_api"}, {"stage", stage}});
      throw std::runtime_error(message);
    }
  }
  void key(SDL_Keycode code) {
    SDL_Event e{};
    e.type = SDL_EVENT_KEY_DOWN;
    e.key.key = code;
    SDL_PushEvent(&e);
  }
  void focus(Uint32 type) {
    SDL_Event e{};
    e.type = type;
    SDL_PushEvent(&e);
  }

public:
  explicit LiveChecks(racer::Diagnostics *sink = nullptr) : diagnostics(sink) {}
  bool complete() const { return stage == 18; }
  void update(double t, const racer::Car &car, bool paused) {
    switch (stage) {
    case 0:
      if (t < .2)
        return;
      {
        SDL_VirtualJoystickDesc d{};
        SDL_INIT_INTERFACE(&d);
        d.type = SDL_JOYSTICK_TYPE_GAMEPAD;
        d.naxes = SDL_GAMEPAD_AXIS_COUNT;
        d.nbuttons = SDL_GAMEPAD_BUTTON_COUNT;
        d.axis_mask = (1 << d.naxes) - 1;
        d.button_mask = (1 << d.nbuttons) - 1;
        d.name = "Racer live checks";
        id = SDL_AttachVirtualJoystick(&d);
        require(id != 0, SDL_GetError());
        joystick = SDL_OpenJoystick(id);
        require(joystick, SDL_GetError());
        SDL_SetJoystickVirtualAxis(joystick, SDL_GAMEPAD_AXIS_LEFT_TRIGGER,
                                   -32768);
        SDL_SetJoystickVirtualAxis(joystick, SDL_GAMEPAD_AXIS_RIGHT_TRIGGER,
                                   -32768);
      }
      break;
    case 1:
      if (t < .4)
        return;
      SDL_SetJoystickVirtualAxis(joystick, SDL_GAMEPAD_AXIS_RIGHT_TRIGGER,
                                 32767);
      break;
    case 2:
      if (t < 1.2)
        return;
      require(car.speed > 1, "live analog drive failed");
      SDL_SetJoystickVirtualAxis(joystick, SDL_GAMEPAD_AXIS_RIGHT_TRIGGER,
                                 -32768);
      SDL_SetJoystickVirtualButton(joystick, SDL_GAMEPAD_BUTTON_NORTH, true);
      break;
    case 3:
      if (t < 1.4)
        return;
      require(car.speed == 0 && car.x == 0 && car.z == 0, "live reset failed");
      SDL_SetJoystickVirtualButton(joystick, SDL_GAMEPAD_BUTTON_NORTH, false);
      break;
    case 4:
      if (t < 1.6)
        return;
      key(SDLK_ESCAPE);
      break;
    case 5:
      if (t < 1.8)
        return;
      require(paused, "pause before stale-input check failed");
      SDL_SetJoystickVirtualAxis(joystick, SDL_GAMEPAD_AXIS_RIGHT_TRIGGER,
                                 32767);
      key(SDLK_RETURN);
      break;
    case 6:
      if (t < 2.0)
        return;
      require(!paused, "held-trigger menu resume failed");
      require(car.speed == 0, "stale trigger applied on menu resume");
      SDL_SetJoystickVirtualAxis(joystick, SDL_GAMEPAD_AXIS_RIGHT_TRIGGER,
                                 -32768);
      focus(SDL_EVENT_WINDOW_FOCUS_LOST);
      break;
    case 7:
      if (t < 2.2)
        return;
      require(paused, "background pause failed");
      SDL_SetJoystickVirtualButton(joystick, SDL_GAMEPAD_BUTTON_START, true);
      break;
    case 8:
      if (t < 2.4)
        return;
      require(paused, "background Start resumed play");
      SDL_SetJoystickVirtualButton(joystick, SDL_GAMEPAD_BUTTON_START, false);
      key(SDLK_ESCAPE);
      break;
    case 9:
      if (t < 2.6)
        return;
      require(paused, "background Escape resumed play");
      focus(SDL_EVENT_WINDOW_FOCUS_GAINED);
      key(SDLK_RETURN);
      break;
    case 10:
      if (t < 2.8)
        return;
      SDL_SetJoystickVirtualAxis(joystick, SDL_GAMEPAD_AXIS_RIGHT_TRIGGER,
                                 16384);
      break;
    case 11:
      if (t < 3.4)
        return;
      require(car.speed > 0, "live restart failed");
      SDL_DetachVirtualJoystick(id);
      SDL_CloseJoystick(joystick);
      joystick = nullptr;
      break;
    case 12:
      if (t < 3.6)
        return;
      require(paused, "disconnect did not pause");
      focus(SDL_EVENT_WINDOW_FOCUS_LOST);
      break;
    case 13:
      if (t < 3.8)
        return;
      require(paused, "focus loss did not pause");
      focus(SDL_EVENT_WINDOW_FOCUS_GAINED);
      key(SDLK_ESCAPE);
      break;
    case 14:
      if (t < 4.0)
        return;
      require(!paused, "escape resume failed");
      focus(SDL_EVENT_WINDOW_FOCUS_LOST);
      break;
    case 15:
      if (t < 4.2)
        return;
      require(paused, "second focus loss failed");
      focus(SDL_EVENT_WINDOW_FOCUS_GAINED);
      key(SDLK_RETURN);
      break;
    case 16:
      if (t < 4.4)
        return;
      require(!paused, "menu resume failed");
      key(SDLK_ESCAPE);
      break;
    case 17:
      if (t < 4.6)
        return;
      require(paused, "escape pause failed");
      key(SDLK_DOWN);
      key(SDLK_RETURN);
      std::cout << "PASS: live SDL drive, reset, disconnect pause, focus "
                   "pause, held-trigger resume, background resume rejection and Quit selection\n";
      break;
    default:
      return;
    }
    ++stage;
  }
};
