#include "play_flow.h"
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <unistd.h>
void require(bool condition,const char *message) { if (!condition) throw std::runtime_error(message); }
int main() try {
  auto root=std::filesystem::temp_directory_path()/("racer-config-"+std::to_string(getpid()));
  std::filesystem::create_directories(root);
  racer::PlayFlow flow((root/"profile.txt").string());
  require(flow.effectiveSetup(0)==racer::VehicleSetup{},"stock unchanged");
  auto &features=flow.features;
  using Page=racer::GarageFeaturePage;using A=racer::FeatureAction;
  features.action(Page::Parts,2,A::Increase); // owned stock engine
  features.action(Page::Parts,4,A::Activate);
  flow.startTest(racer::TestKind::Acceleration);
  require(flow.screen==racer::Screen::Parts && !flow.session.active(),"missing engine blocks test");
  for (int i=0;i<3;++i) features.action(Page::Parts,2,A::Increase); // upgrade engine
  features.action(Page::Parts,3,A::Activate);
  require(features.hasEngine() && flow.effectiveSetup(0).acceleration==1.15,"mounted upgrade effect");
  flow.startTest(racer::TestKind::Acceleration);
  require(flow.session.result().setup.acceleration==1.15,"effective values frozen");
  flow.rearming=false;flow.sim.tick({},0);
  for (int i=0;i<2400 && flow.session.active();++i) flow.tick({});
  require(flow.session.result().valid && std::abs(flow.session.result().seconds-8/1.15)<.01,"measured upgrade effect");
  require(flow.profile.records.size()==1 && flow.profile.records[0].setup.acceleration==1.15,"effective record identity");
  racer::StoredResult stock;stock.testId="acceleration";
  require(!flow.profile.best(stock),"stock cannot match upgrade record");
  flow.profile.garage.applied[0].acceleration=1.2;
  require(flow.effectiveSetup(0).acceleration==1.2,"combined cap");
  racer::PlayFlow reload((root/"profile.txt").string());
  require(reload.effectiveSetup(0).acceleration==1.15 && reload.profile.records.size()==1,"sidecar and record reload");
  std::filesystem::remove_all(root);
  std::cout<<"PASS: stock preservation, engine requirement, upgrade timing, frozen comparisons, cap, reload\n";
} catch (const std::exception &e) { std::cerr<<"FAIL: "<<e.what()<<'\n';return 1; }
