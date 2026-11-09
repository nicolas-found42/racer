#include "hud_layout.h"
#include <cmath>
#include <iostream>
#include <stdexcept>
void require(bool value,const char* reason){if(!value)throw std::runtime_error(reason);}
int main()try{
  const auto normal=racer::hudLayout(1280,720);
  require(!normal.compact&&normal.x==0&&normal.y==0&&normal.width==1280&&normal.height==720&&normal.uMax==1&&normal.vMax==1,"normal layout exact identity");
  const auto medium=racer::hudLayout(960,540,true);
  require(!medium.compact&&medium.width==960&&medium.height==540,"medium window keeps the structured menu layout");
  const auto tiny=racer::hudLayout(800,450,true);
  require(tiny.compact&&tiny.width==600&&tiny.height==450&&tiny.x==100,"below 0.75 scale menus use the compact canvas");
  require(24.*tiny.height/tiny.logicalHeight==22.5,"tiny compact controls remain legible");
  const auto mediumDrive=racer::hudLayout(960,540);
  require(!mediumDrive.compact&&mediumDrive.width==960&&mediumDrive.height==540,"medium driving retains corner card positions");
  require(16.*mediumDrive.height/mediumDrive.logicalHeight==12,"enlarged medium secondary type reaches twelve physical pixels");
  const auto small=racer::hudLayout(320,240);
  require(small.compact&&small.width==320&&small.height==240&&small.logicalWidth==640&&small.logicalHeight==480,"minimum uses compact four by three");
  require(small.uMax==.5f&&std::abs(small.vMax-2.f/3)<1e-6,"compact UV samples upper-left canvas crop");
  require(24.*small.height/small.logicalHeight==12,"compact primary text remains twelve physical pixels at minimum");
  const auto wide=racer::hudLayout(3900,240);
  require(wide.compact&&wide.width==320&&wide.height==240&&wide.x==1790&&wide.y==0,"ultrawide compact safe area centered without stretching");
  for(auto size:{std::pair{1281,721},std::pair{800,600},std::pair{2560,1080},std::pair{320,1000},std::pair{65535,65535}}){
    const auto [w,h]=size;const auto fit=racer::hudLayout(uint16_t(w),uint16_t(h));
    require(fit.width<=w&&fit.height<=h&&fit.x+fit.width<=w&&fit.y+fit.height<=h,"safe area bounded");
    require(std::abs(double(fit.width)/fit.logicalWidth-double(fit.height)/fit.logicalHeight)<=1./fit.logicalHeight+1./fit.logicalWidth,"aspect preserved within pixel rounding");
  }
  require(!racer::hudLayout(0,720).width,"zero size has no viewport");
  std::vector<std::string> lines={"GARAGE"};
  for(int i=0;i<25;++i)lines.push_back((i==20?"> ":"  ")+std::to_string(i));
  lines.push_back("UNSAVED: memory only");lines.push_back("Malformed profile; saving disabled");lines.push_back("DRAFT NOT APPLIED");lines.push_back("Arrows / D-pad: select");
  const auto rows=racer::hudPanelRows(lines);
  require(rows.rows.size()==9&&rows.omitted>0&&rows.omittedStatus==0,"bounded compact pagination retains all actual warning rows");
  for(size_t index:{size_t(21),size_t(26),size_t(27),size_t(28)})require(std::find(rows.rows.begin(),rows.rows.end(),index)!=rows.rows.end(),"selected row and late warnings pinned");
  require(std::is_sorted(rows.rows.begin(),rows.rows.end())&&std::adjacent_find(rows.rows.begin(),rows.rows.end())==rows.rows.end(),"source row order retained without duplication");
  require(std::find(rows.rows.begin(),rows.rows.end(),29)==rows.rows.end(),"full-size help replaced by compact control access");
  require(racer::hudStatusRow("Last action: incompatible part")&&racer::hudStatusRow("NO ENGINE: install engine"),"controlled action and driving rejection status retained");
  lines={"STATUS","> Retry"};for(int i=0;i<15;++i)lines.push_back("UNSAVED: component "+std::to_string(i));
  const auto overflow=racer::hudPanelRows(lines);
  require(overflow.omittedStatus==7&&std::find(overflow.rows.begin(),overflow.rows.end(),1)!=overflow.rows.end(),"excess statuses explicitly counted and selected retry remains accessible");
  require(racer::hudPanelRows({}).rows.empty(),"empty panel handled");
  std::cout<<"PASS: exact normal layout,compact text scale,aspect/UV safe areas,selection pagination,status retention and explicit status overflow\n";
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
