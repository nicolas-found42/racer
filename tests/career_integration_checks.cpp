#include "play_flow.h"
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <unistd.h>
using namespace racer;
void require(bool condition,const char *message) { if (!condition) throw std::runtime_error(message); }
void complete(PlayFlow &flow) {
  flow.rearming=false;flow.sim.tick({},0);
  for (int i=0;i<36000 && flow.session.active();++i) {
    const auto &gate=handlingCourse().gates[flow.session.nextGate()];
    const auto &car=flow.sim.car;
    const auto error=std::remainder(std::atan2(gate.x+gate.nx*8-car.x,gate.z+gate.nz*8-car.z)-car.heading,2*3.141592653589793);
    flow.tick({car.speed<7 ? 1. : 0.,car.speed>8 ? 1. : 0.,std::clamp(error*2,-1.,1.)});
  }
  require(flow.screen==Screen::Results && flow.session.result().valid,"actual simulation event finish");
}
int main() try {
  auto root=std::filesystem::temp_directory_path()/("racer-career-integration-"+std::to_string(getpid()));
  const auto profile=(root/"profile.txt").string();
  PlayFlow flow(profile);
  flow.action(Action::Map);require(flow.screen==Screen::Events,"drive to board");
  flow.menu=2;flow.action(Action::Accept);
  require(flow.careerAttempt && flow.career.state().running() && flow.session.active(),"board starts correlated event");
  const auto countdown=flow.session.countdownRemaining();flow.suspend();flow.tick({1,0,0});
  require(flow.career.state().running() && flow.session.countdownRemaining()==countdown,"pause freezes both workflows");
  flow.action(Action::Accept);complete(flow);
  require(flow.career.state().credits()==5000 && flow.career.state().completed("grid-intro"),"reward after gate traversal");
  flow.action(Action::Accept);complete(flow);
  require(flow.career.state().credits()==5000,"retry cannot duplicate reward");
  flow.action(Action::Accept);flow.action(Action::Reset);
  require(!flow.session.result().valid && !flow.career.state().running() && flow.career.state().credits()==5000,"reset invalid event no reward");
  flow.menu=1;flow.action(Action::Accept);flow.menu=12;flow.action(Action::Accept);
  flow.menu=3;flow.action(Action::Accept);
  require(flow.career.state().owns("touring") && flow.career.state().credits()==2000,"purchase persistent ownership");
  flow.menu=0;flow.action(Action::Right);flow.menu=2;flow.action(Action::Accept);
  require(flow.screen==Screen::Events && !flow.session.active(),"remote undiscovered start rejected");
  // Controlled world-position fixture; not a human or native-input navigation claim.
  flow.sim.car.x=flow.sim.car.z=100;flow.career.updatePosition(100,100);flow.action(Action::Accept);
  require(flow.career.state().running() && flow.career.state().selection()=="club-loop","arrived unlock starts second event");
  complete(flow);require(flow.career.state().credits()==3000,"second reward");
  PlayFlow reload(profile);
  require(reload.career.state().credits()==3000 && reload.career.state().owns("touring") &&
      reload.career.state().completed("club-loop") && !reload.career.state().running(),"cross process state restore");
  reload.garage();reload.profile.garage.draft.acceleration=1.1;
  reload.menu=12;reload.action(Action::Accept);
  require(reload.screen==Screen::Pending && reload.profile.garage.dirty(),"dirty events entry requires decision");
  reload.menu=2;reload.action(Action::Accept);
  require(reload.screen==Screen::Garage && reload.profile.garage.dirty(),"keep editing from events transition");
  reload.menu=12;reload.action(Action::Accept);reload.menu=1;reload.action(Action::Accept);
  require(reload.screen==Screen::Events && !reload.profile.garage.dirty(),"explicit discard enters events");
  reload.action(Action::Back);require(reload.screen==Screen::Garage,"event board returns to originating garage");
  std::filesystem::remove_all(root);
  std::cout<<"PASS: event board, real five-gate simulation, pause, retry, reset, ownership, proximity, reload\n";
} catch (const std::exception &e) { std::cerr<<"FAIL: "<<e.what()<<'\n';return 1; }
