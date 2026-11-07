#pragma once
#include <cstdint>
#include <cstddef>
#include <string>
#include <string_view>
#include <vector>

namespace racer {
// Racer-authored engineering bounds, not recovered Juiced 2 restrictions.
inline constexpr size_t maxLiveryLayers = 32;
inline constexpr size_t maxLiveryDocumentBytes = 16384;
struct DecalTransform {
  double x = 0, y = 0, scaleX = 1, scaleY = 1, rotation = 0, opacity = 1;
  bool valid() const;
  bool operator==(const DecalTransform &) const = default;
};
struct DecalLayer {
  uint32_t id = 0;
  std::string decal;
  DecalTransform transform;
  bool visible = true;
  bool operator==(const DecalLayer &) const = default;
};
struct LiveryState {
  std::vector<DecalLayer> layers; // Back to front draw order.
  uint32_t selected = 0, nextId = 1;
  bool valid() const;
  bool operator==(const LiveryState &) const = default;
};
enum class LiveryError {
  None, InvalidDecal, LayerLimit, NoSelection, InvalidTransform,
  OutOfRange, InvalidDocument, UnsupportedVersion, IdentifierExhausted
};
struct LiveryResult {
  LiveryError error = LiveryError::None;
  bool changed = false;
  explicit operator bool() const { return error == LiveryError::None; }
};
// Decoding is transactional: failure leaves destination unchanged.
LiveryResult decodeLivery(std::string_view text, LiveryState &destination);
std::string encodeLivery(const LiveryState &state); // Empty if state invalid.
class LiveryEditor {
public:
  const LiveryState &applied() const { return applied_; }
  const LiveryState &draft() const { return draft_; }
  bool dirty() const { return draft_ != applied_; }
  LiveryResult add(std::string_view decal);
  LiveryResult select(uint32_t id);
  LiveryResult removeSelected();
  LiveryResult moveSelected(int direction); // Exactly -1 or +1.
  LiveryResult setTransform(const DecalTransform &transform);
  LiveryResult setVisible(bool visible);
  LiveryResult apply();
  LiveryResult cancel();
  LiveryResult clearDraft();
  LiveryResult loadApplied(std::string_view text);
  std::string serializedApplied() const { return encodeLivery(applied_); }
private:
  LiveryState applied_, draft_;
  DecalLayer *selection();
};
} // namespace racer
