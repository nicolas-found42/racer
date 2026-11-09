#include "surface_follow.h"
#include <iostream>
#include <cfenv>
#include <numbers>

namespace {
using namespace racer;
using namespace racer::surfaceFollow;
int failures=0;
void check(bool ok,const char* why){if(!ok){++failures;std::cerr<<"FAIL: "<<why<<'\n';}}
bool near(double a,double b,double epsilon=2e-5){return std::abs(a-b)<=epsilon;}
template<class F>void rejected(F&& f,const char* why){bool caught=false;try{f();}catch(const std::invalid_argument&){caught=true;}check(caught,why);}
MeshAsset plane(double sx=0,double sz=0,double h=0,double x0=-20,double x1=20,double z0=-20,double z1=20,bool blend=false,bool mask=false){
  MeshAsset a;
  auto p=[&](double x,double z){return AssetVertex{float(x),float(h+sx*x+sz*z),float(z),0xffffffff};};
  a.triangles={p(x0,z0),p(x0,z1),p(x1,z1),p(x0,z0),p(x1,z1),p(x1,z0)};
  AssetSection section;section.count=6;section.blend=blend;section.mask=mask;a.sections.push_back(section);return a;
}
SurfaceIndex single(MeshAsset asset,Matrix mount=identity,Limits limits={}){
  SurfaceIndex::Builder builder(limits);builder.add(asset,mount);return builder.finish();
}
Matrix mount(double heading,double x,double y,double z){double c=std::cos(heading),s=std::sin(heading);return {float(c),0,float(-s),0,0,1,0,0,float(s),0,float(c),0,float(x),float(y),float(z),1};}
void rigid(const GroundFrame& frame){
  const auto&m=frame.body;
  for(int i=0;i<3;++i)for(int j=0;j<3;++j){double dot=0;for(int k=0;k<3;++k)dot+=double(m[4*i+k])*m[4*j+k];check(near(dot,i==j?1:0),"body basis orthonormal");}
  check(detail::dot({m[0],m[1],m[2]},detail::cross({m[4],m[5],m[6]},{m[8],m[9],m[10]}))>.9999,"right-handed body basis");
}
}

