#pragma once
// CoreGraphics/CoreText drawing primitives for the HUD canvas.
// The canvas uses a top-left origin (callers flip the CTM once) and
// premultiplied RGBA; all coordinates are logical 1280x720 canvas units.
#include <CoreGraphics/CoreGraphics.h>
#include <CoreText/CoreText.h>
#include "ui_model.h"
#include <algorithm>
#include <cmath>
#include <map>
#include <tuple>
#include <vector>
#include <string>
#include <utility>

namespace racer::paint {

struct Ink {
  CGFloat r, g, b, a;
  constexpr Ink withAlpha(CGFloat alpha) const { return {r, g, b, a * alpha}; }
};
constexpr Ink mix(Ink x, Ink y, CGFloat t) {
  return {x.r + (y.r - x.r) * t, x.g + (y.g - x.g) * t, x.b + (y.b - x.b) * t, x.a + (y.a - x.a) * t};
}

// Palette: deep blue-black glass, cyan primary, amber secondary, red for danger.
constexpr Ink ink{.02, .035, .048, 1};
constexpr Ink white{.96, .97, .95, 1};
constexpr Ink muted{.62, .70, .73, 1};
constexpr Ink dim{.40, .47, .50, 1};
constexpr Ink cyan{.34, .86, .92, 1};
// Runtime accent (HUD colour option); defaults to cyan. Everything that was cyan follows it.
inline Ink gAccent = cyan;
inline Ink accentScaled(CGFloat k, CGFloat a) { return {gAccent.r * k, gAccent.g * k, gAccent.b * k, a}; }
constexpr Ink teal{.10, .46, .52, 1};
constexpr Ink amber{1, .72, .30, 1};
constexpr Ink red{1, .33, .24, 1};
constexpr Ink green{.42, .93, .62, 1};

// Cached colour refs (shadow colours are requested every frame).
inline CGColorRef shade(CGFloat r, CGFloat g, CGFloat b, CGFloat a) {
  static std::map<std::tuple<int, int, int, int>, CGColorRef> cache;
  const auto key = std::make_tuple(int(r * 255), int(g * 255), int(b * 255), int(a * 255));
  auto it = cache.find(key);
  if (it != cache.end()) return it->second;
  CGColorRef color = CGColorCreateGenericRGB(r, g, b, a);
  cache[key] = color;
  return color;
}
inline void setFill(CGContextRef c, Ink k) { CGContextSetRGBFillColor(c, k.r, k.g, k.b, k.a); }
inline void setStroke(CGContextRef c, Ink k) { CGContextSetRGBStrokeColor(c, k.r, k.g, k.b, k.a); }

inline void rounded(CGContextRef c, CGRect rect, CGFloat radius) {
  radius = std::min(radius, std::min(rect.size.width, rect.size.height) / 2);
  CGPathRef path = CGPathCreateWithRoundedRect(rect, radius, radius, nullptr);
  CGContextAddPath(c, path);
  CGPathRelease(path);
}
inline void fill(CGContextRef c, CGRect rect, Ink k, CGFloat radius = 0) {
  setFill(c, k);
  if (radius > 0) {
    rounded(c, rect, radius);
    CGContextFillPath(c);
  } else
    CGContextFillRect(c, rect);
}
inline void stroke(CGContextRef c, CGRect rect, Ink k, CGFloat width, CGFloat radius = 0) {
  setStroke(c, k);
  CGContextSetLineWidth(c, width);
  rounded(c, rect, radius);
  CGContextStrokePath(c);
}

// Parallelogram leaning right by `skew` pixels over its height (racing-UI slant).
inline void skewPath(CGContextRef c, CGRect r, CGFloat skew) {
  CGContextMoveToPoint(c, r.origin.x + skew, r.origin.y);
  CGContextAddLineToPoint(c, r.origin.x + r.size.width + skew, r.origin.y);
  CGContextAddLineToPoint(c, r.origin.x + r.size.width, r.origin.y + r.size.height);
  CGContextAddLineToPoint(c, r.origin.x, r.origin.y + r.size.height);
  CGContextClosePath(c);
}
inline void skewFill(CGContextRef c, CGRect r, CGFloat skew, Ink k) {
  setFill(c, k);
  skewPath(c, r, skew);
  CGContextFillPath(c);
}

inline CGGradientRef makeGradient(Ink a, Ink b) {
  CGColorSpaceRef space = CGColorSpaceCreateDeviceRGB();
  const CGFloat comps[]{a.r, a.g, a.b, a.a, b.r, b.g, b.b, b.a};
  CGGradientRef g = CGGradientCreateWithColorComponents(space, comps, nullptr, 2);
  CGColorSpaceRelease(space);
  return g;
}
// Fill the current path (already added) with a linear gradient between two points.
inline void gradientClip(CGContextRef c, Ink a, Ink b, CGPoint p0, CGPoint p1) {
  CGGradientRef g = makeGradient(a, b);
  CGContextSaveGState(c);
  CGContextClip(c);
  CGContextDrawLinearGradient(c, g, p0, p1, kCGGradientDrawsBeforeStartLocation | kCGGradientDrawsAfterEndLocation);
  CGContextRestoreGState(c);
  CGGradientRelease(g);
}
inline void gradientRect(CGContextRef c, CGRect r, Ink a, Ink b, bool horizontal, CGFloat radius = 0) {
  rounded(c, r, radius);
  gradientClip(c, a, b, {r.origin.x, r.origin.y},
               horizontal ? CGPoint{r.origin.x + r.size.width, r.origin.y} : CGPoint{r.origin.x, r.origin.y + r.size.height});
}
inline void gradientSkew(CGContextRef c, CGRect r, CGFloat skew, Ink a, Ink b) {
  skewPath(c, r, skew);
  gradientClip(c, a, b, {r.origin.x, r.origin.y}, {r.origin.x + r.size.width + skew, r.origin.y});
}
inline void radialGlow(CGContextRef c, CGPoint center, CGFloat radius, Ink inner, Ink outer) {
  CGGradientRef g = makeGradient(inner, outer);
  CGContextSaveGState(c);
  CGContextDrawRadialGradient(c, g, center, 0, center, radius, kCGGradientDrawsAfterEndLocation);
  CGContextRestoreGState(c);
  CGGradientRelease(g);
}

// Screen angles: degrees, clockwise from +x, y down (matches the flipped canvas).
inline CGPoint onCircle(CGPoint center, CGFloat radius, CGFloat degrees) {
  const CGFloat a = degrees * CGFloat(M_PI) / 180;
  return {center.x + radius * std::cos(a), center.y + radius * std::sin(a)};
}
inline void arc(CGContextRef c, CGPoint center, CGFloat radius, CGFloat from, CGFloat to, CGFloat width, Ink k,
                CGLineCap cap = kCGLineCapButt) {
  if (to <= from) return;
  CGContextSaveGState(c);
  setStroke(c, k);
  CGContextSetLineWidth(c, width);
  CGContextSetLineCap(c, cap);
  const int steps = std::max(2, int(std::ceil((to - from) / 2)));
  CGContextBeginPath(c);
  for (int i = 0; i <= steps; ++i) {
    const auto p = onCircle(center, radius, from + (to - from) * i / steps);
    if (i == 0) CGContextMoveToPoint(c, p.x, p.y);
    else CGContextAddLineToPoint(c, p.x, p.y);
  }
  CGContextStrokePath(c);
  CGContextRestoreGState(c);
}
// Arc whose colour blends along its length (segment-wise).
inline void arcBlend(CGContextRef c, CGPoint center, CGFloat radius, CGFloat from, CGFloat to, CGFloat width,
                     Ink a, Ink b, CGFloat t0 = 0, CGFloat t1 = 1) {
  if (to <= from) return;
  const int steps = std::max(1, int(std::ceil((to - from) / 2)));
  for (int i = 0; i < steps; ++i) {
    const CGFloat u0 = CGFloat(i) / steps, u1 = CGFloat(i + 1) / steps;
    const CGFloat t = t0 + (t1 - t0) * (u0 + u1) / 2;
    arc(c, center, radius, from + (to - from) * u0, from + (to - from) * u1 + .6, width, mix(a, b, t));
  }
}

// ---- text ---------------------------------------------------------------
// Global type multiplier: >1 on small windows so physical glyph size stays readable.
inline CGFloat gTypeScale = 1;
inline CTFontRef font(const char* face, CGFloat size) {
  static std::map<std::pair<std::string, int>, CTFontRef> cache;
  const auto key = std::make_pair(std::string(face), int(size * 4));
  auto it = cache.find(key);
  if (it != cache.end()) return it->second;
  CFStringRef name = CFStringCreateWithCString(kCFAllocatorDefault, face, kCFStringEncodingASCII);
  CTFontRef f = CTFontCreateWithName(name, size, nullptr);
  CFRelease(name);
  cache[key] = f;
  return f;
}
constexpr const char* kNumeric = "DINCondensed-Bold";
constexpr const char* kHeading = "AvenirNextCondensed-DemiBoldItalic";
constexpr const char* kHeavy = "AvenirNextCondensed-HeavyItalic";
constexpr const char* kBody = "AvenirNext-DemiBold";
constexpr const char* kBodyMedium = "AvenirNext-Medium";
constexpr const char* kLabel = "AvenirNextCondensed-DemiBold";

inline CTLineRef makeLine(const char* face, CGFloat size, const std::string& value, Ink k, CGFloat tracking) {
  CFStringRef string = CFStringCreateWithBytes(kCFAllocatorDefault, reinterpret_cast<const UInt8*>(value.data()),
                                               CFIndex(value.size()), kCFStringEncodingUTF8, false);
  if (!string) return nullptr;
  const CGFloat rgba[]{k.r, k.g, k.b, k.a};
  CGColorSpaceRef space = CGColorSpaceCreateDeviceRGB();
  CGColorRef color = CGColorCreate(space, rgba);
  CGColorSpaceRelease(space);
  CFNumberRef kern = CFNumberCreate(kCFAllocatorDefault, kCFNumberCGFloatType, &tracking);
  const void* keys[]{kCTFontAttributeName, kCTForegroundColorAttributeName, kCTKernAttributeName};
  const void* values[]{font(face, size * gTypeScale), color, kern};
  CFDictionaryRef attributes = CFDictionaryCreate(kCFAllocatorDefault, keys, values, 3, &kCFTypeDictionaryKeyCallBacks,
                                                  &kCFTypeDictionaryValueCallBacks);
  CFAttributedStringRef attributed = CFAttributedStringCreate(kCFAllocatorDefault, string, attributes);
  CTLineRef line = CTLineCreateWithAttributedString(attributed);
  CFRelease(attributed);
  CFRelease(attributes);
  CFRelease(kern);
  CGColorRelease(color);
  CFRelease(string);
  return line;
}
inline CGFloat measure(const char* face, CGFloat size, const std::string& value, CGFloat tracking = 0) {
  CTLineRef line = makeLine(face, size, value, white, tracking);
  if (!line) return 0;
  const CGFloat w = CTLineGetTypographicBounds(line, nullptr, nullptr, nullptr);
  CFRelease(line);
  return w;
}

enum class Align { Left, Right, Center };
// Draws one line; truncates with an ellipsis beyond `width`. Optional soft shadow
// keeps white text legible over the bright 3D scene.
inline CGFloat text(CGContextRef c, const char* face, CGFloat size, const std::string& value, CGFloat x,
                    CGFloat baseline, Ink k, CGFloat width = 1000, Align align = Align::Left, CGFloat tracking = 0,
                    bool shadow = false) {
  CTLineRef original = makeLine(face, size, value, k, tracking), line = original;
  if (!original) return 0;
  CTLineRef token = nullptr, truncated = nullptr;
  if (CTLineGetTypographicBounds(original, nullptr, nullptr, nullptr) > width) {
    token = makeLine(face, size, "…", k, tracking);
    truncated = CTLineCreateTruncatedLine(original, width, kCTLineTruncationEnd, token);
    if (truncated) line = truncated;
  }
  const CGFloat w = CTLineGetTypographicBounds(line, nullptr, nullptr, nullptr);
  if (align == Align::Right) x -= w;
  else if (align == Align::Center) x -= w / 2;
  CGContextSaveGState(c);
  if (shadow) CGContextSetShadowWithColor(c, {0, 1.5}, 4, shade(0, 0, 0, .75));
  CGContextSetTextMatrix(c, CGAffineTransformMakeScale(1, -1));
  CGContextSetTextPosition(c, x, baseline);
  CTLineDraw(line, c);
  CGContextRestoreGState(c);
  if (truncated) CFRelease(truncated);
  if (token) CFRelease(token);
  CFRelease(original);
  return w;
}

// Greedy word wrap; returns lines no wider than `width`.
inline std::vector<std::string> wrap(const char* face, CGFloat size, const std::string& value, CGFloat width) {
  std::vector<std::string> out;
  std::string line, word;
  auto flush = [&] {
    if (word.empty()) return;
    const std::string trial = line.empty() ? word : line + " " + word;
    if (!line.empty() && measure(face, size, trial) > width) {
      out.push_back(line);
      line = word;
    } else
      line = trial;
    word.clear();
  };
  for (char ch : value) {
    if (ch == ' ') flush();
    else word += ch;
  }
  flush();
  if (!line.empty()) out.push_back(line);
  return out;
}

// Keycap chip (rounded square with the key name); returns its width.
inline CGFloat keycap(CGContextRef c, const std::string& key, CGFloat x, CGFloat y, CGFloat height, Ink tone = white) {
  const CGFloat size = height * .56;
  const CGFloat w = std::max(height, measure(kNumeric, size, key, .6) + height * .62);
  fill(c, CGRectMake(x, y, w, height), {.10, .14, .17, .92}, height * .24);
  fill(c, CGRectMake(x, y + height - 3, w, 3), {0, 0, 0, .35}, 1.5);
  stroke(c, CGRectMake(x + .5, y + .5, w - 1, height - 1), {tone.r, tone.g, tone.b, .42}, 1, height * .24);
  text(c, kNumeric, size, key, x + w / 2, y + height * .72, tone, w, Align::Center, .6);
  return w;
}


// Small vector pictograms for menu rows (drawn in a size x size box centred at c).
// Stroke-based so they inherit the row's ink; shapes are deliberately simple.
inline void icon(CGContextRef c, ui::Icon kind, CGPoint at, CGFloat size, Ink k) {
  if (kind == ui::Icon::None) return;
  CGContextSaveGState(c);
  CGContextTranslateCTM(c, at.x, at.y);
  const CGFloat u = size / 20; // design grid: -10..10
  CGContextScaleCTM(c, u, u);
  setStroke(c, k);
  setFill(c, k);
  CGContextSetLineWidth(c, 2.2);
  CGContextSetLineCap(c, kCGLineCapRound);
  CGContextSetLineJoin(c, kCGLineJoinRound);
  auto line = [&](CGFloat x0, CGFloat y0, CGFloat x1, CGFloat y1) {
    CGContextBeginPath(c); CGContextMoveToPoint(c, x0, y0); CGContextAddLineToPoint(c, x1, y1); CGContextStrokePath(c);
  };
  auto circle = [&](CGFloat cx, CGFloat cy, CGFloat r, bool filled) {
    CGRect rect = CGRectMake(cx - r, cy - r, 2 * r, 2 * r);
    if (filled) CGContextFillEllipseInRect(c, rect); else CGContextStrokeEllipseInRect(c, rect);
  };
  using ui::Icon;
  switch (kind) {
  case Icon::Check: CGContextBeginPath(c); CGContextMoveToPoint(c, -7, 0); CGContextAddLineToPoint(c, -2, 5); CGContextAddLineToPoint(c, 7, -6); CGContextStrokePath(c); break;
  case Icon::Cross: line(-6, -6, 6, 6); line(6, -6, -6, 6); break;
  case Icon::Plus: line(-7, 0, 7, 0); line(0, -7, 0, 7); break;
  case Icon::Minus: line(-7, 0, 7, 0); break;
  case Icon::Retry:
    CGContextBeginPath(c);
    for (int i = 0; i <= 12; ++i) { const double a = (-40 + i * 25.) * M_PI / 180; const CGFloat x = 7 * std::cos(a), y = 7 * std::sin(a); if (i == 0) CGContextMoveToPoint(c, x, y); else CGContextAddLineToPoint(c, x, y); }
    CGContextStrokePath(c);
    CGContextBeginPath(c); CGContextMoveToPoint(c, 4, -9); CGContextAddLineToPoint(c, 6, -4); CGContextAddLineToPoint(c, 1, -3); CGContextClosePath(c); CGContextFillPath(c);
    break;
  case Icon::Play: CGContextBeginPath(c); CGContextMoveToPoint(c, -5, -7); CGContextAddLineToPoint(c, 7, 0); CGContextAddLineToPoint(c, -5, 7); CGContextClosePath(c); CGContextFillPath(c); break;
  case Icon::Stopwatch: circle(0, 2, 7, false); line(0, 2, 0, -2); line(0, 2, 3, 4); line(-2, -8, 2, -8); break;
  case Icon::Cog:
    circle(0, 0, 4, false);
    for (int i = 0; i < 8; ++i) { const double a = i * M_PI / 4; line(5.8 * std::cos(a), 5.8 * std::sin(a), 8.6 * std::cos(a), 8.6 * std::sin(a)); }
    break;
  case Icon::Brush:
    line(-6, 6, 2, -2); CGContextSetLineWidth(c, 4.5); line(3, -3, 7, -7); CGContextSetLineWidth(c, 2.2); circle(-6.5, 6.5, 1.8, true);
    break;
  case Icon::Flag: line(-6, -8, -6, 8); CGContextBeginPath(c); CGContextMoveToPoint(c, -6, -8); CGContextAddLineToPoint(c, 7, -5); CGContextAddLineToPoint(c, -6, 0); CGContextClosePath(c); CGContextFillPath(c); break;
  case Icon::Home: CGContextBeginPath(c); CGContextMoveToPoint(c, -8, 0); CGContextAddLineToPoint(c, 0, -8); CGContextAddLineToPoint(c, 8, 0); CGContextStrokePath(c); CGContextStrokeRect(c, CGRectMake(-5, 0, 10, 8)); break;
  case Icon::Power: line(0, -8, 0, -1); CGContextBeginPath(c); for (int i = 0; i <= 14; ++i) { const double a = (-60 + i * 25.7) * M_PI / 180 - M_PI / 2 + M_PI / 6; const CGFloat x = 7 * std::cos(a + M_PI / 2 + 0), y = 7 * std::sin(a + M_PI / 2) + 1; if (i == 0) CGContextMoveToPoint(c, x, y); else CGContextAddLineToPoint(c, x, y); } CGContextStrokePath(c); break;
  case Icon::Back: CGContextBeginPath(c); CGContextMoveToPoint(c, 3, -7); CGContextAddLineToPoint(c, -5, 0); CGContextAddLineToPoint(c, 3, 7); CGContextStrokePath(c); break;
  case Icon::Car:
    CGContextBeginPath(c); CGContextMoveToPoint(c, -9, 3); CGContextAddLineToPoint(c, -7, -2); CGContextAddLineToPoint(c, -3, -5); CGContextAddLineToPoint(c, 3, -5); CGContextAddLineToPoint(c, 7, -2); CGContextAddLineToPoint(c, 9, 3); CGContextClosePath(c); CGContextStrokePath(c);
    circle(-5, 4, 2.2, true); circle(5, 4, 2.2, true);
    break;
  case Icon::Sliders: line(-8, -4, 8, -4); line(-8, 4, 8, 4); circle(-2, -4, 2.6, true); circle(3, 4, 2.6, true); break;
  case Icon::Layers: for (CGFloat y : {-5., 0., 5.}) line(-7, y, 7, y); break;
  case Icon::Pin: circle(0, -2, 5, false); CGContextBeginPath(c); CGContextMoveToPoint(c, -3.5, 1.5); CGContextAddLineToPoint(c, 0, 9); CGContextAddLineToPoint(c, 3.5, 1.5); CGContextStrokePath(c); circle(0, -2, 1.6, true); break;
  case Icon::Bolt: CGContextBeginPath(c); CGContextMoveToPoint(c, 2, -9); CGContextAddLineToPoint(c, -5, 2); CGContextAddLineToPoint(c, 0, 2); CGContextAddLineToPoint(c, -2, 9); CGContextAddLineToPoint(c, 6, -3); CGContextAddLineToPoint(c, 1, -3); CGContextClosePath(c); CGContextFillPath(c); break;
  case Icon::Brake: circle(0, 0, 7, false); circle(0, 0, 3, true); break;
  case Icon::Wheel: circle(0, 0, 8, false); line(-8, 0, 8, 0); line(0, 0, 0, 8); break;
  case Icon::None: break;
  }
  CGContextRestoreGState(c);
}
} // namespace racer::paint
