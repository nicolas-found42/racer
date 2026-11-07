#pragma once
#include "diagnostics.h"
#include <bgfx/bgfx.h>
#include <atomic>
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
// bgfx fatal/trace callbacks may run on any thread; all others use its render thread.
struct Capture final : bgfx::CallbackI {
  racer::Diagnostics &diagnostics;
  size_t captureBytes = 0, captureCount = 0, callbackFailures = 0;
  std::atomic<size_t> traceCount{0};
  explicit Capture(racer::Diagnostics &sink) : diagnostics(sink) {}
  void fatal(const char *, uint16_t line, bgfx::Fatal::Enum code,
             const char *s) override {
    diagnostics.event("renderer_fatal", {{"code", int(code)}, {"line", line}});
    diagnostics.flush();
    std::cerr << s << '\n';
    std::abort();
  }
  void traceVargs(const char *, uint16_t, const char *f, va_list v) override {
    const auto ordinal = traceCount.fetch_add(1, std::memory_order_relaxed) + 1;
    if (ordinal <= 10) diagnostics.event("renderer_trace", {{"ordinal", ordinal}});
    vfprintf(stderr, f, v);
  }
  void profilerBegin(const char *, uint32_t, const char *, uint16_t) override {}
  void profilerBeginLiteral(const char *, uint32_t, const char *,
                            uint16_t) override {}
  void profilerEnd() override {}
  uint32_t cacheReadSize(uint64_t) override { return 0; }
  bool cacheRead(uint64_t, void *, uint32_t) override { return false; }
  void cacheWrite(uint64_t, const void *, uint32_t) override {}
  void screenShot(const char *p, uint32_t w, uint32_t h, uint32_t pitch,
                  bgfx::TextureFormat::Enum, const void *data, uint32_t,
                  bool flip) noexcept override {
    try {
    const auto captureId = racer::Diagnostics::identity(p);
    if (++captureCount > 48 || uint64_t(w) * h * 3 + captureBytes > 240 * 1024 * 1024) {
      diagnostics.event("capture_end", {{"capture", captureId}, {"success", false}, {"reason", "capture_quota"}});
      return;
    }
    captureBytes += uint64_t(w) * h * 3;
    std::ofstream out(p, std::ios::binary);
    out << "P6\n" << w << ' ' << h << "\n255\n";
    auto b = static_cast<const unsigned char *>(data);
    for (uint32_t y = 0; y < h; y++)
      for (uint32_t x = 0; x < w; x++) {
        auto c = b + (flip ? h - 1 - y : y) * pitch + x * 4;
        char rgb[] = {char(c[2]), char(c[1]), char(c[0])};
        out.write(rgb, 3);
      }
    out.close();
    diagnostics.event("capture_end", {{"capture", captureId}, {"width", w}, {"height", h},
      {"success", bool(out)}, {"callback_failures", callbackFailures}, {"sha256", out ? racer::Diagnostics::fileHash(p) : "unavailable"}});
    } catch (...) {
      // bgfx owns this callback thread. Optional capture/telemetry allocation
      // failures are retained as a count on the next successful capture.
      ++callbackFailures;
    }
  }
  void captureBegin(uint32_t, uint32_t, uint32_t, bgfx::TextureFormat::Enum,
                    bool) override {}
  void captureEnd() override {}
  void captureFrame(const void *, uint32_t) override {}
};
