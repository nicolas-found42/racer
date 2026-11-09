#include "ui_model.h"
#include <iostream>
#include <stdexcept>
using namespace racer::ui;
void require(bool v,const char* r){if(!v)throw std::runtime_error(r);}
int main()try{
  std::vector<std::string> garage={"GARAGE / Acura NSX '04","No pending draft edits.",
    "> Setup A  [Left / Right]","  Acceleration 1.05x [0.80-1.20] - drive force","  Brakes       1.00x [0.80-1.20] - active braking",
    "  Apply and save","  Car: Acura NSX '04 [Left / Right]","Prototype class C / target 0-100: 8.00 s (Racer bands)","",
    "Applied A: defaults in memory; no profile saved yet.","Arrows / D-pad: select, adjust | Enter / South: confirm | Esc / East: back"};
  auto p=parsePanel(garage,5);
  require(p.title=="GARAGE"&&p.subtitle=="Acura NSX '04","title split on slash");
  require(p.hints.size()==3&&p.hints[0].key=="Arrows"&&p.hints[0].action=="select, adjust"&&p.hints[2].key=="Esc","footer becomes keycap hints");
  require(p.rows[0].kind==RowKind::Info&&p.rows[0].label=="No pending draft edits.","notes stay informational");
  require(p.rows[1].selected&&p.rows[1].kind==RowKind::Option&&p.rows[1].adjustable&&p.rows[1].label=="Setup A","adjustable option loses its bracket text");
  require(p.rows[2].kind==RowKind::Slider&&p.rows[2].value=="1.05x"&&p.rows[2].hint=="drive force"&&p.rows[2].label=="Acceleration","slider label/value/hint");
  require(std::abs(sliderFraction(p.rows[2])-.625)<1e-9,"slider fraction within range");
  require(std::abs(sliderFraction(p.rows[3])-.5)<1e-9,"1.00 is mid-range");
  require(p.rows[5].kind==RowKind::Field&&p.rows[5].label=="Car"&&p.rows[5].value=="Acura NSX '04"&&p.rows[5].adjustable,"car selector is an adjustable field");
  require(p.rows[6].kind==RowKind::Info&&p.rows[6].label=="Prototype class C / target 0-100"&&p.rows[6].value.starts_with("8.00"),"prose with colon splits to key/value only when label is short");
  require(p.hasSelection&&selectable(p).size()==5,"selectable rows are exactly the menu entries");
  // Detail lines that share the option indent beyond optionCount are not selectable.
  auto tests=parsePanel({"DRIVING TESTS / NEXT RUN: SETUP A","> Automatic: 0-100","  Garage","A [NEXT] Accel 1.00x","  acceleration: No comparable result"},2);
  require(selectable(tests).size()==2,"detail indent not selectable");
  require(tests.rows.back().kind==RowKind::Info&&tests.rows.back().indented&&tests.rows.back().value=="No comparable result","indented detail row");
  auto warn=parsePanel({"X","UNSAVED: applied for driving","DRAFT NOT APPLIED / apply","Last action: ok"});
  require(warn.rows[0].kind==RowKind::Warning&&warn.rows[1].kind==RowKind::Notice&&warn.rows[2].kind==RowKind::Notice,"warning/notice split matches HUD status tokens");
  require(parsePanel({}).rows.empty(),"empty input");
  require(parsePanel({"ONLY"}).title=="ONLY"&&parsePanel({"ONLY"}).subtitle.empty(),"title without slash");
  Row r;require(!parseSlider("Acceleration 1.00x [1.20-0.80]",r)&&!parseSlider("no numbers here",r),"malformed sliders rejected");
  auto livery=parsePanel({"LIVERY / ORDERED DECALS","> Decal: stripe [Left/Right]","  Horizontal 0.00","  Rotation 0.00 deg","  Visible: no","  Add decal layer","  Selected layer: 0 / 0 - stripe [Left/Right]"},6);
  require(livery.rows[0].kind==RowKind::Field&&livery.rows[0].value=="stripe"&&livery.rows[0].adjustable,"compact bracket variant");
  require(livery.rows[1].kind==RowKind::Field&&livery.rows[1].label=="Horizontal"&&livery.rows[1].value=="0.00","numeric tail field");
  require(livery.rows[2].value=="0.00 deg","numeric tail keeps unit");
  require(livery.rows[4].kind==RowKind::Option&&livery.rows[4].label=="Add decal layer","plain command stays option");
  require(livery.rows[5].kind==RowKind::Field&&livery.rows[5].value.starts_with("0 / 0")&&livery.rows[5].adjustable,"layer selector");
  auto events=parsePanel({"E","> Event: grid-intro [Left / Right]","  Start nearby event (within 25 m)","  Buy Touring ownership / 3000 credits"},3);
  require(events.rows[1].kind==RowKind::Option&&events.rows[2].kind==RowKind::Option,"prose with embedded numbers stays a command");
  std::cout<<"PASS: ui view model classifies titles, hints, sliders, fields, notices and detail rows\n";
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
