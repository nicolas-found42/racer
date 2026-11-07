#include "parts.h"
#include <algorithm>
#include <cmath>
#include <iomanip>
#include <set>
#include <sstream>
#include <stdexcept>
namespace racer {
namespace {
bool token(const std::string &s, bool qualified = false) {
  if (s.empty() || s.size() > 192) return false;
  for (unsigned char c : s)
    if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
          (c >= '0' && c <= '9') || c == '_' || c == '-' || c == '.' || c == '/' || c == ':')) return false;
  const auto colon = s.find(':');
  return !qualified || (colon != std::string::npos && colon > 0 && colon + 1 < s.size());
}
bool positive(double n) { return std::isfinite(n) && n > 0 && n <= 10000; }
bool kindValid(PartKind k) { return k >= PartKind::Body && k <= PartKind::Accessory; }
}
const PartDefinition *PartsCatalog::find(const std::string &id) const {
  for (const auto &part : definitions) if (part.id == id) return &part;
  return nullptr;
}
bool PartsCatalog::valid() const {
  if (definitions.empty() || definitions.size() > 8192) return false;
  std::set<std::string> ids;
  for (const auto &p : definitions) {
    if (!token(p.id, true) || !ids.insert(p.id).second || !kindValid(p.kind) ||
        p.name.empty() || p.name.size() > 192 || p.slots.size() > 32) return false;
    if ((p.kind == PartKind::Wheel) != p.wheel.has_value() ||
        (p.kind == PartKind::Tyre) != p.tyre.has_value()) return false;
    if (p.wheel && (!positive(p.wheel->radiusMm) || !positive(p.wheel->widthMm))) return false;
    if (p.tyre && (!positive(p.tyre->rimRadiusMm) || !positive(p.tyre->minRimWidthMm) ||
        !positive(p.tyre->maxRimWidthMm) || p.tyre->minRimWidthMm > p.tyre->maxRimWidthMm)) return false;
    std::set<std::string> slots;
    for (const auto &s : p.slots) {
      if (!token(s.id) || !slots.insert(s.id).second || !kindValid(s.kind) || s.acceptedParts.size() > 128) return false;
      std::set<std::string> accepted;
      for (const auto &id : s.acceptedParts)
        if (!token(id,true) || !accepted.insert(id).second) return false;
    }
  }
  for (const auto &p : definitions) for (const auto &s : p.slots)
    for (const auto &id : s.acceptedParts) {
      auto part = find(id);
      if (!part || part->kind != s.kind) return false;
    }
  return true;
}
const char *partFailureText(PartFailure r) {
  switch (r) {
  case PartFailure::None: return "Part operation complete.";
  case PartFailure::InvalidState: return "Parts state is invalid.";
  case PartFailure::UnknownPart: return "Part is not in this catalog.";
  case PartFailure::InventoryFull: return "Owned parts inventory is full.";
  case PartFailure::UnknownInstance: return "Owned part was not found.";
  case PartFailure::AlreadyInstalled: return "Remove this part before installing it elsewhere.";
  case PartFailure::ParentNotMounted: return "Install the parent part first.";
  case PartFailure::UnknownSlot: return "Parent part has no such slot.";
  case PartFailure::SlotOccupied: return "Remove the existing part from this slot first.";
  case PartFailure::WrongKind: return "This slot accepts a different part type.";
  case PartFailure::IncompatiblePart: return "This part is not compatible with this slot.";
  case PartFailure::RimRadius: return "Tyre requires a different rim radius.";
  case PartFailure::RimWidth: return "Rim width is outside this tyre's accepted range.";
  case PartFailure::RootRemoval: return "The vehicle root cannot be removed.";
  case PartFailure::NotInstalled: return "This part is already in inventory.";
  case PartFailure::DependentParts: return "Remove mounted child parts first.";
  case PartFailure::InvalidSave: return "Parts save is malformed, unsupported or incompatible.";
  }
  return "Unknown parts failure.";
}
PartAssembly::PartAssembly(PartsCatalog catalog, const std::string &rootPart) : catalog_(std::move(catalog)) {
  auto root = catalog_.find(rootPart);
  if (!catalog_.valid() || !root || root->kind != PartKind::Body)
    throw std::invalid_argument("Invalid parts catalog or vehicle root");
  parts_.push_back({1,rootPart,std::nullopt});
}
const OwnedPart *PartAssembly::find(std::uint64_t id) const {
  for (const auto &part : parts_) if (part.instance == id) return &part;
  return nullptr;
}
bool PartAssembly::mounted(std::uint64_t id) const {
  // Bound the walk even for malformed restored cycles.
  for (std::size_t depth=0; depth <= parts_.size(); ++depth) {
    auto p = find(id); if (!p) return false;
    if (id == 1) return !p->mount;
    if (!p->mount) return false;
    id = p->mount->parent;
  }
  return false;
}
PartFailure PartAssembly::fit(const OwnedPart &part, const OwnedPart &parent, const std::string &slot) const {
  const auto p=catalog_.find(part.partId), owner=catalog_.find(parent.partId);
  if (!p || !owner) return PartFailure::UnknownPart;
  auto s=std::find_if(owner->slots.begin(),owner->slots.end(),[&](const auto &v){return v.id==slot;});
  if (s==owner->slots.end()) return PartFailure::UnknownSlot;
  if (s->kind!=p->kind) return PartFailure::WrongKind;
  if (!s->acceptedParts.empty() && std::find(s->acceptedParts.begin(),s->acceptedParts.end(),p->id)==s->acceptedParts.end()) return PartFailure::IncompatiblePart;
  if (p->tyre) {
    if (!owner->wheel) return PartFailure::IncompatiblePart;
    if (std::abs(owner->wheel->radiusMm-p->tyre->rimRadiusMm)>rimToleranceMm) return PartFailure::RimRadius;
    if (owner->wheel->widthMm<p->tyre->minRimWidthMm || owner->wheel->widthMm>p->tyre->maxRimWidthMm) return PartFailure::RimWidth;
  }
  return PartFailure::None;
}
bool PartAssembly::valid() const {
  if (parts_.empty() || parts_.size()>maxOwnedParts || !catalog_.valid()) return false;
  auto root=find(1); if (!root || root->mount) return false;
  auto rootDefinition=catalog_.find(root->partId);
  if (!rootDefinition || rootDefinition->kind!=PartKind::Body) return false;
  std::set<std::uint64_t> ids; std::set<std::pair<std::uint64_t,std::string>> occupied;
  for (const auto &p:parts_) {
    if (!p.instance || p.instance>=next_ || p.instance>1000000000 || !ids.insert(p.instance).second || !catalog_.find(p.partId)) return false;
    if (p.mount) {
      auto parent=find(p.mount->parent);
      if (!parent || parent==&p || !mounted(p.instance) || !occupied.insert({p.mount->parent,p.mount->slot}).second || fit(p,*parent,p.mount->slot)!=PartFailure::None) return false;
    }
  }
  return true;
}
PartResult PartAssembly::acquire(const std::string &id) {
  if (!catalog_.find(id)) return {PartFailure::UnknownPart};
  if (parts_.size()>=maxOwnedParts || next_>1000000000) return {PartFailure::InventoryFull};
  parts_.push_back({next_,id,std::nullopt}); return {PartFailure::None,next_++};
}
PartResult PartAssembly::install(std::uint64_t id,std::uint64_t parentId,const std::string &slot) {
  auto p=find(id),parent=find(parentId);
  if (!p || !parent) return {PartFailure::UnknownInstance};
  if (id==1 || p->mount) return {PartFailure::AlreadyInstalled};
  if (id==parentId || !mounted(parentId)) return {PartFailure::ParentNotMounted};
  auto reason=fit(*p,*parent,slot); if (reason!=PartFailure::None) return {reason};
  for (const auto &other:parts_) if (other.mount && other.mount->parent==parentId && other.mount->slot==slot) return {PartFailure::SlotOccupied};
  PartMount mount{parentId,slot};
  for (auto &owned:parts_) if (owned.instance==id) owned.mount=std::move(mount);
  return {PartFailure::None,id};
}
PartResult PartAssembly::remove(std::uint64_t id) {
  auto p=find(id); if (!p) return {PartFailure::UnknownInstance};
  if (id==1) return {PartFailure::RootRemoval};
  if (!p->mount) return {PartFailure::NotInstalled};
  for (const auto &other:parts_) if (other.mount && other.mount->parent==id) return {PartFailure::DependentParts};
  for (auto &owned:parts_) if (owned.instance==id) owned.mount.reset();
  return {PartFailure::None,id};
}
std::string PartAssembly::serialize() const {
  std::ostringstream out; out<<"RACER_PARTS 1\n"<<next_<<' '<<parts_.size()<<'\n';
  for (const auto &p:parts_) out<<p.instance<<' '<<std::quoted(p.partId)<<' '<<(p.mount?p.mount->parent:0)<<' '<<std::quoted(p.mount?p.mount->slot:"")<<'\n';
  return out.str();
}
PartResult PartAssembly::restore(const std::string &text) {
  if (text.size()>65536) return {PartFailure::InvalidSave};
  try {
    std::istringstream in(text); std::string magic; unsigned version; std::size_t count; auto next=*this;
    if (!(in>>magic>>version) || magic!="RACER_PARTS" || version!=1 || !(in>>next.next_>>count) || count<1 || count>maxOwnedParts || next.next_>1000000001) return {PartFailure::InvalidSave};
    next.parts_.clear();
    for (std::size_t i=0;i<count;++i) {
      OwnedPart p; std::uint64_t parent; std::string slot;
      if (!(in>>p.instance>>std::quoted(p.partId)>>parent>>std::quoted(slot))) return {PartFailure::InvalidSave};
      if (parent) p.mount=PartMount{parent,slot}; else if (!slot.empty()) return {PartFailure::InvalidSave};
      next.parts_.push_back(std::move(p));
    }
    in>>std::ws;
    auto oldRoot=find(1),newRoot=next.find(1);
    if (!in.eof() || !oldRoot || !newRoot || oldRoot->partId!=newRoot->partId || !next.valid()) return {PartFailure::InvalidSave};
    parts_=std::move(next.parts_); next_=next.next_; return {};
  } catch (const std::exception &) { return {PartFailure::InvalidSave}; }
}
} // namespace racer
