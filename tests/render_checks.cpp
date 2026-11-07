#include "render_transform.h"
#include "render_capture.h"
#include "simulation.h"
#include "test_session.h"
#include <cmath>
#include <iostream>
#include <fstream>
#include <set>
#include <vector>
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
void trace(Capture &callback, const char *format, ...) {
  va_list args;
  va_start(args, format);
  callback.traceVargs("fixture", 1, format, args);
  va_end(args);
}
int main() {
  bool okay = true;
  for (double steer : {-1., 1.}) {
    racer::Simulation sim;
    sim.tick({}, 0);
    for (int i = 0; i < 120; ++i)
      sim.tick({1, 0, steer});
    float model[16];
    racer::worldTransform(model, sim.car.heading, sim.car.x, sim.car.z);
    // Transform the actual mesh's +Z nose (column 2). Compare it with the
    // simulation travel axis, also used by the chase-camera target.
    double dx = std::sin(sim.car.heading), dz = std::cos(sim.car.heading);
    double error = std::hypot(model[8] - dx, model[10] - dz);
    std::cout << "steer=" << steer << " heading=" << sim.car.heading
              << " travel/camera=" << dx << ',' << dz << " mesh="
              << model[8] << ',' << model[10] << " error=" << error << '\n';
    okay &= error < 1e-5;
  }
  for (const auto &g : racer::handlingCourse().gates) {
    float m[16];
    racer::worldTransform(m, std::atan2(g.nx, g.nz), g.x, g.z);
    okay &= std::hypot(m[8] - g.nx, m[10] - g.nz) < 1e-5;
  }
  char temporary[] = "/tmp/racer-render-check-XXXXXX";
  if (!mkdtemp(temporary)) return 1;
  const std::filesystem::path history(temporary);
  {
    racer::Diagnostics diagnostics(history);
    Capture callback(diagnostics);
    std::vector<std::thread> workers;
    for (int thread = 0; thread < 8; ++thread)
      workers.emplace_back([&] {
        for (int call = 0; call < 2000; ++call) trace(callback, "");
      });
    for (auto &worker : workers) worker.join();
    okay &= callback.traceCount.load() == 16000;
    const auto shot=(history / "allocation-probe.ppm").string();
    const unsigned char pixel[]={3,2,1,255};
    failObserverAllocation=true;
    callback.screenShot(shot.c_str(),1,1,4,bgfx::TextureFormat::BGRA8,pixel,4,false);
    failObserverAllocation=false;
    okay &= callback.callbackFailures==1 && !std::filesystem::exists(shot);
    callback.screenShot(shot.c_str(),1,1,4,bgfx::TextureFormat::BGRA8,pixel,4,false);
    std::ifstream ppm(shot,std::ios::binary);
    const std::string bytes{std::istreambuf_iterator<char>(ppm),{}};
    okay &= bytes==std::string("P6\n1 1\n255\n")+std::string("\1\2\3",3);

  }
  size_t events = 0;
  bool recoveredCapture=false;
  std::set<int> ordinals;
  for (const auto &file : std::filesystem::directory_iterator(history)) {
    if (file.path().extension() != ".jsonl") continue;
    std::ifstream in(file.path());
    for (std::string line; std::getline(in, line);) {
      const bool captureRecovery=line.find("\"event\":\"capture_end\"")!=std::string::npos && line.find("\"callback_failures\":1")!=std::string::npos;
      recoveredCapture |= captureRecovery;
      if (captureRecovery) std::cout<<"CAPTURE_EVIDENCE "<<line<<'\n';
      if (line.find("\"event\":\"renderer_trace\"") != std::string::npos) {
        ++events;
        ordinals.insert(std::stoi(line.substr(line.find("\"ordinal\":") + 10)));
      }
    }
  }
  okay &= recoveredCapture;
  okay &= events == 10 && ordinals.size() == 10 && *ordinals.begin() == 1 && *ordinals.rbegin() == 10;
  std::filesystem::remove_all(history);
  std::cout << "Concurrent callback calls=16000 retained=" << events << " unique=" << ordinals.size() << '\n';
  std::cout << (okay ? "PASS" : "FAIL")
            << ": rendered nose, travel/camera axis and gate arrows agree\n";
  return okay ? 0 : 1;
}