int main(){
  using namespace racer;using namespace racer::surfaceFollow;
  VehicleGeometry vehicle;
  for(double sx:{-.4,0.,.4})for(double sz:{-.15,0.,.15})for(double heading:{0.,.7,1.57}){
    auto normal=*detail::unit({-sx,1,-sz});GeometryPoint center{2,.1,-3};
    const auto matrix=footprintMatrix(center,normal,heading,.22,.18);
    for(double x:{-1.,0.,1.})for(double z:{-1.,0.,1.}){
      auto q=detail::transform(matrix,{x,.003,z});
      const double signedDistance=detail::dot(detail::plus(q,detail::times(center,-1)),normal);
      check(near(signedDistance,.003,1e-6),"footprint edges stay3mm above their local receiver plane including alternating slopes");
    }
  }
  auto raisedFootprint=footprintMatrix({1,0,2},{0,1,0},.4,.2,.2);
  check(near(detail::transform(raisedFootprint,{0,.003,0}).y,.003),"flat receiver footprint remains atY0 independent of raised vehicle wheel centers");
  rejected([&]{footprintMatrix({0,0,0},{1,0,0},0,.2,.2);},"footprint rejects vertical receiver");
  rejected([&]{footprintMatrix({0,0,0},{0,1,0},0,-.2,.2);},"footprint rejects negative dimensions");

  {
    auto index=single(plane());check(index.triangleCount()==2&&index.cellCount()>0&&index.referenceCount()>0,"index contains compact faces and bounded grid references");
    for(double heading:{0.,.73,-1.2,std::numbers::pi/2}){
      auto frame=fit(index,vehicle,heading,3,-2,0);check(bool(frame),"flat fit exists");if(!frame)continue;rigid(*frame);check(near(frame->elevation,0)&&frame->maxFitError<1e-6,"flat elevation/error");
      for(size_t wheel=0;wheel<4;++wheel)for(bool rolling:{false,true}){
        float old[16],next[16];wheelRenderTransform(old,vehicle,wheel,heading,3,-2,.31,.83,rolling);wheelMatrix(next,*frame,vehicle,wheel,.31,.83,rolling);
        for(int k=0;k<16;++k)check(near(old[k],next[k]),"flat composed wheel matches existing steer/spin/carrier transform");
        check(near(next[13],vehicle.wheels[wheel].center.y),"flat wheel center height unchanged");
      }
    }
    check(!index.sample(21,0,0)&&!index.sample(0,0,1),"outside footprint/reference band has no extrapolation");
    check(!index.sample(0,0,0,.751)&&!index.sample(std::numeric_limits<double>::quiet_NaN(),0,0),"invalid query has no hit");
  }
  {
    auto raised=vehicle;for(auto&w:raised.wheels)w.center.y+=.2;
    auto index=single(plane(.08,.03,.25));auto frame=fit(index,raised,.4,0,0,.25);check(bool(frame),"common model wheel-bottom clearance is accounted for in placement");
    if(frame){for(size_t i=0;i<4;++i){float m[16];wheelMatrix(m,*frame,raised,i,.2,.4);const auto& c=frame->contacts[i];check(near(m[13]-frame->body[5]*raised.wheels[i].radius,c.ground.y),"elevated local wheel centers still meet fitted ground");}rigid(*frame);}
  }
  for(auto slopes:{std::pair{.1,.07},std::pair{-.12,.05},std::pair{0.,-.2}}){
    const auto [sx,sz]=slopes;auto index=single(plane(sx,sz,.2));
    for(double heading:{0.,.6,-.8,1.57}){
      auto frame=fit(index,vehicle,heading,1,1,.2+sx+sz);check(bool(frame),"analytic graded fit");if(!frame)continue;rigid(*frame);
      check(near(frame->groundElevation,.2+sx+sz)&&frame->maxFitError<3e-6,"analytic elevation and actual float wheel contacts");
      check(near(frame->body[8]/std::hypot(frame->body[8],frame->body[10]),std::sin(heading)),"forward horizontal heading preserved");
      for(size_t i=0;i<4;++i){
        const auto& contact=frame->contacts[i];check(near(contact.ground.y,.2+sx*contact.ground.x+sz*contact.ground.z),"contact lies on independent analytic plane");
        float wheel[16];wheelMatrix(wheel,*frame,vehicle,i,.2,1.3);const auto radius=vehicle.wheels[i].radius;
        check(near(wheel[12]-frame->body[4]*radius,contact.ground.x)&&near(wheel[13]-frame->body[5]*radius,contact.ground.y)&&near(wheel[14]-frame->body[6]*radius,contact.ground.z),"wheel center minus radius along body up contacts ground");
      }
      float normal[16],carrier[16];wheelMatrix(normal,*frame,vehicle,0,.4,0);wheelMatrix(carrier,*frame,vehicle,0,.4,2,false);for(int k=0;k<16;++k)check(near(normal[k],carrier[k]),"graded caliper does not roll");
    }
  }
  {
    const double angle=.7;auto index=single(plane(.05,.1,.2),mount(angle,100,2,-70));
    for(auto point:{std::pair{100.,-70.},std::pair{103.,-74.}}){double dx=point.first-100,dz=point.second+70;double expected=2.2+.05*(std::cos(angle)*dx-std::sin(angle)*dz)+.1*(std::sin(angle)*dx+std::cos(angle)*dz);auto h=index.sample(point.first,point.second,expected);check(h&&near(h->height,expected),"rotated/translated source mounting matches analytic inverse");}
    Matrix tilt=identity;double a=.15;tilt[0]=float(std::cos(a));tilt[1]=float(std::sin(a));tilt[4]=float(-std::sin(a));tilt[5]=float(std::cos(a));tilt[12]=17;tilt[13]=2;tilt[14]=-5;
    auto tilted=single(plane(),tilt);auto h=tilted.sample(18,-5,2);check(h&&near(h->height,2+std::tan(a)),"arbitrary affine tilted mount uses geometric transformed up normal");
  }
  {
    SurfaceIndex::Builder builder;builder.add(plane());builder.add(plane(0,0,2));builder.add(plane(0,0,.5,-20,20,-20,20,true));builder.add(plane(0,0,.6,-20,20,-20,20,false,true));auto index=builder.finish();
    check(near(index.sample(0,0,0)->height,0)&&near(index.sample(0,0,2)->height,2)&&!index.sample(0,0,1),"reference band keeps bridge decks separate and skips alpha geometry");
    SurfaceIndex::Builder high;high.add(plane());high.add(plane(0,0,.7));auto highest=high.finish();check(near(highest.sample(0,0,0)->height,.7)&&near(highest.sample(0,0,0,.5)->height,0),"highest eligible face with explicit window");
    auto reversed=plane();std::swap(reversed.triangles[0],reversed.triangles[2]);std::swap(reversed.triangles[3],reversed.triangles[5]);check(single(reversed).sample(0,0,0)->normal.y>.99,"up face eligibility independent of source winding");
    // Default road support now accepts banked/graded faces up to 60 degrees (normal.y >= .5).
    auto steep=single(plane(2.5,0));check(steep.triangleCount()==0&&!fit(steep,vehicle,0,0,0,0)&&!steep.sampleBelow(0,0,1,2),"steep unsupported faces produce no fit");
    auto banked=single(plane(.6,0));auto bankedHit=banked.sampleBelow(0,0,.2,1);
    check(banked.triangleCount()==2&&bankedHit&&near(bankedHit->normal.y,1/std::sqrt(1.36))&&near(bankedHit->normal.x,-.6/std::sqrt(1.36)),"banked 31 degree road face is driveable support with its true normal");
    Limits legacy;legacy.minimumNormalY=.9;check(single(plane(.6,0),identity,legacy).triangleCount()==0,"legacy 0.9 normal limit remains selectable");
    Limits tooLoose;tooLoose.minimumNormalY=.05;rejected([&]{single(plane(),identity,tooLoose);},"normal limit below 0.1 rejected");
    {
      // Downward-facing underside: two-sided by default, excluded for consistently wound collision meshes.
      auto under=plane();std::swap(under.triangles[0],under.triangles[2]);std::swap(under.triangles[3],under.triangles[5]);
      Limits oneSided;oneSided.twoSided=false;
      check(single(under).triangleCount()==2&&single(under,identity,oneSided).triangleCount()==0&&single(plane(),identity,oneSided).triangleCount()==2,"twoSided=false excludes only downward-facing faces");
    }
    {
      // Bounded downward query: a bridge deck above the origin or a lower deck beyond the drop is never selected.
      SurfaceIndex::Builder decks;decks.add(plane());decks.add(plane(0,0,4));auto both=decks.finish();
      check(near(both.sampleBelow(0,0,.5,1)->height,0)&&near(both.sampleBelow(0,0,4.5,1)->height,4)&&!both.sampleBelow(0,0,3,1)&&!both.sampleBelow(0,0,-.5,.2),"sampleBelow selects the highest support inside the query band only");
      auto sampler=makeRoadSampler(std::make_shared<const SurfaceIndex>(std::move(both)),.8,1.5);
      auto road=sampler(0,0,.5,1);auto air=sampler(0,0,3,1);
      check(road&&near(road->height,0)&&near(road->friction,.8)&&near(road->rollingResistance,1.5)&&!air,"road sampler owns the index, applies multipliers and reports air as no support");
      rejected([&]{makeRoadSampler(nullptr);},"null road sampler index rejected");
    }
    auto tiny=single(plane(0,0,0,0,1,0,1));check(!tiny.sample(1.001,.5,0)&&!tiny.sample(.5,1.001,0),"same-cell query does not extrapolate face");
    auto boundary=single(plane(0,0,0,-8,0,-8,0));check(boundary.sample(-8,-8,0)&&boundary.sample(0,0,0)&&boundary.sample(-.01,-.01,0)&&!boundary.sample(-8.001,-4,0),"negative and exact cell boundaries retain coverage only inside faces");
  }
  {
    auto asset=plane();SurfaceIndex::Builder builder;builder.add(asset);asset.triangles.clear();asset.images.push_back({1,1,{0,0,0,0}});auto independent=builder.finish();check(independent.sample(1,1,0).has_value(),"builder owns compact data after source meshes and RGBA are released");
    auto a=plane(0,0,0,-3,3,-3,3),b=plane(0,0,.25,-3,3,-3,3);const std::array<MountedMesh,2> mounted{{{&a,identity},{&b,identity}}};auto multi=build(mounted);check(near(multi.sample(0,0,0)->height,.25)&&multi.inputTriangleCount()==4,"factory streams same cumulative builder core");
    auto degenerate=plane();for(auto&v:degenerate.triangles)v.x=v.y=v.z=0;check(single(degenerate).triangleCount()==0,"zero-area faces are skipped, not extrapolated");
    auto vertical=plane();for(auto&v:vertical.triangles){v.y=v.z;v.z=0;}check(single(vertical).triangleCount()==0,"vertical faces cannot become ground");
    Limits coordinate;coordinate.maxCoordinate=5;rejected([&]{single(plane(),identity,coordinate);},"transformed coordinate bound enforced");
  }
  {
    auto left=single(plane(0,0,0,-3,-.2,-3,3));check(!fit(left,vehicle,0,0,0,0),"one or more missing wheel contacts rejects entire fit");
    SurfaceIndex::Builder empty;auto nothing=empty.finish();check(!fit(nothing,vehicle,0,0,0,0),"empty index has no fit");
    auto patchIndex=[&](double rightHeight){SurfaceIndex::Builder b;for(size_t i=0;i<4;++i){auto p=vehicle.wheels[i].center;double h=i%2?rightHeight:0;b.add(plane(0,0,h,p.x-.2,p.x+.2,p.z-.2,p.z+.2));}return b.finish();};
    auto patches=patchIndex(.3);FitOptions shortFit;shortFit.iterations=2;shortFit.convergence=1e-8;check(!fit(patches,vehicle,0,0,0,0,shortFit),"bounded resampling failure returns no pose");check(bool(fit(patches,vehicle,0,0,0,0)),"bounded resampling converges on valid patch heights");
    SurfaceIndex::Builder warped;for(size_t i=0;i<4;++i){auto p=vehicle.wheels[i].center;warped.add(plane(0,0,i==0?.3:0,p.x-.2,p.x+.2,p.z-.2,p.z+.2));}auto nonplane=warped.finish();check(!fit(nonplane,vehicle,0,0,0,0),"large nonplanar contact residual rejects visual pose");
    FitOptions reported;reported.maxFitError=.1;auto f=fit(nonplane,vehicle,0,0,0,0,reported);check(f&&f->maxFitError>.07&&f->maxFitError<.09,"per-wheel residual is measured and explicitly bounded");
  }
  {
    Limits low;low.maxTriangles=3;SurfaceIndex::Builder b(low);b.add(plane());rejected([&]{b.add(plane(0,0,.2));},"cumulative triangle budget rejects whole incoming batch");auto index=b.finish();check(index.triangleCount()==2&&index.inputTriangleCount()==2&&near(index.sample(0,0,0)->height,0),"failed batch does not mutate logical index");rejected([&]{b.add(plane());},"finished builder cannot be reused");
    Limits dense;dense.maxReferencesPerCell=3;SurfaceIndex::Builder limited(dense);auto small=plane(0,0,0,.1,.7,.1,.7);limited.add(small);rejected([&]{limited.add(plane(0,0,.2,.1,.7,.1,.7));},"per-cell reference cap rejects dense repeated faces across incoming batches");auto capped=limited.finish();check(capped.triangleCount()==2&&capped.referenceCount()==2&&capped.peakCellReferences()==2&&capped.inputTriangleCount()==2&&near(capped.sample(.2,.2,0)->height,0),"partial pending cell overflow leaves previous geometry/budget/sample unchanged");
    auto bounded=single(plane());for(double extreme:{std::numeric_limits<double>::max(),-std::numeric_limits<double>::max()}){std::feclearexcept(FE_ALL_EXCEPT);check(!fit(bounded,vehicle,0,extreme,0,0)&&!fit(bounded,vehicle,0,0,extreme,0)&&!fit(bounded,vehicle,0,0,0,extreme),"extreme finite coordinates/reference return no fit");check(!std::fetestexcept(FE_OVERFLOW|FE_INVALID),"no float overflow/invalid operation before coordinate rejection");}
    auto enormous=vehicle;for(auto&w:enormous.wheels)w.center.y=1e300;std::feclearexcept(FE_ALL_EXCEPT);check(!fit(bounded,enormous,0,0,0,0),"finite excessive model clearance cannot produce infinite body elevation");check(!std::fetestexcept(FE_OVERFLOW|FE_INVALID),"elevation representability checked before float cast");
    for(int kind=0;kind<4;++kind){Limits l;if(kind==0)l.maxCells=1;if(kind==1)l.maxReferences=1;if(kind==2)l.maxCellsPerTriangle=1;if(kind==3)l.maxInputTriangles=1;rejected([&]{auto ignored=single(plane(),identity,l);},"cell/reference/triangle span/input bounds enforced");}
    Limits invalid;invalid.cellSize=std::numeric_limits<double>::quiet_NaN();rejected([&]{SurfaceIndex::Builder b(invalid);},"nonfinite grid limit");invalid=Limits{};invalid.maxReferencesPerCell=0;rejected([&]{SurfaceIndex::Builder b(invalid);},"zero per-cell reference limit");invalid=Limits{};invalid.maxTriangles=0;rejected([&]{SurfaceIndex::Builder b(invalid);},"zero resource limit");
    auto malformed=plane();malformed.sections[0].first=1;rejected([&]{single(malformed);},"unaligned section rejected");malformed=plane();malformed.sections.push_back(malformed.sections[0]);rejected([&]{single(malformed);},"overlapping section work rejected");malformed=plane();malformed.triangles[0].x=std::numeric_limits<float>::quiet_NaN();rejected([&]{single(malformed);},"nonfinite transformed position");
    Matrix invalidMount=identity;invalidMount[15]=0;rejected([&]{single(plane(),invalidMount);},"nonaffine mount rejected");invalidMount=identity;invalidMount[0]=0;rejected([&]{single(plane(),invalidMount);},"singular mount rejected");
    auto first=single(plane()),second=single(plane());check(first.triangleCount()==second.triangleCount()&&first.cellCount()==second.cellCount()&&first.referenceCount()==second.referenceCount(),"deterministic resource counts");check(first.sample(1,2,0)->triangle==second.sample(1,2,0)->triangle,"deterministic face selection");
    auto flat=fit(first,vehicle,0,0,0,0);FitOptions invalidOptions;invalidOptions.iterations=1;rejected([&]{fit(first,vehicle,0,0,0,0,invalidOptions);},"invalid iteration option rejected");auto bad=*flat;bad.body[5]=2;float wheel[16];rejected([&]{wheelMatrix(wheel,bad,vehicle,0,0,0);},"nonrigid foreign body frame rejected");
  }
  std::cout<<"surface follow checks: "<<failures<<" failures\n";return failures?1:0;
}
