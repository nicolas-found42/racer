#pragma once
#include <array>
#include <optional>
#include <string_view>

namespace racer {
struct VehicleLook {float roughness,metallic,clearcoat;};

// Racer-authored Silverstone exterior finish, not GT4's PS2 BRDF. These six
// exact NSX families have retained native diffuse .5/specular1.5 and inspected
// exterior textures/bounds. Factory variant suffixes alone do not identify paint.
// Paired window passes, lamps/mixed atlases, interiors and wheels stay unmapped.
inline std::optional<VehicleLook> vehicleLook(std::string_view meshSHA,
                                            std::string_view materialName,int wheel) {
  if(wheel!=-1)return std::nullopt;
  // Native sourceShader=CarPaintCustomizable identifies these exterior parts.
  // Finish values are authored; the donor's paint/color formula is unknown.
  constexpr std::string_view roadster="71a6d4ab044ba95673582f34eb9a11621fe89aeda488bea914964a2e1e6e7bd6";
  constexpr std::string_view prefix="vp_nsn_350z_06/resources/vehicle/vp_nsn_350z_06/";
  if(meshSHA==roadster && materialName.starts_with(prefix)) {
    materialName.remove_prefix(prefix.size());
    constexpr std::array<std::string_view,8> paint{{"body_lod_0.xrsc/shader8",
      "bumper_f0_lod_0.xrsc/shader8","bumper_r0_lod_0.xrsc/shader8",
      "door_l0_lod_0.xrsc/shader8","door_r0_lod_0.xrsc/shader8",
      "fenders0_lod_0.xrsc/shader8","hood0_lod_0.xrsc/shader8","skirts0_lod_0.xrsc/shader8"}};
    for(const auto name:paint)if(materialName==name)return VehicleLook{.24f,.25f,.9f};
    return std::nullopt;
  }
  constexpr std::string_view nsx="4c157f280bd085aa43bca9d9f82d380b84e7ebad2cac269fdf7dac3188475e8e";
  if(meshSHA!=nsx) return std::nullopt;
  constexpr std::array<std::string_view,6> exterior{{
    "body/set0/tex4/mat6/MASK/paint0",
    "body/set0/tex23/mat6/MASK/paint0",
    "body/set0/tex24/mat6/MASK/paint0",
    "body/set0/tex25/mat6/MASK/paint0",
    "body/set0/tex31/mat6/MASK/paint0",
    "body/set0/tex35/mat6/MASK/paint0"}};
  for(const auto name:exterior) if(materialName==name) return VehicleLook{.28f,.25f,.8f};
  return std::nullopt;
}
}
