#include "drive_hud.h"
#include "hud_layout.h"
#include <CoreGraphics/CoreGraphics.h>
#include <CoreText/CoreText.h>
#include <bgfx/bgfx.h>
#include <bx/math.h>
#include "vs_debugdraw_fill_texture.bin.h"
#include "fs_debugdraw_fill_texture.bin.h"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <stdexcept>
#include <tuple>
#include <vector>

namespace racer {
namespace {
constexpr uint16_t canvasWidth=1280,canvasHeight=720;
struct HudVertex {float x,y,z;uint32_t color;float u,v;};
struct Ink {CGFloat r,g,b,a;};
std::string boundedText(const std::string& value,size_t bytes) {
  size_t end=std::min(value.size(),bytes);
  while(end>0&&end<value.size()&&(static_cast<unsigned char>(value[end])&0xc0)==0x80) --end;
  return value.substr(0,end);
}
constexpr Ink white{.95,.96,.94,1},muted{.66,.73,.75,1},amber{1,.74,.35,1},cyan{.47,.83,.86,1};
void fill(CGContextRef c,CGRect rect,Ink ink,CGFloat radius=0) {
  CGContextSetRGBFillColor(c,ink.r,ink.g,ink.b,ink.a);
  if(radius>0) {
    CGPathRef path=CGPathCreateWithRoundedRect(rect,radius,radius,nullptr);
    CGContextAddPath(c,path);CGContextFillPath(c);CGPathRelease(path);
  } else CGContextFillRect(c,rect);
}
void label(CGContextRef c,const char* face,CGFloat size,const std::string& value,
           CGFloat x,CGFloat baseline,Ink ink,CGFloat width=1000,bool right=false) {
  CFStringRef string=CFStringCreateWithBytes(kCFAllocatorDefault,
      reinterpret_cast<const UInt8*>(value.data()),CFIndex(value.size()),kCFStringEncodingUTF8,false);
  if(!string) return;
  CFStringRef fontName=CFStringCreateWithCString(kCFAllocatorDefault,face,kCFStringEncodingASCII);
  CTFontRef font=CTFontCreateWithName(fontName,size,nullptr);CFRelease(fontName);
  const CGFloat rgba[]{ink.r,ink.g,ink.b,ink.a};
  CGColorSpaceRef space=CGColorSpaceCreateDeviceRGB();
  CGColorRef color=CGColorCreate(space,rgba);CGColorSpaceRelease(space);
  const void* keys[]{kCTFontAttributeName,kCTForegroundColorAttributeName};
  const void* values[]{font,color};
  CFDictionaryRef attributes=CFDictionaryCreate(kCFAllocatorDefault,keys,values,2,
      &kCFTypeDictionaryKeyCallBacks,&kCFTypeDictionaryValueCallBacks);
  CFAttributedStringRef attributed=CFAttributedStringCreate(kCFAllocatorDefault,string,attributes);
  CTLineRef original=CTLineCreateWithAttributedString(attributed),line=original;
  CFAttributedStringRef tokenString=nullptr;CTLineRef token=nullptr,truncated=nullptr;
  if(CTLineGetTypographicBounds(original,nullptr,nullptr,nullptr)>width) {
    tokenString=CFAttributedStringCreate(kCFAllocatorDefault,CFSTR("…"),attributes);
    token=CTLineCreateWithAttributedString(tokenString);
    truncated=CTLineCreateTruncatedLine(original,width,kCTLineTruncationEnd,token);
    if(truncated) line=truncated;
  }
  CGContextSaveGState(c);
  CGContextSetTextMatrix(c,CGAffineTransformMakeScale(1,-1));
  if(right) x-=CTLineGetTypographicBounds(line,nullptr,nullptr,nullptr);
  CGContextSetTextPosition(c,x,baseline);CTLineDraw(line,c);
  CGContextRestoreGState(c);
  if(truncated) CFRelease(truncated);
  if(token) CFRelease(token);
  if(tokenString) CFRelease(tokenString);
  CFRelease(original);CFRelease(attributed);CFRelease(attributes);
  CGColorRelease(color);CFRelease(font);CFRelease(string);
}
}
struct DriveHud::Impl {
  std::vector<uint8_t> pixels=std::vector<uint8_t>(size_t(canvasWidth)*canvasHeight*4);
  CGContextRef context=nullptr;
  bgfx::TextureHandle texture=BGFX_INVALID_HANDLE;
  bgfx::ProgramHandle program=BGFX_INVALID_HANDLE;
  bgfx::UniformHandle sampler=BGFX_INVALID_HANDLE;
  bgfx::VertexLayout layout;
  using Key=std::tuple<int,bool,std::string,std::string,int,std::string>;
  enum class Mode { None,Drive,Panel };
  Key previous{};Mode mode=Mode::None;
  std::vector<std::string> previousPanel;
  bool previousActiveTest=false;
  bool compact=false,medium=false;
  ~Impl() {
    if(bgfx::isValid(texture)) bgfx::destroy(texture);
    if(bgfx::isValid(program)) bgfx::destroy(program);
    if(bgfx::isValid(sampler)) bgfx::destroy(sampler);
    if(context) CGContextRelease(context);
  }
  void paintCompact(const Key& key) {
    const auto& [speed,reverse,vehicle,destination,metres,bearing]=key;
    std::memset(pixels.data(),0,pixels.size());auto c=context;
    CGContextSaveGState(c);CGContextTranslateCTM(c,0,canvasHeight);CGContextScaleCTM(c,1,-1);
    fill(c,CGRectMake(16,16,608,128),{.025,.045,.055,.88},8);
    label(c,"HelveticaNeue-CondensedBold",28,vehicle,32,50,white,576);
    label(c,"HelveticaNeue-Medium",24,destination.empty()?"EXPLORE THE CITY":destination,32,88,cyan,576);
    char range[32];if(metres<1000)std::snprintf(range,sizeof(range),"%d m",metres);
    else std::snprintf(range,sizeof(range),"%.1f km",double(metres)/1000);
    label(c,"HelveticaNeue-Medium",24,std::string(range)+" / "+bearing,32,124,muted,576);
    fill(c,CGRectMake(388,300,236,112),{.025,.045,.055,.88},8);
    label(c,"HelveticaNeue-CondensedBold",70,std::to_string(speed),530,375,white,132,true);
    label(c,"HelveticaNeue-Medium",24,"MPH",545,373,amber,65);
    label(c,"HelveticaNeue-Medium",24,reverse?"REV":"D",410,402,white,160);
    fill(c,CGRectMake(16,426,608,40),{.025,.045,.055,.9},6);
    label(c,"HelveticaNeue-Medium",24,"WASD/RT DRIVE  R RESET  ESC MENU",30,454,white,580);
    CGContextRestoreGState(c);upload();previous=key;mode=Mode::Drive;
  }
  void paint(const Key& key) {
    if(compact){paintCompact(key);return;}
    const CGFloat small=medium?16:12;
    const auto& [speed,reverse,vehicle,destination,metres,bearing]=key;
    std::memset(pixels.data(),0,pixels.size());
    auto c=context;
    // CoreGraphics draws in a top-left logical canvas; text matrices restore
    // upright glyphs. Upload bytes are RGBA with premultiplied alpha.
    CGContextSaveGState(c);CGContextTranslateCTM(c,0,canvasHeight);CGContextScaleCTM(c,1,-1);
    fill(c,CGRectMake(32,32,410,112),{.025,.045,.055,.72},8);
    fill(c,CGRectMake(32,45,3,83),cyan);
    label(c,"HelveticaNeue-CondensedBold",23,"R A C E R",50,61,white);
    label(c,"HelveticaNeue-Medium",10,"CENTRAL DISTRICT  /  FREE DRIVE",194,59,muted,230);
    label(c,"HelveticaNeue-Medium",18,vehicle,50,88,white,370);
    char range[32];
    if(metres<1000) std::snprintf(range,sizeof(range),"%d m",metres);
    else std::snprintf(range,sizeof(range),"%.1f km",double(metres)/1000);
    label(c,"HelveticaNeue-Medium",small,destination.empty()?"EXPLORE THE CITY":destination,50,117,cyan,239);
    label(c,"HelveticaNeue-Medium",small,std::string(range)+"  /  "+bearing,422,117,muted,125,true);
    fill(c,CGRectMake(938,558,310,130),{.025,.045,.055,.78},9);
    fill(c,CGRectMake(958,558,270,2),amber);
    label(c,"HelveticaNeue-Medium",medium?16:11,"GROUND SPEED",958,584,muted);
    fill(c,CGRectMake(1185,573,43,24),reverse?Ink{.7,.29,.12,.65}:Ink{.17,.29,.3,.8},4);
    label(c,"HelveticaNeue-CondensedBold",14,reverse?"REV":"D",1218,590,white,40,true);
    label(c,"HelveticaNeue-CondensedBold",84,std::to_string(speed),1130,666,white,180,true);
    label(c,"HelveticaNeue-Light",22,"MPH",1147,649,amber,78);
    fill(c,CGRectMake(32,616,586,72),{.025,.045,.055,.60},7);
    label(c,"HelveticaNeue-Medium",small,medium?"WASD/RT DRIVE   R RESET   ESC MENU":"WASD / RT   DRIVE     R   RESET     ESC   MENU / GARAGE",49,640,white,551);
    label(c,"HelveticaNeue-Medium",medium?16:11,"M   EVENTS     F8   REPORT",49,660,cyan,551);
    label(c,"HelveticaNeue-Medium",medium?16:10,"BRAKE  ·  RELEASE  ·  BRAKE TO REVERSE",49,677,muted,551);
    CGContextRestoreGState(c);
    upload();previous=key;mode=Mode::Drive;
  }
  void upload() {
    bgfx::updateTexture2D(texture,0,0,0,0,canvasWidth,canvasHeight,
                         bgfx::copy(pixels.data(),uint32_t(pixels.size())));
  }
  void paintCompactPanel(const std::vector<std::string>& lines,bool activeTest) {
    std::memset(pixels.data(),0,pixels.size());auto c=context;
    CGContextSaveGState(c);CGContextTranslateCTM(c,0,canvasHeight);CGContextScaleCTM(c,1,-1);
    fill(c,CGRectMake(12,12,616,456),{.025,.045,.055,.94},8);
    label(c,"HelveticaNeue-CondensedBold",28,lines.front(),28,46,white,584);
    fill(c,CGRectMake(28,58,584,2),cyan);
    const auto visible=hudPanelRows(lines);CGFloat baseline=94;
    for(auto index:visible.rows){
      const auto& text=lines[index];const bool selected=text.starts_with("> ");
      if(selected)fill(c,CGRectMake(22,baseline-27,596,34),{.13,.34,.36,.85},4);
      label(c,selected?"HelveticaNeue-Bold":"HelveticaNeue-Medium",24,text,30,baseline,
        hudStatusRow(text)?amber:selected?cyan:white,580);baseline+=36;
    }
    if(visible.omittedStatus)label(c,"HelveticaNeue-Medium",22,std::to_string(visible.omittedStatus)+" MORE STATUS ROWS / ENLARGE WINDOW",28,421,amber,584);
    else if(visible.omitted)label(c,"HelveticaNeue-Medium",22,std::to_string(visible.omitted)+" MORE ROWS / selection scrolls",28,421,muted,584);
    label(c,"HelveticaNeue-Medium",24,activeTest?"WASD/RT DRIVE  ESC PAUSE":"↑↓/D-PAD  ENTER/SOUTH OK  ESC/EAST BACK",28,454,muted,584);
    CGContextRestoreGState(c);upload();previousPanel=lines;previousActiveTest=activeTest;mode=Mode::Panel;
  }
  void paintPanel(const std::vector<std::string>& lines,bool activeTest) {
    if(compact){paintCompactPanel(lines,activeTest);return;}
    std::memset(pixels.data(),0,pixels.size());
    auto c=context;
    CGContextSaveGState(c);CGContextTranslateCTM(c,0,canvasHeight);CGContextScaleCTM(c,1,-1);
    const CGFloat body=lines.size()>22?14:16;
    auto rows=[&](size_t first,size_t count,CGRect rect,CGFloat font,CGFloat step,bool title) {
      if(!count) return;
      fill(c,rect,{.025,.045,.055,.91},10);
      fill(c,CGRectMake(rect.origin.x+24,rect.origin.y,rect.size.width-48,2),cyan);
      CGFloat y=rect.origin.y+(title?36:25);
      for(size_t i=0;i<count;++i) {
        const auto& text=lines[first+i];
        const bool heading=title&&i==0,selected=text.starts_with("> ");
        const bool error=text.find("INVALID")!=std::string::npos||
                         text.find("UNSAVED")!=std::string::npos||
                         text.find("Malformed")!=std::string::npos||
                         text.find("Saving disabled")!=std::string::npos;
        const bool draft=text.find("DRAFT NOT")!=std::string::npos;
        const bool controls=text.starts_with("Arrows / D-pad")||text.starts_with("ESC /")||
                            text.starts_with("WASD /")||text.starts_with("AUTOMATIC INPUT");
        const Ink ink=error?Ink{1,.49,.34,1}:draft?amber:selected?cyan:controls?muted:white;
        if(selected) {
          fill(c,CGRectMake(rect.origin.x+16,y-font-3,rect.size.width-32,step),{.13,.34,.36,.68},4);
          fill(c,CGRectMake(rect.origin.x+16,y-font-3,3,step),amber);
        }
        label(c,heading?"HelveticaNeue-CondensedBold":selected?"HelveticaNeue-Bold":"HelveticaNeue-Medium",
              heading?22:font,text,rect.origin.x+27,y,ink,rect.size.width-54);
        y+=heading?step+6:step;
      }
    };
    if(activeTest) {
      const size_t top=std::min(size_t(6),lines.size()),bottom=lines.size()-top;
      rows(0,top,CGRectMake(32,32,1040,CGFloat(top)*20+36),16,20,true);
      if(bottom) {
        const CGFloat step=bottom>18?18:22;
        const CGFloat height=CGFloat(bottom)*step+28;
        rows(top,bottom,CGRectMake(32,688-height,1216,height),bottom>18?14:16,step,false);
      }
    } else {
      const CGFloat step=body==14?18:25;
      const CGFloat height=CGFloat(lines.size())*step+50;
      rows(0,lines.size(),CGRectMake(32,std::max(CGFloat(32),(720-height)*.5),1216,height),body,step,true);
    }
    CGContextRestoreGState(c);upload();
    previousPanel=lines;previousActiveTest=activeTest;mode=Mode::Panel;
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
void DriveHud::draw(uint16_t width,uint16_t height,double mph,bool reverse,
                    const std::string& vehicle,const std::string& destination,
                    double distance,const std::string& bearing) {
  if(!width||!height) return;
  const int speed=std::isfinite(mph)?int(std::clamp(std::round(std::abs(mph)),0.,999.)):0;
  const int metres=std::isfinite(distance)?int(std::clamp(std::round(distance/10)*10,0.,100000000.)):0;
  const Impl::Key key{speed,reverse,boundedText(vehicle,512),boundedText(destination,512),metres,boundedText(bearing,64)};
  auto& p=*impl;const bool compact=hudLayout(width,height).compact;
  const bool medium=!compact&&(width<1280||height<720);
  if(p.compact!=compact||p.medium!=medium){p.compact=compact;p.medium=medium;p.mode=Impl::Mode::None;}
  if(p.mode!=Impl::Mode::Drive||key!=p.previous) p.paint(key);
  p.submit(width,height);
}
void DriveHud::drawPanel(uint16_t width,uint16_t height,
                         const std::vector<std::string>& lines,bool activeTest) {
  if(!width||!height||lines.empty()) return;
  auto& p=*impl;const bool compact=hudLayout(width,height,true).compact;
  if(p.compact!=compact){p.compact=compact;p.mode=Impl::Mode::None;}
  if(p.mode!=Impl::Mode::Panel||lines!=p.previousPanel||activeTest!=p.previousActiveTest)
    p.paintPanel(lines,activeTest);
  p.submit(width,height);
}
}
