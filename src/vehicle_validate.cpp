#include "vehicle_asset.h"
#include <iomanip>
#include <iostream>
#include <string_view>
namespace {
void validate(const racer::VehicleDefinition &v) {
  const auto mesh=racer::loadVehicleAsset(v);
  std::cout<<std::quoted(v.id)<<' '<<std::quoted(v.name)<<" sha="<<mesh.sourceSHA256
    <<" physics="<<racer::vehiclePhysicsIdentity(v)<<" wheelbase="<<std::setprecision(12)<<v.geometry.wheelbase()
    <<" triangles="<<mesh.triangles.size()/3<<" images="<<mesh.images.size()<<'\n';
}
}
int main(int argc,char **argv) {
  const bool single=argc==3 && std::string_view(argv[1])=="--descriptor";
  if (!single && (argc!=2 || std::string_view(argv[1])=="--descriptor")) {
    std::cerr<<"Usage: vehicle_validate catalog.racer | --descriptor car.vehicle\n";return 2;
  }
  try {
    if (single) validate(racer::readVehicleDefinition(argv[2]));
    else for (const auto &v:racer::readVehicleLibrary(argv[1])) validate(v);
    return 0;
  } catch (const racer::MeshAssetError &e) {std::cerr<<"REJECT: "<<e.what()<<'\n';return 1;}
    catch (...) {std::cerr<<"REJECT: allocation_or_system_failure\n";return 1;}
}
