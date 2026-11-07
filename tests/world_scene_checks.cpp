#include "world_scene.h"
#include "world_scale.h"
#include <algorithm>
#include <cmath>
#include <iostream>
#include <map>
#include <set>
#include <utility>

namespace {
int failures=0;
const char* mode="default";
void check(bool ok,const char* name) {
  if(!ok) {++failures;std::cerr<<"FAIL ["<<mode<<"]: "<<name<<'\n';}
}
bool sameVertex(const racer::AssetVertex& a,const racer::AssetVertex& b) {
  return a.x==b.x&&a.y==b.y&&a.z==b.z&&a.color==b.color&&
    a.u==b.u&&a.v==b.v&&a.nx==b.nx&&a.ny==b.ny&&a.nz==b.nz&&a.occlusion==b.occlusion&&a.opacity==b.opacity&&
    a.tx==b.tx&&a.ty==b.ty&&a.tz==b.tz&&a.tw==b.tw;
}
bool insideWorld(const racer::AssetVertex& v) {
  return std::abs(v.x)<=racer::worldScale::halfExtent&&
    std::abs(v.z)<=racer::worldScale::halfExtent;
}
std::pair<int,int> block(const racer::AssetVertex& v) {
  return {int(std::floor(v.x/racer::worldScale::blockSpacing)),
          int(std::floor(v.z/racer::worldScale::blockSpacing))};
}
void inspectScene(const std::vector<racer::AssetVertex>& scene,bool textured) {
  mode=textured?"textured palms":"authored fallback";
  check(!scene.empty(),"city contains rendered geometry");
  // Budget raised 200000->300000: street trees (~22k vertices) and night lamp grid (~30k); fallback was at 197k.
  check(scene.size()<=300000,"city stays within its GPU vertex budget");
  check(scene.size()%3==0,"triangle-list vertex count");
  bool finite=true,unit=true,clear=true,triangles=true,normalsAgree=true,noRoadBridges=true;
  bool foliageDomain=true,foliageColor=true;
  size_t foliageVertices=0;
  std::set<std::pair<float,float>> foliageCorners;
  std::set<std::pair<int,int>> occupiedBlocks;
  float tallest=0;
  for(const auto& v:scene) {
    for(float component:{v.x,v.y,v.z,v.u,v.v,v.nx,v.ny,v.nz}) finite&=std::isfinite(component);
    const double norm=double(v.nx)*v.nx+double(v.ny)*v.ny+double(v.nz)*v.nz;
    unit&=std::abs(norm-1)<.0001;
    if(v.v>=5.5f) {
      ++foliageVertices;
      foliageDomain&=(v.u==0 || v.u==1) && (v.v==6 || v.v==7);
      foliageColor&=v.color==0xffffffff;
      foliageCorners.insert({v.u,v.v});
    }
    if(insideWorld(v)) {
      const double clearance=std::min(std::abs(std::remainder(double(v.x),racer::worldScale::blockSpacing)),
                                      std::abs(std::remainder(double(v.z),racer::worldScale::blockSpacing)));
      clear&=clearance>=7;
      if(v.y>3) occupiedBlocks.insert(block(v));
      tallest=std::max(tallest,v.y);
    }
  }
  for(std::size_t i=0;i+2<scene.size();i+=3) {
    const auto& a=scene[i];const auto& b=scene[i+1];const auto& c=scene[i+2];
    const double ux=double(b.x)-a.x,uy=double(b.y)-a.y,uz=double(b.z)-a.z;
    const double vx=double(c.x)-a.x,vy=double(c.y)-a.y,vz=double(c.z)-a.z;
    const double nx=uy*vz-uz*vy,ny=uz*vx-ux*vz,nz=ux*vy-uy*vx;
    const double length=std::sqrt(nx*nx+ny*ny+nz*nz);
    triangles&=std::isfinite(length)&&length>1e-7;
    if(length>0) for(const auto* v:{&a,&b,&c})
      normalsAgree&=(nx*v->nx+ny*v->ny+nz*v->nz)/length>(v->z>=560?.85:.999);
    // Vertex clearance alone misses a large face spanning across a road.
    // Requiring each in-world triangle to stay in one convex block catches it.
    if(insideWorld(a)||insideWorld(b)||insideWorld(c))
      noRoadBridges&=insideWorld(a)&&insideWorld(b)&&insideWorld(c)&&block(a)==block(b)&&block(a)==block(c);
  }
  check(finite,"positions, UVs and normals are finite");
  check(unit,"normals have unit length");
  check(triangles,"all triangles have finite nonzero area");
  check(normalsAgree,"surface normals agree with triangle winding");
  check(clear,"all in-world vertices preserve 7m road clearance");
  check(noRoadBridges,"no scenery face bridges a road or the world boundary");
  check(occupiedBlocks.size()>=16&&tallest>=15,"district contains distributed buildings and a skyline");
  check(foliageDomain,"foliage vertices use the dedicated complete-image UV domain");
  check(foliageColor,"foliage source RGB is retained with white vertex modulation");
  if(textured) {
    check(foliageVertices>0,"textured mode emits alpha crown geometry");
    check(foliageCorners==std::set<std::pair<float,float>>{{0,6},{0,7},{1,6},{1,7}},"foliage covers all source image corners");
  } else check(foliageVertices==0,"fallback scene has no texture-dependent crown geometry");
  std::cout<<"world scene: "<<scene.size()<<" vertices; "<<occupiedBlocks.size()
           <<" occupied blocks; "<<foliageVertices<<" foliage vertices; "<<mode<<'\n';
}
}

