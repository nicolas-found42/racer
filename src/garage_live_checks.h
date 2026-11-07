#pragma once
#include "play_flow.h"
#include <SDL3/SDL.h>
#include <cmath>
#include <iostream>
#include <stdexcept>
#include "diagnostics.h"
class GarageLiveChecks {
  racer::Diagnostics *diagnostics = nullptr;
  bool usePad, done = false;
  int stage = 0;
  SDL_JoystickID id = 0;
  SDL_Joystick *joystick = nullptr;
  int pressed = -1;
  double next = .15, mark = 0, frozen = 0;
  std::size_t savedCount = 0;
  void require(bool v, const char *m) {
    if (!v) {
      if (diagnostics) diagnostics->event("check_failed", {{"check", std::string(m).starts_with("garage") ? m : "device_api"}, {"stage", stage}});
      throw std::runtime_error(m);
    }
  }
  static void event(Uint32 type) {
    SDL_Event e{};
    e.type = type;
    SDL_PushEvent(&e);
  }
  void send(racer::Action a) {
    SDL_Keycode key = SDLK_RETURN;
    SDL_GamepadButton button = SDL_GAMEPAD_BUTTON_SOUTH;
    using A = racer::Action;
    switch (a) {
    case A::Up:
      key = SDLK_UP;
      button = SDL_GAMEPAD_BUTTON_DPAD_UP;
      break;
    case A::Down:
      key = SDLK_DOWN;
      button = SDL_GAMEPAD_BUTTON_DPAD_DOWN;
      break;
    case A::Left:
      key = SDLK_LEFT;
      button = SDL_GAMEPAD_BUTTON_DPAD_LEFT;
      break;
    case A::Right:
      key = SDLK_RIGHT;
      button = SDL_GAMEPAD_BUTTON_DPAD_RIGHT;
      break;
    case A::Back:
      key = SDLK_ESCAPE;
      button = SDL_GAMEPAD_BUTTON_EAST;
      break;
    case A::Pause:
      key = SDLK_ESCAPE;
      button = SDL_GAMEPAD_BUTTON_START;
      break;
    default:
      break;
    }
    if (usePad && joystick) {
      require(SDL_SetJoystickVirtualButton(joystick, button, true),
              SDL_GetError());
      pressed = button;
    } else {
      SDL_Event e{};
      e.type = SDL_EVENT_KEY_DOWN;
      e.key.key = key;
      SDL_PushEvent(&e);
    }
  }
  bool select(const racer::PlayFlow &f, int target) {
    if (f.menu != target) {
      send(racer::Action::Down);
      return false;
    }
    return true;
  }
  void attach() {
    SDL_VirtualJoystickDesc d{};
    SDL_INIT_INTERFACE(&d);
    d.type = SDL_JOYSTICK_TYPE_GAMEPAD;
    d.naxes = SDL_GAMEPAD_AXIS_COUNT;
    d.nbuttons = SDL_GAMEPAD_BUTTON_COUNT;
    d.axis_mask = (1 << d.naxes) - 1;
    d.button_mask = (1 << d.nbuttons) - 1;
    d.name = "Racer garage live checks";
    id = SDL_AttachVirtualJoystick(&d);
    require(id != 0, SDL_GetError());
    joystick = SDL_OpenJoystick(id);
    require(joystick, SDL_GetError());
    SDL_SetJoystickVirtualAxis(joystick, SDL_GAMEPAD_AXIS_LEFT_TRIGGER, -32768);
    SDL_SetJoystickVirtualAxis(joystick, SDL_GAMEPAD_AXIS_RIGHT_TRIGGER,
                               -32768);
  }

public:
  explicit GarageLiveChecks(bool gamepad, racer::Diagnostics *sink = nullptr) : diagnostics(sink), usePad(gamepad) {}
  void close() {
    if (joystick) {
      SDL_DetachVirtualJoystick(id);
      SDL_CloseJoystick(joystick);
      joystick = nullptr;
    }
  }
  ~GarageLiveChecks() { close(); }
  bool complete() const { return done; }
  void update(double t, const racer::PlayFlow &f, SDL_Gamepad *pad) {
    using S = racer::Screen;
    using A = racer::Action;
    if (done || t < next)
      return;
    next = t + .07;
    if (pressed >= 0) {
      SDL_SetJoystickVirtualButton(joystick, pressed, false);
      pressed = -1;
      return;
    }
    switch (stage) {
    case 0:
      if (usePad)
        attach();
      ++stage;
      return;
    case 1:
      if (usePad && !pad)
        return;
      require(f.screen == S::Drive, "garage check initial drive");
      send(A::Pause);
      break;
    case 2:
      require(f.screen == S::Pause, "garage check pause");
      if (!select(f, 2))
        return;
      send(A::Accept);
      break;
    case 3:
      require(f.screen == S::Garage, "garage check enter");
      if (!select(f, 1))
        return;
      send(A::Right);
      break;
    case 4:
      require(f.profile.garage.dirty(), "garage live edit draft");
      if (!select(f, 4))
        return;
      send(A::Accept);
      break;
    case 5:
      require(
          !f.profile.garage.dirty() &&
              f.profile.garage.applied[f.profile.garage.selected].acceleration >
                  1,
          "garage live apply");
      if (!select(f, 8))
        return;
      send(A::Accept);
      break;
    case 6:
      require(f.screen == S::Tests, "garage live tests menu");
      if (usePad)
        SDL_SetJoystickVirtualAxis(joystick, SDL_GAMEPAD_AXIS_RIGHT_TRIGGER,
                                   32767);
      send(A::Accept);
      mark = t;
      break;
    case 7:
      require(f.screen == S::Drive && f.session.active(),
              "garage live benchmark start");
      if (t - mark < .25)
        return;
      if (usePad) {
        require(f.rearming && f.sim.car.speed == 0 &&
                    f.session.countdownRemaining() == 3,
                "held trigger advanced benchmark");
        SDL_SetJoystickVirtualAxis(joystick, SDL_GAMEPAD_AXIS_RIGHT_TRIGGER,
                                   -32768);
      }
      mark = t;
      break;
    case 8:
      if (f.screen != S::Results) {
        require(t - mark < 15, "garage live benchmark timeout");
        return;
      }
      require(f.session.result().valid, "garage live result invalid");
      require(f.session.result().setup ==
                  f.profile.garage.applied[f.profile.garage.selected],
              "garage live snapshot");
      require(!f.profile.records.empty(), "garage live result not recorded");
      {
        racer::Profile loaded;
        racer::ProfileStore restart(f.store.path());
        require(restart.load(loaded) && loaded.records == f.profile.records &&
                    loaded.garage.applied == f.profile.garage.applied,
                "garage live restart/load");
      }
      savedCount = f.profile.records.size();
      if (!select(f, 3))
        return;
      send(A::Accept);
      break;
    case 9:
      require(f.screen == S::Tests, "garage live compare menu");
      {
        bool found = false;
        for (const auto &line : f.lines())
          if (line.find("acceleration:") != std::string::npos &&
              line.find(" s") != std::string::npos)
            found = true;
        require(found, "garage live comparison absent");
      }
      send(A::Accept);
      mark = t;
      break;
    case 10:
      require(f.session.active(), "garage live retry failed");
      if (t - mark < .2)
        return;
      frozen = f.session.countdownRemaining();
      event(SDL_EVENT_WINDOW_FOCUS_LOST);
      mark = t;
      break;
    case 11:
      require(f.screen == S::Pause && !f.focus, "garage live focus pause");
      if (t - mark < .2)
        return;
      require(std::abs(f.session.countdownRemaining() - frozen) < .1,
              "focus pause accumulated simulation time");
      send(A::Accept);
      break;
    case 12:
      require(f.screen == S::Pause, "background menu resumed test");
      event(SDL_EVENT_WINDOW_FOCUS_GAINED);
      break;
    case 13:
      send(A::Accept);
      break;
    case 14:
      require(f.screen == S::Drive, "garage live focus resume");
      if (usePad) {
        SDL_DetachVirtualJoystick(id);
        SDL_CloseJoystick(joystick);
        joystick = nullptr;
      } else
        send(A::Pause);
      break;
    case 15:
      require(f.screen == S::Pause, "garage live disconnect pause");
      if (!select(f, 3))
        return;
      send(A::Accept);
      break;
    case 16:
      require(f.screen == S::Results && !f.session.result().valid &&
                  f.profile.records.size() == savedCount,
              "cancelled retry saved valid record");
      if (!select(f, 1))
        return;
      send(A::Accept);
      break;
    case 17:
      require(f.screen == S::Garage && f.sim.car.speed == 0,
              "garage live return");
      std::cout << "PASS: live " << (usePad ? "virtual gamepad" : "keyboard")
                << " garage edit/apply, automatic test, comparison, persisted "
                   "restart/load, retry/cancel, focus freeze/resume"
                << (usePad ? ", held-trigger rearm and disconnect pause" : "")
                << '\n';
      done = true;
      event(SDL_EVENT_QUIT);
      return;
    default:
      return;
    }
    ++stage;
  }
};
