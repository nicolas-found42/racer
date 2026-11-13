// Drives the pure half of the incremental HUD repaint: which widget groups a
// sanitised DriveState change can repaint, and how dirty windows combine.
#include "hud_repaint.h"
#include <iostream>
#include <stdexcept>

namespace {
void require(bool value, const char *reason) {
  if (!value)
    throw std::runtime_error(reason);
}
using racer::DriveState;
using racer::DriveTest;
using racer::HudChanges;
using racer::HudDriveFrame;
using racer::HudRect;

DriveState baseline() {
  DriveState s;
  s.mph = 42;
  s.throttle = .5;
  s.brake = 0;
  s.steer = .1;
  s.reverse = false;
  s.vehicle = "Acura NSX '04";
  s.destination = "Grid Intro";
  s.bearing = "AHEAD";
  s.distance = 120;
  s.bearingRadians = .2;
  s.hasDestination = true;
  s.heading = 1.1;
  s.carX = 4;
  s.carZ = -8;
  s.blips.push_back({.1, 90, 0});
  s.blips.push_back({-.4, 210, 2});
  s.markerActive = true;
  s.markerBehind = false;
  s.markerX = 640;
  s.markerY = 380;
  s.markerLabel = "Gate 1";
  s.markerDistance = 90;
  s.test = DriveTest{};
  s.test->kind = 2;
  s.test->name = "Player Handling Course";
  s.test->note = "Cross toward north";
  s.test->elapsed = 3.25;
  s.test->gate = 2;
  s.test->gates = 5;
  s.test->distance = 90;
  s.test->speedKmh = 64;
  s.test->bearing = .3;
  s.test->turn = "right";
  s.test->gateDistance = 80;
  return s;
}
HudDriveFrame frame(const DriveState &s, int bannerStep = 0) {
  HudDriveFrame f;
  f.state = &s;
  f.bannerStep = bannerStep;
  f.compact = false;
  f.width = 1920;
  f.height = 1080;
  return f;
}
HudChanges diff(const DriveState &before, const DriveState &after,
                int bannerStep = 0) {
  return racer::hudDriveChanges(frame(before, bannerStep),
                                frame(after, bannerStep));
}
bool onlySpeed(const HudChanges &c) {
  return c.speed && !c.controls && !c.radar && !c.identity && !c.marker &&
         !c.banner && !c.test && !c.countdown && !c.full;
}
} // namespace

