#include "career.h"
#include <iostream>
#include <limits>
#include <stdexcept>
using namespace racer;
void check(bool v, const char *m) {
  if (!v)
    throw std::runtime_error(m);
}
Career sample() {
  return Career({{"intro", {}, "prototype", 2, 100},
                 {"final", {"intro"}, "sport", 1, 200}},
                {{"prototype", 0}, {"sport", 80}});
}
CareerFinish run(Career &c, const std::string &id, double time) {
  check(c.select(id) && c.start(), "start");
  for (std::size_t i = 0; i < 2; ++i)
    check(c.checkpoint(i), "progress");
  return c.finish(true, time);
}
int main() {
  try {
    auto c = sample();
    check(!c.select("intro"), "undiscovered blocked");
    check(!c.discover("unknown"), "unknown discovery");
    check(c.discover("intro") && c.discover("final"), "discovery");
    check(!c.eligible("final"), "prerequisite blocked");
    check(c.select("intro") && c.start(), "launch");
    check(!c.checkpoint(1) && c.nextCheckpoint() == 0, "out of order ignored");
    check(c.checkpoint(0) && !c.checkpoint(0), "duplicate ignored");
    check(!c.select("final") && !c.buy("sport"), "running transitions blocked");
    check(!c.finish(true, 5).valid && c.credits() == 0 && !c.completed("intro"),
          "partial no reward");
    auto first = run(c, "intro", 10);
    check(first.valid && first.firstCompletion && first.newBest &&
              first.reward == 100 && c.credits() == 100,
          "first completion");
    check(!c.finish(true, 1).valid && c.credits() == 100,
          "duplicate finish no reward");
    auto again = run(c, "intro", 12);
    check(again.valid && !again.firstCompletion && !again.newBest &&
              again.reward == 0 && c.bestSeconds("intro") == 10,
          "valid slower no reward");
    auto faster = run(c, "intro", 9);
    check(faster.valid && faster.newBest && c.credits() == 100,
          "better independent");
    check(!c.eligible("final"), "vehicle ownership required");
    check(c.buy("sport") && c.credits() == 20 && !c.buy("sport"),
          "purchase once");
    check(c.eligible("final") && c.select("final") && c.start(),
          "unlocked event");
    check(c.checkpoint(0), "final progress");
    auto saved = c.serialize();
    auto restored = sample();
    check(restored.restore(saved) && !restored.running() &&
              restored.nextCheckpoint() == 0,
          "restart cancels active");
    check(!restored.finish(true, 1).valid && restored.credits() == 20,
          "restart cannot finish partial");
    check(restored.start() && restored.checkpoint(0), "restart fresh");
    check(restored.finish(true, 20).reward == 200 && restored.credits() == 220,
          "reward after restart");
    auto saved2 = restored.serialize();
    auto round = sample();
    check(round.restore(saved2) && round.serialize() == saved2,
          "stable roundtrip");
    check(round.start() && round.checkpoint(0) &&
              round.finish(true, 21).reward == 0 && round.credits() == 220,
          "durable idempotence");
    auto before = round.serialize();
    for (auto bad :
         {std::string("RACER_CAREER 99"), saved2 + "extra",
          saved2.substr(0, saved2.size() / 2), std::string(65537, 'x')}) {
      check(!round.restore(bad) && round.serialize() == before,
            "transactional invalid restore");
    }
    std::vector<std::string> corrupt;
    for (const auto &replacement :
         std::vector<std::pair<std::string, std::string>>{
             {"\n220\n", "\n-1\n"},
             {"\n220\n", "\n1000000000001\n"},
             {"prototype\nsport", "prototype\nprototype"},
             {"RACER_CAREER 1 1", "RACER_CAREER 1 other"}}) {
      auto text = saved2;
      auto position = text.find(replacement.first);
      check(position != std::string::npos, "corrupt fixture");
      text.replace(position, replacement.first.size(), replacement.second);
      corrupt.push_back(text);
    }
    for (const auto &text : corrupt)
      check(!round.restore(text) && round.serialize() == before,
            "invalid money/duplicates/revision transactional");
    auto invalid = sample();
    invalid.discover("intro");
    invalid.select("intro");
    invalid.start();
    invalid.checkpoint(0);
    invalid.checkpoint(1);
    check(!invalid.finish(false, 5).valid && invalid.credits() == 0,
          "invalid no reward");
    invalid.start();
    invalid.checkpoint(0);
    invalid.checkpoint(1);
    check(!invalid.finish(true, std::numeric_limits<double>::infinity()).valid,
          "nonfinite rejected");
    invalid.start();
    invalid.checkpoint(0);
    invalid.cancel();
    check(!invalid.finish(true, 5).valid && invalid.credits() == 0,
          "cancel no reward");
    Career overflow({{"a", {}, "prototype", 1, Career::maxCredits},
                     {"b", {}, "prototype", 1, 1}},
                    {{"prototype", 0}});
    overflow.discover("a");
    overflow.discover("b");
    overflow.select("a");
    overflow.start();
    overflow.checkpoint(0);
    check(overflow.finish(true, 1).reward == Career::maxCredits, "max reward");
    overflow.select("b");
    overflow.start();
    overflow.checkpoint(0);
    check(!overflow.finish(true, 1).valid && !overflow.completed("b") &&
              overflow.credits() == Career::maxCredits,
          "overflow atomic rejection");
    bool rejected = false;
    try {
      Career cycle({{"a", {"b"}}, {"b", {"a"}}}, {{"prototype", 0}});
    } catch (const std::invalid_argument &) {
      rejected = true;
    }
    check(rejected, "cycle rejected");
    rejected = false;
    try {
      Career reserved({{"-", {}, "prototype", 1, 1}}, {{"prototype", 0}});
    } catch (const std::invalid_argument &) {
      rejected = true;
    }
    check(rejected, "no-selection sentinel rejected as event identifier");
    Career hyphenated({{"city-race", {}, "prototype", 1, 1}},
                      {{"prototype", 0}});
    hyphenated.discover("city-race");
    check(hyphenated.select("city-race"), "ordinary hyphenated ID accepted");
    auto hyphenSave = hyphenated.serialize();
    check(hyphenated.restore(hyphenSave) &&
              hyphenated.selection() == "city-race" &&
              hyphenated.serialize() == hyphenSave,
          "hyphenated selection roundtrips without sentinel ambiguity");
    std::cout << "PASS: discovery/eligibility/progress, idempotent "
                 "rewards/best, purchase, restart, invalid/cancel, strict "
                 "transactional restore and overflow\n";
    return 0;
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
