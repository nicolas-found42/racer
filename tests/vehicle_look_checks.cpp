#include "vehicle_look.h"
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {
void require(bool value,const char* reason) {if(!value) throw std::runtime_error(reason);}
constexpr std::string_view nsx="4c157f280bd085aa43bca9d9f82d380b84e7ebad2cac269fdf7dac3188475e8e";
constexpr std::string_view panel="body/set0/tex23/mat6/MASK/paint0";
}
int main() try {
  const auto look=racer::vehicleLook(nsx,panel,-1);
  require(look && look->roughness==.28f && look->metallic==.25f && look->clearcoat==.8f,"inspected NSX exterior family receives explicit authored finish");
  for(float value:{look->roughness,look->metallic,look->clearcoat})
    require(std::isfinite(value) && value>=0 && value<=1,"authored factors are finite and normalized");
  require(racer::vehicleLook(nsx,"body/set0/tex25/mat6/MASK/paint0",-1).has_value(),"independently bound side body receives finish");
  auto changedHash=std::string(nsx);changedHash[0]='0';
  require(!racer::vehicleLook(changedHash,panel,-1),"changed mesh identity cannot inherit material assumptions");
  require(!racer::vehicleLook({},panel,-1),"missing mesh identity has no look override");
  for(int wheel:{-2,0,1,2,3,4})
    require(!racer::vehicleLook(nsx,panel,wheel),"body finish never overrides wheel or invalid binding roles");
  for(const auto name:{
      "body/set0/tex23/mat6/MASK/paint1", // White native variant has zero specular.
      "body/set0/tex23/mat6/MASK/paint6",
      "body/set0/tex40/mat6/OPAQUE/paint0", // Rear-window native pass, despite mat6.
      "body/set0/tex41/mat-1/BLEND/paint0",
      "body/set0/tex42/mat13/OPAQUE/paint0",
      "body/set0/tex43/mat-1/BLEND/paint0",
      "body/set0/tex44/mat13/OPAQUE/paint0",
      "body/set0/tex45/mat-1/BLEND/paint0",
      "body/set0/tex18/mat6/MASK/paint0", // Mixed lamp/body atlas remains ambiguous.
      "body/set0/tex26/mat6/MASK/paint0",
      "body/set0/tex27/mat6/MASK/paint0",
      "body/set0/tex33/mat6/MASK/paint0",
      "body/set0/tex12/mat-1+vc/MASK/paint0",
      "tire_front/set0/tex0/mat0/MASK/paint0",
      "wheel_front/set0/tex0/mat0/MASK/paint0",
      "body/set0/tex023/mat6/MASK/paint0",
      "body/set0/tex23/mat6/BLEND/paint0",
      "body/set0/tex23/mat6/MASK/paint00",
      "body/set0/tex23/mat6/MASK/paint0/extra",
      "BODY/set0/tex23/mat6/MASK/paint0",
      "body/set0/tex23/mat6/MASK/paint0 "})
    require(!racer::vehicleLook(nsx,name,-1),"uninspected family or variant remains unchanged");
  constexpr std::string_view roadster="71a6d4ab044ba95673582f34eb9a11621fe89aeda488bea914964a2e1e6e7bd6";
  const std::string prefix="vp_nsn_350z_06/resources/vehicle/vp_nsn_350z_06/";
  const auto painted=racer::vehicleLook(roadster,prefix+"body_lod_0.xrsc/shader8",-1);
  require(painted&&painted->roughness==.24f&&painted->metallic==.25f&&painted->clearcoat==.9f,"source-qualified roadster exterior paint receives authored finish");
  for(const auto name:{"body_lod_0.xrsc/shader28","interior0_lod_0.xrsc/shader8",
    "interior0_lod_0.xrsc/shader14","door_l_int0_lod_0.xrsc/shader14","taillight0_lod_0.xrsc/shader28",
    "body_lod_0.xrsc/shader08","body_lod_0.xrsc/shader8/extra"})
    require(!racer::vehicleLook(roadster,prefix+name,-1),"roadster lamp/interior or malformed family receives no exterior override");
  require(!racer::vehicleLook(nsx,prefix+"body_lod_0.xrsc/shader8",-1),"roadster name with wrong source identity remains unchanged");
  require(!racer::vehicleLook(roadster,prefix+"body_lod_0.xrsc/shader8",0),"roadster wheel binding cannot receive exterior paint");
  std::cout<<"PASS: exact hash/body binding authored finish; variants, window pairs, mixed atlases and malformed names remain unchanged\n";
} catch(const std::exception& error) {std::cerr<<"FAIL: "<<error.what()<<'\n';return 1;}
