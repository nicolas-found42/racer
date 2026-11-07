#include "vehicle_asset.h"
#include "play_flow.h"
#include <algorithm>
#include <CommonCrypto/CommonDigest.h>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <unistd.h>
#include <sys/stat.h>
void require(bool c,const char *why) {if (!c) throw std::runtime_error(why);}
std::string hash(const std::string &text) {
  unsigned char digest[CC_SHA256_DIGEST_LENGTH];CC_SHA256(text.data(),CC_LONG(text.size()),digest);
  std::ostringstream out;for (auto b:digest) out<<std::hex<<std::setw(2)<<std::setfill('0')<<unsigned(b);return out.str();
}
int main() try {
  char temporary[]="/tmp/racer-vehicle-XXXXXX";require(mkdtemp(temporary),"temporary directory");
  const auto root=std::filesystem::path(temporary);
  struct Cleanup {std::filesystem::path path;~Cleanup(){std::filesystem::remove_all(path);}} cleanup{root};
  const std::string mesh=R"({"asset":{"version":"2.0"},"scene":0,"scenes":[{"nodes":[0,1,2,3,4]}],"nodes":[{"mesh":0},{"mesh":0,"translation":[-0.8,0.3,1.3],"scale":[0.1,0.1,0.1]},{"mesh":0,"translation":[0.8,0.3,1.3],"scale":[0.1,0.1,0.1]},{"mesh":0,"translation":[-0.8,0.3,-1.3],"scale":[0.1,0.1,0.1]},{"mesh":0,"translation":[0.8,0.3,-1.3],"scale":[0.1,0.1,0.1]}],"meshes":[{"primitives":[{"attributes":{"POSITION":0},"indices":1}]}],"buffers":[{"byteLength":42,"uri":"data:application/octet-stream;base64,AAAAAAAAAAAAAAAAAACAPwAAAAAAAAAAAAAAAAAAAAAAAIA/AAABAAIA"}],"bufferViews":[{"buffer":0,"byteOffset":0,"byteLength":36},{"buffer":0,"byteOffset":36,"byteLength":6}],"accessors":[{"bufferView":0,"componentType":5126,"count":3,"type":"VEC3"},{"bufferView":1,"componentType":5123,"count":3,"type":"SCALAR"}]})";
  {std::ofstream out(root/"fixture.gltf");out<<mesh;}
  const auto sha=hash(mesh);const std::string descriptor="RACER_VEHICLE 1\nid \"vehicle-"+sha+"\"\nname \"Test car\"\nmesh \"fixture.gltf\"\nsha256 "+sha+"\nsource_sha256 "+std::string(64,'a')+"\nbody -1 0 -2 1 1 2\nwheel FL -.8 .3 1.3 .3 .25\nwheel FR .8 .3 1.3 .3 .25\nwheel RL -.8 .3 -1.3 .3 .25\nwheel RR .8 .3 -1.3 .3 .25\ngroups 5\ngroup 0 -1\ngroup 1 0\ngroup 2 1\ngroup 3 2\ngroup 4 3\n";
  auto read=[&](const std::string &text) {std::ofstream out(root/"fixture.vehicle");out<<text;out.close();return racer::readVehicleDefinition(root/"fixture.vehicle");};
  auto definition=read(descriptor);racer::AssetLoadContext context;
  auto asset=racer::loadVehicleAsset(definition,&context);
  require(std::string(context.actualMeshSHA256.data())==sha && std::string(context.expectedMeshSHA256.data())==sha &&
          std::string(context.descriptorSHA256.data())==hash(descriptor) && std::string(context.sourceSHA256.data())==std::string(64,'a') &&
          context.stage==racer::AssetLoadStage::Complete && std::string(racer::assetInputIdentity(context))=="match","successful exact input context");
  require(asset.triangles.size()==15 && asset.sections.size()==5,"all groups loaded");
  require(std::abs(asset.triangles[3].x)<1e-6 && std::abs(asset.triangles[4].x-.1)<1e-6,"wheel vertices pivot centered");
  auto modern=descriptor;modern.replace(0,15,"RACER_VEHICLE 2");
  const std::array<std::string,5> oldGroups={"group 0 -1","group 1 0","group 2 1","group 3 2","group 4 3"};
  const std::array<std::string,5> newGroups={"group 0 body","group 1 wheel FL","group 2 wheel FR","group 3 wheel RL","group 4 wheel RR"};
  for(size_t i=0;i<5;++i)modern.replace(modern.find(oldGroups[i]),oldGroups[i].size(),newGroups[i]);
  const auto modernDefinition=read(modern);auto modernAsset=racer::loadVehicleAsset(modernDefinition);
  require(definition.descriptorSHA256!=modernDefinition.descriptorSHA256 &&
          racer::vehiclePhysicsIdentity(definition)==racer::vehiclePhysicsIdentity(modernDefinition),"descriptor revision distinct from equal physics identity");
  require(modernAsset.triangles.size()==asset.triangles.size() && modernAsset.sections[1].rolling,"version2 rolling groups preserve old rendering");
  auto carrier=modern;const std::string rollingGroup="group 1 wheel FL";
  carrier.replace(carrier.find(rollingGroup),rollingGroup.size(),"group 1 carrier FL");
  auto carrierDefinition=read(carrier);
  require(carrierDefinition.bindings[1].wheel==0 && !carrierDefinition.bindings[1].rolling,"carrier retains axle and disables spin");
  const auto carrierMesh=racer::loadMeshAsset(carrierDefinition.mesh,carrierDefinition.bindings);
  const auto carrierSection=std::find_if(carrierMesh.sections.begin(),carrierMesh.sections.end(),[](const auto &section){return section.wheel==0;});
  require(carrierSection!=carrierMesh.sections.end() && !carrierSection->rolling,"carrier motion propagated to renderer sections");
  bool missingRolling=false;try {racer::loadVehicleAsset(carrierDefinition);}catch(const racer::MeshAssetError &e){missingRolling=std::string(e.what())=="vehicle_incomplete_sections";}
  require(missingRolling,"carrier cannot substitute for missing rolling tyre");
  auto reject=[&](const auto &action,const char *reason) {try{action();}catch(const std::runtime_error &e){require(std::string(e.what())==reason,"unexpected rejection reason");return;}throw std::runtime_error("invalid input accepted");};
  auto changed=definition;changed.sha256=std::string(64,'0');reject([&]{racer::loadVehicleAsset(changed,&context);},"vehicle_mesh_hash");
  require(context.stage==racer::AssetLoadStage::Identity && std::string(racer::assetInputIdentity(context))=="mismatch" &&
          std::string(context.actualMeshSHA256.data())==sha,"valid mesh wrong expected hash context");
  changed=definition;changed.geometry.body.maximum.x=.5;reject([&]{racer::loadVehicleAsset(changed,&context);},"vehicle_body_containment");
  require(context.stage==racer::AssetLoadStage::Containment && std::string(racer::assetInputIdentity(context))=="match","geometry failure on expected bytes");
  changed=definition;for(auto &w:changed.geometry.wheels)w.width=.1;reject([&]{racer::loadVehicleAsset(changed);},"vehicle_wheel_containment");
  changed=definition;changed.bindings.pop_back();reject([&]{racer::loadVehicleAsset(changed);},"asset_unbound_mesh");
  auto text=descriptor;text.replace(text.find("fixture.gltf"),12,"../other.gltf");reject([&]{read(text);},"vehicle_descriptor_path");
  reject([&]{read(descriptor+"extra\n");},"vehicle_descriptor_trailing");
  std::filesystem::create_symlink(root/"fixture.vehicle",root/"link.vehicle");reject([&]{racer::readVehicleDefinition(root/"link.vehicle");},"vehicle_descriptor_not_regular");
  ::mkfifo((root/"pipe.vehicle").c_str(),0600);reject([&]{racer::readVehicleDefinition(root/"pipe.vehicle");},"vehicle_descriptor_not_regular");
  // Both cases retain the same historical parser reason. The new context
  // distinguishes corrupted/different input from parser rejection on pinned bytes.
  const std::string broken="broken model fixture";
  {std::ofstream out(root/"fixture.gltf");out<<broken;}
  reject([&]{racer::loadVehicleAsset(definition,&context);},"asset_parse");
  require(context.stage==racer::AssetLoadStage::Parse && context.inputBytes==broken.size() &&
          std::string(context.actualMeshSHA256.data())==hash(broken) && std::string(context.expectedMeshSHA256.data())==sha &&
          std::string(context.descriptorSHA256.data())==hash(descriptor) && std::string(racer::assetInputIdentity(context))=="mismatch","wrong bytes parse failure diagnosis");
  auto brokenDescriptor=descriptor;size_t position=0;
  while ((position=brokenDescriptor.find(sha,position))!=std::string::npos) {brokenDescriptor.replace(position,sha.size(),hash(broken));position+=sha.size();}
  auto pinnedBroken=read(brokenDescriptor);
  reject([&]{racer::loadVehicleAsset(pinnedBroken,&context);},"asset_parse");
  require(context.stage==racer::AssetLoadStage::Parse && std::string(context.actualMeshSHA256.data())==hash(broken) &&
          std::string(context.descriptorSHA256.data())==hash(brokenDescriptor) && std::string(racer::assetInputIdentity(context))=="match","parser rejected exact expected bytes");
  changed=definition;changed.mesh=root/"missing.gltf";
  reject([&]{racer::loadVehicleAsset(changed,&context);},"asset_not_regular");
  require(context.stage==racer::AssetLoadStage::Open && !context.actualMeshSHA256[0] && context.inputBytes==0 &&
          std::string(context.expectedMeshSHA256.data())==sha && std::string(racer::assetInputIdentity(context))=="unavailable","missing file cannot inherit previous hash");
  {std::ofstream out(root/"fixture.gltf");out<<mesh;}
  racer::loadVehicleAsset(definition,&context);
  require(std::string(racer::assetInputIdentity(context))=="match" && std::string(context.descriptorSHA256.data())==hash(descriptor),"repaired file uses original in-memory descriptor revision");
  // Library context reports the exact bytes being parsed, not a later reread or
  // the previous successfully read descriptor when the next entry is missing.
  auto writeFile=[&](const char *name,const std::string &bytes) {std::ofstream out(root/name);out<<bytes;};
  const std::string malformedDescriptor="not a vehicle descriptor\n";
  writeFile("bad.vehicle",malformedDescriptor);
  racer::AssetDigest descriptorDigest=definition.descriptorSHA256;
  reject([&]{racer::readVehicleDefinition(root/"bad.vehicle",&descriptorDigest);},"vehicle_descriptor_schema");
  require(std::string(descriptorDigest.data())==hash(malformedDescriptor),"malformed descriptor digest captured before parsing");
  reject([&]{racer::readVehicleDefinition(root/"absent.vehicle",&descriptorDigest);},"vehicle_descriptor_not_regular");
  require(!descriptorDigest[0],"missing descriptor resets prior digest");
  writeFile("first.vehicle",descriptor);
  const auto exactDefinition=racer::readVehicleDefinition(root/"first.vehicle",&descriptorDigest);
  require(descriptorDigest==definition.descriptorSHA256 && exactDefinition.descriptorSHA256==definition.descriptorSHA256 &&
          racer::vehiclePhysicsIdentity(exactDefinition)==racer::vehiclePhysicsIdentity(definition),"optional digest leaves successful definition and physics identity unchanged");
  racer::VehicleLibraryLoadContext libraryContext;
  const std::string twoEntries="RACER_VEHICLES 1\n2\n\"first.vehicle\"\n\"bad.vehicle\"\n";
  writeFile("catalog.racer",twoEntries);
  reject([&]{racer::readVehicleLibrary(root/"catalog.racer",&libraryContext);},"vehicle_descriptor_schema");
  require(std::string(libraryContext.librarySHA256.data())==hash(twoEntries) && libraryContext.descriptorIndex==1 &&
          std::string(libraryContext.descriptorSHA256.data())==hash(malformedDescriptor),"library captures failing second descriptor exact hash and index");
  std::filesystem::remove(root/"bad.vehicle");
  reject([&]{racer::readVehicleLibrary(root/"catalog.racer",&libraryContext);},"vehicle_descriptor_not_regular");
  require(libraryContext.descriptorIndex==1 && !libraryContext.descriptorSHA256[0] &&
          std::string(libraryContext.librarySHA256.data())==hash(twoEntries),"missing second descriptor never inherits first descriptor hash");
  writeFile("bad.vehicle",descriptor);
  reject([&]{racer::readVehicleLibrary(root/"catalog.racer",&libraryContext);},"vehicle_library_duplicate");
  require(libraryContext.descriptorIndex==1 && libraryContext.descriptorSHA256==definition.descriptorSHA256,"duplicate descriptor retains active index and bytes");
  const std::string oneEntry="RACER_VEHICLES 1\n1\n\"first.vehicle\"\n";
  writeFile("catalog.racer",oneEntry);
  const auto library=racer::readVehicleLibrary(root/"catalog.racer",&libraryContext);
  require(library.size()==1 && library[0].descriptorSHA256==definition.descriptorSHA256 && libraryContext.descriptorIndex==-1 &&
          !libraryContext.descriptorSHA256[0] && std::string(libraryContext.librarySHA256.data())==hash(oneEntry),"successful whole library has no active or selected descriptor claim");
  const std::string missingEntry="RACER_VEHICLES 1\n2\n\"first.vehicle\"\n";
  writeFile("catalog.racer",missingEntry);
  reject([&]{racer::readVehicleLibrary(root/"catalog.racer",&libraryContext);},"vehicle_library_entry");
  require(libraryContext.descriptorIndex==1 && !libraryContext.descriptorSHA256[0],"unread second entry resets descriptor identity");
  writeFile("catalog.racer",oneEntry+"extra\n");
  reject([&]{racer::readVehicleLibrary(root/"catalog.racer",&libraryContext);},"vehicle_library_trailing");
  require(libraryContext.descriptorIndex==-1 && !libraryContext.descriptorSHA256[0],"library trailer is not attributed to last descriptor");
  const std::string malformedLibrary="RACER_VEHICLES 2\n1\n\"first.vehicle\"\n";
  writeFile("catalog.racer",malformedLibrary);
  reject([&]{racer::readVehicleLibrary(root/"catalog.racer",&libraryContext);},"vehicle_library_schema");
  require(std::string(libraryContext.librarySHA256.data())==hash(malformedLibrary) && libraryContext.descriptorIndex==-1 &&
          !libraryContext.descriptorSHA256[0],"library schema failure retains only library digest");
  reject([&]{racer::readVehicleLibrary(root/"absent.racer",&libraryContext);},"vehicle_descriptor_not_regular");
  require(!libraryContext.librarySHA256[0] && libraryContext.descriptorIndex==-1 && !libraryContext.descriptorSHA256[0],"missing library resets entire reused context");
  const auto identity=racer::vehiclePhysicsIdentity(definition);changed=definition;changed.geometry.body.maximum.z+=.01;
  require(identity!=racer::vehiclePhysicsIdentity(changed),"geometry changes physics identity");
  racer::PlayFlow flow((root/"profile.txt").string());
  require(flow.configureVehicle(identity,definition.name,definition.geometry),"imported car configured");
  require(flow.sim.wheelbase()==2.6 && flow.sim.car.travel==0,"configured wheelbase and reset");
  flow.startTest(racer::TestKind::Acceleration);flow.rearming=false;flow.sim.tick({},0);
  for (int i=0;i<1800 && flow.session.active();++i)flow.tick({});
  require(flow.session.result().valid && std::abs(flow.session.result().seconds-8)<1e-8,"stock acceleration preserved");
  require(flow.session.result().carId==identity && flow.session.result().handlingRevision==2,"frozen imported identity");
  require(flow.profile.records.size()==1 && flow.profile.records[0].carId==identity,"imported result stored");
  auto query=flow.profile.records[0];query.carId=racer::vehiclePhysicsIdentity(changed);
  require(!flow.profile.best(query),"different geometry cannot compare");
  racer::StoredResult legacy;legacy.testId="acceleration";legacy.seconds=8;require(flow.profile.record(legacy),"legacy record accepted alongside imported");
  require(flow.store.save(flow.profile),"mixed profile save");
  std::ifstream profile(root/"profile.txt");std::string first;std::getline(profile,first);require(first=="RACER_PROFILE 2","mixed profile schema2");
  racer::Profile loaded;racer::ProfileStore store(root/"profile.txt");require(store.load(loaded) && loaded.records==flow.profile.records,"profile2 exact roundtrip");
  racer::Simulation shortCar,longCar;auto longer=definition.geometry;for(auto &w:longer.wheels)w.center.z*=1.1;
  require(shortCar.setGeometry(definition.geometry)&&longCar.setGeometry(longer),"geometry pair configured");
  shortCar.car.speed=longCar.car.speed=5;shortCar.tick({0,0,.5});longCar.tick({0,0,.5});
  require(std::abs(shortCar.car.heading/longCar.car.heading-1.1)<1e-10,"wheelbase controls turn curvature");
  shortCar.reset();shortCar.tick({},0);shortCar.tick({0,1,0});require(shortCar.car.direction==-1 && shortCar.car.travel<0,"reverse unwinds signed wheel travel");
  shortCar.reset();require(shortCar.car.travel==0,"reset clears wheel travel");
  std::cout<<"PASS: asset binding/hash/containment, physics identity, imported flow, profile2 and cross-car isolation, turning/reverse/reset\n";
} catch(const std::exception &e){std::cerr<<"FAIL: "<<e.what()<<'\n';return 1;}
