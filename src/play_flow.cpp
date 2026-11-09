#include "play_flow.h"
#include "vehicle_tuning.h"
#include <algorithm>
#include <cmath>
#include <sstream>
namespace racer {
namespace {
StoredResult stored(const TestResult &r) {
  StoredResult s;
  s.testId = testId(r.kind);
  s.carId = r.carId;
  s.slot = r.slot;
  s.setup = r.setup;
  s.seconds = r.seconds;
  s.distance = r.distance;
  s.initialSpeed = r.initialSpeed;
  s.testRevision = r.testRevision;
  s.modelRevision = r.handlingRevision;
  return s;
}
} // namespace
bool PlayFlow::configureVehicle(const std::string &id,const std::string &name,const VehicleGeometry &geometry) {
  StoredResult check;check.carId=id;check.modelRevision=2;check.testId="acceleration";check.seconds=1;
  if (!check.valid() || !geometry.valid() || name.empty() || name.size()>96 || !sim.setGeometry(geometry) ||
      !sim.setDynamics(dynamicsFor(geometry))) return false;
  cancelCareer();session.cancel();vehicleId=id;vehicleName=name;
  resetPose();sim.setSetup(effectiveSetup(profile.garage.selected));observe("vehicle");return true;
}
PlayFlow::PlayFlow(const std::string &path, Diagnostics *sink) : store(path, sink), features(path, sink), career(path,sink), diagnostics(sink) {
  store.load(profile);
  sim.setSetup(effectiveSetup(profile.garage.selected));
  career.updatePosition(sim.car.x,sim.car.z);
  observe("load");
}
void PlayFlow::show(Screen s) {
  screen = s;
  paused = s != Screen::Drive;
  menu = 0;
  rearming = true;
  sim.rearm();
  if (s == Screen::Parts || s == Screen::Livery)
    features.observe(s == Screen::Parts ? GarageFeaturePage::Parts : GarageFeaturePage::Livery,menu);
  observe("screen");
}
void PlayFlow::save() { store.context(attempt); store.save(profile); }
void PlayFlow::resetPose() {
  sim.reset();
  previousBoundaryContact = false;
  ++poseRevision;
  rearming = true;
}
void PlayFlow::drive() {
  if (!focus)
    return;
  if (!features.hasEngine()) { show(Screen::Parts); return; }
  sim.setSetup(effectiveSetup(profile.garage.selected));
  show(Screen::Drive);
}
void PlayFlow::suspend() {
  if (screen == Screen::Drive)
    show(Screen::Pause);
  rearming = true;
  sim.rearm();
}
void PlayFlow::garage() {
  cancelCareer();
  session.cancel();
  resetPose();
  profile.garage.discard();
  show(Screen::Garage);
}
void PlayFlow::startTest(TestKind kind) {
  if (!focus)
    return;
  if (!features.hasEngine()) { show(Screen::Parts); return; }
  cancelCareer();
  careerAttempt=false;
  attempt = diagnostics ? diagnostics->operation() : attempt + 1;
  lastTest = kind;
  retention = Retention::None;
  priorRecord.reset();
  session.start(kind, int(profile.garage.selected),
                effectiveSetup(profile.garage.selected), sim,vehicleId,vehicleId=="prototype" ? 1 : 2);
  ++poseRevision;
  prior.reset();
  show(Screen::Drive);
}
void PlayFlow::cancelCareer() {
  if (career.state().running()) career.cancel();
  careerAttempt=false;
}
void PlayFlow::beginCareer(bool retry) {
  startTest(TestKind::Handling);
  if (screen!=Screen::Drive || !session.active()) return;
  career.context(attempt);
  if (retry ? career.restart() : career.start()) careerAttempt=true;
  else { session.cancel();show(Screen::Events); }
}
VehicleSetup PlayFlow::effectiveSetup(size_t slot) const {
  auto setup=profile.garage.applied.at(slot);
  const auto parts=features.partMultipliers();
  setup.acceleration=std::clamp(setup.acceleration*parts.acceleration,.8,1.2);
  setup.brake=std::clamp(setup.brake*parts.brake,.8,1.2);
  setup.steering=std::clamp(setup.steering*parts.steering,.8,1.2);
  return setup;
}
int PlayFlow::count() const {
  switch (screen) {
  case Screen::Pause:
    return session.active() ? 4 : 3;
  case Screen::Garage:
    return 14;
  case Screen::Events:
    return 6;
  case Screen::Parts:
    return GarageFeatures::menuCount(GarageFeaturePage::Parts);
  case Screen::Livery:
    return GarageFeatures::menuCount(GarageFeaturePage::Livery);
  case Screen::Pending:
    return 3;
  case Screen::Tests:
    return 4;
  case Screen::Results:
    return 4;
  default:
    return 0;
  }
}
void PlayFlow::action(Action a) {
  if (diagnostics) diagnostics->event("command", {{"action", int(a)}, {"screen", int(screen)},
    {"menu", menu}, {"focus", focus}}, attempt);
  actionImpl(a);
  if (screen == Screen::Parts || screen == Screen::Livery)
    features.observe(screen == Screen::Parts ? GarageFeaturePage::Parts : GarageFeaturePage::Livery,menu);
  observe("command");
}
void PlayFlow::actionImpl(Action a) {
  if (!focus)
    return;
  if (a==Action::Map && screen==Screen::Drive) {
    if (session.active()) suspend();
    else { eventReturn=Screen::Drive;career.updatePosition(sim.car.x,sim.car.z);show(Screen::Events); }
    return;
  }
  if (a == Action::Reset && screen == Screen::Drive) {
    if (session.active()) {
      session.invalidate("Reset");
      if (career.state().running()) career.finish(false,0);
      show(Screen::Results);
    }
    resetPose();
    return;
  }
  if (a == Action::Pause || a == Action::Back) {
    if (screen==Screen::Events) { if (eventReturn==Screen::Garage) show(Screen::Garage);else drive();return; }
    if (screen == Screen::Parts || screen == Screen::Livery) {
      features.leave(screen == Screen::Parts ? GarageFeaturePage::Parts : GarageFeaturePage::Livery,menu);
      show(Screen::Garage);
      return;
    }
    if (screen == Screen::Drive) {
      suspend();
      return;
    }
    if (screen == Screen::Pause) {
      drive();
      return;
    }
    if (screen == Screen::Pending) {
      if (pendingSlot==-4) vehicleCycleRequest=0;
      show(Screen::Garage);
      return;
    }
    if (screen == Screen::Garage) {
      profile.garage.discard();
      show(Screen::Pause);
      return;
    }
    garage();
    return;
  }
  int n = count();
  if (!n)
    return;
  if (a == Action::Up) {
    menu = (menu + n - 1) % n;
    return;
  }
  if (a == Action::Down) {
    menu = (menu + 1) % n;
    return;
  }
  if (screen == Screen::Parts || screen == Screen::Livery) {
    if (a == Action::Left || a == Action::Right || a == Action::Accept)
      if (features.action(screen == Screen::Parts ? GarageFeaturePage::Parts : GarageFeaturePage::Livery, menu,
          a == Action::Left ? FeatureAction::Decrease : a == Action::Right ? FeatureAction::Increase : FeatureAction::Activate, attempt))
        show(Screen::Garage);
    return;
  }
  if (screen==Screen::Events) {
    if (a==Action::Left || a==Action::Right || a==Action::Accept) {
      const auto result=career.action(menu,a==Action::Left ? -1 : a==Action::Right ? 1 : 0,sim.car.x,sim.car.z);
      if (result==CareerBoardResult::StartHandling) beginCareer();
      else if (result==CareerBoardResult::Return) { if (eventReturn==Screen::Garage) show(Screen::Garage);else drive(); }
    }
    return;
  }
  auto &g = profile.garage;
  if (screen == Screen::Garage && (a == Action::Left || a == Action::Right)) {
    int d = a == Action::Right ? 1 : -1;
    if (menu==13) {
      if (g.dirty()) { pendingSlot=-4;vehicleCycleRequest=d*2;show(Screen::Pending); }
      else vehicleCycleRequest=d;
    } else if (menu == 0) {
      int slot = (int(g.selected) + d + 3) % 3;
      if (!g.select(slot)) {
        pendingSlot = slot;
        show(Screen::Pending);
      } else
        save();
    } else if (menu <= 3) {
      double &v = menu == 1   ? g.draft.acceleration
                  : menu == 2 ? g.draft.brake
                              : g.draft.steering;
      v = std::clamp(std::round((v + d * .05) * 100) / 100, .8, 1.2);
    }
    return;
  }
  if (a != Action::Accept)
    return;
  switch (screen) {
  case Screen::Pause:
    if (menu == 0)
      drive();
    else if (menu == 1) {
      cancelCareer();
      session.cancel();
      quit = true;
    } else if (menu == 2)
      garage();
    else {
      session.invalidate("Cancelled");
      if (career.state().running()) career.finish(false,0);
      show(Screen::Results);
    }
    break;
  case Screen::Garage:
    if (menu == 4) {
      if (g.apply())
        save();
    } else if (menu == 5)
      g.discard();
    else if (menu == 6)
      g.defaults();
    else if (menu == 7 || menu == 8) {
      if (g.dirty()) {
        pendingSlot = menu == 7 ? -1 : -2;
        show(Screen::Pending);
      } else if (menu == 7)
        drive();
      else
        show(Screen::Tests);
    } else if (menu == 9) {
      save();vehicleSaveRetryRequest=true;
    }
    else if (menu == 10)
      show(Screen::Parts);
    else if (menu == 11)
      show(Screen::Livery);
    else if (menu == 12) {
      eventReturn=Screen::Garage;
      career.updatePosition(sim.car.x,sim.car.z);
      if (g.dirty()) { pendingSlot=-3;show(Screen::Pending); }
      else show(Screen::Events);
    }
    break;
  case Screen::Pending:
    if (menu == 2) {
      if (pendingSlot==-4) vehicleCycleRequest=0;
      show(Screen::Garage);
      break;
    }
    if (menu == 0) {
      if (!g.apply())
        break;
    } else
      g.discard();
    if (pendingSlot >= 0)
      g.select(pendingSlot);
    save();
    if (pendingSlot == -1)
      drive();
    else if (pendingSlot == -4) { vehicleCycleRequest/=2;show(Screen::Garage); }
    else if (pendingSlot == -3)
      show(Screen::Events);
    else
      show(pendingSlot == -2 ? Screen::Tests : Screen::Garage);
    break;
  case Screen::Tests:
    if (menu == 3)
      garage();
    else
      startTest(menu == 0   ? TestKind::Acceleration
                : menu == 1 ? TestKind::Braking
                            : TestKind::Handling);
    break;
  case Screen::Results:
    if (menu == 0) {
      if (careerAttempt) beginCareer(true);
      else startTest(lastTest);
    }
    else if (menu == 1)
      garage();
    else if (menu == 2) {
      cancelCareer();
      session.cancel();
      resetPose();
      drive();
    } else
      show(Screen::Tests);
    break;
  default:
    break;
  }
}
void PlayFlow::tick(Input input) {
  if (paused || rearming)
    return;
  if (session.active()) {
    session.tick(sim, input);
    if (career.state().running()) {
      while (career.state().nextCheckpoint()<session.nextGate())
        if (!career.checkpoint(career.state().nextCheckpoint())) break;
    }
    if (!session.active()) {
      if (career.state().running()) career.finish(session.result().valid,session.result().seconds);
      if (session.phase() == TestPhase::Result) {
        auto r = stored(session.result());
        if (auto best = profile.best(r)) {
          priorRecord = *best;
          prior = r.testId == "braking" ? best->distance : best->seconds;
        }
        const double metric = r.testId == "braking" ? r.distance : r.seconds;
        retention = !prior || metric < *prior ? Retention::NewBest
                                              : Retention::Unchanged;
        if (profile.record(r))
          save();
        else
          retention = Retention::Full;
      }
      show(Screen::Results);
    }
  } else
    sim.tick(input);
  career.updatePosition(sim.car.x,sim.car.z);
  observeBoundary(input);
  if (diagnostics) observe("tick");
}
void PlayFlow::observeBoundary(Input input) noexcept {
  const bool rising=sim.boundaryContact && !previousBoundaryContact;
  previousBoundaryContact=sim.boundaryContact;
  if (!rising || !diagnostics || !diagnostics->enabled()) return;
  try {
    diagnostics->event("boundary_contact",{{"vehicle_id",vehicleId},{"pose_revision",poseRevision},
      {"x",sim.car.x},{"z",sim.car.z},{"heading",sim.car.heading},{"speed",sim.car.speed},
      {"requested_throttle",input.throttle},{"requested_brake",input.brake},{"requested_steer",input.steer},
      {"test_active",session.active()},{"phase",int(session.phase())}},attempt);
  } catch (...) {} // Optional edge history cannot change simulation behavior.
}
void PlayFlow::observe(const char *cause) noexcept {
  if (!diagnostics || !diagnostics->enabled()) return;
  try {
  const auto &g = profile.garage;
  const auto &r = session.result();
  std::ostringstream key;
  key << vehicleId << ':' << features.partsRevision() << ':' << features.liveryRevision() << ':' << features.draftRevision() << ':' << career.revision() << ':';
  key << int(screen) << ':' << menu << ':' << focus << ':' << paused << ':' << rearming
      << ':' << poseRevision << ':' << int(session.phase()) << ':' << session.nextGate()
      << ':' << session.measuringBraking() << ':' << int(store.persistence()) << ':' << g.selected
      << ':' << g.draft.acceleration << ':' << g.draft.brake << ':' << g.draft.steering;
  for (const auto &s : g.applied) key << ':' << s.acceleration << ':' << s.brake << ':' << s.steering;
  if (key.str() == lastObservation) return;
  lastObservation = key.str();
  const char *reason = r.valid ? "valid" : r.reason.starts_with("Boundary") ? "boundary"
      : r.reason.starts_with("Timed") ? "timeout" : r.reason.starts_with("Reset") ? "reset"
      : r.reason.starts_with("Cancel") ? "cancel" : "none";
  diagnostics->event("state", {{"cause", cause}, {"observation_failures", observationFailures}, {"screen", int(screen)}, {"menu", menu},
    {"focus", focus}, {"paused", paused}, {"rearming", rearming}, {"pose_revision", poseRevision},
    {"phase", int(session.phase())}, {"test", testId(r.kind)}, {"gate", session.nextGate()},
    {"braking", session.measuringBraking()}, {"valid", r.valid}, {"reason", reason},
    {"seconds", r.seconds}, {"distance", r.distance}, {"records", profile.records.size()},
    {"persistence", int(store.persistence())}, {"slot", g.selected}, {"dirty", g.dirty()},
    {"draft_accel", g.draft.acceleration}, {"draft_brake", g.draft.brake}, {"draft_steer", g.draft.steering},
    {"applied_accel", g.applied[g.selected].acceleration}, {"applied_brake", g.applied[g.selected].brake},
    {"applied_steer", g.applied[g.selected].steering}, {"frozen_accel", r.setup.acceleration},
    {"frozen_brake", r.setup.brake}, {"frozen_steer", r.setup.steering},
    {"parts_identity",features.partsIdentity()},{"engine_installed",features.hasEngine()},
    {"effective_accel",effectiveSetup(g.selected).acceleration},{"career_attempt",careerAttempt},
    {"career_running",career.state().running()},{"career_credits",career.state().credits()},
    {"vehicle_id",vehicleId},{"wheelbase",sim.wheelbase()}}, attempt);
  } catch (...) {
    // A failed optional observation must not interrupt gameplay. Clearing this
    // key retries the state once memory recovers; the next event reports loss.
    ++observationFailures;
    lastObservation.clear();
  }
}
} // namespace racer
