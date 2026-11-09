#include "simulation.h"
#include "test_session.h"
#include "surface_follow.h"
#include "tyre_contact.h"
#include <algorithm>
#include <cmath>
#include <functional>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <numbers>
#include <stdexcept>
#include <string>
#include <vector>
using namespace racer;
namespace {
struct Case { std::string name; std::function<void()> run; };
std::vector<Case> cases;
std::map<std::string,double> metrics;
void check(bool yes, const std::string &message) { if (!yes) throw std::runtime_error(message); }
void near(double a,double b,double tolerance,const std::string &message) {
  check(std::isfinite(a)&&std::isfinite(b)&&std::abs(a-b)<=tolerance,
        message+" ("+std::to_string(a)+" vs "+std::to_string(b)+")");
}
void add(std::string name,std::function<void()> run) { cases.push_back({std::move(name),std::move(run)}); }
Simulation fresh() { Simulation sim; sim.reset(); sim.tick({},0); return sim; }
void advance(Simulation &sim,Input input,double duration,double dt=step) {
  const int count=int(std::ceil(duration/dt-1e-10));
  for(int i=0;i<count;++i) sim.tick(input,std::min(dt,duration-i*dt));
}
void finite(const Simulation &sim) {
  for(double v:{sim.car.x,sim.car.y,sim.car.z,sim.car.heading,sim.car.speed,
                sim.car.velocityX,sim.car.velocityY,sim.car.velocityZ,
                sim.car.yawRate,sim.car.pitch,sim.car.roll,sim.car.engineRpm,
                sim.car.distance,sim.car.travel}) check(std::isfinite(v),"non-finite chassis state");
  for(const auto &w:sim.car.wheels) {
    for(double v:{w.compression,w.angularVelocity,w.rotation,w.normalLoad,
                  w.longitudinalForce,w.lateralForce,w.slipRatio,w.slipAngle})
      check(std::isfinite(v),"non-finite wheel state");
    check(w.normalLoad>=0,"negative normal load");
    if(!w.grounded) near(std::hypot(w.longitudinalForce,w.lateralForce),0,1e-9,"airborne tyre force");
  }
}
RoadSampler flat(double friction) {
  return [friction](double,double,double maximum,double drop)->std::optional<RoadSample> {
    if(maximum>=0 && maximum-drop<=0) return RoadSample{0,{0,1,0},friction,1};
    return {};
  };
}
TestResult benchmark(TestKind kind,double dt=step,VehicleSetup setup={}) {
  auto sim=fresh(); TestSession test;
  check(test.start(kind,0,setup,sim),"test start failed");
  for(unsigned i=0;i<20000 && test.active();++i) test.tick(sim,{},dt);
  check(test.result().valid,"benchmark invalid: "+test.result().reason);
  finite(sim);
  return test.result();
}
MeshAsset plane(double height,double slope=0) {
  MeshAsset mesh;
  mesh.triangles={{-5,float(height-slope*5),-5},{5,float(height-slope*5),-5},{5,float(height+slope*5),5},
                  {-5,float(height-slope*5),-5},{5,float(height+slope*5),5},{-5,float(height+slope*5),5}};
  mesh.sections.push_back({0,6,-1,false,false,false}); return mesh;
}
}
int main() {
  add("parameter_validation_is_transactional",[]{
    auto sim=fresh(); check(sim.dynamics().valid(),"default dynamics invalid");
    auto p=sim.dynamics(); const auto revision=sim.configurationRevision();
    p.mass=std::numeric_limits<double>::quiet_NaN();
    check(!sim.setDynamics(p),"NaN mass accepted");
    near(sim.dynamics().mass,1450,1e-12,"invalid update changed mass");
    check(sim.configurationRevision()==revision,"invalid update changed revision");
    p=sim.dynamics(); p.frontBrakeBias=1.2; check(!sim.setDynamics(p),"invalid bias accepted");
    p=sim.dynamics(); p.gearRatios[2]=0; check(!sim.setDynamics(p),"zero gear accepted");
    p=sim.dynamics(); p.torqueRpm[3]=p.torqueRpm[2]; check(!sim.setDynamics(p),"nonordered curve accepted");
  });
  add("extreme_vertical_geometry_rejected_transactionally",[]{
    auto sim=fresh();const VehicleGeometry accepted{};
    check(sim.setGeometry(accepted),"baseline geometry rejected");
    const auto revision=sim.configurationRevision();
    auto bad=accepted;bad.body.maximum.y=1e200;
    check(!sim.setGeometry(bad),"finite enormous body height accepted");
    check(sim.configurationRevision()==revision,"rejected body changed configuration");
    near(sim.geometry()->body.maximum.y,accepted.body.maximum.y,0,"rejected body replaced geometry");
    bad=accepted;for(auto &wheel:bad.wheels)wheel.center.y=1e200;
    check(!sim.setGeometry(bad),"finite enormous wheel elevation accepted");
    check(sim.configurationRevision()==revision,"rejected wheel height changed configuration");
    for(unsigned i=0;i<4;++i)
      near(sim.geometry()->wheels[i].center.y,accepted.wheels[i].center.y,0,
           "rejected wheel height replaced geometry");
  });
  add("extreme_suspension_micro_roll_is_passive",[]{
    auto sim=fresh();auto p=sim.dynamics();VehicleGeometry g;
    p.mass=250;p.rollInertia=50;
    p.frontSuspension.bumpDamping=p.rearSuspension.bumpDamping=30000;
    p.frontSuspension.reboundDamping=p.rearSuspension.reboundDamping=40000;
    p.frontSuspension.springRate=p.rearSuspension.springRate=300000;
    p.frontSuspension.antiRollRate=p.rearSuspension.antiRollRate=200000;
    g.wheels[0].center.x=g.wheels[2].center.x=-4;
    g.wheels[1].center.x=g.wheels[3].center.x=4;
    check(sim.setDynamics(p)&&sim.setGeometry(g),"valid extreme test profile rejected");
    constexpr double initialRoll=1e-6;
    sim.car.z=-200;sim.car.roll=initialRoll;sim.synchronizeState();
    // Small-angle stored energy in four wheel springs and two anti-roll bars.
    // This perturbation must decay, not excite the explicit-damper instability.
    const double initialElastic=.5*4*p.frontSuspension.springRate*std::pow(4*initialRoll,2)+
        .5*2*p.frontSuspension.antiRollRate*std::pow(8*initialRoll,2);
    double peakKinetic=0,peakRoll=0;Input released;released.clutch=1;
    for(unsigned i=0;i<1200;++i) {
      sim.tick(released);finite(sim);
      check(!sim.chassisContact,"microscopic roll launched chassis into collision");
      const auto &c=sim.car;
      const double kinetic=.5*p.mass*(c.velocityX*c.velocityX+c.velocityY*c.velocityY+c.velocityZ*c.velocityZ)+
          .5*(p.rollInertia*c.rollRate*c.rollRate+p.pitchInertia*c.pitchRate*c.pitchRate+
              p.yawInertia*c.yawRate*c.yawRate);
      peakKinetic=std::max(peakKinetic,kinetic);peakRoll=std::max(peakRoll,std::abs(c.roll));
    }
    check(peakKinetic<=1.25*initialElastic+1e-7,"suspension injected mechanical energy");
    check(peakRoll<=1.05*initialRoll,"microscopic roll perturbation grew");
    check(std::abs(sim.car.roll)<1e-8&&sim.groundSpeed()<1e-6,"micro perturbation did not settle");
    metrics["extreme_micro_roll_peak_kinetic_j"]=peakKinetic;
  });
  add("stationary_support_and_no_steering_teleport",[]{
    auto sim=fresh(); advance(sim,{0,0,1},3); finite(sim);
    near(sim.groundSpeed(),0,1e-5,"stationary steering created speed");
    near(sim.car.heading,0,1e-6,"stationary steering created yaw");
    double load=0; for(auto&w:sim.car.wheels){check(w.grounded,"stationary wheel airborne");load+=w.normalLoad;}
    near(load,sim.dynamics().mass*9.81,sim.dynamics().mass*9.81*.03,"static force balance");
    metrics["static_load_n"]=load;
  });
  add("straight_acceleration_and_load_transfer",[]{
    auto sim=fresh(); advance(sim,{1,0,0},6); finite(sim);
    check(sim.car.speed>15&&sim.car.speed<70,"implausible acceleration envelope");
    near(sim.car.x,0,1e-6,"straight acceleration drift"); near(sim.car.heading,0,1e-6,"straight yaw drift");
    const double front=sim.car.wheels[0].normalLoad+sim.car.wheels[1].normalLoad;
    check(front<sim.dynamics().mass*9.81*sim.dynamics().frontWeightFraction,"acceleration did not unload front axle");
    metrics["speed_after_6s_mps"]=sim.car.speed;
    metrics["front_load_under_power_n"]=front;
  });
  add("gearbox_full_throttle_does_not_hunt",[]{
    auto sim=fresh(); int priorGear=sim.car.gear; unsigned upshifts=0,downshifts=0;
    for(unsigned i=0;i<1440;++i) {
      sim.tick({1,0,0}); finite(sim);
      if(sim.car.gear>priorGear) {
        ++upshifts;
        const double shaft=.5*(sim.car.wheels[2].angularVelocity+sim.car.wheels[3].angularVelocity);
        const double engagedRpm=shaft*sim.dynamics().gearRatios[std::size_t(sim.car.gear-1)]*
            sim.dynamics().finalDrive*30/std::numbers::pi;
        check(engagedRpm>=sim.dynamics().shiftDownRpm*.9,
              "upshift selects lugging gear "+std::to_string(sim.car.gear)+" at "+
              std::to_string(i*step)+"s / "+std::to_string(engagedRpm)+" shaft rpm");
      }
      if(sim.car.gear<priorGear && i*step>3)++downshifts;
      priorGear=sim.car.gear;
    }
    check(downshifts==0,"gearbox up/down hunts during continuous dry full-throttle acceleration");
    check(upshifts<=sim.dynamics().gearRatios.size()-1,"excess repeated upshifts");
    metrics["full_throttle_upshifts_12s"]=upshifts;
  });
  add("coasting_dissipates_energy",[]{
    auto sim=fresh(); advance(sim,{1,0,0},4); const double speed=sim.groundSpeed();
    advance(sim,{},2); finite(sim); check(sim.groundSpeed()<speed,"coasting accelerates");
    check(sim.car.speed>0,"coasting reverses direction");
    metrics["coast_speed_loss_2s_mps"]=speed-sim.groundSpeed();
  });
  add("benchmark_acceleration",[]{
    const auto r=benchmark(TestKind::Acceleration); check(r.seconds>2&&r.seconds<30,"0-100 outside broad sanity range");
    check(r.testRevision==2,"benchmark revision not bumped");
    metrics["zero_to_100_seconds"]=r.seconds; metrics["zero_to_100_distance_m"]=r.distance;
  });
  add("benchmark_braking",[]{
    const auto r=benchmark(TestKind::Braking); near(r.initialSpeed,100.0/3.6,1e-6,"braking initial speed differs from threshold");
    check(r.seconds>1&&r.seconds<15&&r.distance>10&&r.distance<140,"braking outside broad sanity envelope");
    metrics["hundred_to_stop_seconds"]=r.seconds; metrics["hundred_to_stop_distance_m"]=r.distance;
  });
  add("benchmarks_frame_partition",[]{
    const auto slow=benchmark(TestKind::Braking,1./30),fast=benchmark(TestKind::Braking,1./120);
    near(slow.seconds,fast.seconds,.015,"braking time depends on frame partition");
    near(slow.distance,fast.distance,.15,"braking distance depends on frame partition");
  });
  add("mirrored_turns",[]{
    auto a=fresh(),b=fresh(); advance(a,{1,0,0},3);advance(b,{1,0,0},3);
    advance(a,{.3,0,.25},1.5);advance(b,{.3,0,-.25},1.5);finite(a);finite(b);
    check(a.car.x>0&&a.car.heading>0,"positive steering does not turn right");
    near(a.car.x,-b.car.x,1e-5,"left/right position asymmetry");
    near(a.car.z,b.car.z,1e-5,"left/right progress asymmetry");
    near(a.car.heading,-b.car.heading,1e-5,"left/right yaw asymmetry");
    check(std::abs(a.car.wheels[0].slipAngle)>1e-4,"turning produces no tyre slip");
    metrics["turn_yaw_rad"]=a.car.heading; metrics["turn_slip_angle_rad"]=a.car.wheels[0].slipAngle;
  });
  add("integration_frame_partition",[]{
    auto a=fresh(),b=fresh();
    for(auto pair:std::vector<std::pair<Input,double>>{{{1,0,0},3},{{.5,0,.2},1},{{0,.6,-.2},1}}) {
      advance(a,pair.first,pair.second,1./30);advance(b,pair.first,pair.second,1./120);
    }
    near(a.car.x,b.car.x,1e-3,"frame partition x");near(a.car.z,b.car.z,1e-3,"frame partition z");
    near(a.car.heading,b.car.heading,1e-4,"frame partition heading");near(a.car.speed,b.car.speed,1e-3,"frame partition speed");
  });
  add("complete_state_copy_replays",[]{
    auto a=fresh();advance(a,{1,0,.1},2);auto b=a;
    advance(a,{.3,.1,-.2},1);advance(b,{.3,.1,-.2},1);
    near(a.car.x,b.car.x,0,"snapshot x mismatch");near(a.car.engineRpm,b.car.engineRpm,0,"snapshot engine mismatch");
    for(unsigned i=0;i<4;++i)near(a.car.wheels[i].angularVelocity,b.car.wheels[i].angularVelocity,0,"snapshot wheel mismatch");
  });
  add("invalid_dt_and_controls",[]{
    auto sim=fresh(); const auto original=sim.car;
    for(double dt:{-1.,std::numeric_limits<double>::infinity(),std::numeric_limits<double>::quiet_NaN(),2.})sim.tick({1,1,1},dt);
    near(sim.car.x,original.x,0,"invalid dt moved x");near(sim.car.z,original.z,0,"invalid dt moved z");
    sim.tick({std::numeric_limits<double>::quiet_NaN(),std::numeric_limits<double>::infinity(),-std::numeric_limits<double>::infinity()},step);
    finite(sim);
  });
  add("public_state_bounds_and_recovery",[]{
    auto sim=fresh();advance(sim,{1,0,0},.5);
    sim.car.gear=999;sim.car.direction=0;sim.car.steering=4;
    sim.tick({},0);
    check(sim.car.gear>=1&&sim.car.gear<=6&&sim.car.direction==1,"invalid public gear was not normalized");
    check(std::abs(sim.car.steering)<=sim.dynamics().maxSteeringAngle,"invalid saved steering was not clamped");
    const Car before=sim.car;
    sim.car.wheels[0].angularVelocity=std::numeric_limits<double>::quiet_NaN();
    sim.tick({1,0,0});
    near(sim.car.x,before.x,0,"invalid wheel momentum advanced x");
    near(sim.car.z,before.z,0,"invalid wheel momentum advanced z");
    check(std::isfinite(sim.car.velocityX)&&std::isfinite(sim.car.velocityZ),"invalid wheel poisoned chassis");
    sim.synchronizeState();finite(sim);
    sim.car.wheels[1].brakePressure=-1;const double distance=sim.car.distance;
    sim.tick({1,0,0});near(sim.car.distance,distance,0,"invalid brake pressure advanced state");
    sim.synchronizeState();finite(sim);
  });
  add("head_on_wall_keeps_lateral_symmetry",[]{
    auto sim=fresh();sim.car={0,495,0,30,0,1};sim.synchronizeState();
    bool touched=false;
    for(unsigned i=0;i<60;++i){sim.tick({},step);touched|=sim.boundaryContact;finite(sim);}
    check(touched,"head-on wall contact was not detected");
    near(sim.car.x,0,1e-4,"head-on wall generated arbitrary sideways motion");
    near(sim.car.heading,0,1e-4,"head-on wall generated arbitrary yaw");
  });
  add("reverse_and_pedal_latch",[]{
    auto sim=fresh(); advance(sim,{0,1,0},2);finite(sim);
    check(sim.car.direction==-1&&sim.car.speed<-.5&&sim.car.z<0,"reverse pedal did not drive backward");
    advance(sim,{1,0,0},3);check(sim.car.speed<=.02,"brake pedal caused unintended forward shift");
    sim.tick({},step); advance(sim,{1,0,0},1);check(sim.car.direction==1&&sim.car.speed>.2,"release/repress did not select forward");
  });
  add("low_grip_limits_acceleration",[]{
    auto dry=fresh(),ice=fresh();ice.setRoadSampler(flat(.2));
    advance(dry,{1,0,0},3);advance(ice,{1,0,0},3);finite(ice);
    check(ice.groundSpeed()<dry.groundSpeed()*.75,"low-grip surface did not reduce acceleration");
    metrics["dry_speed_3s_mps"]=dry.groundSpeed();metrics["low_grip_speed_3s_mps"]=ice.groundSpeed();
  });
  add("combined_force_budget",[]{
    auto sim=fresh();
    for(unsigned i=0;i<900;++i) {
      sim.tick(i<500?Input{1,0,.2}:Input{0,.7,-.2});finite(sim);
      for(unsigned k=0;k<4;++k) {
        const auto&w=sim.car.wheels[k];const auto&p=k<2?sim.dynamics().frontTyre:sim.dynamics().rearTyre;
        const double capacity=tyrePhysics::frictionCapacity(p,w.normalLoad,1);
        check(std::hypot(w.longitudinalForce,w.lateralForce)<=capacity+1e-5,"wheel exceeds combined friction circle");
      }
    }
  });
  add("airborne_gravity_and_zero_grip",[]{
    auto sim=fresh();sim.setRoadSampler([](double,double,double,double)->std::optional<RoadSample>{return {};});
    advance(sim,{1,0,1},.3);finite(sim);
    check(sim.car.velocityY<-2,"airborne car lacks gravity");
    for(auto&w:sim.car.wheels) {check(!w.grounded,"absent ground generated contact");near(w.normalLoad,0,1e-9,"airborne normal load");}
    near(sim.groundSpeed(),0,1e-6,"airborne tyre propulsion");
  });
  add("independent_wheel_support",[]{
    auto sim=fresh();sim.setRoadSampler([](double x,double,double maximum,double drop)->std::optional<RoadSample>{
      if(x<0&&maximum>=0&&maximum-drop<=0)return RoadSample{0,{0,1,0},1,1};
      return {};});
    sim.tick({},step);finite(sim);
    check(sim.car.wheels[0].grounded&&sim.car.wheels[2].grounded,"left-side support missed");
    check(!sim.car.wheels[1].grounded&&!sim.car.wheels[3].grounded,"right wheels gained phantom support");
  });
  add("grade_gravity",[]{
    auto sim=fresh();sim.setRoadSampler([](double,double z,double maximum,double drop)->std::optional<RoadSample>{
      const double h=.08*z,n=std::hypot(1.,.08);if(h<=maximum&&h>=maximum-drop)return RoadSample{h,{0,1/n,-.08/n},1,1};return {};});
    advance(sim,{},3);finite(sim);check(sim.car.velocityZ<-.1,"unbraked car does not roll downhill");
    metrics["grade_downhill_speed_mps"]=-sim.car.velocityZ;
  });
  add("boundary_is_bounded",[]{
    auto sim=fresh();sim.car={497,0,std::numbers::pi/2,20,0,1};sim.tick({},step);finite(sim);
    bool touched=sim.boundaryContact;for(unsigned i=0;i<120;++i){sim.tick({},step);touched|=sim.boundaryContact;}
    check(touched,"boundary was not reported");
    const auto bounds=orientedBoundaryClearance(VehicleGeometry{},sim.car.heading);
    check(sim.car.x<=bounds.maxX+1e-5&&sim.car.x>=bounds.minX-1e-5,"body escaped world boundary");
  });
  add("ackermann_shared_geometry",[]{
    VehicleGeometry g;const double left=wheelSteeringAngle(g,0,.3),right=wheelSteeringAngle(g,1,.3);
    check(right>left&&left>0,"inner wheel steering not greater");
    near(left,-wheelSteeringAngle(g,1,-.3),1e-12,"Ackermann reflection");
    near(wheelSteeringAngle(g,2,.3),0,0,"rear wheel steers");
    near(wheelSteeringAngle(g,0,.3,0),.3,1e-12,"parallel steer option");
  });
  add("tyre_shape_symmetry_and_saturation",[]{
    const TyreParameters p;
    for(double load:{0.,100.,1000.,3500.,10000.})for(double slip:{-.8,-.12,0.,.12,.8})for(double lateral:{-.4,0.,.4}) {
      const auto a=tyrePhysics::evaluate(p,load,1,slip,lateral),b=tyrePhysics::evaluate(p,load,1,-slip,-lateral);
      check(std::hypot(a.longitudinal,a.lateral)<=a.capacity+1e-8,"brush exceeds capacity");
      near(a.longitudinal,-b.longitudinal,1e-8,"longitudinal odd symmetry");near(a.lateral,-b.lateral,1e-8,"lateral odd symmetry");
      check(a.longitudinal*slip>=0&&a.lateral*lateral<=0,"tyre force has wrong slip sign");
    }
    check(tyrePhysics::frictionCapacity(p,7000,1)<2*tyrePhysics::frictionCapacity(p,3500,1),"no load sensitivity");
    const auto mixed=tyrePhysics::evaluate(p,3500,1,.15,.15),pure=tyrePhysics::evaluate(p,3500,1,0,.15);
    check(std::abs(mixed.lateral)<std::abs(pure.lateral),"combined slip did not reduce cornering");
  });
  add("surface_multilevel_and_missing",[]{
    using namespace surfaceFollow;SurfaceIndex::Builder builder;builder.add(plane(0));builder.add(plane(5));auto index=builder.finish();
    const auto ground=index.sampleBelow(0,0,1,2),bridge=index.sampleBelow(0,0,6,2);
    check(ground&&bridge,"valid downward surface hit missing");near(ground->height,0,1e-12,"query selected overhead bridge");near(bridge->height,5,1e-12,"query selected wrong deck");
    check(!index.sampleBelow(50,0,1,2),"uncovered ground extrapolated");check(!index.sampleBelow(0,0,3,1),"ray exceeded travel range");
    SurfaceIndex::Builder grade;grade.add(plane(0,.6));auto graded=grade.finish();
    check(graded.sampleBelow(0,0,1,2).has_value(),"graded road was discarded");
  });
  add("mesh_validation_and_empty_rim",[]{
    MeshAsset bad=plane(0);bad.sections[0].count=99;bool rejected=false;
    try{surfaceFollow::SurfaceIndex::Builder b;b.add(bad);}catch(const std::invalid_argument&){rejected=true;}
    check(rejected,"out-of-range surface section accepted");
    bad.sections[0].wheel=0;bad.sections[0].rolling=true;rejected=false;
    try{(void)tyreRadialReach(bad,0);}catch(const std::invalid_argument&){rejected=true;}
    check(rejected,"out-of-range tyre section accepted");
    check(std::isinf(tyreLowestY({},surfaceFollow::identity.data())),"empty rim fabricated support");
  });
  add("benchmark_configuration_invalidation",[]{
    auto sim=fresh();TestSession test;check(test.start(TestKind::Acceleration,0,{},sim),"start failed");
    auto p=sim.dynamics();p.mass+=100;check(sim.setDynamics(p),"valid mass update failed");test.tick(sim,{},step);
    check(test.phase()==TestPhase::Invalid,"changed physics did not invalidate benchmark");
  });
  add("benchmark_observed_braking_event",[]{
    auto sim=fresh();TestSession test;check(test.start(TestKind::Braking,0,{},sim),"start failed");
    for(int i=0;i<3;++i)test.tick(sim,{},1);
    Car a{},b{};b.speed=100./3.6;b.z=10;test.observeMotion(a,b,1);check(test.measuringBraking(),"braking lead-in failed");
    a=b;b.speed=5;b.z=25;test.observeMotion(a,b,2);a=b;b.speed=0;b.z=27;test.observeMotion(a,b,1);
    check(test.result().valid,"observed braking did not finish");near(test.result().seconds,2.998,1e-9,"observer assumes fixed brake deceleration");
  });
  add("deterministic_input_soak",[]{
    auto sim=fresh();unsigned rng=12345;
    for(unsigned i=0;i<2400;++i){rng=1664525*rng+1013904223;const double steer=(int((rng>>16)%201)-100)/100.;
      sim.tick({i%240<120?.8:0.,i%240>180?.4:0.,steer*.7});finite(sim);
      check(sim.groundSpeed()<100,"unbounded speed during input soak");
    }
  });
  unsigned failures=0;std::cout<<std::setprecision(12);
  for(const auto&t:cases)try{t.run();std::cout<<"PASS "<<t.name<<'\n';}catch(const std::exception&e){++failures;std::cout<<"FAIL "<<t.name<<": "<<e.what()<<'\n';}
  for(const auto &[name,value]:metrics)std::cout<<"METRIC "<<name<<' '<<value<<'\n';
  std::cout<<"RESULT "<<cases.size()-failures<<'/'<<cases.size()<<" passed\n";
  return failures?1:0;
}
