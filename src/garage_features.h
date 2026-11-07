#pragma once
#include "document_store.h"
#include "livery.h"
#include "parts.h"
#include "setup.h"
namespace racer {
enum class GarageFeaturePage { Parts, Livery };
enum class FeatureAction { Decrease, Increase, Activate };
// Shared domain/UI boundary for authored prototype parts and decal editing.
// Does not modify simulation or the existing profile schema.
class GarageFeatures {
public:
  explicit GarageFeatures(const std::string &profilePath, Diagnostics *diagnostics = nullptr);
  const PartAssembly &parts() const { return parts_; }
  const LiveryEditor &livery() const { return livery_; }
  const DocumentStore &partsStore() const { return partsStore_; }
  const DocumentStore &liveryStore() const { return liveryStore_; }
  unsigned partsRevision() const { return partsRevision_; }
  unsigned liveryRevision() const { return liveryRevision_; }
  unsigned draftRevision() const { return draftRevision_; }
  VehicleSetup partMultipliers() const;
  bool hasEngine() const;
  std::string partsIdentity() const { return partsIdentity_; }
  static int menuCount(GarageFeaturePage page);
  // True means the explicit Return row was activated. Back also calls leave().
  bool action(GarageFeaturePage page, int row, FeatureAction action, uint64_t parent = 0);
  void leave(GarageFeaturePage page, int menu = -1);
  std::vector<std::string> lines(GarageFeaturePage page, int menu) const;
  void observe(GarageFeaturePage page, int menu);
private:
  PartAssembly parts_;
  LiveryEditor livery_;
  DocumentStore partsStore_, liveryStore_;
  Diagnostics *diagnostics_;
  size_t ownedIndex_ = 0, catalogIndex_ = 0, decalIndex_ = 0;
  unsigned partsRevision_ = 0, liveryRevision_ = 0, draftRevision_ = 0;
  uint64_t operation_ = 0;
  std::string partsIdentity_, lastObservation_, partsMessage_, liveryMessage_;
  uint64_t selectedPart() const;
  uint64_t mounted(PartKind kind) const;
  void saveParts();
  void saveLivery();
  void appliedLayers();
};
} // namespace racer