int main() try {
  // ---- unchanged frames repaint nothing ---------------------------------
  {
    const auto s = baseline();
    require(!racer::hudDriveChanges(frame(s), frame(s)).any(),
            "identical frames have no dirty groups");
  }
  // ---- speedometer inputs ------------------------------------------------
  {
    const auto s = baseline();
    auto t = s;
    t.mph = 43;
    const auto c = diff(s, t);
    require(onlySpeed(c) == false && c.speed && c.radar && !c.controls,
            "mph repaints dial and radar range");
    t = s;
    t.throttle = .55;
    require(onlySpeed(diff(s, t)), "throttle only repaints the pedal rails");
    require(!diff(s, t).radar, "throttle does not touch the radar");
    t = s;
    t.brake = .1;
    require(onlySpeed(diff(s, t)), "brake only repaints the pedal rails");
    t = s;
    t.reverse = true;
    require(onlySpeed(diff(s, t)), "gear indicator only repaints the dial");
    t = s;
    t.mph = 1; // 1.5 mph fade threshold
    require(diff(s, t).controls,
            "crossing the controls fade threshold repaints the key hints");
    t = s;
    t.mph = 41;
    require(!diff(s, t).controls,
            "speed changes above the threshold leave the key hints alone");
  }
  // ---- radar inputs -----------------------------------------------------
  {
    const auto s = baseline();
    auto t = s;
    t.heading = 1.12;
    require(diff(s, t).radar && !diff(s, t).speed,
            "heading only rotates the radar");
    t = s;
    t.carX = 5;
    require(diff(s, t).radar, "car position moves the radar grid");
    t = s;
    t.carZ = -9;
    require(diff(s, t).radar, "car position moves the radar grid in z");
    t = s;
    t.blips[0].bearing = .12;
    require(diff(s, t).radar, "blip bearing repaints the radar");
    t = s;
    t.blips[1].kind = 1;
    require(diff(s, t).radar, "blip kind repaints the radar");
    t = s;
    t.blips.pop_back();
    require(diff(s, t).radar, "blip count repaints the radar");
  }
  // ---- identity ---------------------------------------------------------
  {
    const auto s = baseline();
    auto t = s;
    t.vehicle = "Nissan 350Z";
    const auto c = diff(s, t);
    require(c.identity && !c.speed && !c.radar && !c.marker,
            "vehicle name only repaints the identity card");
  }
  // ---- compact-only fields are invisible in the wide layout -------------
  {
    const auto s = baseline();
    for (auto mutate : {0, 1, 2, 3, 4}) {
      auto t = s;
      if (mutate == 0)
        t.destination = "Something Else";
      if (mutate == 1)
        t.distance = 240;
      if (mutate == 2)
        t.bearing = "LEFT";
      if (mutate == 3)
        t.bearingRadians = .8;
      if (mutate == 4)
        t.steer = -.4;
      if (mutate == 5)
        t.hasDestination = false;
      require(
          !racer::hudDriveChanges(frame(s), frame(t)).any(),
          "wide layout ignores trip text that only the compact layout draws");
    }
    auto t = s;
    t.hasDestination = false;
    require(!diff(s, t).any(), "hasDestination is compact-only");
  }
  // ---- marker -----------------------------------------------------------
  {
    const auto s = baseline();
    for (auto mutate : {0, 1, 2, 3, 4, 5}) {
      auto t = s;
      if (mutate == 0)
        t.markerX = 700;
      if (mutate == 1)
        t.markerY = 200;
      if (mutate == 2)
        t.markerBehind = true;
      if (mutate == 3)
        t.markerLabel = "Gate 2";
      if (mutate == 4)
        t.markerDistance = 180;
      if (mutate == 5)
        t.markerActive = false;
      const auto c = diff(s, t);
      require(c.marker && !c.radar && !c.speed,
              "waypoint change repaints only the waypoint window");
    }
  }
  // ---- banner -----------------------------------------------------------
  {
    const auto s = baseline();
    const auto c = racer::hudDriveChanges(frame(s, 3), frame(s, 4));
    require(c.banner && !c.speed && !c.radar,
            "banner animation step repaints only the banner window");
    require(!racer::hudDriveChanges(frame(s, 0), frame(s, 0)).banner,
            "an idle banner never repaints");
  }
  // ---- driving tests ----------------------------------------------------
  {
    const auto s = baseline();
    auto t = s;
    t.test->elapsed = 3.26;
    const auto c = diff(s, t);
    require(c.test && !c.countdown, "measurement card timer repaints the card");
    auto countdown = s;
    countdown.test->countdown = true;
    countdown.test->countdownSeconds = 2.4;
    auto moved = countdown;
    moved.test->countdownSeconds = 2.38;
    const auto cc = diff(countdown, moved);
    require(cc.countdown && !cc.test,
            "countdown progress repaints the countdown window");
    const auto transition = diff(countdown, s);
    require(transition.test && transition.countdown,
            "countdown to measurement repaints both test windows");
    auto absent = s;
    absent.test.reset();
    const auto gone = diff(s, absent);
    require(gone.test && gone.countdown,
            "ending a test erases both test windows");
    require(diff(absent, s).test && diff(absent, s).countdown,
            "starting a test draws both windows");
  }
  // ---- layout changes always repaint in full ----------------------------
  {
    const auto s = baseline();
    auto wider = frame(s);
    wider.width = 2560;
    require(racer::hudDriveChanges(frame(s), wider).full,
            "window width change repaints in full");
    auto taller = frame(s);
    taller.height = 1200;
    require(racer::hudDriveChanges(frame(s), taller).full,
            "window height change repaints in full");
    auto compact = frame(s);
    compact.compact = true;
    require(racer::hudDriveChanges(frame(s), compact).full,
            "switching to the compact layout repaints in full");
    require(racer::hudDriveChanges(compact, frame(s)).full,
            "leaving the compact layout repaints in full");
    // The compact layout composes different widgets on the 640x480 crop, so its
    // own frames must never use the wide-layout windows.
    auto compactMoved = s;
    compactMoved.heading = 2.5;
    auto compactNext = frame(compactMoved, 0);
    compactNext.compact = true;
    require(racer::hudDriveChanges(compact, compactNext).full,
            "compact frames always repaint in full");
    HudDriveFrame empty{{}, 0, false, 0, 0};
    require(racer::hudDriveChanges(frame(s), empty).full,
            "missing state repaints in full");
    require(racer::hudDriveChanges(empty, frame(s)).full,
            "first frame repaints in full");
  }
  // ---- dirty window bookkeeping ----------------------------------------
  {
    racer::HudDirty d;
    require(d.empty() && d.area() == 0, "fresh dirty set is empty");
    d.add({10, 20, 30, 40});
    require(d.count == 1 && d.area() == 1200, "window recorded");
    d.add({12, 24, 5, 5});
    require(d.count == 1, "contained window is dropped");
    d.add({});
    require(d.count == 1, "empty window is dropped");
    d.add({-40, -40, 100, 100});
    require(d.rects[1].x == 0 && d.rects[1].y == 0 && d.rects[1].w == 60 &&
                d.rects[1].h == 60,
            "window clamped to the canvas");
    d.add({2000, 2000, 10, 10});
    require(d.count == 2, "off-canvas window is dropped");
    require(!d.full, "still incremental");
    racer::HudDirty overflow;
    for (int i = 0; i < racer::HudDirty::capacity; ++i)
      overflow.add({i * 100, 0, 50, 50});
    require(overflow.count == racer::HudDirty::capacity && !overflow.full,
            "capacity windows fit");
    overflow.add({900, 400, 50, 50});
    require(overflow.full && overflow.area() == int64_t(racer::hudCanvasWidth) *
                                                    racer::hudCanvasHeight,
            "overflow upgrades to a full repaint");
    // Widget windows must sit inside the canvas and stay disjoint enough that
    // the drive layout is covered by the groups that own them.
    for (auto r : {racer::hudSpeedometerWindow, racer::hudRadarWindow,
                   racer::hudControlsWindow, racer::hudIdentityWindow,
                   racer::hudTestCardWindow, racer::hudCountdownWindow}) {
      require(!r.empty() && r.x >= 0 && r.y >= 0 &&
                  r.x + r.w <= racer::hudCanvasWidth &&
                  r.y + r.h <= racer::hudCanvasHeight,
              "widget window inside the canvas");
    }
    require(racer::hudContains(racer::hudSpeedometerWindow,
                               {1096 - 114, 578 - 114, 228, 228}),
            "dial disc covered by its window");
    require(racer::hudContains(racer::hudRadarWindow,
                               {122 - 84, 590 - 84, 168, 168}),
            "radar disc covered by its window");
  }
  std::cout << "PASS: HUD repaint groups, compact-only fields, "
               "banner/marker/window bookkeeping\n";
} catch (const std::exception &e) {
  std::cerr << e.what() << '\n';
  return 1;
}
