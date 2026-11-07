#include "setup.h"
#include <cmath>
namespace racer {
bool VehicleSetup::valid() const {
  for (double value : {acceleration, brake, steering})
    if (!std::isfinite(value) || value < .8 || value > 1.2)
      return false;
  return true;
}
bool GarageState::valid() const {
  if (selected >= applied.size() || !draft.valid())
    return false;
  for (const auto &setup : applied)
    if (!setup.valid())
      return false;
  return true;
}
bool GarageState::dirty() const {
  return selected >= applied.size() || draft != applied[selected];
}
bool GarageState::apply() {
  if (selected >= applied.size() || !draft.valid())
    return false;
  applied[selected] = draft;
  return true;
}
void GarageState::discard() {
  if (selected < applied.size())
    draft = applied[selected];
}
void GarageState::defaults() { draft = {}; }
bool GarageState::select(std::size_t slot) {
  if (slot >= applied.size() || dirty())
    return false;
  selected = slot;
  discard();
  return true;
}
} // namespace racer
