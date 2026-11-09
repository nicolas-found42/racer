#include "tyre_contact.h"
#include <cassert>
#include <iostream>
#include <limits>
int main() {
 using namespace racer;
 VehicleDynamics d;
 assert(d.valid());
 for(double nan : {std::numeric_limits<double>::infinity(),std::numeric_limits<double>::quiet_NaN()}) {auto bad=d;bad.mass=nan;assert(!bad.valid());bad=d;bad.frontTyre.friction=nan;assert(!bad.valid());}
 TyreParameters p;
 auto invalid=p;invalid.referenceLoad=0;assert(!invalid.valid());
 int checks=0;
 for(double load: {0.,1.,500.,3500.,7500.,20000.})
  for(double grip: {0.,.05,.3,1.,2.})
   for(double x: {-100.,-1.,-.2,-.1,-.01,0.,.01,.1,.2,1.,100.})
    for(double y: {-100.,-1.,-.2,-.1,-.01,0.,.01,.1,.2,1.,100.}) {
      auto f=tyrePhysics::evaluate(p,load,grip,x,y);
      assert(std::isfinite(f.longitudinal)&&std::isfinite(f.lateral)&&std::isfinite(f.aligningMoment));
      assert(std::hypot(f.longitudinal,f.lateral)<=f.capacity*(1+1e-12));
      assert(f.longitudinal*x>=-1e-12 && f.lateral*y<=1e-12);
      auto reflected=tyrePhysics::evaluate(p,load,grip,-x,-y);
      assert(std::abs(f.longitudinal+reflected.longitudinal)<1e-9);
      assert(std::abs(f.lateral+reflected.lateral)<1e-9);
      ++checks;
    }
 auto light=tyrePhysics::frictionCapacity(p,3500,1),heavy=tyrePhysics::frictionCapacity(p,7000,1);
 assert(heavy<2*light);
 auto lon=tyrePhysics::evaluate(p,3500,1,.15,0),combined=tyrePhysics::evaluate(p,3500,1,.15,.15);
 assert(combined.longitudinal<lon.longitudinal);
 auto camber=tyrePhysics::evaluate(p,3500,1,0,0,.05);assert(camber.lateral>0);
 auto zero=tyrePhysics::evaluate(p,0,1,.1,.1);assert(zero.longitudinal==0&&zero.lateral==0);
 auto relax=tyrePhysics::relaxSlip(0,1,10,.5,.1);assert(relax>0&&relax<1);
 auto half=tyrePhysics::relaxSlip(0,1,10,.5,.05);half=tyrePhysics::relaxSlip(half,1,10,.5,.05);assert(std::abs(half-relax)<1e-12);
 MeshAsset a;decltype(a.sections)::value_type sec;sec.wheel=0;sec.rolling=true;sec.count=99;a.sections.push_back(sec);bool threw=false;try{tyreRadialReach(a,0);}catch(const std::invalid_argument&){threw=true;}assert(threw);
 assert(std::isinf(tyreLowestY({},nullptr)));
 std::cout<<checks<<" combined-slip cases passed; profile, load-sensitivity, relaxation, camber and mesh bounds passed\n";
}
