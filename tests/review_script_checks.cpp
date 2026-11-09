#include "review_script.h"
#include <iostream>

int main() {
  bool okay = true;
  for (const auto &[name, expected] : {
           std::pair{"accept", SDLK_RETURN}, std::pair{"back", SDLK_ESCAPE},
           std::pair{"right", SDLK_RIGHT}, std::pair{"left", SDLK_LEFT},
           std::pair{"up", SDLK_UP}, std::pair{"down", SDLK_DOWN},
           std::pair{"reset", SDLK_R}, std::pair{"accent", SDLK_H}})
    okay &= ReviewScript::keyCode(name) == expected;
  // The actual failed reload used "confirm" and silently selected Down.
  // Unsupported input must fail before an SDL event can be submitted.
  for (const char *invalid : {"confirm", "", "DOWN", "accept extra"}) {
    bool rejected = false;
    try { ReviewScript::keyCode(invalid); }
    catch (const std::runtime_error &) { rejected = true; }
    okay &= rejected;
  }
  std::cout << (okay ? "PASS" : "FAIL")
            << ": supported review keys preserved; unknown keys rejected\n";
  return okay ? 0 : 1;
}
