#include "career_flow.h"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <sys/stat.h>
#include <unistd.h>
using namespace racer;
void check(bool v, const char *m) {
  if (!v)
    throw std::runtime_error(m);
}
std::string bytes(const std::filesystem::path &p) {
  std::ifstream in(p);
  return {std::istreambuf_iterator<char>(in), {}};
}
void finishRoute(CareerFlow &f) {
  for (std::size_t i = 0; i < 5; ++i)
    check(f.checkpoint(i), "ordered progress");
}
int main() {
  char name[] = "/tmp/racer-career-flow-XXXXXX";
  auto dir = mkdtemp(name);
  if (!dir)
    return 1;
  std::filesystem::path root(dir);
  try {
    auto profile = root / "profile";
    {
      CareerFlow f(profile);
      check(!f.state().discovered("grid-intro"), "initial undiscovered");
      f.updatePosition(1000, 1000);
      check(!f.canStart(0, 0), "not discovered blocked");
      f.updatePosition(0, 0);
      check(f.state().discovered("grid-intro") && f.canStart(0, 0) &&
                !f.canStart(26, 0),
            "near/far");
      check(f.action(2, 0, 0, 0) == CareerBoardResult::StartHandling &&
                !f.state().running(),
            "request does not inject/start");
      check(f.start(), "domain starts");
      check(!f.checkpoint(1) && f.checkpoint(0) && !f.checkpoint(0),
            "order duplicates");
      f.cancel();
      check(f.state().credits() == 0, "cancel no reward");
      check(f.start(), "restart attempt");
      finishRoute(f);
      auto done = f.finish(true, 75);
      check(done.valid && done.reward == 5000 && f.state().credits() == 5000,
            "reward");
      check(!f.finish(true, 75).valid && f.state().credits() == 5000,
            "idempotent finish");
      f.action(0, 1, 0, 0);
      f.action(1, 0, 0, 0);
      check(f.selectedMarker().id == "club-loop" && !f.canStart(100, 100),
            "locked before discovery/ownership");
      f.updatePosition(100, 100);
      check(!f.canStart(100, 100), "touring locked");
      f.action(3, 0, 100, 100);
      check(f.state().owns("touring") && f.state().credits() == 2000 &&
                f.canStart(100, 100),
            "purchase eligibility");
      f.action(3, 0, 100, 100);
      check(f.state().credits() == 2000, "no doublecharge");
      check(f.action(2, 0, 100, 100) == CareerBoardResult::StartHandling &&
                f.start(),
            "club start");
      finishRoute(f);
      check(f.finish(false, 75).reward == 0 && f.state().credits() == 2000,
            "invalid no reward");
      check(f.start(), "validretry");
      finishRoute(f);
      check(f.finish(true, 75).reward == 1000 && f.state().credits() == 3000,
            "club first reward");
    }
    {
      CareerFlow f(profile);
      check(f.state().credits() == 3000 && f.state().owns("touring") &&
                f.state().completed("club-loop"),
            "restart state");
      f.updatePosition(100, 100);
      check(f.start(), "repeat start");
      finishRoute(f);
      check(f.finish(true, 80).valid && f.state().credits() == 3000,
            "repeat no payout");
    }
    {
      CareerFlow retry(root / "retry");
      check(!retry.restart(), "no restart before process starts an event");
      retry.updatePosition(0, 0);
      retry.action(2, 0, 0, 0);
      check(retry.start() && !retry.restart(), "running retry rejected");
      finishRoute(retry);
      check(retry.finish(true, 75).valid, "finish enables retry");
      retry.updatePosition(400, 400);
      check(!retry.start() && retry.restart(),
            "explicit retry bypasses proximity only after finish");
      finishRoute(retry);
      check(!retry.finish(false, 75).valid && retry.restart(),
            "invalid result permits fresh retry");
      retry.cancel();
      check(!retry.restart(), "explicit cancel clears retry permission");
      CareerFlow loaded(root / "retry");
      check(!loaded.restart(), "restart permission not restored from disk");
    }
    auto malformed = root / "bad";
    {
      std::ofstream out(malformed.string() + ".career");
      out << "not career";
    }
    {
      CareerFlow f(malformed);
      f.updatePosition(0, 0);
      check(!f.store().writable() && !f.retrySave(),
            "semantic rejection disableswrites");
      check(bytes(malformed.string() + ".career") == "not career",
            "malformed preserved");
    }
    auto locked = root / "locked";
    std::filesystem::create_directory(locked);
    auto lockedProfile = locked / "profile";
    {
      CareerFlow f(lockedProfile);
      f.updatePosition(0, 0);
      auto prior = bytes(lockedProfile.string() + ".career");
      check(chmod(locked.c_str(), 0500) == 0, "lock fixture");
      f.action(2, 0, 0, 0);
      check(f.start(), "memory start underfailure");
      finishRoute(f);
      check(f.finish(true, 70).reward == 5000, "valid result preserved");
      check(f.store().outcome().status == DocumentStatus::Failed &&
                bytes(lockedProfile.string() + ".career") == prior,
            "lastgood preserved");
      check(chmod(locked.c_str(), 0700) == 0, "unlock fixture");
      check(f.retrySave(), "retry succeeds");
    }
    std::filesystem::remove_all(root);
    std::cout << "PASS: event discovery/proximity/requests, ordered progress, "
                 "locks/ownership/rewards/restart, malformed preservation and "
                 "real save failure/retry\n";
    return 0;
  } catch (const std::exception &e) {
    chmod((root / "locked").c_str(), 0700);
    std::filesystem::remove_all(root);
    std::cerr << e.what() << '\n';
    return 1;
  }
}
