#include "garage_features.h"
#include <algorithm>
#include <cmath>
#include <iomanip>
#include <sstream>
namespace racer {
namespace {
constexpr const char *body = "racer:prototype";
constexpr const char *catalogIds[] = {"racer:stock_engine", "racer:upgrade_engine", "racer:stock_wheel", "racer:wrong_wheel", "racer:stock_tyre"};
constexpr const char *decals[] = {"stripe", "number", "checker"};
PartsCatalog prototypeCatalog() {
  // Racer-authored catalog and effect; these are not recovered donor numbers.
  PartsCatalog c;
  c.definitions.push_back({body, "Prototype body", PartKind::Body,
      {{"engine", PartKind::Engine, {}}, {"wheel", PartKind::Wheel, {}}}, {}, {}});
  c.definitions.push_back({catalogIds[0], "Stock engine", PartKind::Engine, {}, {}, {}});
  c.definitions.push_back({catalogIds[1], "Upgrade engine", PartKind::Engine, {}, {}, {}});
  c.definitions.push_back({catalogIds[2], "18-inch stock rim", PartKind::Wheel,
      {{"tyre",PartKind::Tyre,{}}}, WheelDimensions{228.6,200}, {}});
  c.definitions.push_back({catalogIds[3], "20-inch incompatible rim", PartKind::Wheel,
      {{"tyre",PartKind::Tyre,{}}}, WheelDimensions{254,200}, {}});
  c.definitions.push_back({catalogIds[4], "18-inch stock tyre", PartKind::Tyre, {}, {}, TyreFitment{228.6,190,235}});
  return c;
}
std::filesystem::path sidecar(const std::string &profile, const char *suffix) {
  return profile.empty() ? std::filesystem::path{} : std::filesystem::path(profile + suffix);
}
bool knownDecal(const std::string &name) {
  return std::any_of(std::begin(decals), std::end(decals), [&](const auto *id) { return name == id; });
}
std::string number(double value) { std::ostringstream out; out << std::fixed << std::setprecision(2) << value; return out.str(); }
std::string persistence(const char *label, const DocumentStore &store, bool dirty = false) {
  const auto status = store.outcome().status;
  if (!store.writable() || status == DocumentStatus::Disabled)
    return std::string(label) + ": saving disabled; original preserved.";
  if (status == DocumentStatus::Failed)
    return std::string("UNSAVED ") + label + ": active in memory; Retry save.";
  if (status == DocumentStatus::Loaded)
    return std::string(label) + ": loaded from disk" + (dirty ? " (draft excluded)." : ".");
  if (status == DocumentStatus::Saved)
    return std::string(label) + ": saved to disk" + (dirty ? " (draft excluded)." : ".");
  return std::string(label) + ": default in memory; not saved yet.";
}
const DecalLayer *selected(const LiveryState &state) {
  for (const auto &layer : state.layers) if (layer.id == state.selected) return &layer;
  return nullptr;
}
}
GarageFeatures::GarageFeatures(const std::string &profilePath, Diagnostics *diagnostics)
    : parts_(prototypeCatalog(), body),
      partsStore_(sidecar(profilePath,".parts"),DocumentComponent::Parts,65536,diagnostics),
      liveryStore_(sidecar(profilePath,".livery"),DocumentComponent::Livery,maxLiveryDocumentBytes,diagnostics), diagnostics_(diagnostics) {
  auto engine = parts_.acquire(catalogIds[0]); parts_.install(engine.instance,1,"engine");
  auto wheel = parts_.acquire(catalogIds[2]); parts_.install(wheel.instance,1,"wheel");
  auto tyre = parts_.acquire(catalogIds[4]); parts_.install(tyre.instance,wheel.instance,"tyre");
  parts_.acquire(catalogIds[1]); parts_.acquire(catalogIds[3]);
  std::string text;
  auto result = partsStore_.load(text);
  if (result.status == DocumentStatus::Loaded && !parts_.restore(text)) {
    partsStore_.disableWrites(); partsMessage_ = "Malformed parts document; stock assembly in memory.";
  } else if (!result) partsMessage_ = "Parts document unavailable; stock assembly in memory.";
  text.clear(); result = liveryStore_.load(text);
  if (result.status == DocumentStatus::Loaded) {
    LiveryEditor candidate;
    bool okay = bool(candidate.loadApplied(text));
    if (okay) for (const auto &layer : candidate.applied().layers) okay &= knownDecal(layer.decal);
    if (okay) livery_ = std::move(candidate);
    else { liveryStore_.disableWrites(); liveryMessage_ = "Malformed or unknown-decal document; empty livery in memory."; }
  } else if (!result) liveryMessage_ = "Livery document unavailable; empty livery in memory.";
  partsIdentity_ = Diagnostics::identity(parts_.serialize());
  if (diagnostics_) for (const auto &part : parts_.inventory())
    diagnostics_->event("feature_inventory", {{"instance",part.instance},{"definition",part.partId},
      {"parent",part.mount ? part.mount->parent : 0},{"slot",part.mount ? part.mount->slot : ""}});
  appliedLayers();
}
uint64_t GarageFeatures::selectedPart() const { return parts_.inventory()[std::min(ownedIndex_,parts_.inventory().size()-1)].instance; }
uint64_t GarageFeatures::mounted(PartKind kind) const {
  for (const auto &part : parts_.inventory()) if (parts_.catalog().find(part.partId)->kind == kind && parts_.mounted(part.instance)) return part.instance;
  return 0;
}
bool GarageFeatures::hasEngine() const { return mounted(PartKind::Engine) != 0; }
VehicleSetup GarageFeatures::partMultipliers() const {
  auto id = mounted(PartKind::Engine); auto part = parts_.find(id);
  return {part && part->partId == catalogIds[1] ? 1.15 : 1., 1, 1};
}
int GarageFeatures::menuCount(GarageFeaturePage page) { return page == GarageFeaturePage::Parts ? 7 : 17; }
void GarageFeatures::saveParts() { partsStore_.context(operation_); partsStore_.save(parts_.serialize()); }
void GarageFeatures::saveLivery() { liveryStore_.context(operation_); liveryStore_.save(livery_.serializedApplied()); }
void GarageFeatures::leave(GarageFeaturePage page, int menu) {
  operation_ = diagnostics_ ? diagnostics_->operation() : operation_ + 1;
  const bool discarded = page == GarageFeaturePage::Livery && livery_.dirty();
  if (page == GarageFeaturePage::Livery && livery_.dirty()) { livery_.cancel(); ++draftRevision_; }
  if (diagnostics_) diagnostics_->event("feature_leave", {{"page",int(page)},{"menu",menu},{"discarded_draft",discarded}},operation_);
  observe(page,menu);
}
void GarageFeatures::appliedLayers() {
  if (!diagnostics_) return;
  size_t order = 0;
  for (const auto &layer : livery_.applied().layers) {
    const auto &t = layer.transform;
    diagnostics_->event("feature_layer", {{"revision",liveryRevision_},{"order",order++},{"layer",layer.id},
      {"decal",layer.decal},{"x",t.x},{"y",t.y},{"scale_x",t.scaleX},{"scale_y",t.scaleY},
      {"rotation",t.rotation},{"opacity",t.opacity},{"visible",layer.visible}}, operation_);
  }
}
bool GarageFeatures::action(GarageFeaturePage page, int row, FeatureAction command, uint64_t parent) {
  operation_ = diagnostics_ ? diagnostics_->operation() : operation_ + 1;
  partsStore_.context(operation_); liveryStore_.context(operation_);
  int direction = command == FeatureAction::Decrease ? -1 : 1;
  bool activate = command == FeatureAction::Activate, exit = false, changed = false;
  int rejection = 0;
  if (row < 0 || row >= menuCount(page)) return false;
  if (page == GarageFeaturePage::Parts) {
    PartResult result;
    bool mutation = false;
    if (row == 0 && !activate) catalogIndex_ = (catalogIndex_ + 5 + direction) % 5;
    else if (row == 2 && !activate) ownedIndex_ = (ownedIndex_ + parts_.inventory().size() + direction) % parts_.inventory().size();
    else if (activate && row == 1) {
      result = parts_.acquire(catalogIds[catalogIndex_]); mutation = bool(result);
      if (mutation) ownedIndex_ = parts_.inventory().size()-1;
    } else if (activate && row == 3) {
      const auto *part = parts_.find(selectedPart()); auto kind = parts_.catalog().find(part->partId)->kind;
      result = parts_.install(part->instance, kind == PartKind::Tyre ? mounted(PartKind::Wheel) : 1,
                             kind == PartKind::Tyre ? "tyre" : kind == PartKind::Wheel ? "wheel" : "engine"); mutation = bool(result);
    } else if (activate && row == 4) { result = parts_.remove(selectedPart()); mutation = bool(result); }
    else if (activate && row == 5) { saveParts(); partsMessage_ = "Save retried for the current assembly."; }
    else if (activate && row == 6) exit = true;
    if (activate && (row == 1 || row == 3 || row == 4)) {
      rejection = int(result.failure); partsMessage_ = result.message();
      if (mutation) { ++partsRevision_; changed = true; partsIdentity_ = Diagnostics::identity(parts_.serialize()); saveParts(); }
    }
  } else {
    LiveryResult result;
    auto *layer = selected(livery_.draft());
    if (row == 0 && !activate) decalIndex_ = (decalIndex_ + 3 + direction) % 3;
    else if (row == 2 && !activate && layer) {
      size_t index = 0; while (livery_.draft().layers[index].id != layer->id) ++index;
      result = livery_.select(livery_.draft().layers[(index + livery_.draft().layers.size() + direction) % livery_.draft().layers.size()].id);
    } else if (!activate && row >= 3 && row <= 8) {
      if (!layer) result = {LiveryError::NoSelection,false};
      else {
        auto t = layer->transform;
        if (row == 3) t.x = std::clamp(t.x + direction*.05,-1.,1.);
        if (row == 4) t.y = std::clamp(t.y + direction*.05,-1.,1.);
        if (row == 5) t.scaleX = std::clamp(t.scaleX + direction*.1,.01,4.);
        if (row == 6) t.scaleY = std::clamp(t.scaleY + direction*.1,.01,4.);
        if (row == 7) t.rotation = std::clamp(t.rotation + direction*15.,-180.,180.);
        if (row == 8) t.opacity = std::clamp(t.opacity + direction*.1,0.,1.);
        result = livery_.setTransform(t);
      }
    } else if (row == 9) result = layer ? livery_.setVisible(!layer->visible) : LiveryResult{LiveryError::NoSelection,false};
    else if (activate && row == 1) result = livery_.add(decals[decalIndex_]);
    else if (activate && row == 10) result = livery_.moveSelected(-1);
    else if (activate && row == 11) result = livery_.moveSelected(1);
    else if (activate && row == 12) result = livery_.removeSelected();
    else if (activate && row == 13) {
      result = livery_.apply();
      if (result.changed) { ++liveryRevision_; appliedLayers(); }
      saveLivery();
    } else if (activate && row == 14) result = livery_.cancel();
    else if (activate && row == 15) saveLivery();
    else if (activate && row == 16) { leave(page,row); exit = true; }
    changed = result.changed;
    if (changed) ++draftRevision_;
    rejection = int(result.error);
    liveryMessage_ = !result ? "Operation rejected: no layer, boundary or layer cap."
        : activate && row == 13 ? "Applied livery updated in memory."
        : activate && row == 14 ? "Draft canceled; applied livery restored."
        : activate && row == 15 ? "Save retried for applied livery."
        : changed ? "Draft changed; Apply and save to keep changes." : "";
  }
  if (diagnostics_) diagnostics_->event("feature_action", {{"page",int(page)},{"row",row},{"action",int(command)},
    {"changed",changed},{"rejection",rejection},{"parent_operation",parent}},operation_);
  observe(page,row);
  return exit;
}
void GarageFeatures::observe(GarageFeaturePage page, int menu) {
  if (!diagnostics_) return;
  auto part = parts_.find(selectedPart()); auto layer = selected(livery_.draft());
  std::ostringstream key;
  key << int(page) << ':' << menu << ':' << partsRevision_ << ':' << liveryRevision_ << ':' << draftRevision_
      << ':' << selectedPart() << ':' << catalogIndex_ << ':' << decalIndex_ << ':' << int(partsStore_.outcome().status)
      << ':' << int(liveryStore_.outcome().status);
  if (key.str() == lastObservation_) return;
  lastObservation_ = key.str();
  DecalTransform t = layer ? layer->transform : DecalTransform{};
  diagnostics_->event("feature_state", {{"page",int(page)},{"menu",menu},{"parts_revision",partsRevision_},
    {"livery_revision",liveryRevision_},{"draft_revision",draftRevision_},{"parts_identity",partsIdentity_},
    {"selected_part",selectedPart()},{"part_definition",part->partId},{"part_parent",part->mount ? part->mount->parent : 0},
    {"part_slot",part->mount ? part->mount->slot : ""},{"engine",mounted(PartKind::Engine)},{"wheel",mounted(PartKind::Wheel)},{"tyre",mounted(PartKind::Tyre)},
    {"owned",parts_.inventory().size()},{"layer",layer ? layer->id : 0},{"layers",livery_.draft().layers.size()},
    {"applied_layers",livery_.applied().layers.size()},{"dirty",livery_.dirty()},{"decal",layer ? layer->decal : ""},
    {"x",t.x},{"y",t.y},{"scale_x",t.scaleX},{"scale_y",t.scaleY},{"rotation",t.rotation},{"opacity",t.opacity},
    {"visible",layer && layer->visible},{"parts_save",int(partsStore_.outcome().status)},{"livery_save",int(liveryStore_.outcome().status)}}, operation_);
}
std::vector<std::string> GarageFeatures::lines(GarageFeaturePage page, int menu) const {
  std::vector<std::string> out;
  auto option = [&](int row, const std::string &label) { out.push_back((menu == row ? "> " : "  ") + label); };
  if (page == GarageFeaturePage::Parts) {
    auto part = parts_.find(selectedPart()); auto def = parts_.catalog().find(part->partId);
    out = {"PARTS / PROTOTYPE", "Install/remove changes the in-memory assembly."};
    option(0,"Catalog: " + parts_.catalog().find(catalogIds[catalogIndex_])->name + " [Left/Right]");
    option(1,"Acquire selected catalog part");
    option(2,"Owned: " + def->name + " #" + std::to_string(part->instance) + (parts_.mounted(part->instance) ? " [mounted]" : " [inventory]") + " [Left/Right]");
    option(3,"Install selected owned part"); option(4,"Remove selected owned part");
    option(5,"Save / retry parts save"); option(6,"Return to garage");
    out.push_back("Fitment: remove tyre before rim; match tyre/rim radius and width.");
    out.push_back(hasEngine() ? "Engine fitted. Upgrade: 1.15x drive force, combined tune capped at 1.20x."
                             : "NO ENGINE: install an engine before driving or testing.");
    if (!partsMessage_.empty()) out.push_back("Last action: " + partsMessage_);
    out.push_back(persistence("Parts assembly",partsStore_));
  } else {
    auto layer = selected(livery_.draft()); const auto t = layer ? layer->transform : DecalTransform{};
    out = {"LIVERY / ORDERED DECALS", livery_.dirty() ? "DRAFT NOT APPLIED / Apply and save to keep changes." : "No pending livery edits."};
    option(0,std::string("Decal: ") + decals[decalIndex_] + " [Left/Right]"); option(1,"Add decal layer");
    size_t position = 0;
    for (size_t i = 0; i < livery_.draft().layers.size(); ++i)
      if (livery_.draft().layers[i].id == livery_.draft().selected) position = i + 1;
    option(2,"Selected layer: " + std::to_string(position) + " / " + std::to_string(livery_.draft().layers.size()) +
             (layer ? " - " + layer->decal : "") + " [Left/Right]");
    option(3,"Horizontal " + number(t.x)); option(4,"Vertical " + number(t.y)); option(5,"Width " + number(t.scaleX));
    option(6,"Height " + number(t.scaleY)); option(7,"Rotation " + number(t.rotation) + " deg"); option(8,"Opacity " + number(t.opacity));
    option(9,std::string("Visible: ") + (layer && layer->visible ? "yes" : "no"));
    option(10,"Move layer backward"); option(11,"Move layer forward"); option(12,"Remove selected layer");
    option(13,"Apply and save livery"); option(14,"Cancel draft edits"); option(15,"Retry applied livery save"); option(16,"Return (discard draft edits)");
    if (!liveryMessage_.empty()) out.push_back("Last action: " + liveryMessage_);
    out.push_back(persistence("Applied livery",liveryStore_,livery_.dirty()));
  }
  out.push_back("Arrows / D-pad: select, adjust | Enter / South: confirm | Esc / East: back");
  return out;
}
} // namespace racer
