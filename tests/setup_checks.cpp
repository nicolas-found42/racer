#include "profile.h"
#include <cmath>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <unistd.h>
using namespace racer;
void check(bool yes, const char *message) {
  if (!yes)
    throw std::runtime_error(message);
}
std::string read(const std::filesystem::path &p) {
  std::ifstream f(p);
  return {std::istreambuf_iterator<char>(f), {}};
}
struct RestorePermissions {
  std::filesystem::path path;
  std::filesystem::perms original;
  ~RestorePermissions() {
    std::error_code ignored;
    std::filesystem::permissions(path, original, ignored);
  }
};
int main() {
  auto root = std::filesystem::temp_directory_path() /
              ("racer-profile-check-" + std::to_string(getpid()));
  try {
    GarageState g;
    g.draft.acceleration = 1.1;
    check(g.dirty() && !g.select(1) && g.applied[0].acceleration == 1,
          "dirty slot switch");
    check(g.apply() && g.select(1) && g.draft == VehicleSetup{},
          "apply then switch");
    g.draft.brake = 1.2;
    g.discard();
    check(!g.dirty() && g.draft.brake == 1, "cancel discards");
    g.draft.steering = .8;
    check(g.apply(), "apply valid");
    g.defaults();
    check(g.dirty() && g.applied[1].steering == .8, "defaults stays draft");
    g.draft.acceleration = std::numeric_limits<double>::quiet_NaN();
    check(!g.apply(), "reject nonfinite");
    for (double v : {.79, 1.21, std::numeric_limits<double>::infinity()}) {
      VehicleSetup s;
      s.brake = v;
      check(!s.valid(), "reject range");
    }
    Profile p;
    ProfileStore store(root / "profile.txt");
    check(store.load(p) && p.records.empty(), "missing defaults");
    p.garage.draft.acceleration = 1.1;
    p.garage.apply();
    p.garage.select(2);
    StoredResult result;
    result.testId = "acceleration";
    result.slot = 0;
    result.setup = p.garage.applied[0];
    result.seconds = 7.3;
    check(p.record(result), "record valid");
    result.seconds = 8;
    p.record(result);
    check(p.best(result)->seconds == 7.3, "best retained");
    result.seconds = 7;
    p.record(result);
    check(p.best(result)->seconds == 7, "better replaces");
    check(store.save(p), "save");
    auto good = read(store.path());
    Profile restored;
    ProfileStore restart(store.path());
    check(restart.load(restored) && restored.garage.selected == 2 &&
              restored.garage.applied == p.garage.applied &&
              restored.records == p.records,
          "restart roundtrip");
    restored.garage.applied[0].acceleration = 1.2;
    check(restored.records[0].setup.acceleration == 1.1, "snapshot immutable");
    restored.garage.applied[0].brake = 2;
    check(!restart.save(restored) && read(store.path()) == good,
          "invalid save preserves good");
    const std::string header = "RACER_PROFILE 1\n0\n";
    const std::string setups = "1 1 1\n1 1 1\n1 1 1\n";
    std::vector<std::string> malformedProfiles = {
        "RACER_PROFILE 2\n", "RACER_PROFILE 1\n0\n1 1 1\n", good + "extra",
        "RACER_PROFILE 1\n9\n"};
    for (const char *value : {"nan", "inf", "-inf", "0.79", "1.21"})
      malformedProfiles.push_back(header + value + " 1 1\n1 1 1\n1 1 1\n0\n");
    for (const char *record : {"unknown acceleration 1 1 0 1 1 1 8 100 0",
                               "prototype unknown 1 1 0 1 1 1 8 100 0",
                               "prototype acceleration 2 1 0 1 1 1 8 100 0",
                               "prototype acceleration 1 2 0 1 1 1 8 100 0",
                               "prototype acceleration 1 1 3 1 1 1 8 100 0",
                               "prototype acceleration 1 1 0 1.3 1 1 8 100 0",
                               "prototype acceleration 1 1 0 1 1 1 nan 100 0",
                               "prototype acceleration 1 1 0 1 1 1 8 inf 0",
                               "prototype acceleration 1 1 0 1 1 1 8 100 -1"})
      malformedProfiles.push_back(header + setups + "1\n" + record + "\n");
    for (const std::string &bad : malformedProfiles) {
      {
        std::ofstream f(store.path());
        f << bad;
      }
      Profile candidate;
      candidate.garage.applied[0].brake = 1.1;
      ProfileStore malformed(store.path());
      check(!malformed.load(candidate) && !malformed.writable(),
            "malformed blocked");
      check(candidate.garage.applied[0].brake == 1.1 && !malformed.save(p) &&
                read(store.path()) == bad,
            "malformed original preserved");
    }
    if (geteuid() != 0) {
      const auto readOnlyDir = root / "read-only";
      ProfileStore readOnly(readOnlyDir / "profile.txt");
      check(readOnly.save(p),
            "create existing good profile before write failure");
      const auto lastGood = read(readOnly.path());
      Profile changed = p;
      changed.garage.applied[0].brake = 1.2;
      {
        RestorePermissions restore{
            readOnlyDir, std::filesystem::status(readOnlyDir).permissions()};
        std::filesystem::permissions(readOnlyDir,
                                     std::filesystem::perms::owner_read |
                                         std::filesystem::perms::owner_exec);
        check(!readOnly.save(changed), "read-only parent must reject save");
        check(
            read(readOnly.path()) == lastGood,
            "failed atomic replacement preserves existing good profile bytes");
        check(readOnly.message().find("Unsaved changes") != std::string::npos,
              "read-only save failure reports unsaved changes");
      }
      std::cout << "PASS: read-only directory save failure preserves existing "
                   "good profile byte-for-byte\n";
    } else {
      std::cout << "SKIP: read-only directory permission branch requires "
                   "non-root effective UID\n";
    }
    // A file as the parent is unwritable on all permission levels, including
    // root.
    {
      std::ofstream f(root / "blocked");
      f << "last good";
    }
    ProfileStore blocked(root / "blocked" / "profile");
    check(!blocked.save(p) && read(root / "blocked") == "last good" &&
              blocked.message().find("Unsaved") != std::string::npos,
          "write error visible");
    std::filesystem::remove_all(root);
    std::cout << "PASS: draft/apply/cancel/defaults, dirty switch, validation, "
                 "best attribution, restart, malformed/unsupported and "
                 "failed-save preservation\n";
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    std::filesystem::remove_all(root);
    return 1;
  }
}
