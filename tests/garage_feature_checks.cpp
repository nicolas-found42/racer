#include "play_flow.h"
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <sys/stat.h>
#include <unistd.h>
using namespace racer;
void check(const auto &value, const char *message) {
  if (!value) { std::cerr << "FAIL: " << message << '\n'; std::exit(1); }
}
std::string read(const std::filesystem::path &p) { std::ifstream in(p); return {std::istreambuf_iterator<char>(in),{}}; }
bool contains(const std::vector<std::string> &lines,const std::string &text) {
  for (const auto &line : lines) if (line.find(text)!=std::string::npos) return true;
  return false;
}
void activate(PlayFlow &f,int row) { f.menu=row; f.action(Action::Accept); }
void adjust(PlayFlow &f,int row,int direction,int times=1) {
  f.menu=row; for (int i=0;i<times;++i) f.action(direction>0?Action::Right:Action::Left);
}
int main() {
  char temporary[]="/tmp/racer-garage-features-XXXXXX";check(mkdtemp(temporary),"fixture directory");
  std::filesystem::path root(temporary);const auto profile=(root/"profile.txt").string();
  {
    Diagnostics diagnostics(root/"history");
    PlayFlow f(profile,&diagnostics);f.store.save(f.profile);const auto original=read(profile);
    check(f.features.parts().valid() && f.features.hasEngine(),"stock assembly valid");
    check(f.features.partMultipliers().acceleration==1,"stock neutral multiplier");
    f.garage();activate(f,10);
    check(f.screen==Screen::Parts && f.paused && f.rearming,"appended parts screen pauses/rearms");
    adjust(f,2,1);activate(f,4);check(!f.features.hasEngine(),"remove stock engine");
    adjust(f,2,1,3);activate(f,3);
    check(f.features.hasEngine() && f.features.partMultipliers().acceleration==1.15,"install authored upgrade");
    check(f.features.partsStore().outcome().status==DocumentStatus::Saved,"parts change persisted");
    adjust(f,2,-1);activate(f,4); // stock tyre
    adjust(f,2,-1);activate(f,4); // stock rim now has no dependent tyre
    adjust(f,2,1,3);activate(f,3); // wrong-radius rim
    adjust(f,2,-1,2);const auto before=f.features.parts().serialize();activate(f,3);
    check(f.features.parts().serialize()==before && contains(f.features.lines(GarageFeaturePage::Parts,3),"different rim radius"),"fit failure leaves valid assembly unchanged");
    f.action(Action::Back);check(f.screen==Screen::Garage,"parts back preserves garage");
    activate(f,11);check(f.screen==Screen::Livery,"appended livery screen");
    activate(f,1);adjust(f,3,1);adjust(f,8,-1);activate(f,9);
    check(f.features.livery().dirty() && f.features.livery().applied().layers.empty(),"isolated transformed hidden draft");
    adjust(f,0,1);activate(f,1);activate(f,10);
    check(f.features.livery().draft().layers.front().decal=="number","layer ordering UI");
    activate(f,13);check(!f.features.livery().dirty() && f.features.livery().applied().layers.size()==2,"apply entire livery");
    check(f.features.liveryStore().outcome().status==DocumentStatus::Saved,"livery saved");
    const auto persisted=f.features.livery().serializedApplied();adjust(f,3,-1);f.action(Action::Back);
    check(f.screen==Screen::Garage && !f.features.livery().dirty() && f.features.livery().serializedApplied()==persisted,"back cancels only draft");
    activate(f,11);f.focus=false;adjust(f,3,1);check(!f.features.livery().dirty(),"unfocused feature edit rejected");f.focus=true;
    adjust(f,3,1);check(chmod(root.c_str(),0500)==0,"lock fixture parent");activate(f,13);
    check(f.features.liveryStore().outcome().status==DocumentStatus::Failed && !f.features.livery().dirty(),"valid applied livery retained despite save failure");
    check(read(f.features.liveryStore().path())==persisted && contains(f.features.lines(GarageFeaturePage::Livery,13),"UNSAVED"),"old saved bytes and truthful failure");
    check(chmod(root.c_str(),0700)==0,"unlock parent");activate(f,15);
    check(f.features.liveryStore().outcome().status==DocumentStatus::Saved,"retry saves applied livery");
    check(read(profile)==original,"sidecars do not alter profilev1 bytes");
    PlayFlow restart(profile);check(restart.features.parts().serialize()==f.features.parts().serialize(),"parts reload");
    check(restart.features.livery().serializedApplied()==f.features.livery().serializedApplied(),"livery reload exact applied state");
    std::ofstream(f.features.liveryStore().path()) << "malformed";
    PlayFlow malformed(profile);check(!malformed.features.liveryStore().writable(),"malformed livery disables writes");
    malformed.garage();activate(malformed,11);activate(malformed,1);activate(malformed,13);
    check(read(f.features.liveryStore().path())=="malformed" && malformed.features.livery().applied().layers.size()==1,"malformed original preserved with valid in-memory edit");
  }
  std::string log;for(const auto &p:std::filesystem::directory_iterator(root/"history"))if(p.path().extension()==".jsonl")log+=read(p.path());
  check(log.find("feature_action")!=std::string::npos && log.find("feature_state")!=std::string::npos && log.find("feature_layer")!=std::string::npos,"central feature history persisted");
  check(log.find("\"draft_revision\"")!=std::string::npos && log.find("\"rotation\"")!=std::string::npos,"transform history retained");
  std::filesystem::remove_all(root);
  std::cout<<"PASS: Parts/Livery UI transitions, fitment rejection, drafts/order, save failure/retry, reload, malformed preservation, focus and telemetry\n";
}
