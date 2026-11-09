#include "drive_hud.h"
#include "hud_layout.h"
#include "ui_model.h"
#include "ui_paint.h"
#include "world_scale.h"
#include <CoreGraphics/CoreGraphics.h>
#include <CoreText/CoreText.h>
#include <bgfx/bgfx.h>
#include <bx/math.h>
#include "vs_debugdraw_fill_texture.bin.h"
#include "fs_debugdraw_fill_texture.bin.h"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <sstream>
#include <stdexcept>
#include <vector>

namespace racer {
namespace {
using namespace paint;
using ui::upper;
constexpr uint16_t canvasWidth=1280,canvasHeight=720;
struct HudVertex {float x,y,z;uint32_t color;float u,v;};
std::string boundedText(const std::string& value,size_t bytes) {
  size_t end=std::min(value.size(),bytes);
  while(end>0&&end<value.size()&&(static_cast<unsigned char>(value[end])&0xc0)==0x80) --end;
  return value.substr(0,end);
}
std::string rangeText(int metres) {
  char range[32];
  if(metres<1000) std::snprintf(range,sizeof(range),"%d m",metres);
  else std::snprintf(range,sizeof(range),"%.1f km",double(metres)/1000);
  return range;
}
std::string clock(double seconds) {
  char text[32];
  const int whole=int(seconds);
  if(whole>=60) std::snprintf(text,sizeof(text),"%d:%05.2f",whole/60,seconds-60*(whole/60));
  else std::snprintf(text,sizeof(text),"%.2f",seconds);
  return text;
}
Ink speedColour(double t) {
  t=std::clamp(t,0.,1.);
  return t<.7?mix(cyan,amber,t/.7):mix(amber,red,(t-.7)/.3);
}
// Dark glass plate used by every HUD cluster: soft shadow, vertical gradient, hairline.
void plate(CGContextRef c,CGRect r,CGFloat radius,CGFloat alpha=1,CGFloat skew=0) {
  CGContextSaveGState(c);
  CGContextSetShadowWithColor(c,{0,3},12,shade(0,0,0,.45*alpha));
  if(skew>0) skewFill(c,r,skew,{.02,.035,.048,.55*alpha});
  else fill(c,r,{.02,.035,.048,.55*alpha},radius);
  CGContextRestoreGState(c);
  if(skew>0) gradientSkew(c,r,skew,{.07,.11,.14,.80*alpha},{.02,.035,.048,.72*alpha});
  else gradientRect(c,r,{.07,.11,.14,.80*alpha},{.02,.035,.048,.72*alpha},false,radius);
  setStroke(c,{1,1,1,.10*alpha});CGContextSetLineWidth(c,1);
  if(skew>0){skewPath(c,r,skew);CGContextStrokePath(c);}
  else{rounded(c,r,radius);CGContextStrokePath(c);}
}
void triangleArrow(CGContextRef c,CGPoint at,CGFloat size,double radians,Ink k) {
  const CGPoint pts[]{{0,-size},{size*.78,size*.82},{0,size*.36},{-size*.78,size*.82}};
  const CGFloat s=std::sin(radians),co=std::cos(radians);
  setFill(c,k);
  for(int i=0;i<4;++i){
    const CGFloat x=at.x+pts[i].x*co-pts[i].y*s,y=at.y+pts[i].x*s+pts[i].y*co;
    if(i==0) CGContextMoveToPoint(c,x,y);else CGContextAddLineToPoint(c,x,y);
  }
  CGContextClosePath(c);CGContextFillPath(c);
}
void diamond(CGContextRef c,CGPoint at,CGFloat r,Ink k) {
  setFill(c,k);
  CGContextMoveToPoint(c,at.x,at.y-r);CGContextAddLineToPoint(c,at.x+r,at.y);
  CGContextAddLineToPoint(c,at.x,at.y+r);CGContextAddLineToPoint(c,at.x-r,at.y);
  CGContextClosePath(c);CGContextFillPath(c);
}

// ---- driving HUD ---------------------------------------------------------
void speedometer(CGContextRef c,const DriveState& s,CGPoint centre) {
  constexpr double maxMph=180,start=135,sweep=270;
  const double mph=std::clamp(s.mph,0.,999.),fraction=std::min(mph/maxMph,1.);
  // Backing disc with a faint top-light so it reads as a lens, not a flat circle.
  CGContextSaveGState(c);
  CGContextSetShadowWithColor(c,{0,4},16,shade(0,0,0,.5));
  setFill(c,{.02,.035,.048,.62});CGContextFillEllipseInRect(c,CGRectMake(centre.x-114,centre.y-114,228,228));
  CGContextRestoreGState(c);
  CGContextSaveGState(c);
  CGContextAddEllipseInRect(c,CGRectMake(centre.x-114,centre.y-114,228,228));CGContextClip(c);
  radialGlow(c,{centre.x,centre.y-50},170,{.16,.26,.31,.50},{.02,.035,.048,.78});
  CGContextRestoreGState(c);
  setStroke(c,{1,1,1,.12});CGContextSetLineWidth(c,1.5);
  CGContextStrokeEllipseInRect(c,CGRectMake(centre.x-113.5,centre.y-113.5,227,227));
  // Track + value arc (cyan -> amber -> red as speed climbs).
  arc(c,centre,102,start,start+sweep,6,{1,1,1,.10},kCGLineCapButt);
  const int segments=std::max(1,int(fraction*sweep/2));
  for(int i=0;i<segments;++i) {
    const double t0=double(i)/segments,t1=double(i+1)/segments;
    arc(c,centre,102,start+sweep*fraction*t0,start+sweep*fraction*t1+.8,6,speedColour(fraction*(t0+t1)/2));
  }
  // Ticks every 10 mph, labels every 20; passed ticks light up.
  for(int v=0;v<=int(maxMph);v+=10) {
    const double angle=start+sweep*v/maxMph;const bool major=v%20==0,lit=v<=mph;
    const Ink k=lit?speedColour(double(v)/maxMph):Ink{1,1,1,major?.40:.24};
    const auto a=onCircle(centre,91,angle),b=onCircle(centre,major?78:84,angle);
    setStroke(c,k);CGContextSetLineWidth(c,major?2.4:1.3);
    CGContextBeginPath(c);CGContextMoveToPoint(c,a.x,a.y);CGContextAddLineToPoint(c,b.x,b.y);CGContextStrokePath(c);
    if(major&&v%40==0) {
      const auto p=onCircle(centre,64,angle);
      text(c,kNumeric,13,std::to_string(v),p.x,p.y+4.5,lit?white.withAlpha(.9):Ink{1,1,1,.38},40,Align::Center,.4);
    }
  }
  // Needle tip: a small bright bead riding the arc end.
  if(fraction>0.002) {
    const auto tip=onCircle(centre,102,start+sweep*fraction);
    CGContextSaveGState(c);
    CGContextSetShadowWithColor(c,{0,0},10,shade(.4,.9,1,.9));
    setFill(c,white);CGContextFillEllipseInRect(c,CGRectMake(tip.x-4.5,tip.y-4.5,9,9));
    CGContextRestoreGState(c);
  }
  text(c,kNumeric,76,std::to_string(int(std::round(mph))),centre.x+4,centre.y+22,white,120,Align::Center,0,true);
  text(c,kLabel,15,"MPH",centre.x,centre.y+43,amber,60,Align::Center,3.5);
  const CGRect gear=CGRectMake(centre.x-19,centre.y+62,38,24);
  fill(c,gear,s.reverse?Ink{.75,.30,.12,.80}:Ink{.12,.34,.38,.85},5);
  text(c,kNumeric,18,s.reverse?"R":"D",centre.x,centre.y+80,white,30,Align::Center,.6);
  // Pedal bars (real inputs): brake left, throttle right of the dial.
  const CGFloat barX[]{centre.x+126,centre.x+142};const double values[]{s.brake,s.throttle};
  const Ink tones[]{red,green};const char* names[]{"B","T"};
  for(int i=0;i<2;++i) {
    const CGRect rail=CGRectMake(barX[i],centre.y-52,9,112);
    fill(c,CGRectInset(rail,-2,-2),{.02,.035,.048,.62},5);
    fill(c,rail,{1,1,1,.10},3);
    const CGFloat h=rail.size.height*CGFloat(std::clamp(values[i],0.,1.));
    if(h>0.5) fill(c,CGRectMake(rail.origin.x,rail.origin.y+rail.size.height-h,rail.size.width,h),tones[i],3);
    text(c,kNumeric,12,names[i],rail.origin.x+4.5,rail.origin.y+rail.size.height+16,muted,12,Align::Center,.4);
  }
}

// Radar: heading-up disc with a rotating compass rim and blips for the
// destination and upcoming gates (real positions; no road data is drawn).
void radar(CGContextRef c,const DriveState& s,CGPoint centre) {
  constexpr CGFloat R=76;
  const double range=120+std::clamp(s.mph,0.,100.)*1.8;
  CGContextSaveGState(c);
  CGContextSetShadowWithColor(c,{0,4},14,shade(0,0,0,.5));
  setFill(c,{.02,.035,.048,.62});CGContextFillEllipseInRect(c,CGRectMake(centre.x-R-8,centre.y-R-8,2*R+16,2*R+16));
  CGContextRestoreGState(c);
  CGContextSaveGState(c);
  CGContextAddEllipseInRect(c,CGRectMake(centre.x-R-8,centre.y-R-8,2*R+16,2*R+16));CGContextClip(c);
  radialGlow(c,{centre.x,centre.y-30},R*1.9,{.14,.24,.29,.5},{.02,.035,.048,.8});
  // Authored street grid: roads every 100 m (road width 12 m) inside +-500 m.
  {
    const double k=(R+4)/range,sh=std::sin(s.heading),ch=std::cos(s.heading);
    auto toScreen=[&](double wx,double wz){
      const double dx=wx-s.carX,dz=wz-s.carZ,fwd=dx*sh+dz*ch,right=dx*ch-dz*sh;
      return CGPoint{CGFloat(centre.x+right*k),CGFloat(centre.y-fwd*k)};
    };
    const double e=worldScale::halfExtent;
    const CGPoint corners[]{toScreen(-e,-e),toScreen(e,-e),toScreen(e,e),toScreen(-e,e)};
    setFill(c,{.09,.15,.18,1});
    CGContextMoveToPoint(c,corners[0].x,corners[0].y);
    for(int i=1;i<4;++i) CGContextAddLineToPoint(c,corners[i].x,corners[i].y);
    CGContextClosePath(c);CGContextFillPath(c);
    setStroke(c,{.27,.35,.38,1});CGContextSetLineWidth(c,std::max(2.4,worldScale::roadWidth*k));
    CGContextSetLineCap(c,kCGLineCapButt);
    for(int i=-int(e/worldScale::blockSpacing);i<=int(e/worldScale::blockSpacing);++i) {
      const double axis=i*worldScale::blockSpacing;
      const auto a=toScreen(axis,-e),b=toScreen(axis,e),c1=toScreen(-e,axis),d1=toScreen(e,axis);
      CGContextBeginPath(c);CGContextMoveToPoint(c,a.x,a.y);CGContextAddLineToPoint(c,b.x,b.y);
      CGContextMoveToPoint(c,c1.x,c1.y);CGContextAddLineToPoint(c,d1.x,d1.y);CGContextStrokePath(c);
    }
  }
  // View wedge (forward 70 degrees).
  setFill(c,{cyan.r,cyan.g,cyan.b,.10});
  CGContextMoveToPoint(c,centre.x,centre.y);
  for(int i=0;i<=14;++i){const auto p=onCircle(centre,R,-125+i*70./14);CGContextAddLineToPoint(c,p.x,p.y);}
  CGContextClosePath(c);CGContextFillPath(c);
  CGContextRestoreGState(c);
  setStroke(c,{1,1,1,.12});CGContextSetLineWidth(c,1.5);
  CGContextStrokeEllipseInRect(c,CGRectMake(centre.x-R-7.5,centre.y-R-7.5,2*R+15,2*R+15));
  for(CGFloat f:{.33,.66}) {setStroke(c,{1,1,1,.07});CGContextSetLineWidth(c,1);CGContextStrokeEllipseInRect(c,CGRectMake(centre.x-R*f,centre.y-R*f,2*R*f,2*R*f));}
  // Compass rim: north is -heading from the car's forward axis.
  const char* names[]{"N","E","S","W"};
  for(int i=0;i<4;++i) {
    const double a=-s.heading+i*M_PI/2;const CGFloat deg=a*180/M_PI-90;
    const auto p=onCircle(centre,R-1,deg),q=onCircle(centre,R-9,deg),t=onCircle(centre,R-20,deg);
    setStroke(c,i==0?Ink{red}:Ink{1,1,1,.45});CGContextSetLineWidth(c,i==0?3:2);
    CGContextBeginPath(c);CGContextMoveToPoint(c,p.x,p.y);CGContextAddLineToPoint(c,q.x,q.y);CGContextStrokePath(c);
    text(c,kNumeric,i==0?15:12,names[i],t.x,t.y+(i==0?5:4),i==0?red:Ink{1,1,1,.55},20,Align::Center);
  }
  for(int i=0;i<24;++i) if(i%6) {
    const CGFloat deg=(-s.heading*180/M_PI)+i*15-90;
    const auto p=onCircle(centre,R-1,deg),q=onCircle(centre,R-5,deg);
    setStroke(c,{1,1,1,.22});CGContextSetLineWidth(c,1);
    CGContextBeginPath(c);CGContextMoveToPoint(c,p.x,p.y);CGContextAddLineToPoint(c,q.x,q.y);CGContextStrokePath(c);
  }
  // Blips.
  for(const auto& b:s.blips) {
    const bool clamped=b.distance>range;const CGFloat r=(clamped?1.:b.distance/range)*(R-26);
    const CGFloat deg=b.bearing*180/M_PI-90;const auto p=onCircle(centre,r,deg);
    const Ink tone=b.kind==2?amber.withAlpha(.55):amber;
    CGContextSaveGState(c);CGContextSetShadowWithColor(c,{0,0},8,shade(1,.7,.25,b.kind==2?.4:.9));
    if(clamped) triangleArrow(c,p,6,b.bearing,tone);else diamond(c,p,b.kind==2?4.5:6.5,tone);
    CGContextRestoreGState(c);
  }
  triangleArrow(c,centre,7,0,white);
  text(c,kLabel,10.5,"RANGE "+std::to_string(int(std::round(range/10)*10))+" M",centre.x,centre.y+R+23,muted,120,Align::Center,1.8);
}
void identity(CGContextRef c,const DriveState& s) {
  gradientRect(c,CGRectMake(34,36,3.5,62),{cyan.r,cyan.g,cyan.b,1},{amber.r,amber.g,amber.b,1},false,1.5);
  text(c,kHeavy,28,"RACER",50,62,white,200,Align::Left,7,true);
  text(c,kBody,17,s.vehicle,50,86,white.withAlpha(.94),340,Align::Left,.2,true);
  text(c,kLabel,12.5,"CENTRAL DISTRICT   ·   FREE DRIVE",50,106,muted,340,Align::Left,2.2,true);
}
void controls(CGContextRef c,const DriveState& s) {
  const double alpha=s.mph<1.5?1.:.38;
  struct Group {std::vector<const char*> keys;const char* label;};
  const std::vector<std::vector<Group>> rows{
    {{{"W","S"},"THROTTLE / BRAKE"},{{"A","D"},"STEER"}},
    {{{"R"},"RESET"},{{"M"},"EVENTS"},{{"F8"},"REPORT"},{{"ESC"},"MENU"}}};
  CGFloat y=646;
  CGContextSaveGState(c);CGContextSetAlpha(c,alpha);
  for(const auto& row:rows) {
    CGFloat x=222;
    for(const auto& group:row) {
      for(auto key:group.keys) x+=keycap(c,key,x,y,22,white)+3;
      x+=4;
      x+=text(c,kLabel,12.5,group.label,x,y+16,muted,200,Align::Left,1.6,true)+18;
    }
    y+=28;
  }
  CGContextRestoreGState(c);
}
void destinationStrip(CGContextRef c,const DriveState& s) {
  if(!s.hasDestination||s.test) return;
  const CGRect r=CGRectMake(470,24,340,46);
  plate(c,r,0,1,12);
  triangleArrow(c,{r.origin.x+36,r.origin.y+24},11,s.bearingRadians,cyan);
  text(c,kLabel,11,"DESTINATION",r.origin.x+62,r.origin.y+18,muted,170,Align::Left,2.6);
  text(c,kHeading,19,upper(s.destination.empty()?"EXPLORE THE CITY":s.destination),r.origin.x+62,r.origin.y+38,white,180,Align::Left,1);
  const int metres=int(std::clamp(std::round(s.distance/10)*10,0.,1e8));
  text(c,kNumeric,25,rangeText(metres),r.origin.x+r.size.width-12,r.origin.y+31,amber,110,Align::Right,.5);
  text(c,kLabel,11,s.bearing,r.origin.x+r.size.width-12,r.origin.y+43,muted,80,Align::Right,2);
}
// Floating waypoint: diamond over the target when visible; edge arrow when not.
bool worldMarker(CGContextRef c,const DriveState& s,const HudLayout& fit,float windowWidth,float windowHeight) {
  if(!s.markerActive) return false;
  float lx=(s.markerX-fit.x)/std::max(1.f,float(fit.width))*fit.logicalWidth,
        ly=(s.markerY-fit.y)/std::max(1.f,float(fit.height))*fit.logicalHeight;
  (void)windowWidth;(void)windowHeight;
  const float w=fit.logicalWidth,h=fit.logicalHeight;
  const CGFloat inset=70;
  const bool inside=!s.markerBehind&&lx>inset&&lx<w-inset&&ly>inset+10&&ly<h-inset-60;
  const std::string label=upper(s.markerLabel)+"  ·  "+rangeText(int(std::clamp(std::round(s.markerDistance/10)*10,0.,1e8)));
  if(inside) {
    CGContextSaveGState(c);
    CGContextSetShadowWithColor(c,{0,0},14,shade(1,.7,.25,.9));
    diamond(c,{lx,ly},11,amber);
    CGContextRestoreGState(c);
    diamond(c,{lx,ly},5,Ink{.02,.035,.048,1});
    setStroke(c,{amber.r,amber.g,amber.b,.55});CGContextSetLineWidth(c,1.5);
    CGContextBeginPath(c);CGContextMoveToPoint(c,lx,ly+14);CGContextAddLineToPoint(c,lx,ly+40);CGContextStrokePath(c);
    const CGFloat tw=measure(kLabel,13,label,1.6)+24;
    plate(c,CGRectMake(lx-tw/2,ly+42,tw,24),4,1);
    text(c,kLabel,13,label,lx,ly+59,white,320,Align::Center,1.6);
    return true;
  } else {
    const float cx=w/2,cy=h/2;float dx=lx-cx,dy=ly-cy;
    if(s.markerBehind){dx=-dx;dy=-dy;if(std::abs(dx)<1&&std::abs(dy)<1)dy=1;}
    const float scale=std::min((w/2-inset)/std::max(std::abs(dx),1e-3f),(h/2-inset-30)/std::max(std::abs(dy),1e-3f));
    const float ex=cx+dx*scale,ey=cy+dy*scale;
    CGContextSaveGState(c);
    CGContextSetShadowWithColor(c,{0,0},12,shade(1,.7,.25,.9));
    triangleArrow(c,{ex,ey},14,std::atan2(dx,-dy),amber);
    CGContextRestoreGState(c);
    const auto dist=rangeText(int(std::clamp(std::round(s.markerDistance/10)*10,0.,1e8)));
    text(c,kNumeric,17,dist,ex,ey+(dy>0?-24:34),white,90,Align::Center,.4,true);
  }
  return false;
}

// Announcement banner: slides in with a two-step echo, holds, then fades (cf. console
// "GO" / "FINAL LAP" banners). `phase` runs 0..1 over the banner lifetime.
void banner(CGContextRef c,const std::string& title,const std::string& sub,double phase,Ink tone) {
  const double in=std::clamp(phase/.12,0.,1.),out=std::clamp((1-phase)/.25,0.,1.);
  const double ease=1-(1-in)*(1-in),alpha=ease*out;
  const CGFloat w=std::max<CGFloat>(300,measure(kHeavy,46,title,3)+90),h=64,cx=640,y=236;
  for(int i=2;i>=0;--i) {
    const CGFloat offset=-(1-ease)*220-i*16;
    CGContextSaveGState(c);CGContextSetAlpha(c,alpha*(i==0?1:i==1?.30:.14));
    const CGRect r=CGRectMake(cx-w/2+offset,y,w,h);
    gradientSkew(c,r,16,mix(teal,cyan,.35),{teal.r,teal.g,teal.b,.85});
    if(i==0) {
      skewFill(c,CGRectMake(r.origin.x,r.origin.y,w,3),16,{1,1,1,.55});
      text(c,kHeavy,46,title,cx+offset+8,y+48,white,w-30,Align::Center,3,true);
      if(!sub.empty()) text(c,kLabel,13,sub,cx+offset+8,y+h+22,tone,w,Align::Center,4,true);
    }
    CGContextRestoreGState(c);
  }
}
void testHud(CGContextRef c,const DriveState& s) {
  const auto& t=*s.test;
  const std::string name=upper(t.name);
  if(t.countdown) {
    text(c,kLabel,14,name,640,92,white.withAlpha(.85),420,Align::Center,4,true);
    text(c,kLabel,13,t.automatic?"AUTOMATIC INPUT":"GET READY",640,114,amber,300,Align::Center,5,true);
    const CGFloat cx=640,cy=196;
    arc(c,{cx,cy},62,-90,-90+360*std::clamp(t.countdownSeconds-std::floor(t.countdownSeconds),0.,1.),5,amber,kCGLineCapRound);
    arc(c,{cx,cy},62,0,360,2,{1,1,1,.18});
    // Each second the digit pops in (scale 1.45 -> 1, fade 0 -> 1) like the console launch countdowns.
    const double phase=1-(t.countdownSeconds-std::floor(t.countdownSeconds));
    const double pop=std::clamp(phase/.35,0.,1.),ease=1-(1-pop)*(1-pop);
    CGContextSaveGState(c);
    CGContextTranslateCTM(c,cx,cy+8);CGContextScaleCTM(c,1.45-.45*ease,1.45-.45*ease);
    text(c,kNumeric,92,std::to_string(std::max(1,int(std::ceil(t.countdownSeconds)))),0,24,white.withAlpha(.25+.75*ease),200,Align::Center,0,true);
    CGContextRestoreGState(c);
    return;
  }
  const CGRect r=CGRectMake(430,24,420,t.kind==2?108:96);
  plate(c,r,0,1,14);
  text(c,kLabel,12,name,r.origin.x+28,r.origin.y+22,muted,300,Align::Left,2.6);
  text(c,kNumeric,54,clock(t.elapsed),r.origin.x+26,r.origin.y+70,white,230,Align::Left,0,true);
  text(c,kLabel,14,"SEC",r.origin.x+26+measure(kNumeric,54,clock(t.elapsed))+6,r.origin.y+70,amber,60,Align::Left,2);
  if(t.kind==2) {
    text(c,kLabel,11,"GATE",r.origin.x+r.size.width-26,r.origin.y+22,muted,80,Align::Right,2.6);
    text(c,kNumeric,34,std::to_string(t.gate)+"/"+std::to_string(t.gates),r.origin.x+r.size.width-26,r.origin.y+58,white,120,Align::Right,.5);
    triangleArrow(c,{r.origin.x+r.size.width-150,r.origin.y+46},13,t.bearing,cyan);
    text(c,kNumeric,22,rangeText(int(t.gateDistance)),r.origin.x+r.size.width-26,r.origin.y+86,amber,120,Align::Right,.4);
    text(c,kLabel,12.5,upper(t.note),r.origin.x+28,r.origin.y+96,muted,260,Align::Left,1.6);
  } else {
    const double target=t.kind==0?100.:100.;
    const double fraction=std::clamp(t.speedKmh/target,0.,1.);
    const CGRect bar=CGRectMake(r.origin.x+28,r.origin.y+80,r.size.width-60,6);
    fill(c,bar,{1,1,1,.12},3);
    if(fraction>0) gradientRect(c,CGRectMake(bar.origin.x,bar.origin.y,bar.size.width*fraction,6),cyan,t.kind==1?red:amber,true,3);
    text(c,kNumeric,22,t.kind==0?"0 → 100 KM/H":(t.measuring?"100 → 0 KM/H":"ACCELERATE TO 100 KM/H"),r.origin.x+r.size.width-26,r.origin.y+58,white,240,Align::Right,.6);
    text(c,kNumeric,22,rangeText(int(t.distance)),r.origin.x+r.size.width-26,r.origin.y+26,amber,120,Align::Right,.4);
  }
}
}

struct DriveHud::Impl {
  std::vector<uint8_t> pixels=std::vector<uint8_t>(size_t(canvasWidth)*canvasHeight*4);
  CGContextRef context=nullptr;
  bgfx::TextureHandle texture=BGFX_INVALID_HANDLE;
  bgfx::ProgramHandle program=BGFX_INVALID_HANDLE;
  bgfx::UniformHandle sampler=BGFX_INVALID_HANDLE;
  bgfx::VertexLayout layout;
  enum class Mode { None,Drive,Panel };
  Mode mode=Mode::None;
  std::vector<std::string> previousPanel;int previousOptions=-2;
  bool previousActiveTest=false;
  bool compact=false;
  double scale=1;
  std::string driveKey;
  HudLayout lastFit;
  // Announcement banner state (set from draw() on test events).
  std::string bannerTitle,bannerSub;double bannerStart=-100;
  bool wasCountdown=false;int lastGate=0;
  static double now(){using namespace std::chrono;return duration<double>(steady_clock::now().time_since_epoch()).count();}
  ~Impl() {
    if(bgfx::isValid(texture)) bgfx::destroy(texture);
    if(bgfx::isValid(program)) bgfx::destroy(program);
    if(bgfx::isValid(sampler)) bgfx::destroy(sampler);
    if(context) CGContextRelease(context);
  }
  void begin(CGContextRef& c) {
    std::memset(pixels.data(),0,pixels.size());c=context;
    CGContextSaveGState(c);CGContextTranslateCTM(c,0,canvasHeight);CGContextScaleCTM(c,1,-1);
    CGContextSetAllowsAntialiasing(c,true);CGContextSetShouldAntialias(c,true);
    CGContextSetAllowsFontSmoothing(c,false);
  }
  void end(CGContextRef c) {CGContextRestoreGState(c);upload();}
  void upload() {
    bgfx::updateTexture2D(texture,0,0,0,0,canvasWidth,canvasHeight,
                         bgfx::copy(pixels.data(),uint32_t(pixels.size())));
  }
  void paintCompact(const DriveState& s) {
    CGContextRef c;begin(c);gTypeScale=1;
    const int metres=int(std::clamp(std::round(s.distance/10)*10,0.,1e8));
    plate(c,CGRectMake(16,16,608,s.test?60:128),8);
    if(s.test) {
      const auto& t=*s.test;
      text(c,kHeading,26,upper(t.name),32,48,white,576);
      text(c,kNumeric,34,t.countdown?"GET READY":clock(t.elapsed)+" s",32,86,amber,300);
      if(t.kind==2) text(c,kNumeric,34,"GATE "+std::to_string(t.gate)+"/"+std::to_string(t.gates),608,86,white,260,Align::Right);
    } else {
      text(c,kHeading,28,s.vehicle,32,50,white,576);
      text(c,kBody,22,s.destination.empty()?"EXPLORE THE CITY":s.destination,32,88,cyan,576);
      text(c,kBody,22,rangeText(metres)+" / "+s.bearing,32,124,muted,576);
    }
    CGContextSaveGState(c);CGContextTranslateCTM(c,500,330);CGContextScaleCTM(c,.8,.8);
    speedometer(c,s,{0,0});
    CGContextRestoreGState(c);
    plate(c,CGRectMake(16,426,608,40),6);
    text(c,kLabel,22,"WASD/RT DRIVE  R RESET  ESC MENU",30,454,white,580,Align::Left,1);
    end(c);mode=Mode::Drive;
  }
  void paintDrive(const DriveState& s,const HudLayout& fit,uint16_t width,uint16_t height) {
    gTypeScale=scale<.9?1.2:1;
    if(compact){gTypeScale=1;paintCompact(s);return;}
    CGContextRef c;begin(c);
    if(s.test) {
      testHud(c,s);
      if(s.test->kind==2||s.test->kind==0||s.test->kind==1) {
        const CGRect note=CGRectMake(0,0,0,0);(void)note;
        if(!s.test->countdown&&s.test->kind!=2) text(c,kLabel,12.5,upper(s.test->note),640,142,white.withAlpha(.8),500,Align::Center,2,true);
      }
    } else {
      identity(c,s);
    }
    const bool markerVisible=worldMarker(c,s,fit,width,height);
    // The destination strip only appears when the world marker is off screen.
    if(!s.test&&!markerVisible) destinationStrip(c,s);
    const double bannerPhase=(now()-bannerStart)/1.9;
    if(bannerPhase>=0&&bannerPhase<1) banner(c,bannerTitle,bannerSub,bannerPhase,amber);
    controls(c,s);
    radar(c,s,{122,590});
    speedometer(c,s,{1096,578});
    end(c);mode=Mode::Drive;
  }
  // ---- menus ------------------------------------------------------------
  struct Block {
    enum Kind {Hero,Detail,KeyValue,Paragraph,Warning,Notice,Sub,Header,Gap} kind=Gap;
    std::string label,value;std::vector<std::string> wrapped;CGFloat height=0;bool good=true;
  };
  static std::vector<Block> buildBlocks(const ui::Panel& panel,const ui::Row* selected,CGFloat width,CGFloat scale) {
    std::vector<Block> blocks;
    if(selected&&!selected->hint.empty()) {
      Block b;b.kind=Block::Detail;b.label=selected->label;b.wrapped=wrap(kBodyMedium,15*scale,selected->hint,width-36);
      b.height=34+CGFloat(b.wrapped.size())*21*scale;blocks.push_back(b);
    }
    for(size_t i=0;i<panel.rows.size();++i) {
      const auto& row=panel.rows[i];
      const bool inColumn=!(row.kind==ui::RowKind::Option||row.kind==ui::RowKind::Slider||row.kind==ui::RowKind::Field)||row.indented;
      if(!inColumn) continue;
      Block b;b.label=row.label;b.value=row.value;
      switch(row.kind) {
      case ui::RowKind::Spacer:b.kind=Block::Gap;b.height=8*scale;break;
      case ui::RowKind::Warning:
      case ui::RowKind::Notice:
        b.kind=row.kind==ui::RowKind::Warning?Block::Warning:Block::Notice;
        b.wrapped=wrap(kBodyMedium,15*scale,row.label,width-52);b.height=CGFloat(b.wrapped.size())*21*scale+18*scale;break;
      default:
        if(!row.value.empty()&&row.label!="MEASUREMENT"&&row.label!="PARTIAL (INVALID)"&&
           measure(kBodyMedium,15*scale,row.label+": "+row.value)>width-40&&
           measure(kBody,15.5*scale,row.value)>(width-40)*.6) {
          Block q=b;q.kind=Block::Paragraph;q.wrapped=wrap(kBodyMedium,15*scale,row.label+": "+row.value,width-36);
          q.height=CGFloat(q.wrapped.size())*21*scale+6*scale;blocks.push_back(std::move(q));continue;
        }
        if(!row.value.empty()&&(row.label=="MEASUREMENT"||row.label=="PARTIAL (INVALID)")) {
          b.kind=Block::Hero;b.good=row.label=="MEASUREMENT";b.height=92;
        } else if(row.indented) {
          b.kind=Block::Sub;b.height=22*scale;
          if(row.value.empty()) {b.wrapped=wrap(kBodyMedium,14*scale,row.label,width-40);b.height=CGFloat(b.wrapped.size())*19*scale+4;}
        } else if(!row.value.empty()) {b.kind=Block::KeyValue;b.height=27*scale;}
        else {
          const bool header=i+1<panel.rows.size()&&panel.rows[i+1].indented;
          b.wrapped=wrap(header?kBody:kBodyMedium,15*scale,row.label,width-36);
          b.kind=header?Block::Header:Block::Paragraph;
          b.height=CGFloat(b.wrapped.size())*21*scale+(header?12*scale:6*scale);
        }
      }
      blocks.push_back(std::move(b));
    }
    return blocks;
  }
  void drawBlocks(CGContextRef c,const std::vector<Block>& blocks,CGRect card,CGFloat scale) {
    CGFloat y=card.origin.y+18*scale;const CGFloat x=card.origin.x+20,w=card.size.width-40;
    for(const auto& b:blocks) {
      switch(b.kind) {
      case Block::Gap:break;
      case Block::Hero: {
        text(c,kLabel,13,b.label=="MEASUREMENT"?"RESULT":"PARTIAL / INVALID",x,y+14,muted,w,Align::Left,3);
        text(c,kNumeric,66,b.value,x,y+72,b.good?green:red,w,Align::Left,0,true);break;
      }
      case Block::Detail: {
        fill(c,CGRectMake(card.origin.x+12,y,card.size.width-24,b.height-8),{cyan.r,cyan.g,cyan.b,.10},4);
        fill(c,CGRectMake(card.origin.x+12,y,3,b.height-8),cyan);
        text(c,kLabel,12,upper(b.label),x+10,y+19,cyan,w-10,Align::Left,2.2);
        CGFloat ty=y+40*scale;for(const auto& line:b.wrapped){text(c,kBodyMedium,15*scale,line,x+10,ty,white.withAlpha(.9),w-10);ty+=21*scale;}
        break;
      }
      case Block::KeyValue:
        text(c,kLabel,13.5*scale,upper(b.label),x,y+17*scale,muted,w*.58,Align::Left,1.6);
        text(c,kBody,15.5*scale,b.value,x+w,y+17*scale,white,w*.62,Align::Right);
        fill(c,CGRectMake(x,y+25*scale,w,1),{1,1,1,.07});break;
      case Block::Paragraph: {
        CGFloat ty=y+16*scale;for(const auto& line:b.wrapped){text(c,kBodyMedium,15*scale,line,x,ty,white.withAlpha(.84),w);ty+=21*scale;}break;
      }
      case Block::Header: {
        CGFloat ty=y+17*scale;for(const auto& line:b.wrapped){text(c,kBody,16*scale,line,x,ty,white,w);ty+=21*scale;}
        gradientRect(c,CGRectMake(x,y+b.height-6*scale,w,2),{cyan.r,cyan.g,cyan.b,.55},{cyan.r,cyan.g,cyan.b,0},true);break;
      }
      case Block::Sub:
        if(b.wrapped.empty()) {
          text(c,kLabel,13*scale,upper(b.label),x+14,y+15*scale,muted,w*.5,Align::Left,1.4);
          const bool none=b.value.find("No comparable")!=std::string::npos;
          text(c,kBodyMedium,14*scale,b.value,x+w,y+15*scale,none?dim:white.withAlpha(.92),w*.62,Align::Right);
        } else {
          CGFloat ty=y+15*scale;for(const auto& line:b.wrapped){text(c,kBodyMedium,14*scale,line,x+14,ty,muted,w-14);ty+=19*scale;}
        }
        break;
      case Block::Warning:
      case Block::Notice: {
        const Ink tone=b.kind==Block::Warning?red:amber;
        fill(c,CGRectMake(card.origin.x+12,y,card.size.width-24,b.height-6),{tone.r,tone.g,tone.b,.13},4);
        fill(c,CGRectMake(card.origin.x+12,y,3,b.height-6),tone);
        text(c,kNumeric,20,"!",card.origin.x+30,y+22*scale,tone,20,Align::Center);
        CGFloat ty=y+19*scale;for(const auto& line:b.wrapped){text(c,kBodyMedium,15*scale,line,x+22,ty,white.withAlpha(.92),w-22);ty+=21*scale;}
        break;
      }
      }
      y+=b.height;
    }
  }
  static CGFloat blocksHeight(const std::vector<Block>& blocks,CGFloat scale) {
    CGFloat h=36*scale;for(const auto& b:blocks) h+=b.height;return h;
  }
  void backdrop(CGContextRef c,bool centred) {
    if(centred) {
      fill(c,CGRectMake(0,0,canvasWidth,canvasHeight),{0,.01,.02,.52});
      CGContextSaveGState(c);CGContextClipToRect(c,CGRectMake(0,0,canvasWidth,canvasHeight));
      radialGlow(c,{640,360},700,{0,.01,.02,.0},{0,0,.01,.62});CGContextRestoreGState(c);
    } else {
      gradientRect(c,CGRectMake(0,0,720,canvasHeight),{.005,.015,.025,.92},{.005,.015,.025,.50},true);
      gradientRect(c,CGRectMake(720,0,560,canvasHeight),{.005,.015,.025,.50},{.005,.015,.025,.10},true);
    }
    gradientRect(c,CGRectMake(0,0,canvasWidth,150),{0,0,0,.55},{0,0,0,0},false);
    gradientRect(c,CGRectMake(0,624,canvasWidth,96),{0,0,0,0},{0,0,0,.70},false);
  }
  void header(CGContextRef c,const ui::Panel& panel,bool centred) {
    const CGFloat x=centred?640:64;const Align a=centred?Align::Center:Align::Left;
    text(c,kLabel,12.5,"RACER",x,50,cyan,200,a,6);
    text(c,kHeavy,50,upper(panel.title),x,102,white,900,a,2.5,true);
    if(!panel.subtitle.empty()&&panel.subtitle!="RACER") text(c,kBody,18,panel.subtitle,x,132,muted,900,a,.6,true);
    const CGFloat sx=centred?(640-80):64,sy=centred&&panel.subtitle.empty()?116:(panel.subtitle.empty()?116:144);
    gradientSkew(c,CGRectMake(sx,sy,120,3),8,cyan,{cyan.r,cyan.g,cyan.b,.0});
    skewFill(c,CGRectMake(sx+128,sy,22,3),8,amber);
  }
  void footer(CGContextRef c,const ui::Panel& panel) {
    CGFloat x=64;const CGFloat y=670;
    auto chip=[&](const std::string& key,const std::string& action) {
      x+=keycap(c,key,x,y,24,white)+6;
      x+=text(c,kLabel,13,upper(action),x,y+17,muted,260,Align::Left,1.8,true)+26;
    };
    if(panel.hints.empty()) {chip("ESC","BACK");return;}
    for(const auto& hint:panel.hints) {
      const std::string key=ui::upper(hint.key);
      if(key=="ARROWS") {
        const auto comma=hint.action.find(", ");
        chip("↑↓",ui::upper(hint.action.substr(0,comma)));
        if(comma!=std::string::npos) chip("←→",ui::upper(hint.action.substr(comma+2)));
      } else chip(key,hint.action);
    }
  }
  void paintPanelNormal(const std::vector<std::string>& lines,int optionCount) {
    gTypeScale=scale<.9?1.22:1;
    const auto panel=ui::parsePanel(lines,optionCount<0?size_t(-1):size_t(optionCount));
    CGContextRef c;begin(c);
    std::vector<size_t> menu=ui::selectable(panel);
    size_t informational=0;
    for(const auto& row:panel.rows) if(!(row.kind==ui::RowKind::Option||row.kind==ui::RowKind::Slider||row.kind==ui::RowKind::Field)||row.indented) if(row.kind!=ui::RowKind::Spacer) ++informational;
    const bool centred=menu.size()<=5&&informational<=3;
    backdrop(c,centred);header(c,panel,centred);
    const ui::Row* selected=nullptr;
    for(auto index:menu) if(panel.rows[index].selected) selected=&panel.rows[index];
    // Menu column.
    const bool dense=menu.size()>12;
    const CGFloat top=centred?170:dense?164:176,bottom=dense?654:648,colX=centred?(1280-520)/2:64,colW=centred?520:540;
    const CGFloat pitch=std::clamp((bottom-top)/std::max<size_t>(1,menu.size()),28.,centred?58.:44.);
    const CGFloat rowH=pitch-5,skew=rowH*.32;CGFloat y=top;
    for(auto index:menu) {
      const auto& row=panel.rows[index];
      const CGRect r=CGRectMake(colX,y,colW,rowH);
      if(row.selected) {
        CGContextSaveGState(c);CGContextSetShadowWithColor(c,{0,0},14,shade(cyan.r,cyan.g,cyan.b,.35));
        skewFill(c,r,skew,{.10,.40,.45,.9});CGContextRestoreGState(c);
        gradientSkew(c,r,skew,{.18,.62,.68,.96},{.06,.26,.31,.78});
        skewFill(c,CGRectMake(r.origin.x-2,r.origin.y,5,r.size.height),skew,amber);
      } else {
        const bool odd=(&index-&menu[0])%2;
        gradientSkew(c,r,skew,{.05,.08,.10,odd?.74:.58},{.05,.08,.10,odd?.40:.24});
      }
      const CGFloat fs=std::max<CGFloat>(14,std::min<CGFloat>(20,rowH*.54)),base=y+rowH/2+fs*.34,tx0=colX+skew+16;
      CGFloat tx=tx0;
      const Ink body=row.selected?white:white.withAlpha(.80);
      const CGFloat iconW=row.icon!=ui::Icon::None?28:0;
      if(row.icon!=ui::Icon::None) icon(c,row.icon,{tx0+9,y+rowH/2},std::min<CGFloat>(rowH*.58,19),row.selected?amber:Ink{cyan.r,cyan.g,cyan.b,.75});
      tx=tx0+iconW;
      if(row.kind==ui::RowKind::Slider) {
        text(c,kBody,fs*.92,row.label,tx,base,body,150-iconW);
        const CGFloat bx=tx0+150,bw=colW-150-skew-16-96,by=y+rowH/2-3;
        fill(c,CGRectMake(bx,by,bw,6),{0,0,0,.45},3);
        const double fr=ui::sliderFraction(row);
        gradientRect(c,CGRectMake(bx,by,std::max<CGFloat>(6,bw*fr),6),cyan,fr>.8?amber:mix(cyan,green,.5),true,3);
        fill(c,CGRectMake(bx+bw*(row.high>row.low?(1-row.low)/(row.high-row.low):.5)-1,by-5,2,16),{1,1,1,.35}); // 1.00x reference
        CGContextSaveGState(c);CGContextSetShadowWithColor(c,{0,0},8,shade(1,1,1,.5));
        setFill(c,white);CGContextFillEllipseInRect(c,CGRectMake(bx+bw*fr-6,by-3,12,12));CGContextRestoreGState(c);
        if(row.selected) {
          const CGFloat kx=bx+bw*fr,bubble=measure(kNumeric,12,row.value,.3)+14;
          plate(c,CGRectMake(kx-bubble/2,by-26,bubble,18),4,1);
          text(c,kNumeric,12,row.value,kx,by-13,amber,bubble,Align::Center,.3);
        }
        text(c,kNumeric,fs*1.15,row.value,colX+colW-skew-14,base,row.selected?amber:white,80,Align::Right,.4);
      } else if(row.kind==ui::RowKind::Field) {
        text(c,kLabel,fs*.78,upper(row.label),tx,base,row.selected?white.withAlpha(.9):muted,160-iconW,Align::Left,1.6);
        const CGFloat vx=colX+colW-skew-(row.adjustable?44:16);
        text(c,kBody,fs*.95,row.value,vx,base,body,colW-190,Align::Right);
        if(row.adjustable) {
          const Ink k=row.selected?amber:Ink{1,1,1,.35};
          triangleArrow(c,{colX+colW-skew-22,y+rowH/2},5,-1.5708,k);
          triangleArrow(c,{colX+colW-skew-8,y+rowH/2},5,1.5708,k);
        }
      } else {
        text(c,row.selected?kHeading:kBody,fs,row.label,tx,base,body,colW-skew-(row.adjustable?70:44),Align::Left,row.selected?.6:.2);
        if(row.adjustable) {
          const Ink k=row.selected?amber:Ink{1,1,1,.35};
          triangleArrow(c,{colX+colW-skew-22,y+rowH/2},5,-1.5708,k);
          triangleArrow(c,{colX+colW-skew-8,y+rowH/2},5,1.5708,k);
        } else if(row.selected) triangleArrow(c,{colX+colW-skew-14,y+rowH/2},5,1.5708,amber);
      }
      y+=pitch;
    }
    // Information card.
    if(!centred) {
      const CGFloat cardX=colX+colW+48,cardW=1280-64-cardX,cardH=bottom-top;
      CGFloat scale=1;std::vector<Block> blocks;
      for(CGFloat candidate:{1.,.92,.85,.78,.7}) {
        scale=candidate;blocks=buildBlocks(panel,selected,cardW,scale);
        if(blocksHeight(blocks,scale)<=cardH) break;
      }
      const CGFloat h=std::min(cardH,blocksHeight(blocks,scale));
      const CGRect card=CGRectMake(cardX,top,cardW,h);
      plate(c,card,6,.95);
      gradientRect(c,CGRectMake(card.origin.x,card.origin.y,card.size.width,2),cyan,{cyan.r,cyan.g,cyan.b,0},true);
      drawBlocks(c,blocks,card,scale);
    } else if(informational) {
      auto blocks=buildBlocks(panel,nullptr,520,.9);
      CGFloat yy=top+CGFloat(menu.size())*pitch+14;
      const CGFloat h=std::min<CGFloat>(648-yy,blocksHeight(blocks,.9));
      if(h>40) {
        const CGRect card=CGRectMake(380,yy,520,h);
        plate(c,card,6,.85);drawBlocks(c,blocks,card,.9);
      }
    }
    footer(c,panel);
    if(menu.size()>3) {
      size_t at=0;for(size_t i=0;i<menu.size();++i) if(panel.rows[menu[i]].selected) at=i+1;
      if(at) text(c,kLabel,13,std::to_string(at)+" OF "+std::to_string(menu.size()),1216,687,muted,200,Align::Right,2.4,true);
    }
    end(c);mode=Mode::Panel;
  }
  void paintCompactPanel(const std::vector<std::string>& lines,bool activeTest) {
    CGContextRef c;begin(c);gTypeScale=1;
    fill(c,CGRectMake(12,12,616,456),{.02,.035,.048,.94},8);
    text(c,kHeavy,30,upper(lines.front()),28,46,white,584,Align::Left,1);
    gradientSkew(c,CGRectMake(28,58,300,3),8,cyan,{cyan.r,cyan.g,cyan.b,0});
    const auto visible=hudPanelRows(lines);CGFloat baseline=94;
    for(auto index:visible.rows){
      const auto& line=lines[index];const bool selected=line.starts_with("> ");
      if(selected) skewFill(c,CGRectMake(22,baseline-27,590,34),10,{.13,.45,.50,.92});
      text(c,selected?kHeading:kBody,24,line,30,baseline,hudStatusRow(line)?amber:selected?white:white.withAlpha(.86),580);baseline+=36;
    }
    if(visible.omittedStatus) text(c,kBody,22,std::to_string(visible.omittedStatus)+" MORE STATUS ROWS / ENLARGE WINDOW",28,421,amber,584);
    else if(visible.omitted) text(c,kBody,22,std::to_string(visible.omitted)+" MORE ROWS / selection scrolls",28,421,muted,584);
    text(c,kLabel,22,activeTest?"WASD/RT DRIVE  ESC PAUSE":"↑↓/D-PAD  ENTER/SOUTH OK  ESC/EAST BACK",28,454,muted,584,Align::Left,1);
    end(c);mode=Mode::Panel;
  }
  void paintPanel(const std::vector<std::string>& lines,bool activeTest,int optionCount) {
    if(compact) paintCompactPanel(lines,activeTest);
    else paintPanelNormal(lines,optionCount);
    previousPanel=lines;previousActiveTest=activeTest;previousOptions=optionCount;
  }
  void submit(uint16_t width,uint16_t height) {
    constexpr uint16_t view=14; // After the scene optical finish (views10..13).
    const auto fit=hudLayout(width,height,mode==Mode::Panel);
    float projection[16];bx::mtxOrtho(projection,0,fit.logicalWidth,fit.logicalHeight,0,0,100,0,bgfx::getCaps()->homogeneousDepth);
    bgfx::setViewRect(view,int16_t(fit.x),int16_t(fit.y),fit.width,fit.height);bgfx::setViewTransform(view,nullptr,projection);
    bgfx::setViewMode(view,bgfx::ViewMode::Sequential);
    float model[16];bx::mtxIdentity(model);bgfx::setTransform(model);
    bgfx::setScissor();
    if(bgfx::getAvailTransientVertexBuffer(6,layout)<6) return;
    bgfx::TransientVertexBuffer buffer;bgfx::allocTransientVertexBuffer(&buffer,6,layout);
    const float w=fit.logicalWidth,h=fit.logicalHeight,u=fit.uMax,v=fit.vMax;
    const HudVertex vertices[]={{0,0,0,0xffffffff,0,0},{w,0,0,0xffffffff,u,0},{w,h,0,0xffffffff,u,v},
                                {0,0,0,0xffffffff,0,0},{w,h,0,0xffffffff,u,v},{0,h,0,0xffffffff,0,v}};
    static_assert(sizeof(HudVertex)==24);
    std::memcpy(buffer.data,vertices,sizeof(vertices));
    bgfx::setVertexBuffer(0,&buffer);bgfx::setTexture(0,sampler,texture);
    bgfx::setState(BGFX_STATE_WRITE_RGB|BGFX_STATE_WRITE_A|
                   BGFX_STATE_BLEND_FUNC(BGFX_STATE_BLEND_ONE,BGFX_STATE_BLEND_INV_SRC_ALPHA));
    bgfx::submit(view,program);
  }
};
DriveHud::DriveHud():impl(std::make_unique<Impl>()) {
  auto& p=*impl;
  CGColorSpaceRef space=CGColorSpaceCreateDeviceRGB();
  p.context=CGBitmapContextCreate(p.pixels.data(),canvasWidth,canvasHeight,8,size_t(canvasWidth)*4,
      space,CGBitmapInfo(kCGImageAlphaPremultipliedLast)|CGBitmapInfo(kCGBitmapByteOrder32Big));
  CGColorSpaceRelease(space);
  if(!p.context) throw std::runtime_error("drive_hud_bitmap");
  p.layout.begin().add(bgfx::Attrib::Position,3,bgfx::AttribType::Float)
      .add(bgfx::Attrib::Color0,4,bgfx::AttribType::Uint8,true)
      .add(bgfx::Attrib::TexCoord0,2,bgfx::AttribType::Float).end();
  auto vs=bgfx::createShader(bgfx::copy(vs_debugdraw_fill_texture_mtl,sizeof(vs_debugdraw_fill_texture_mtl)));
  auto fs=bgfx::createShader(bgfx::copy(fs_debugdraw_fill_texture_mtl,sizeof(fs_debugdraw_fill_texture_mtl)));
  if(!bgfx::isValid(vs)||!bgfx::isValid(fs)) {
    if(bgfx::isValid(vs)) bgfx::destroy(vs);
    if(bgfx::isValid(fs)) bgfx::destroy(fs);
    throw std::runtime_error("drive_hud_shader");
  }
  p.program=bgfx::createProgram(vs,fs,true);
  p.sampler=bgfx::createUniform("s_texColor",bgfx::UniformType::Sampler);
  p.texture=bgfx::createTexture2D(canvasWidth,canvasHeight,false,1,bgfx::TextureFormat::RGBA8,
      BGFX_SAMPLER_U_CLAMP|BGFX_SAMPLER_V_CLAMP);
  if(!bgfx::isValid(p.program)||!bgfx::isValid(p.sampler)||!bgfx::isValid(p.texture))
    throw std::runtime_error("drive_hud_gpu");
}
DriveHud::~DriveHud()=default;
void DriveHud::draw(uint16_t width,uint16_t height,const DriveState& input) {
  if(!width||!height) return;
  DriveState s=input;
  s.mph=std::isfinite(s.mph)?std::clamp(std::round(std::abs(s.mph)),0.,999.):0;
  s.distance=std::isfinite(s.distance)?std::clamp(std::round(s.distance/10)*10,0.,1e8):0;
  s.vehicle=boundedText(s.vehicle,512);s.destination=boundedText(s.destination,512);
  s.bearing=boundedText(s.bearing,64);s.markerLabel=boundedText(s.markerLabel,128);
  auto q=[](double v,double step){return std::isfinite(v)?std::round(v/step)*step:0.;};
  s.throttle=q(std::clamp(s.throttle,0.,1.),.05);s.brake=q(std::clamp(s.brake,0.,1.),.05);
  s.bearingRadians=q(s.bearingRadians,.02);s.heading=q(std::remainder(s.heading,2*M_PI),.02);s.carX=q(s.carX,1);s.carZ=q(s.carZ,1);
  for(auto& b:s.blips){b.bearing=q(b.bearing,.02);b.distance=q(b.distance,2);}s.markerDistance=q(s.markerDistance,10);
  s.markerX=float(std::round(s.markerX));s.markerY=float(std::round(s.markerY));
  s.time=0;
  if(s.test){
    auto& t=*s.test;t.elapsed=q(t.elapsed,.01);t.countdownSeconds=q(t.countdownSeconds,.02);
    t.distance=std::round(t.distance);t.speedKmh=std::round(t.speedKmh);t.gateDistance=std::round(t.gateDistance);
    t.bearing=q(t.bearing,.02);t.name=boundedText(t.name,128);t.note=boundedText(t.note,128);t.turn=boundedText(t.turn,64);
  }
  auto& p=*impl;const auto fit=hudLayout(width,height);const bool compact=fit.compact;
  const double scale=double(fit.width)/fit.logicalWidth;
  if(std::abs(scale-p.scale)>1e-6){p.scale=scale;p.mode=Impl::Mode::None;}
  if(s.test) {
    if(p.wasCountdown&&!s.test->countdown){p.bannerTitle="GO!";p.bannerSub=upper(s.test->name);p.bannerStart=Impl::now();}
    if(s.test->kind==2&&p.lastGate>0&&s.test->gate>p.lastGate){p.bannerTitle="GATE "+std::to_string(p.lastGate)+" CLEARED";p.bannerSub=std::to_string(s.test->gates-p.lastGate)+" TO GO";p.bannerStart=Impl::now();}
    p.wasCountdown=s.test->countdown;p.lastGate=s.test->gate;
  } else {p.wasCountdown=false;p.lastGate=0;}
  const double bannerPhase=(Impl::now()-p.bannerStart)/1.9;
  const int bannerStep=bannerPhase>=0&&bannerPhase<1?int(bannerPhase*90)+1:0;
  std::ostringstream out;
  out<<bannerStep<<'#'<<int(s.mph)<<'|'<<s.reverse<<'|'<<s.throttle<<'|'<<s.brake<<'|'<<s.hasDestination<<'|'<<s.vehicle<<'|'<<s.destination<<'|'
     <<s.distance<<'|'<<s.bearing<<'|'<<s.bearingRadians<<'|'<<s.markerActive<<s.markerBehind<<'|'<<s.markerX<<','<<s.markerY<<'|'
     <<s.markerLabel<<'|'<<s.markerDistance<<'|'<<s.heading<<'|'<<s.carX<<','<<s.carZ;
  for(const auto& b:s.blips) out<<'|'<<b.kind<<','<<b.bearing<<','<<b.distance;
  out<<'|'<<compact<<'|'<<width<<'x'<<height;
  if(s.test){const auto& t=*s.test;
    out<<"|T"<<t.kind<<'|'<<t.name<<'|'<<t.note<<'|'<<t.countdown<<t.measuring<<t.automatic<<'|'<<t.countdownSeconds<<'|'<<t.elapsed<<'|'
       <<t.distance<<'|'<<t.speedKmh<<'|'<<t.gate<<'/'<<t.gates<<'|'<<t.gateDistance<<'|'<<t.bearing<<'|'<<t.turn;}
  const std::string signature=out.str();
  if(p.compact!=compact){p.compact=compact;p.mode=Impl::Mode::None;}
  if(p.mode!=Impl::Mode::Drive||signature!=p.driveKey){p.paintDrive(s,fit,width,height);p.driveKey=signature;}
  p.submit(width,height);
}
void DriveHud::drawPanel(uint16_t width,uint16_t height,
                         const std::vector<std::string>& lines,bool activeTest,int optionCount) {
  if(!width||!height||lines.empty()) return;
  auto& p=*impl;const auto fit=hudLayout(width,height,true);const bool compact=fit.compact;
  const double scale=double(fit.width)/fit.logicalWidth;
  if(std::abs(scale-p.scale)>1e-6){p.scale=scale;p.mode=Impl::Mode::None;}
  if(p.compact!=compact){p.compact=compact;p.mode=Impl::Mode::None;}
  if(p.mode!=Impl::Mode::Panel||lines!=p.previousPanel||activeTest!=p.previousActiveTest||optionCount!=p.previousOptions)
    p.paintPanel(lines,activeTest,optionCount);
  p.submit(width,height);
}
}
