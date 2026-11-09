#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <string>
#include <string_view>
#include <vector>
namespace racer {
struct HudLayout {
  uint16_t x=0,y=0,width=0,height=0,logicalWidth=1280,logicalHeight=720;
  bool compact=false;
  float uMax=1,vMax=1;
};
inline HudLayout hudLayout(uint16_t width,uint16_t height,bool panel=false) {
  HudLayout out;if(!width||!height)return out;
  const double normal=std::min(double(width)/1280,double(height)/720);
  // The structured menus scale down gracefully to 0.75 (960x540); below that
  // both modes switch to the cropped 640x480 canvas with large type.
  (void)panel;
  out.compact=normal<.75;
  if(out.compact){out.logicalWidth=640;out.logicalHeight=480;out.uMax=.5f;out.vMax=480.f/720;}
  const double scale=std::min(double(width)/out.logicalWidth,double(height)/out.logicalHeight);
  out.width=std::max(uint16_t(1),uint16_t(std::floor(out.logicalWidth*scale)));
  out.height=std::max(uint16_t(1),uint16_t(std::floor(out.logicalHeight*scale)));
  out.x=(width-out.width)/2;out.y=(height-out.height)/2;return out;
}
// These are explicit tokens emitted by the existing presentation producers.
// They retain warnings while compact mode pages options; no source state changes.
inline bool hudStatusRow(std::string_view row) {
  for(auto token:{"UNSAVED","INVALID","Malformed","Saving disabled","saving disabled","DRAFT NOT"})
    if(row.find(token)!=row.npos)return true;
  return row.starts_with("Last action: ")||row.starts_with("NO ENGINE:");
}
inline bool hudControlRow(std::string_view row) {
  return row.starts_with("Arrows / D-pad")||row.starts_with("ESC /")||row.starts_with("WASD /")||row.starts_with("AUTOMATIC INPUT");
}
struct HudPanelRows {std::vector<size_t> rows;size_t omitted=0,omittedStatus=0;};
inline HudPanelRows hudPanelRows(const std::vector<std::string>& lines,size_t capacity=9) {
  HudPanelRows out;if(lines.empty())return out;
  size_t selected=0;
  for(size_t i=1;i<lines.size();++i)if(lines[i].starts_with("> ")){selected=i;break;}
  auto add=[&](size_t i){if(i&&i<lines.size()&&!lines[i].empty()&&!hudControlRow(lines[i])&&out.rows.size()<capacity&&
    std::find(out.rows.begin(),out.rows.end(),i)==out.rows.end())out.rows.push_back(i);};
  add(selected);
  for(size_t i=1;i<lines.size();++i)if(hudStatusRow(lines[i]))add(i);
  size_t trailing=0;
  for(size_t i=lines.size();i>1&&trailing<2;){--i;if(!lines[i].empty()&&!hudControlRow(lines[i])){add(i);++trailing;}}
  for(size_t distance=0;distance<lines.size()&&out.rows.size()<capacity;++distance){
    if(selected>distance)add(selected-distance);
    if(selected+distance<lines.size())add(selected+distance);
  }
  std::sort(out.rows.begin(),out.rows.end());
  for(size_t i=1;i<lines.size();++i)if(!lines[i].empty()&&!hudControlRow(lines[i])&&std::find(out.rows.begin(),out.rows.end(),i)==out.rows.end()){
    ++out.omitted;if(hudStatusRow(lines[i]))++out.omittedStatus;
  }
  return out;
}
}
