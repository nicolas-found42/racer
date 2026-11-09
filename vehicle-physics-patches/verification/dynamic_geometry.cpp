#include "simulation.h"
#include "surface_follow.h"
#include <cassert>
#include <cmath>
#include <iostream>
#include <memory>
using namespace racer;
using namespace racer::surfaceFollow;
static MeshAsset deck(float y){
 MeshAsset a;
 a.triangles={{-20,y,-20},{20,y,20},{20,y,-20},
              {-20,y,-20},{-20,y,20},{20,y,20}};
 a.sections.push_back({0,6});return a;
}
static GeometryPoint transform(const std::array<float,16>&m,GeometryPoint p){
 return {m[0]*p.x+m[4]*p.y+m[8]*p.z+m[12],m[1]*p.x+m[5]*p.y+m[9]*p.z+m[13],m[2]*p.x+m[6]*p.y+m[10]*p.z+m[14]};
}
static double separation(GeometryPoint a,GeometryPoint b){return std::hypot(a.x-b.x,a.y-b.y,a.z-b.z);}
static void orthonormal(const std::array<float,16>&m){
 assert(m[3]==0&&m[7]==0&&m[11]==0&&m[15]==1);
 for(int a=0;a<3;++a)for(int b=0;b<3;++b){double d=0;for(int k=0;k<3;++k)d+=m[a*4+k]*m[b*4+k];assert(std::abs(d-(a==b?1.:0.))<2e-6);}
 const double det=m[0]*(m[5]*m[10]-m[6]*m[9])-m[4]*(m[1]*m[10]-m[2]*m[9])+m[8]*(m[1]*m[6]-m[2]*m[5]);
 assert(std::abs(det-1)<2e-6);
}
static void poseChecks(const Simulation&s,const VehicleGeometry&g){
 const auto body=s.bodyTransform();orthonormal(body);
 assert(separation({body[12],body[13],body[14]},{s.car.x,s.car.y,s.car.z})<1e-5);
 for(size_t i=0;i<4;++i){
  const auto wheel=s.wheelTransform(i);const auto brake=s.wheelTransform(i,false);orthonormal(wheel);orthonormal(brake);
  const auto center=transform(body,{g.wheels[i].center.x,g.wheels[i].center.y+s.car.wheels[i].compression,g.wheels[i].center.z});
  assert(separation(center,{wheel[12],wheel[13],wheel[14]})<1e-5);
  assert(separation({wheel[12],wheel[13],wheel[14]},{brake[12],brake[13],brake[14]})<1e-8);
  // Wheel axle remains unchanged by rolling spin.
  assert(separation({wheel[0],wheel[1],wheel[2]},{brake[0],brake[1],brake[2]})<1e-7);
  const auto axis=transform(body,{std::cos(s.car.wheels[i].steeringAngle),0,-std::sin(s.car.wheels[i].steeringAngle)});
  assert(separation({axis.x-body[12],axis.y-body[13],axis.z-body[14]},{wheel[0],wheel[1],wheel[2]})<1e-5);
 }
}
int main(){
 VehicleGeometry g;
 Limits l;l.twoSided=false;SurfaceIndex::Builder b(l);b.add(deck(0));b.add(deck(4));
 auto index=std::make_shared<SurfaceIndex>(b.finish());
 auto road=makeRoadSampler(index);
 for(double y:{0.,4.}){
  Simulation s;assert(s.setGeometry(g));s.setRoadSampler(road);s.car.y=y;s.synchronizeState();s.tick({},0);
  for(int i=0;i<240;++i)s.tick({});
  assert(std::abs(s.car.y-y)<.05);
  for(const auto&w:s.car.wheels){assert(w.grounded);assert(std::abs(w.contactPoint.y-y)<1e-5);}
  poseChecks(s,g);
 }
 Simulation s;assert(s.setGeometry(g));s.car.x=3;s.car.z=4;s.car.y=20;s.car.heading=.73;s.car.pitch=.23;s.car.roll=-.31;s.synchronizeState();
 s.setRoadSampler([](double,double,double,double)->std::optional<RoadSample>{return {};});
 s.tick({.7,0,.5},.1);poseChecks(s,g);
 Simulation driven;assert(driven.setGeometry(g));driven.tick({},0);for(int i=0;i<300;++i)driven.tick({.6,0,.08});poseChecks(driven,g);
 std::cout<<"Dynamic transform and separated bridge-deck checks passed\n";
}
