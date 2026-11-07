#include "livery_raster.h"
#include <iostream>
#include <stdexcept>
void require(bool condition,const char *message) { if (!condition) throw std::runtime_error(message); }
int main() try {
  racer::LiveryEditor editor;
  auto empty=racer::rasterLivery(editor.applied());
  require(empty.size()==512*512 && empty[256*512+256]==0xffffffff,"empty white");
  editor.add("stripe");
  auto stripe=racer::rasterLivery(editor.draft());
  require(stripe[256*512+256]==0xff2828e8 && stripe[256*512+100]==0xffffffff,"stripe mask");
  auto t=editor.draft().layers[0].transform;t.opacity=.5;editor.setTransform(t);
  auto half=racer::rasterLivery(editor.draft());
  require(half[256*512+256]==0xff9494f4,"source over opacity");
  auto transparent=racer::rasterLivery(editor.draft(),true);
  require(transparent[256*512+256]==0x802828e8 && transparent[0]==0x00ffffff,"transparent overlay preserves source color and half alpha");
  t.opacity=0;editor.setTransform(t);
  require(racer::rasterLivery(editor.draft(),true)==racer::rasterLivery(editor.applied(),true),"zero opacity never divides by zero");
  t.opacity=.5;editor.setTransform(t);
  editor.setVisible(false);require(racer::rasterLivery(editor.draft())==empty,"hidden");
  editor.setVisible(true);t.opacity=1;t.rotation=90;editor.setTransform(t);
  auto rotated=racer::rasterLivery(editor.draft());
  require(rotated[256*512+100]==0xff2828e8 && rotated[100*512+256]==0xffffffff,"rotation");
  t.rotation=0;editor.setTransform(t);editor.add("checker");
  auto front=racer::rasterLivery(editor.draft());
  editor.moveSelected(-1);auto behind=racer::rasterLivery(editor.draft());
  require(front!=behind && behind[256*512+256]==0xff2828e8,"layer order");
  require(front[0]==0xffffffff,"reserved unpainted texel");
  editor.cancel();require(racer::rasterLivery(editor.draft())==empty,"cancel preview");
  std::cout<<"PASS: raster order, opacity, visibility, rotation, cancel and unpainted sections\n";
} catch (const std::exception &e) { std::cerr<<"FAIL: "<<e.what()<<'\n';return 1; }
