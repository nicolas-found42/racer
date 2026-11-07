#include "street_detail.h"
#include <iostream>
#include <set>
#include <utility>

int main() {
  const auto mesh=racer::streetDetails::build(),second=racer::streetDetails::build();
  int failures=0;auto check=[&](bool ok,const char* why){if(!ok){std::cerr<<why<<'\n';++failures;}};
  check(!mesh.empty()&&mesh.size()%3==0&&mesh.size()<30000,"bounded triangle mesh");
  check(mesh.size()==second.size(),"deterministic size");
  bool finite=true,unit=true,clear=true,deterministic=true,area=true,winding=true;
  std::set<std::pair<int,int>> intersections;
  for(size_t i=0;i<mesh.size();++i) {
    const auto& v=mesh[i];const auto& b=second[i];
    for(float f:{v.x,v.y,v.z,v.nx,v.ny,v.nz,v.u,v.v})finite&=std::isfinite(f);
    unit&=std::abs(std::hypot(v.nx,v.ny,v.nz)-1)<.0001f;
    deterministic&=v.x==b.x&&v.y==b.y&&v.z==b.z&&v.nx==b.nx&&v.ny==b.ny&&v.nz==b.nz&&v.color==b.color;
    const double dx=std::abs(std::remainder(v.x,100.)),dz=std::abs(std::remainder(v.z,100.));
    // Low fixtures must clear BOTH grid-road axes; overhead arms may project
    // into the road only above the explicit authored 5m vehicle envelope.
    clear&=(dx>=7&&dz>=7)||v.y>=5;
    intersections.insert({int(std::round(v.x/100)),int(std::round(v.z/100))});
  }
  for(size_t i=0;i<mesh.size();i+=3) {
    const auto&a=mesh[i];const auto&b=mesh[i+1];const auto&c=mesh[i+2];
    const double ux=b.x-a.x,uy=b.y-a.y,uz=b.z-a.z,vx=c.x-a.x,vy=c.y-a.y,vz=c.z-a.z;
    const double nx=uy*vz-uz*vy,ny=uz*vx-ux*vz,nz=ux*vy-uy*vx,len=std::hypot(nx,ny,nz);
    area&=len>1e-7;
    if(len>0)for(const auto*v:{&a,&b,&c})winding&=(nx*v->nx+ny*v->ny+nz*v->nz)/len>.999;
  }
  check(finite&&unit,"finite unit normals");check(area&&winding,"usable nondegenerate outward triangles");
  check(clear,"ground fixtures and overhead arms preserve driving clearance");check(deterministic,"deterministic vertex content");
  check(intersections.size()==5,"five central intersections carry detail");
  std::cout<<mesh.size()<<" vertices; "<<failures<<" failures\n";
  return failures?1:0;
}
