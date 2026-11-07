#pragma once
#include "mesh_asset.h"
#include "vehicle_geometry.h"
namespace racer {
struct VehicleDefinition {
  std::string id,name,sha256,sourceSHA256;
  std::filesystem::path mesh;
  VehicleGeometry geometry;
  std::vector<MeshNodeBinding> bindings;
  AssetDigest descriptorSHA256{}; // Exact bytes from readVehicleDefinition, not a reread.
};
struct VehicleLibraryLoadContext {
  AssetDigest librarySHA256{},descriptorSHA256{};
  int descriptorIndex=-1; // Active entry only; -1 before/after descriptor processing.
};
// Small strict local descriptor. Relative mesh paths stay within its directory;
// no network requests or arbitrary source paths are followed at runtime.
// Optional digest is reset before reading and populated before parsing, including
// malformed complete reads. It stays empty when no complete bounded read exists.
VehicleDefinition readVehicleDefinition(const std::filesystem::path &path,AssetDigest *descriptorDigest = nullptr);
std::vector<VehicleDefinition> readVehicleLibrary(const std::filesystem::path &path,
                                                VehicleLibraryLoadContext *context = nullptr);
MeshAsset loadVehicleAsset(const VehicleDefinition &vehicle,AssetLoadContext *context = nullptr);
std::string vehiclePhysicsIdentity(const VehicleDefinition &vehicle);
}
