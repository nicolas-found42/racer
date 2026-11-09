#pragma once
#include <cstdint>
#include <vector>
// Validation-only representation of the fields actually read by supplied headers.
// The real application's mesh_asset.h remains the integration dependency.
namespace racer {
struct ValidationMeshVertex { float x=0, y=0, z=0; };
struct ValidationMeshSection {
  std::uint32_t first=0, count=0;
  int wheel=-1;
  bool rolling=false, blend=false, mask=false;
};
struct MeshAsset {
  std::vector<ValidationMeshVertex> triangles;
  std::vector<ValidationMeshSection> sections;
};
}
