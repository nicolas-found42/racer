#include "livery.h"
#include <algorithm>
#include <cmath>
#include <iomanip>
#include <limits>
#include <locale>
#include <sstream>
namespace racer {
namespace {
bool decalValid(std::string_view value) {
  if (value.empty() || value.size() > 64 || value == "." || value == "..") return false;
  return std::all_of(value.begin(), value.end(), [](unsigned char c) {
    return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
           (c >= '0' && c <= '9') || c == '_' || c == '-' || c == '.';
  });
}
bool readId(std::istream &in, uint32_t &out) {
  std::string token; if (!(in >> token) || token.empty() || token.size() > 10) return false;
  uint64_t value = 0;
  for (char c : token) {
    if (c < '0' || c > '9') return false;
    value = value * 10 + unsigned(c - '0');
    if (value > std::numeric_limits<uint32_t>::max()) return false;
  }
  out = uint32_t(value); return true;
}
bool range(double v, double lo, double hi) {
  return std::isfinite(v) && v >= lo && v <= hi;
}
LiveryResult error(LiveryError value) { return {value, false}; }
}
bool DecalTransform::valid() const {
  return range(x, -1, 1) && range(y, -1, 1) &&
         range(scaleX, .01, 4) && range(scaleY, .01, 4) &&
         range(rotation, -180, 180) && range(opacity, 0, 1);
}
bool LiveryState::valid() const {
  if (layers.size() > maxLiveryLayers || nextId == 0) return false;
  if (layers.empty()) return selected == 0;
  if (!selected) return false;
  bool found = false;
  for (size_t i = 0; i < layers.size(); ++i) {
    const auto &l = layers[i];
    if (!l.id || l.id >= nextId || !decalValid(l.decal) || !l.transform.valid()) return false;
    for (size_t j = 0; j < i; ++j) if (layers[j].id == l.id) return false;
    found |= l.id == selected;
  }
  return found;
}
std::string encodeLivery(const LiveryState &state) {
  if (!state.valid()) return {};
  std::ostringstream out; out.imbue(std::locale::classic());
  out << std::setprecision(17) << "RACER_LIVERY 1\n" << state.nextId << ' '
      << state.selected << ' ' << state.layers.size() << '\n';
  for (const auto &l : state.layers) {
    const auto &t = l.transform;
    out << l.id << ' ' << l.decal << ' ' << t.x << ' ' << t.y << ' '
        << t.scaleX << ' ' << t.scaleY << ' ' << t.rotation << ' ' << t.opacity
        << ' ' << int(l.visible) << '\n';
  }
  out << "END\n";
  return out.str();
}
LiveryResult decodeLivery(std::string_view text, LiveryState &destination) {
  if (text.size() > maxLiveryDocumentBytes) return error(LiveryError::InvalidDocument);
  std::istringstream in{std::string(text)}; in.imbue(std::locale::classic());
  std::string magic, end; int version = 0; LiveryState candidate; uint32_t count = 0;
  if (!(in >> magic >> version) || magic != "RACER_LIVERY") return error(LiveryError::InvalidDocument);
  if (version != 1) return error(LiveryError::UnsupportedVersion);
  if (!readId(in, candidate.nextId) || !readId(in, candidate.selected) ||
      !readId(in, count) || count > maxLiveryLayers)
    return error(LiveryError::InvalidDocument);
  for (size_t i = 0; i < count; ++i) {
    DecalLayer l; int visible = -1; auto &t = l.transform;
    if (!readId(in, l.id) || !(in >> l.decal >> t.x >> t.y >> t.scaleX >> t.scaleY >>
          t.rotation >> t.opacity >> visible) || (visible != 0 && visible != 1))
      return error(LiveryError::InvalidDocument);
    l.visible = visible == 1; candidate.layers.push_back(l);
  }
  if (!(in >> end) || end != "END") return error(LiveryError::InvalidDocument);
  in >> std::ws;
  if (!in.eof() || !candidate.valid()) return error(LiveryError::InvalidDocument);
  const bool changed = destination != candidate; destination = std::move(candidate);
  return {LiveryError::None, changed};
}
DecalLayer *LiveryEditor::selection() {
  auto it = std::find_if(draft_.layers.begin(), draft_.layers.end(),
                         [&](const auto &l) { return l.id == draft_.selected; });
  return it == draft_.layers.end() ? nullptr : &*it;
}
LiveryResult LiveryEditor::add(std::string_view decal) {
  if (!decalValid(decal)) return error(LiveryError::InvalidDecal);
  if (draft_.layers.size() == maxLiveryLayers) return error(LiveryError::LayerLimit);
  if (draft_.nextId == std::numeric_limits<uint32_t>::max()) return error(LiveryError::IdentifierExhausted);
  auto id = draft_.nextId;
  draft_.layers.push_back({id, std::string(decal), {}, true});
  ++draft_.nextId; draft_.selected = id;
  return {LiveryError::None, true};
}
LiveryResult LiveryEditor::select(uint32_t id) {
  if (!std::any_of(draft_.layers.begin(), draft_.layers.end(), [&](const auto &l) { return l.id == id; }))
    return error(LiveryError::NoSelection);
  bool changed = draft_.selected != id; draft_.selected = id;
  return {LiveryError::None, changed};
}
LiveryResult LiveryEditor::removeSelected() {
  auto *l = selection(); if (!l) return error(LiveryError::NoSelection);
  size_t index = size_t(l - draft_.layers.data());
  draft_.layers.erase(draft_.layers.begin() + index);
  draft_.selected = draft_.layers.empty() ? 0 : draft_.layers[std::min(index, draft_.layers.size()-1)].id;
  return {LiveryError::None, true};
}
LiveryResult LiveryEditor::moveSelected(int direction) {
  if (direction != -1 && direction != 1) return error(LiveryError::OutOfRange);
  auto *l = selection(); if (!l) return error(LiveryError::NoSelection);
  auto index = l - draft_.layers.data(); auto next = index + direction;
  if (next < 0 || size_t(next) >= draft_.layers.size()) return error(LiveryError::OutOfRange);
  std::swap(draft_.layers[size_t(index)], draft_.layers[size_t(next)]);
  return {LiveryError::None, true};
}
LiveryResult LiveryEditor::setTransform(const DecalTransform &transform) {
  if (!transform.valid()) return error(LiveryError::InvalidTransform);
  auto *l = selection(); if (!l) return error(LiveryError::NoSelection);
  bool changed = l->transform != transform; l->transform = transform;
  return {LiveryError::None, changed};
}
LiveryResult LiveryEditor::setVisible(bool visible) {
  auto *l = selection(); if (!l) return error(LiveryError::NoSelection);
  bool changed = l->visible != visible; l->visible = visible;
  return {LiveryError::None, changed};
}
LiveryResult LiveryEditor::apply() {
  bool changed = dirty(); applied_ = draft_; return {LiveryError::None, changed};
}
LiveryResult LiveryEditor::cancel() {
  bool changed = dirty(); draft_ = applied_; return {LiveryError::None, changed};
}
LiveryResult LiveryEditor::clearDraft() {
  LiveryState empty; empty.nextId = draft_.nextId;
  bool changed = draft_ != empty; draft_ = empty;
  return {LiveryError::None, changed};
}
LiveryResult LiveryEditor::loadApplied(std::string_view text) {
  LiveryState candidate; auto result = decodeLivery(text, candidate);
  if (!result) return result;
  result.changed = applied_ != candidate || draft_ != candidate;
  applied_ = candidate; draft_ = std::move(candidate); return result;
}
} // namespace racer
