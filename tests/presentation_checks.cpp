#include "play_flow.h"
#include "presentation.h"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <unistd.h>
using namespace racer;
void check(bool v, const char *why) {
  if (!v)
    throw std::runtime_error(why);
}
bool has(const PlayFlow &f, const std::string &text) {
  for (const auto &line : f.lines())
    if (line.find(text) != std::string::npos)
      return true;
  return false;
}
void choose(PlayFlow &f, int n) {
  for (int i = 0; f.menu != n && i < 12; ++i)
    f.action(Action::Down);
  f.action(Action::Accept);
}
void finish(PlayFlow &f) {
  f.rearming = false;
  for (int i = 0; f.session.active() && i < 6000; ++i)
    f.tick({});
  check(f.session.result().valid, "real automatic result");
}
std::string bytes(const std::filesystem::path &p) {
  std::ifstream in(p);
  return {std::istreambuf_iterator<char>(in), {}};
}
int main() {
  auto root = std::filesystem::temp_directory_path() /
              ("racer-presentation-" + std::to_string(getpid()));
  try {
    std::filesystem::create_directories(root);
    PlayFlow f((root / "profile").string());
    f.garage();
    check(has(f, "no profile saved yet") && has(f, "No pending"), "new status");
    choose(f, 4);
    check(has(f, "Applied A: saved"), "save status");
    auto saved = bytes(f.store.path());
    choose(f, 1);
    f.action(Action::Right);
    check(has(f, "DRAFT NOT APPLIED") && has(f, "excludes current draft"),
          "draft after save truth");
    check(bytes(f.store.path()) == saved, "draft does not save");
    choose(f, 8);
    check(has(f, "DRAFT NOT APPLIED"), "pending truth");
    choose(f, 2);
    check(f.profile.garage.dirty(), "keep editing");
    choose(f, 5);
    check(!f.profile.garage.dirty(), "discard");
    f.startTest(TestKind::Acceleration);
    check(has(f, "COUNTDOWN") && has(f, "frozen setup A"),
          "countdown identity");
    f.rearming = false;
    for (int i = 0; i < 361; ++i)
      f.tick({});
    check(has(f, "ACCELERATION MEASUREMENT") && !has(f, "COUNTDOWN"),
          "running phase");
    finish(f);
    check(has(f, "NEW BEST") && has(f, "Best records saved"),
          "valid first result");
    const auto snapshot = f.session.result();
    choose(f, 0);
    finish(f);
    check(has(f, "best unchanged") && has(f, "+0.000 s equal to prior"),
          "valid non-best and named delta");
    choose(f, 3);
    check(has(f, "matching setup, recorded as A") && has(f, "A [NEXT]"),
          "same-value provenance");
    choose(f, 3);
    f.action(Action::Right);
    choose(f, 1);
    for (int i = 0; i < 4; ++i)
      f.action(Action::Right);
    choose(f, 4);
    f.startTest(TestKind::Acceleration);
    finish(f);
    check(std::abs(f.session.result().seconds - 6.6666667) < .009,
          "tuned measurement unchanged");
    choose(f, 3);
    check(has(f, "B [NEXT]") && has(f, "-1.333 s better than A"),
          "active B and cross-setup delta");
    choose(f, 3);
    choose(f, 0);
    f.action(Action::Right);
    choose(f, 1);
    f.action(Action::Right);
    choose(f, 4);
    choose(f, 8);
    check(has(f, "No comparable result"), "changed C missing record");
    check(snapshot.setup.acceleration == 1, "immutable captured result");
    StoredResult query = f.profile.records.front();
    query.testRevision++;
    check(!f.profile.best(query), "revision mismatch cannot compare");
    query = f.profile.records.front();
    query.modelRevision++;
    check(!f.profile.best(query), "model mismatch cannot compare");
    f.startTest(TestKind::Braking);
    f.rearming = false;
    for (int i = 0; i < 361; ++i)
      f.tick({});
    check(has(f, "LEAD-IN"), "braking lead-in");
    while (!f.session.measuringBraking())
      f.tick({});
    check(has(f, "BRAKING MEASUREMENT"), "braking measuring");
    f.action(Action::Reset);
    check(has(f, "ATTEMPT NOT SAVED") && !has(f, "Best records saved"),
          "invalid save truth");
    f.garage();
    auto good = bytes(f.store.path());
    std::filesystem::permissions(root, std::filesystem::perms::owner_read |
                                           std::filesystem::perms::owner_exec);
    choose(f, 1);
    f.action(Action::Right);
    choose(f, 4);
    check(has(f, "UNSAVED: applied for driving") &&
              bytes(f.store.path()) == good,
          "actual unwritable apply preserves bytes");
    f.startTest(TestKind::Acceleration);
    finish(f);
    check(f.session.result().valid && has(f, "NOT saved to disk"),
          "result remains valid on write failure");
    std::filesystem::permissions(root, std::filesystem::perms::owner_all);
    f.garage();
    choose(f, 9);
    check(has(f, "saved to disk") && !has(f, "UNSAVED"),
          "retry clears only on success");
    PlayFlow restart(f.store.path().string());
    restart.garage();
    check(has(restart, "loaded from disk") &&
              restart.profile.records == f.profile.records,
          "restart persistence");
    for (const auto &bad : {"junk", "RACER_PROFILE 99\n"}) {
      auto path = root / "bad";
      std::ofstream(path) << bad;
      PlayFlow broken(path.string());
      broken.garage();
      choose(broken, 4);
      check(has(broken, "saving disabled") &&
                has(broken, "restart to recover") && bytes(path) == bad,
            "malformed preserved and recovery visible");
    }
    auto cue = courseGuidance({100, 100, 1, 0, 18}, {0, 100, 0, 0, 0, 1});
    check(cue.turn == "> RIGHT" && cue.distance == 100 &&
              cue.crossing == "EAST",
          "offscreen right cue");
    cue = courseGuidance({0, 200, -1, 0, 18}, {100, 200, 0, 0, 0, 1});
    check(cue.turn == "< LEFT", "left cue");
    cue = courseGuidance({0, 100, 0, 1, 18}, {20, 120, 0, 0, 0, 1});
    check(cue.returnToApproach, "missed gate approach guidance");
    std::filesystem::remove_all(root);
    std::cout
        << "PASS: presentation status matrix, real save failures/recovery, "
           "provenance/deltas, phases and offscreen/missed guidance\n";
  } catch (const std::exception &e) {
    std::filesystem::permissions(root, std::filesystem::perms::owner_all);
    std::cerr << e.what() << '\n';
    return 1;
  }
}
