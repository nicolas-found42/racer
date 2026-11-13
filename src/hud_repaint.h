#pragma once
// Incremental drive-HUD repaint.
//
// The drive HUD rasterises a 1280x720 CoreGraphics canvas and uploads it to a
// Metal texture. A full repaint costs several milliseconds (shadow blurs,
// gradients, glyphs), so the canvas is only cleared and repainted where the
// visible content can change. This header owns the pure part: which widget
// groups a sanitised DriveState change can affect, and a conservative window
// for every widget whose drawn extent does not depend on measured text. The
// painter keeps those windows in sync; text-measured widgets (marker, banner)
// report their own bounds from the painting module.
//
// A repaint always re-runs the complete paint pipeline clipped to the dirty
// window, so a changed widget cannot be drawn over stale neighbours: the
// pipeline order, alpha blending and antialiasing are identical to a full
// repaint inside the clip, and everything outside the clip is unchanged by
// construction because its inputs did not change.
#include "drive_hud.h"
#include "hud_layout.h"
#include <algorithm>
#include <cstdint>

namespace racer {
inline constexpr int hudCanvasWidth = 1280;
inline constexpr int hudCanvasHeight = 720;
// Largest per-channel difference a clipped repaint may show against an
// unclipped one: CoreGraphics applies the clip mask to gradient dithering and
// to antialiased glyph/arc edges, which can shift a pixel by two 8-bit steps.
// A stale or missing widget is orders of magnitude larger (see the audit).
inline constexpr int hudRepaintSlack = 2;

struct HudRect {
  int x = 0, y = 0, w = 0, h = 0;
  bool empty() const { return w <= 0 || h <= 0; }
  bool operator==(const HudRect &o) const {
    return x == o.x && y == o.y && w == o.w && h == o.h;
  }
  bool operator!=(const HudRect &o) const { return !(*this == o); }
};
// Intersection; empty when the rectangles do not overlap.
inline HudRect hudIntersect(HudRect a, HudRect b) {
  const int x0 = std::max(a.x, b.x), y0 = std::max(a.y, b.y);
  const int x1 = std::min(a.x + a.w, b.x + b.w),
            y1 = std::min(a.y + a.h, b.y + b.h);
  return {x0, y0, std::max(0, x1 - x0), std::max(0, y1 - y0)};
}
// Bounding union; an empty input is ignored.
inline HudRect hudUnion(HudRect a, HudRect b) {
  if (a.empty())
    return b;
  if (b.empty())
    return a;
  const int x0 = std::min(a.x, b.x), y0 = std::min(a.y, b.y);
  const int x1 = std::max(a.x + a.w, b.x + b.w),
            y1 = std::max(a.y + a.h, b.y + b.h);
  return {x0, y0, x1 - x0, y1 - y0};
}
inline HudRect hudClampToCanvas(HudRect r) {
  return hudIntersect(r, {0, 0, hudCanvasWidth, hudCanvasHeight});
}
inline bool hudContains(HudRect outer, HudRect inner) {
  return !inner.empty() && inner.x >= outer.x && inner.y >= outer.y &&
         inner.x + inner.w <= outer.x + outer.w &&
         inner.y + inner.h <= outer.y + outer.h;
}

// CoreGraphics interprets a shadow blur radius r as a Gaussian with sigma=r/2,
// so a shadow's visible tail reaches roughly 1.5r. Every window below therefore
// reserves two blur radii of margin; the repaint audit checks the result against
// the drawn pixels.
// Speedometer dial at (1096,578): 114 px disc, 16 px shadow, pedal rails to
// x+151 and the B/T labels below them.
inline constexpr HudRect hudSpeedometerWindow{958, 438, 302, 280};
// Radar disc at (122,590): 84 px radius, 14 px shadow, RANGE caption below.
inline constexpr HudRect hudRadarWindow{12, 478, 220, 224};
// Throttle/brake key hints, two rows from y=646 with 1.5 px text shadows.
inline constexpr HudRect hudControlsWindow{206, 632, 624, 84};
// Vehicle identity card, top left.
inline constexpr HudRect hudIdentityWindow{24, 24, 386, 96};
// Test measurement card at (430,24,420,108) with its 12 px plate shadow.
inline constexpr HudRect hudTestCardWindow{390, 0, 504, 168};
// Launch countdown: caption rows, 62 px ring at (640,196) and the popping
// digit scaled up to 1.45.
inline constexpr HudRect hudCountdownWindow{500, 60, 282, 244};

// Rectangles to clear and repaint. The capacity bounds one frame's work; an
// overflow upgrades to a full repaint rather than dropping a change.
struct HudDirty {
  static constexpr int capacity = 8;
  HudRect rects[capacity];
  int count = 0;
  bool full = false;
  bool empty() const { return !full && count == 0; }
  void add(HudRect r) {
    r = hudClampToCanvas(r);
    if (r.empty() || full)
      return;
    for (int i = 0; i < count; ++i)
      if (hudContains(rects[i], r))
        return;
    if (count == capacity) {
      full = true;
      return;
    }
    rects[count++] = r;
  }
  // Pixel work implied by the repaint, for diagnostics.
  int64_t area() const {
    int64_t sum = 0;
    for (int i = 0; i < count; ++i)
      sum += int64_t(rects[i].w) * rects[i].h;
    return full ? int64_t(hudCanvasWidth) * hudCanvasHeight : sum;
  }
};

// What the drive painter consumed for one frame.
struct HudDriveFrame {
  const DriveState *state = nullptr;
  int bannerStep = 0; // quantised announcement-banner phase, 0 when idle
  bool compact = false;
  uint16_t width = 0, height = 0;
};

// Widget groups a change can touch. Every field the drive painter reads is
// mapped here; unmapped visible state is a bug the unit checks catch.
struct HudChanges {
  bool full = false;
  bool speed = false;     // dial arc, tick lighting, number, pedal rails
  bool controls = false;  // key hints fade below 1.5 mph
  bool radar = false;     // street grid, compass, blips, range caption
  bool identity = false;  // vehicle card
  bool marker = false;    // world-anchored waypoint
  bool banner = false;    // announcement banner
  bool test = false;      // measurement card
  bool countdown = false; // launch countdown
  bool any() const {
    return full || speed || controls || radar || identity || marker || banner ||
           test || countdown;
  }
};

inline bool hudSameTest(const DriveTest &a, const DriveTest &b) {
  return a.kind == b.kind && a.name == b.name && a.note == b.note &&
         a.countdown == b.countdown && a.measuring == b.measuring &&
         a.automatic == b.automatic &&
         a.countdownSeconds == b.countdownSeconds && a.elapsed == b.elapsed &&
         a.distance == b.distance && a.speedKmh == b.speedKmh &&
         a.gate == b.gate && a.gates == b.gates &&
         a.gateDistance == b.gateDistance && a.bearing == b.bearing &&
         a.turn == b.turn;
}
inline bool hudSameBlips(const std::vector<RadarBlip> &a,
                         const std::vector<RadarBlip> &b) {
  if (a.size() != b.size())
    return false;
  for (size_t i = 0; i < a.size(); ++i)
    if (a[i].bearing != b[i].bearing || a[i].distance != b[i].distance ||
        a[i].kind != b[i].kind)
      return false;
  return true;
}

// Which groups `before` -> `after` can change in the drive canvas. Both states
// are already sanitised (rounded to the precision the painter draws).
inline HudChanges hudDriveChanges(const HudDriveFrame &before,
                                  const HudDriveFrame &after) {
  HudChanges c;
  if (!before.state || !after.state) {
    c.full = true;
    return c;
  }
  const DriveState &a = *before.state;
  const DriveState &b = *after.state;
  // The compact layout is a different composition on the 640x480 crop (other
  // widgets, other type scale), so it always repaints in full; so does any
  // window-size change, which changes the scale of the wide layout.
  if (before.compact || after.compact) {
    c.full = true;
    return c;
  }
  if (before.width != after.width || before.height != after.height) {
    c.full = true;
    return c;
  }
  if (before.bannerStep != after.bannerStep)
    c.banner = true;
  // mph drives the dial, the radar range ring and blip radii.
  if (a.mph != b.mph) {
    c.speed = true;
    c.radar = true;
  }
  if ((a.mph < 1.5) != (b.mph < 1.5))
    c.controls = true;
  if (a.throttle != b.throttle || a.brake != b.brake || a.reverse != b.reverse)
    c.speed = true;
  if (a.heading != b.heading || a.carX != b.carX || a.carZ != b.carZ ||
      !hudSameBlips(a.blips, b.blips))
    c.radar = true;
  if (a.vehicle != b.vehicle)
    c.identity = true;
  if (a.markerActive != b.markerActive || a.markerBehind != b.markerBehind ||
      a.markerX != b.markerX || a.markerY != b.markerY ||
      a.markerLabel != b.markerLabel || a.markerDistance != b.markerDistance)
    c.marker = true;
  if (a.test.has_value() != b.test.has_value()) {
    c.test = true;
    c.countdown = true;
  } else if (a.test && !hudSameTest(*a.test, *b.test)) {
    // The card and the countdown are exclusive branches; a change inside one
    // still repaints that branch only.
    (b.test->countdown ? c.countdown : c.test) = true;
    if (a.test->countdown != b.test->countdown) {
      c.test = true;
      c.countdown = true;
    }
    if (a.test->kind != b.test->kind) {
      c.test = true;
      c.countdown = true;
    }
  }
  // Deliberately not mapped: destination, distance, bearing text,
  // bearingRadians and steer are only drawn by the compact layout, which
  // always repaints in full.
  return c;
}
} // namespace racer
