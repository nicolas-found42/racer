#pragma once
#include <array>
#include <cstddef>
namespace racer {
struct VehicleSetup {
  double acceleration = 1, brake = 1, steering = 1;
  bool valid() const;
  bool operator==(const VehicleSetup &) const = default;
};
class GarageState {
public:
  std::array<VehicleSetup, 3> applied{};
  std::size_t selected = 0;
  VehicleSetup draft;
  bool dirty() const;
  bool apply();
  void discard();
  void defaults();
  // Dirty drafts require an explicit apply or discard before selection changes.
  bool select(std::size_t slot);
  bool valid() const;
};
} // namespace racer
