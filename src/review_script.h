#pragma once
// Explicit opt-in native evidence driver. Menu actions pass through SDL events;
// benchmarks use the ordinary simulation and persistence paths.
#include "play_flow.h"
#include <SDL3/SDL.h>
#include <fstream>
#include <cmath>
#include <array>
#include <iostream>
#include <sstream>
#include <stdexcept>
struct ReviewScript {
  struct InvalidKey : std::runtime_error {
    InvalidKey() : std::runtime_error("Unknown review key") {}
  };
  std::vector<std::string> commands;
  size_t cursor = 0;
  double ready = 1;
  std::string capture;
  bool driveCourse = false;
  std::optional<racer::Input> vehicleInput;
  std::optional<std::array<int,2>> windowSize;
  static SDL_Keycode keyCode(const std::string &arg) {
    if (arg == "accept") return SDLK_RETURN;
    if (arg == "back") return SDLK_ESCAPE;
    if (arg == "right") return SDLK_RIGHT;
    if (arg == "left") return SDLK_LEFT;
    if (arg == "up") return SDLK_UP;
    if (arg == "down") return SDLK_DOWN;
    if (arg == "reset") return SDLK_R;
    throw InvalidKey();
  }
  explicit ReviewScript(const std::string &path) {
    if (path.empty())
      return;
    std::ifstream file(path);
    if (!file)
      throw std::runtime_error("Cannot read review script");
    for (std::string line; std::getline(file, line);)
      if (!line.empty() && line[0] != '#')
        commands.push_back(line);
  }
  void key(SDL_Keycode code) {
    SDL_Event e{};
    e.type = SDL_EVENT_KEY_DOWN;
    e.key.key = code;
    SDL_PushEvent(&e);
    e.type = SDL_EVENT_KEY_UP;
    SDL_PushEvent(&e);
  }
  void update(double t, const racer::PlayFlow &f) {
    if (cursor == commands.size() || t < ready)
      return;
    // Only the opt-in evidence driver supplies synthetic focus events. This
    // lets a bounded capture finish without taking the user's desktop focus.
    // Normal play and the separate focus-loss checks never enter this path.
    if (!f.focus) {
      std::cout << "REVIEW: synthetic focus gained at command " << cursor
                << std::endl;
      SDL_Event e{};
      e.type = SDL_EVENT_WINDOW_FOCUS_GAINED;
      SDL_PushEvent(&e);
      ready = t + .15;
      return;
    }
    std::istringstream in(commands[cursor]);
    std::string op, arg;
    in >> op >> arg;
    if ((op == "result" || op == "running" || op == "gate") &&
        f.screen == racer::Screen::Pause) {
      std::cout << "REVIEW: resume interrupted wait at command " << cursor
                << std::endl;
      key(SDLK_ESCAPE);
      ready = t + .15;
      return;
    }
    if (op == "select") {
      if (f.menu != std::stoi(arg)) {
        key(SDLK_DOWN);
        ready = t + .1;
        return;
      }
    } else if (op == "key") {
      key(keyCode(arg));
    } else if (op == "result") {
      if (f.screen != racer::Screen::Results)
        return;
    } else if (op == "running") {
      if (f.session.phase() != racer::TestPhase::Running ||
          f.session.elapsed() < std::stod(arg))
        return;
    } else if (op == "gate") {
      if (f.session.nextGate() + 1 < size_t(std::stoi(arg)))
        return;
    } else if (op == "drive-course") {
      driveCourse = arg == "on";
    } else if (op == "drive-input") {
      if (arg=="off") vehicleInput.reset();
      else {
        racer::Input value;value.throttle=std::stod(arg);
        if (!(in>>value.brake>>value.steer) || !std::isfinite(value.throttle) ||
            !std::isfinite(value.brake) || !std::isfinite(value.steer) ||
            value.throttle<0 || value.throttle>1 || value.brake<0 || value.brake>1 || std::abs(value.steer)>1)
          throw std::runtime_error("Invalid synthetic vehicle input");
        vehicleInput=value;
      }
    } else if (op == "assert") {
      const auto expected = commands[cursor].substr(7);
      bool found = false;
      for (const auto &line : f.lines())
        if (line.find(expected) != std::string::npos)
          found = true;
      if (!found)
        throw std::runtime_error("Review assertion: " + expected);
    } else if (op == "capture") {
      capture = arg;
      std::cout << "CAPTURE " << arg << '\n';
      for (const auto &line : f.lines())
        std::cout << line << '\n';
    } else if (op == "resize") {
      const int width=std::stoi(arg);int height;std::string trailing;
      if(!(in>>height)||in>>trailing||width<320||height<240||width>4096||height>2160)
        throw std::runtime_error("Invalid review window size");
      windowSize=std::array{width,height};
    } else if (op == "wait") {
      ready = t + std::stod(arg);
      ++cursor;
      return;
    } else if (op == "quit") {
      SDL_Event e{};
      e.type = SDL_EVENT_QUIT;
      SDL_PushEvent(&e);
    } else
      throw std::runtime_error("Unknown review command: " + op);
    ++cursor;
    ready = t + .15;
  }
};
