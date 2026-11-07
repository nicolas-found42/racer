#pragma once
#include <cstdint>
#include <optional>
#include <string>
#include <vector>
namespace racer {
// Racer-authored domain rules; donor resource IDs remain package-qualified.
enum class PartKind { Body, Engine, Wheel, Tyre, Accessory };
struct WheelDimensions { double radiusMm = 0, widthMm = 0; };
struct TyreFitment { double rimRadiusMm = 0, minRimWidthMm = 0, maxRimWidthMm = 0; };
struct PartSlot {
  std::string id;
  PartKind kind = PartKind::Accessory;
  // Empty means the typed kind is sufficient; otherwise exact qualified IDs.
  std::vector<std::string> acceptedParts;
};
struct PartDefinition {
  std::string id, name;
  PartKind kind = PartKind::Accessory;
  std::vector<PartSlot> slots;
  std::optional<WheelDimensions> wheel;
  std::optional<TyreFitment> tyre;
};
struct PartsCatalog {
  std::vector<PartDefinition> definitions;
  const PartDefinition *find(const std::string &id) const;
  bool valid() const;
};
enum class PartFailure {
  None, InvalidState, UnknownPart, InventoryFull, UnknownInstance,
  AlreadyInstalled, ParentNotMounted, UnknownSlot, SlotOccupied,
  WrongKind, IncompatiblePart, RimRadius, RimWidth, RootRemoval,
  NotInstalled, DependentParts, InvalidSave
};
const char *partFailureText(PartFailure reason);
struct PartResult {
  PartFailure failure = PartFailure::None;
  std::uint64_t instance = 0;
  explicit operator bool() const { return failure == PartFailure::None; }
  const char *message() const { return partFailureText(failure); }
};
struct PartMount { std::uint64_t parent = 0; std::string slot; };
struct OwnedPart {
  std::uint64_t instance = 0;
  std::string partId;
  std::optional<PartMount> mount;
};
class PartAssembly {
public:
  // Invalid catalog/root throws invalid_argument. The root must be a Body.
  PartAssembly(PartsCatalog catalog, const std::string &rootPart);
  static constexpr std::size_t maxOwnedParts = 128;
  static constexpr double rimToleranceMm = .01; // authored numeric tolerance
  const PartsCatalog &catalog() const { return catalog_; }
  const std::vector<OwnedPart> &inventory() const { return parts_; }
  const OwnedPart *find(std::uint64_t instance) const;
  bool mounted(std::uint64_t instance) const;
  bool valid() const;
  PartResult acquire(const std::string &partId);
  PartResult install(std::uint64_t instance, std::uint64_t parent, const std::string &slot);
  PartResult remove(std::uint64_t instance);
  std::string serialize() const;
  // Replacement is transactional; malformed/unsupported/incompatible state is rejected.
  PartResult restore(const std::string &text);
private:
  PartsCatalog catalog_;
  std::vector<OwnedPart> parts_;
  std::uint64_t next_ = 2;
  PartFailure fit(const OwnedPart &part, const OwnedPart &parent, const std::string &slot) const;
};
} // namespace racer
