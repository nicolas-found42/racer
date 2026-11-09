#pragma once
// Car geometries for physics checks: synthetic bodies that span the catalogued
// range (clearance 8.6-22 cm, wheelbase 1.8-3.6 m, wheel radius .26-.40 m) and,
// when present, every real local descriptor under assets/local/vehicles. The
// real files are ignored game assets; their absence only shortens the list.
#include "vehicle_geometry.h"
#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

struct NamedGeometry {
  std::string name;
  racer::VehicleGeometry geometry;
};

inline racer::VehicleGeometry syntheticGeometry(double wheelbase, double halfTrack,
                                                double radius, double clearance,
                                                double height, double frontOverhang,
                                                double rearOverhang, double halfWidth) {
  racer::VehicleGeometry g;
  g.body = {{-halfWidth, clearance, -(wheelbase / 2 + rearOverhang)},
            {halfWidth, height, wheelbase / 2 + frontOverhang}};
  const double y = radius, front = wheelbase / 2;
  g.wheels = {{{{-halfTrack, y, front}, radius, .25},
               {{halfTrack, y, front}, radius, .25},
               {{-halfTrack, y, -front}, radius, .25},
               {{halfTrack, y, -front}, radius, .25}}};
  return g;
}

inline std::vector<NamedGeometry> syntheticCars() {
  return {{"default 2.7 m", racer::VehicleGeometry{}},
          {"low sports 8.6 cm", syntheticGeometry(2.72, .82, .32, .086, 1.1, .8, .75, .99)},
          {"compact 1.84 m", syntheticGeometry(1.84, .57, .265, .17, 1.65, .5, .45, .70)},
          {"truck 3.57 m", syntheticGeometry(3.57, .87, .40, .22, 1.93, 1.2, 1.0, 1.2)},
          {"wide estate 2.9 m", syntheticGeometry(2.9, 1.0, .36, .15, 1.45, .9, .9, 1.1)}};
}

// Parses `body minx miny minz maxx maxy maxz` and four
// `wheel NAME x y z radius width` lines (FL FR RL RR).
inline std::vector<NamedGeometry> localCars(const std::filesystem::path &directory) {
  std::vector<NamedGeometry> cars;
  std::error_code error;
  if (!std::filesystem::is_directory(directory, error)) return cars;
  std::vector<std::filesystem::path> files;
  for (const auto &entry : std::filesystem::directory_iterator(directory, error))
    if (entry.path().extension() == ".vehicle") files.push_back(entry.path());
  std::sort(files.begin(), files.end());
  for (const auto &file : files) {
    std::ifstream in(file);
    racer::VehicleGeometry g;
    std::string line, name = file.stem().string().substr(0, 8);
    int wheels = 0;
    bool body = false;
    while (std::getline(in, line)) {
      std::istringstream fields(line);
      std::string key;
      fields >> key;
      if (key == "name") {
        const auto first = line.find('"'), last = line.rfind('"');
        if (first != std::string::npos && last > first) name = line.substr(first + 1, last - first - 1);
      } else if (key == "body") {
        body = bool(fields >> g.body.minimum.x >> g.body.minimum.y >> g.body.minimum.z >>
                    g.body.maximum.x >> g.body.maximum.y >> g.body.maximum.z);
      } else if (key == "wheel" && wheels < 4) {
        std::string wheelName;
        auto &w = g.wheels[size_t(wheels)];
        if (fields >> wheelName >> w.center.x >> w.center.y >> w.center.z >> w.radius >> w.width) ++wheels;
      }
    }
    if (body && wheels == 4 && g.valid()) cars.push_back({name + " [" + file.stem().string().substr(0, 6) + "]", g});
  }
  return cars;
}

// Synthetic cars plus real descriptors found under argv[1] (if given).
inline std::vector<NamedGeometry> allCars(int argc, char **argv) {
  auto cars = syntheticCars();
  if (argc > 1)
    for (auto &car : localCars(argv[1])) cars.push_back(std::move(car));
  return cars;
}
