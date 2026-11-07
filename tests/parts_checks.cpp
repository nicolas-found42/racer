#include "parts.h"
#include <iostream>
#include <stdexcept>
#include <limits>
using namespace racer;
void check(bool v,const char *m) { if(!v) throw std::runtime_error(m); }
int main() {
 try {
  PartsCatalog c;
  PartDefinition body{"racer:body","Vehicle",PartKind::Body,{{"front",PartKind::Wheel,{}},{"rear",PartKind::Wheel,{"wheels:standard"}},{"engine",PartKind::Engine,{}}}};
  PartDefinition wheel{"wheels:standard","Standard rim",PartKind::Wheel,{{"tyre",PartKind::Tyre,{}}},WheelDimensions{200,180}};
  PartDefinition narrow=wheel;narrow.id="wheels:narrow";narrow.wheel->widthMm=100;
  PartDefinition tyre{"tyres:road","Road tyre",PartKind::Tyre,{},std::nullopt,TyreFitment{200,150,210}};
  PartDefinition wrong=tyre;wrong.id="tyres:wrong-radius";wrong.tyre->rimRadiusMm=220;
  PartDefinition engine{"engine:stock","Stock engine",PartKind::Engine};
  c.definitions={body,wheel,narrow,tyre,wrong,engine};check(c.valid(),"catalog");
  PartAssembly a(c,"racer:body");auto w=a.acquire(wheel.id),w2=a.acquire(wheel.id),n=a.acquire(narrow.id),t=a.acquire(tyre.id),bad=a.acquire(wrong.id),e=a.acquire(engine.id);
  check(bool(w)&&bool(w2)&&w.instance!=w2.instance,"distinct ownership");
  auto unchanged=[&](PartResult result,PartFailure expected,const std::string &before){check(result.failure==expected,"wrong rejection");check(a.serialize()==before,"failure changed state");};
  auto before=a.serialize();unchanged(a.install(t.instance,w.instance,"tyre"),PartFailure::ParentNotMounted,before);
  check(bool(a.install(w.instance,1,"front")),"wheel mount");before=a.serialize();unchanged(a.install(w2.instance,1,"front"),PartFailure::SlotOccupied,before);
  unchanged(a.install(bad.instance,w.instance,"tyre"),PartFailure::RimRadius,before);
  unchanged(a.install(e.instance,w.instance,"tyre"),PartFailure::WrongKind,before);
  unchanged(a.install(n.instance,1,"rear"),PartFailure::IncompatiblePart,before);
  check(bool(a.install(t.instance,w.instance,"tyre")),"tyre mount");before=a.serialize();unchanged(a.remove(w.instance),PartFailure::DependentParts,before);
  PartAssembly restored(c,"racer:body");check(bool(restored.restore(before))&&restored.serialize()==before&&restored.valid(),"round trip");
  for(const auto &text: {std::string("RACER_PARTS 2\n"),std::string("RACER_PARTS 1\n2 1\n1 \"unknown:root\" 0 \"\"\n"),before+"trailing",std::string(65537,'x'),std::string("RACER_PARTS 1\n5 2\n1 \"racer:body\" 0 \"\"\n2 \"wheels:standard\" 2 \"tyre\"\n")}) {
   check(!restored.restore(text)&&restored.serialize()==before,"invalid restore changed state");
  }
  check(bool(a.remove(t.instance))&&bool(a.remove(w.instance)),"ordered removal");check(a.inventory().size()==7,"removal lost ownership");
  check(bool(a.install(n.instance,1,"front")),"narrow rim install");before=a.serialize();unchanged(a.install(t.instance,n.instance,"tyre"),PartFailure::RimWidth,before);
  unchanged(a.remove(1),PartFailure::RootRemoval,before);unchanged(a.install(w.instance,1,"missing"),PartFailure::UnknownSlot,before);
  auto invalid=c;invalid.definitions[1].wheel->radiusMm=std::numeric_limits<double>::quiet_NaN();check(!invalid.valid(),"NaN accepted");
  invalid=c;invalid.definitions.push_back(wheel);check(!invalid.valid(),"duplicate qualified id");
  invalid=c;invalid.definitions[0].id="unqualified";check(!invalid.valid(),"unqualified id");
  while(a.inventory().size()<PartAssembly::maxOwnedParts)check(bool(a.acquire(engine.id)),"inventory fill");before=a.serialize();unchanged(a.acquire(engine.id),PartFailure::InventoryFull,before);
  check(a.valid(),"final valid");std::cout<<"PASS: typed fitment, package IDs, owned hierarchy, occupancy, rim constraints, transactional failures and bounded persistence\n";return 0;
 } catch(const std::exception &e) { std::cerr<<e.what()<<'\n';return 1; }
}
