#include "play_flow.h"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <unistd.h>
#include <cstdlib>
#include <new>
// Only this test thread fails allocations; the asynchronous recorder remains normal.
thread_local bool failObserverAllocation = false;
void *operator new(std::size_t size) {
  if (failObserverAllocation) throw std::bad_alloc();
  if (void *p=std::malloc(size ? size : 1)) return p;
  throw std::bad_alloc();
}
void operator delete(void *p) noexcept { std::free(p); }
void operator delete(void *p,std::size_t) noexcept { std::free(p); }
using namespace racer;
void check(bool value, const char *message) {
  if (!value)
    throw std::runtime_error(message);
}
void choose(PlayFlow &f, int item) {
  for (int tries = 0; f.menu != item && tries < 32; ++tries)
    f.action(Action::Down);
  check(f.menu == item, "menu item reachable");
  f.action(Action::Accept);
}
void released(PlayFlow &f) {
  f.rearming = false;
  f.sim.tick({}, 0);
}
void finish(PlayFlow &f) {
  released(f);
  for (int ticks = 0; ticks < 6000 && f.screen == Screen::Drive; ++ticks)
    f.tick({0, 1, 1});
  check(f.screen == Screen::Results && f.session.result().valid,
        "automatic benchmark finishes despite player input");
}
int main() {
  auto root = std::filesystem::temp_directory_path() /
              ("racer-flow-check-" + std::to_string(getpid()));
  try {
    // Fault the observer itself, then retrieve its recovery marker from disk.
    {
      Diagnostics diagnostics(root / "observer-history");
      PlayFlow observed((root / "observer-profile").string(),&diagnostics);
      failObserverAllocation=true;
      observed.observe("allocation_probe");
      failObserverAllocation=false;
      observed.observe("recovered");
      observed.paused=false;observed.rearming=false;
      observed.sim.car.x=497.49;observed.sim.car.heading=1.5707963267948966;observed.sim.car.speed=10;
      observed.tick({});
      check(observed.sim.boundaryContact,"single-tick boundary fixture reaches wall");
      observed.tick({});
      check(!observed.sim.boundaryContact,"collision clears before10Hz sample");
      diagnostics.flush();
      bool recovered=false;size_t boundaryEvents=0;
      for (const auto &file:std::filesystem::directory_iterator(root / "observer-history")) {
        if (file.path().extension()!=".jsonl") continue;
        std::ifstream input(file.path());
        for (std::string row;std::getline(input,row);) {
          const bool boundary=row.find("\"event\":\"boundary_contact\"")!=std::string::npos;
          boundaryEvents+=boundary;
          if (boundary || row.find("\"observation_failures\":1")!=std::string::npos)
            std::cout<<"OBSERVATION_EVIDENCE "<<row<<'\n';
          recovered|=row.find("\"event\":\"state\"")!=std::string::npos && row.find("\"observation_failures\":1")!=std::string::npos;
        }
      }
      check(boundaryEvents==1,"transient collision retained despite cleared sampled flag");
      check(recovered,"observer allocation fails open and retained recovery reports loss");
    }
    PlayFlow f((root / "profile.txt").string());
    f.action(Action::Pause);
    choose(f, 2);
    check(f.screen == Screen::Garage && f.sim.car.speed == 0,
          "pause to stationary garage");
    f.action(Action::Down);
    f.action(Action::Right);
    check(f.profile.garage.dirty() &&
              f.profile.garage.applied[0].acceleration == 1,
          "menu edit is draft");
    f.action(Action::Up);
    f.action(Action::Right);
    check(f.screen == Screen::Pending,
          "dirty switch requires explicit decision");
    choose(f, 2);
    check(f.screen == Screen::Garage && f.profile.garage.selected == 0 &&
              f.profile.garage.dirty(),
          "keep editing");
    f.action(Action::Right);
    choose(f, 1);
    check(f.screen == Screen::Garage && f.profile.garage.selected == 1 &&
              !f.profile.garage.dirty(),
          "discard switch");
    f.action(Action::Down);
    f.action(Action::Right);
    choose(f, 4);
    check(f.profile.garage.applied[1].acceleration == 1.05, "apply menu");
    choose(f, 6);
    check(f.profile.garage.dirty() &&
              f.profile.garage.applied[1].acceleration == 1.05,
          "defaults menu remains draft");
    choose(f, 5);
    check(!f.profile.garage.dirty(), "cancel edits menu");
    choose(f, 8);
    check(f.screen == Screen::Tests, "test menu");
    choose(f, 0);
    check(f.rearming, "test transition rearms");
    auto remaining = f.session.countdownRemaining();
    f.tick({1, 0, 0});
    check(f.session.countdownRemaining() == remaining,
          "rearm freezes countdown");
    released(f);
    f.tick({});
    remaining = f.session.countdownRemaining();
    f.focus = false;
    f.suspend();
    for (int i = 0; i < 100; ++i)
      f.tick({1, 0, 0});
    f.action(Action::Accept);
    check(f.paused && f.session.countdownRemaining() == remaining,
          "unfocused resume rejected and time frozen");
    f.focus = true;
    choose(f, 0);
    finish(f);
    check(f.profile.records.size() == 1 && !f.prior, "first record");
    auto record = f.profile.records.front();
    choose(f, 0);
    finish(f);
    check(f.prior && f.profile.records.size() == 1,
          "retry compares prior exact configuration");
    choose(f, 1);
    check(f.screen == Screen::Garage, "results to garage");
    f.action(Action::Down);
    f.action(Action::Right);
    choose(f, 4);
    check(f.profile.records.front() == record,
          "slot edit cannot rewrite record snapshot");
    choose(f, 8);
    choose(f, 0);
    released(f);
    f.action(Action::Reset);
    check(f.screen == Screen::Results && !f.session.result().valid &&
              f.profile.records.size() == 1,
          "reset invalidates without record");
    choose(f, 0);
    released(f);
    f.action(Action::Pause);
    choose(f, 3);
    check(!f.session.result().valid && f.profile.records.size() == 1,
          "cancel retry no record");
    choose(f, 0);
    released(f);
    f.action(Action::Pause);
    choose(f, 2);
    check(f.screen == Screen::Garage && !f.session.active() &&
              f.profile.records.size() == 1,
          "garage cancels active test");
    PlayFlow restart((root / "profile.txt").string());
    check(restart.profile.records == f.profile.records &&
              restart.profile.garage.selected == 1 &&
              restart.profile.garage.applied == f.profile.garage.applied,
          "flow restart loads applied setups and snapshots");
    std::filesystem::remove_all(root);
    std::cout << "PASS: playable garage pending/apply/cancel/defaults, "
                 "benchmark/retry/compare, rearm/focus freeze, invalidation "
                 "and restart\n";
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    std::filesystem::remove_all(root);
    return 1;
  }
}