int main() {
  const auto fallback=racer::buildCityScene(),explicitFallback=racer::buildCityScene(false);
  check(fallback.size()==explicitFallback.size()&&std::equal(fallback.begin(),fallback.end(),explicitFallback.begin(),sameVertex),
        "default scene preserves the optional-texture fallback contract");
  inspectScene(fallback,false);
  const auto textured=racer::buildCityScene(true);
  inspectScene(textured,true);
  const auto shell=racer::buildCityScene(true,false);
  inspectScene(shell,true);
  bool fallbackRoof=false;
  for(size_t i=0;i<shell.size();i+=3) {
    const auto &a=shell[i],&b=shell[i+1],&c=shell[i+2];
    if(std::min({a.y,b.y,c.y})<=3)continue;
    const double det=(b.z-c.z)*(a.x-c.x)+(c.x-b.x)*(a.z-c.z);
    if(std::abs(det)<1e-8)continue;
    const double u=((b.z-c.z)*(27-c.x)+(c.x-b.x)*(27-c.z))/det;
    const double v=((c.z-a.z)*(27-c.x)+(a.x-c.x)*(27-c.z))/det;
    fallbackRoof|=u>=0&&v>=0&&u+v<=1;
  }
  check(!fallbackRoof,"prepared scenery lots are free of overlapping fallback roofs");
  std::vector<racer::AssetVertex> land;
  racer::city::terrain(land);
  std::map<std::pair<float,float>,std::array<float,4>> shared;
  std::set<int> heights;
  bool connected=true,outside=true,landBounds=true;
  for(const auto& v:land) {
    outside&=v.z>racer::worldScale::halfExtent;
    landBounds&=v.y>=-1&&v.y<220&&v.ny>0;
    const std::array<float,4> attributes{v.y,v.nx,v.ny,v.nz};
    auto [at,inserted]=shared.emplace(std::pair{v.x,v.z},attributes);
    connected&=inserted||at->second==attributes;heights.insert(int(v.y));
  }
  check(connected&&outside&&landBounds,"terrain seams share positions/normals beyond drivable bounds");
  check(heights.size()>80,"terrain has a varied bounded ridgeline rather than repeated peaks");
  // Distinct crown rotations remain deterministic without rebuilding the whole
  // district repeatedly or relying on counts that mirror each emission loop.
  std::vector<racer::AssetVertex> first,repeat,other;
  racer::city::palm(first,15,15,8,1,true);racer::city::palm(repeat,15,15,8,1,true);
  racer::city::palm(other,15,15,8,2,true);
  check(first.size()==repeat.size()&&std::equal(first.begin(),first.end(),repeat.begin(),sameVertex),"same palm variant has deterministic crown geometry");
  const auto crown=std::find_if(first.begin(),first.end(),[](const auto& v){return v.v>=5.5f;});
  const auto otherCrown=std::find_if(other.begin(),other.end(),[](const auto& v){return v.v>=5.5f;});
  check(crown!=first.end() && otherCrown!=other.end(),"focused palm variants contain textured crowns");
  if(crown!=first.end() && otherCrown!=other.end()) {
    const float dx=(crown+1)->x-crown->x,dz=(crown+1)->z-crown->z;
    const float otherDx=(otherCrown+1)->x-otherCrown->x,otherDz=(otherCrown+1)->z-otherCrown->z;
    check(std::abs(std::hypot(dx,dz)-7)<.0001,"authored crown spans seven metres");
    check(std::abs(dx*otherDz-dz*otherDx)>1,"variant rotates crown planes independently of trunk translation");
    float bottom=100,top=-100;
    for(auto v=crown;v!=first.end();++v) {bottom=std::min(bottom,v->y);top=std::max(top,v->y);}
    check(bottom==5 && top==10.5f,"authored crown extends three metres below and2.5 above trunk end");
  }
  std::cout<<failures<<" world scene failures\n";
  // These geometry checks cannot certify material quality or a visual standard.
  return failures?1:0;
}
