#pragma once
#include "world_scene.h"
#include "world_scale.h"

namespace racer::streetDetails {
// Original authored static streetscape: signal appearance supplies human-scale
// intersection context only. No recovered donor mesh, timing, AI or traffic rule.
inline std::vector<AssetVertex> build() {
  std::vector<AssetVertex> result;result.reserve(30000);
  using namespace city;
  // One local assembly faces an approaching vehicle on the +Z arm. Rotating
  // complete assemblies preserves correct face normals and mounted lens hoods.
  auto signal=[&](float cx,float cz,int turn,bool green) {
    std::vector<AssetVertex> local;
    const auto steel=rgb(77,81,77),dark=rgb(31,34,31),rim=rgb(76,72,52);
    box(local,-7.7f,.16f,7.7f,.55f,.3f,.55f,steel,.7f);
    pole(local,{-7.7f,.46f,7.7f},{-7.7f,6.9f,7.7f},.105f,steel,8);
    // Cantilever and support brace remain above a 5m vehicle envelope.
    pole(local,{-7.7f,6.8f,7.7f},{-2.0f,6.8f,7.7f},.085f,steel,8);
    pole(local,{-7.7f,6.1f,7.7f},{-6.3f,6.8f,7.7f},.045f,steel,6);
    box(local,-2.0f,5.1f,7.7f,.46f,1.45f,.25f,dark,.75f);
    box(local,-2.0f,5.05f,7.7f,.64f,1.55f,.08f,rim,.85f);
    for(int i=0;i<3;++i) {
      const float y=6.28f-float(i)*.44f;
      const auto lens=i==0?(green?rgb(71,28,22):rgb(204,48,30)):
        i==1?rgb(85,58,20):(green?rgb(47,179,100):rgb(18,60,38));
      pole(local,{-2,y,7.79f},{-2,y,7.88f},.155f,dark,10);
      pole(local,{-2,y,7.875f},{-2,y,7.895f},.124f,lens,12);
      // Three-sided projecting sun visor, open below the lens.
      box(local,-2,y+.17f,7.96f,.38f,.04f,.25f,dark,.85f);
      box(local,-2.18f,y+.04f,7.96f,.035f,.25f,.25f,dark,.85f);
      box(local,-1.82f,y+.04f,7.96f,.035f,.25f,.25f,dark,.85f);
    }
    // Small curb-side control cabinet and crossing button are separate readable
    // volumes, all outside the 7m ground-level road-clearance corridor.
    box(local,-8.5f,.16f,8.6f,.55f,1.05f,.38f,rgb(123,127,116),.8f);
    box(local,-7.7f,1.08f,7.82f,.2f,.32f,.12f,dark,.6f);
    box(local,-7.7f,1.18f,7.90f,.09f,.09f,.025f,rgb(197,169,65),.5f);
    for(auto v:local) {
      for(int r=0;r<turn;++r) {
        const float x=v.x,nx=v.nx;v.x=-v.z;v.z=x;v.nx=-v.nz;v.nz=nx;
      }
      v.x+=cx;v.z+=cz;result.push_back(v);
    }
  };
  for(int ix=-1;ix<=1;++ix)for(int iz=-1;iz<=1;++iz)
    if(std::abs(ix)+std::abs(iz)<=1)for(int turn=0;turn<4;++turn)
      signal(float(ix*worldScale::blockSpacing),float(iz*worldScale::blockSpacing),turn,turn%2==0);
  return result;
}
} // namespace racer::streetDetails
