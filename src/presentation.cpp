#include "presentation.h"
#include "performance_class.h"
#include "play_flow.h"
#include <cmath>
#include <iomanip>
#include <numbers>
#include <sstream>
namespace racer {
namespace {
std::string number(double v, int places = 3) {
  std::ostringstream out;
  out << std::fixed << std::setprecision(places) << v;
  return out.str();
}
std::string values(const VehicleSetup &s) {
  return "Accel " + number(s.acceleration, 2) + "x / Brake " +
         number(s.brake, 2) + "x / Steer " + number(s.steering, 2) + "x";
}
std::string rating(const VehicleSetup &s) {
  const auto r=prototypeRating(s);
  return std::string("Prototype class ")+r.className+" / target 0-100: "+number(r.targetSeconds,2)+" s (Racer bands)";
}
std::string slot(size_t s) { return std::string(1, char('A' + s)); }
double metric(const StoredResult &r) {
  return r.testId == "braking" ? r.distance : r.seconds;
}
std::string delta(double d, const std::string &unit,
                  const std::string &reference) {
  if (std::abs(d) < .0005)
    d = 0;
  return (d >= 0 ? "+" : "") + number(d) + unit +
         (d < 0   ? " better than "
          : d > 0 ? " worse than "
                  : " equal to ") +
         reference;
}
void persistence(std::vector<std::string> &out, const PlayFlow &f) {
  const auto &g = f.profile.garage;
  switch (f.store.persistence()) {
  case Persistence::New:
    out.push_back("Applied " + slot(g.selected) +
                  ": defaults in memory; no profile saved yet.");
    break;
  case Persistence::Loaded:
    out.push_back("Applied " + slot(g.selected) + ": loaded from disk.");
    break;
  case Persistence::Saved:
    out.push_back("Applied " + slot(g.selected) + ": saved to disk" +
                  (g.dirty() ? " (excludes current draft)." : "."));
    break;
  case Persistence::Failed:
    out.push_back("UNSAVED: applied for driving, not saved to disk. Garage > "
                  "Retry save.");
    out.push_back(f.store.message());
    break;
  case Persistence::Disabled:
    out.push_back(f.store.message());
    out.push_back("Saving disabled: move the original profile aside, then "
                  "restart to recover.");
    break;
  }
}
std::string phase(const TestSession &s) {
  if (s.phase() == TestPhase::Countdown)
    return "COUNTDOWN  " + number(s.countdownRemaining(), 1) + " s";
  if (s.result().kind == TestKind::Handling)
    return "COURSE RUNNING / PLAYER INPUT";
  if (s.result().kind == TestKind::Braking)
    return s.measuringBraking()
               ? "BRAKING MEASUREMENT / 100-0 km/h"
               : "LEAD-IN / accelerating to 100 km/h (not measured)";
  return "ACCELERATION MEASUREMENT / 0-100 km/h";
}
} // namespace
CourseGuidance courseGuidance(const Gate &g, const Car &car) {
  CourseGuidance cue;
  cue.distance = std::hypot(g.x - car.x, g.z - car.z);
  cue.returnToApproach = (car.x - g.x) * g.nx + (car.z - g.z) * g.nz >= 0;
  // After a miss, point to the approach side instead of asking for a reverse
  // crossing.
  const double x = g.x - (cue.returnToApproach ? 18 * g.nx : 0);
  const double z = g.z - (cue.returnToApproach ? 18 * g.nz : 0);
  cue.bearing = std::remainder(std::atan2(x - car.x, z - car.z) - car.heading,
                               2 * std::numbers::pi);
  const double degrees = cue.bearing * 180 / std::numbers::pi;
  cue.turn = std::abs(degrees) < 12    ? "^ AHEAD"
             : std::abs(degrees) > 160 ? "v TURN BACK"
             : degrees > 0             ? "> RIGHT"
                                       : "< LEFT";
  cue.crossing = g.nz > .5    ? "NORTH"
                 : g.nz < -.5 ? "SOUTH"
                 : g.nx > 0   ? "EAST"
                              : "WEST";
  return cue;
}
std::vector<std::string> PlayFlow::lines() const {
  if (screen==Screen::Events) return career.lines(menu);
  if (screen == Screen::Parts || screen == Screen::Livery)
    return features.lines(screen == Screen::Parts ? GarageFeaturePage::Parts
                                                 : GarageFeaturePage::Livery, menu);
  std::vector<std::string> out;
  auto option = [&](int index, std::string s) {
    out.push_back((menu == index ? "> " : "  ") + s);
  };
  const auto &g = profile.garage;
  if (screen == Screen::Pause) {
    out = {"PAUSED / RACER"};
    option(0, "Resume");
    option(1, "Quit");
    option(2, "Garage");
    if (session.active()) {
      option(3, "Cancel test (no record)");
      out.push_back(std::string(testName(session.result().kind)) +
                    " / frozen setup " + slot(session.result().slot));
      out.push_back("Paused: " + phase(session));
    }
  } else if (screen == Screen::Garage) {
    out = {"GARAGE / " + vehicleName,
           g.dirty() ? "DRAFT NOT APPLIED / Apply to drive with these values"
                     : "No pending draft edits."};
    option(0, "Setup " + slot(g.selected) + "  [Left / Right]");
    option(1, "Acceleration " + number(g.draft.acceleration, 2) +
                  "x [0.80-1.20] - drive force");
    option(2, "Brakes       " + number(g.draft.brake, 2) +
                  "x [0.80-1.20] - active braking");
    option(3, "Steering     " + number(g.draft.steering, 2) +
                  "x [0.80-1.20] - response speed");
    option(4, "Apply and save");
    option(5, "Cancel edits");
    option(6, "Restore defaults to draft");
    option(7, "Drive");
    option(8, "Run test / compare");
    option(9, "Retry save");
    option(10, "Parts / inventory");
    option(11, "Livery / layers");
    option(12, "Events / destination / career");
    option(13, "Car: " + vehicleName + " [Left / Right]");
    if (!vehicleSaveStatus.empty()) out.push_back(vehicleSaveStatus);
    if (features.partMultipliers().acceleration!=1)
      out.push_back("Hardware + tune: " + values(effectiveSetup(g.selected)) + " (1.20x cap)");
    out.push_back(rating(effectiveSetup(g.selected)));
  } else if (screen == Screen::Pending) {
    out = {"UNAPPLIED CHANGES / SETUP " + slot(g.selected),
           "DRAFT NOT APPLIED / previously applied values remain in use.",
           values(g.draft)};
    option(0, "Apply and continue");
    option(1, "Discard and continue");
    option(2, "Keep editing");
  } else if (screen == Screen::Tests) {
    out = {"DRIVING TESTS / NEXT RUN: SETUP " + slot(g.selected),
           values(effectiveSetup(g.selected))};
    option(0, "Automatic: 0-100 km/h (62.14 mph)");
    option(1, "Automatic: 100-0 km/h braking");
    option(2, "Player run: handling course");
    option(3, "Garage");
    out.push_back(rating(effectiveSetup(g.selected)));
    out.push_back("BEST FOR EACH EXACT APPLIED SETUP / lower is better");
    for (int s = 0; s < 3; ++s) {
      out.push_back(slot(s) +
                    (size_t(s) == g.selected ? " [NEXT] " : "        ") +
                    values(effectiveSetup(s)));
      for (const char *id : {"acceleration", "braking", "handling"}) {
        StoredResult query;
        query.carId=vehicleId;query.modelRevision=vehicleId=="prototype" ? 1 : 2;
        query.testId = id;
        query.setup = effectiveSetup(s);
        auto best = profile.best(query);
        const std::string unit = query.testId == "braking" ? " m" : " s";
        std::string line = "  " + query.testId + ": ";
        if (!best)
          line += "No comparable result";
        else {
          line += number(metric(*best)) + unit + " / " +
                  (best->slot != size_t(s) ? "matching setup, recorded as "
                                           : "recorded as ") +
                  slot(best->slot);
          query.setup = effectiveSetup(0);
          if (s != 0)
            if (auto reference = profile.best(query))
              line +=
                  " / " + delta(metric(*best) - metric(*reference), unit, "A");
        }
        out.push_back(line);
      }
    }
    out.push_back(
        "Handling: player runs; differences also depend on driving skill.");
  } else if (screen == Screen::Results) {
    const auto &r = session.result();
    out = {r.valid ? "VALID FINISH / TEST RESULT"
                   : "INVALID / ATTEMPT NOT SAVED: " + r.reason,
           std::string(testName(r.kind)) + " / frozen setup " + slot(r.slot),
           values(r.setup)};
    out.push_back(
        std::string(r.valid ? "MEASUREMENT: " : "PARTIAL (INVALID): ") +
        number(r.kind == TestKind::Braking ? r.distance : r.seconds) +
        (r.kind == TestKind::Braking ? " m" : " s"));
    out.push_back(rating(r.setup));
    out.push_back("Time " + number(r.seconds) + " s / Distance " +
                  number(r.distance) + " m / Initial " +
                  number(r.initialSpeed * 3.6, 2) + " km/h");
    if (r.valid) {
      if (priorRecord)
        out.push_back(delta(
            (r.kind == TestKind::Braking ? r.distance : r.seconds) - *prior,
            r.kind == TestKind::Braking ? " m" : " s",
            "prior exact-setup best recorded as " + slot(priorRecord->slot)));
      else
        out.push_back("No prior comparable result for this exact setup.");
      out.push_back(retention == Retention::NewBest
                        ? "NEW BEST retained in memory."
                    : retention == Retention::Unchanged
                        ? "Valid completion; best unchanged."
                        : "Valid completion; record capacity full. Attempt not "
                          "retained.");
      if (retention != Retention::Full)
        out.push_back(store.persistence() == Persistence::Saved
                          ? "Best records saved to disk."
                          : "Best records NOT saved to disk this run.");
    } else
      out.push_back("Attempt not saved. Previous best records are unchanged.");
    if (r.kind == TestKind::Handling)
      out.push_back(
          "Player run: time differences do not isolate setup effects.");
    if (careerAttempt) {
      out.push_back(career.message());
      out.push_back("Career credits: " + std::to_string(career.state().credits()) +
          (career.store().outcome().status==DocumentStatus::Saved ? " / saved to disk" : " / disk save unconfirmed"));
    }
    option(0, "Retry");
    option(1, "Garage");
    option(2, "Free drive");
    option(3, "Tests / compare A B C");
  } else if (session.active()) {
    const auto &r = session.result();
    out = {std::string(testName(r.kind)) + " / frozen setup " + slot(r.slot),
           values(r.setup), phase(session)};
    out.push_back("MEASURED " + number(session.elapsed(), 2) + " s / " +
                  number(session.distance(), 2) + " m / " +
                  number(std::abs(sim.car.speed) * 3.6, 1) + " km/h");
    if (r.kind == TestKind::Handling) {
      const auto &gates = handlingCourse().gates;
      const auto cue = courseGuidance(gates[session.nextGate()], sim.car);
      out.push_back("NEXT GATE " + std::to_string(session.nextGate() + 1) +
                    "/" + std::to_string(gates.size()) + " / " +
                    number(cue.distance, 0) + " m / " + cue.turn + " " +
                    number(std::abs(cue.bearing) * 180 / std::numbers::pi, 0) +
                    " deg");
      out.push_back((cue.returnToApproach ? "MISSED? Return to approach side; "
                                          : "Cross the numbered gate toward ") +
                    cue.crossing);
      out.push_back("WASD / Stick + RT/LT: drive | R / Y: invalidate + reset");
    } else
      out.push_back(
          "AUTOMATIC INPUT / pedals and steering ignored | R / Y: invalidate");
    out.push_back("ESC / Menu: pause, then Cancel test | release controls to "
                  "start/resume");
  }
  if (screen != Screen::Drive) {
    out.push_back("");
    persistence(out, *this);
    out.push_back("Arrows / D-pad: select, adjust | Enter / South: confirm | "
                  "Esc / East: back");
  }
  return out;
}
} // namespace racer
