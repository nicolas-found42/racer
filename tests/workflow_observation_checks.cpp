#include "workflow_observation.h"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <unistd.h>
using namespace racer;
void check(bool value,const char *reason) { if (!value) throw std::runtime_error(reason); }
std::string read(const std::filesystem::path &p) { std::ifstream in(p);return {std::istreambuf_iterator<char>(in),{}}; }
size_t count(const std::string &s,const std::string &needle) { size_t result=0,at=0;while ((at=s.find(needle,at))!=std::string::npos) {++result;at+=needle.size();}return result; }
std::string logs(const std::filesystem::path &directory) {std::string result;for(const auto &e:std::filesystem::directory_iterator(directory)) if(e.path().extension()==".jsonl")result+=read(e.path());return result;}
int main(int argc,char **argv) try {
  char temporary[]="/tmp/racer-workflow-XXXXXX";
  const bool retain=argc==2;
  auto root=retain ? std::filesystem::path(argv[1]) : std::filesystem::path(mkdtemp(temporary));
  if (retain) check(std::filesystem::create_directories(root),"fresh evidence directory");
  auto directory=root/"diagnostics",profile=root/"private-player-name";
  std::string appliedHash,careerHash;
  {
    Diagnostics sink(directory);PlayFlow f(profile.string(),&sink);WorkflowObservation observer(&sink);
    observer.observe(f,0);for(int i=1;i<=100;++i)observer.observe(f,i);sink.flush();
    check(count(logs(directory),"\"event\":\"workflow_state\"")==1,"idle snapshot spam");
    check(f.configureVehicle("vehicle-"+std::string(64,'a'),"Test car",VehicleGeometry{}),"configure test vehicle");observer.observe(f,100);sink.flush();
    check(count(logs(directory),"\"event\":\"workflow_state\"")==2,"vehicle identity change omitted");
    f.attempt=sink.operation();f.career.context(f.attempt);
    f.features.action(GarageFeaturePage::Livery,1,FeatureAction::Activate,f.attempt);observer.observe(f,101);
    // Safely force nonregular-target metadata failure after normal successful missing-load.
    std::filesystem::create_directory(profile.string()+".livery");
    f.features.action(GarageFeaturePage::Livery,13,FeatureAction::Activate,f.attempt);observer.observe(f,102);
    check(f.features.liveryStore().outcome().status==DocumentStatus::Failed && f.features.liveryStore().outcome().stage==DocumentStage::Metadata,"injected failure stage");
    check(f.features.livery().applied().layers.size()==1,"telemetry changed in-memory apply");
    std::filesystem::remove(profile.string()+".livery");
    f.features.action(GarageFeaturePage::Livery,15,FeatureAction::Activate,f.attempt);observer.observe(f,103);
    check(f.features.liveryStore().outcome().status==DocumentStatus::Saved,"retry save");
    appliedHash=Diagnostics::identity(f.features.livery().serializedApplied());
    f.career.updatePosition(0,0);f.career.action(2,0,0,0);check(f.career.start(),"career start");
    observer.observe(f,104);
    check(f.career.checkpoint(0),"career first checkpoint");observer.observe(f,105);
    for(size_t i=1;i<5;++i)check(f.career.checkpoint(i),"career checkpoints");
    check(f.career.finish(true,75).reward==5000,"reward");observer.observe(f,106);
    careerHash=Diagnostics::identity(f.career.state().serialize());
    sink.flush();
  }
  {
    Diagnostics sink(directory);PlayFlow restarted(profile.string(),&sink);WorkflowObservation observer(&sink);observer.observe(restarted,0);
    check(Diagnostics::identity(restarted.features.livery().serializedApplied())==appliedHash,"livery restart identity");
    check(Diagnostics::identity(restarted.career.state().serialize())==careerHash,"career restart identity");
    check(restarted.career.state().credits()==5000,"reward restart");sink.flush();
  }
  {
    auto bad=root/"malformed";std::ofstream(bad.string()+".parts")<<"private-document-secret";
    Diagnostics sink(directory);PlayFlow f(bad.string(),&sink);WorkflowObservation observer(&sink);observer.observe(f,0);
    check(!f.features.partsStore().writable(),"malformed writes disabled");sink.flush();
  }
  {
    auto disabled=root/"disabled-recorder";std::ofstream(disabled)<<"not a directory";
    Diagnostics sink(disabled);PlayFlow f((root/"fail-open").string(),&sink);WorkflowObservation observer(&sink);
    observer.observe(f,0);f.features.action(GarageFeaturePage::Livery,1,FeatureAction::Activate);observer.observe(f,1);
    check(f.features.livery().draft().layers.size()==1,"recorder failure changed domain behavior");
  }
  auto text=logs(directory);
  check(text.find("private-player-name")==std::string::npos && text.find("private-document-secret")==std::string::npos,"redaction");
  check(count(text,appliedHash)>=2 && count(text,careerHash)>=2,"cross-run identities missing");
  check(text.find("\"livery_stage\":\"metadata\"")!=std::string::npos,"failure stage missing");
  check(text.find("\"parts_writable\":false")!=std::string::npos,"disabled state missing");

  std::cout<<"PASS: change-only, save failure/retry, restart identities/reward, disabled writes, privacy, recorder fail-open\n";
  if(!retain)std::filesystem::remove_all(root);
  return 0;
} catch(const std::exception &e) {std::cerr<<"FAIL: "<<e.what()<<'\n';return 1;}
