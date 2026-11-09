#pragma once
#include "mesh_asset.h"
#include "simulation.h"
#include "vehicle_geometry.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <limits>
#include <map>
#include <memory>
#include <optional>
#include <span>
#include <stdexcept>
#include <utility>
#include <vector>

namespace racer::surfaceFollow {
using Matrix=std::array<float,16>;
inline constexpr Matrix identity{1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
struct Limits {
  double cellSize=8,maxCoordinate=20000;
  size_t maxTriangles=200000,maxCells=65536,maxReferences=2000000;
  size_t maxCellsPerTriangle=4096,maxReferencesPerCell=4096,maxInputTriangles=1000000,maxSections=16384;
  // Include banked/graded driveable faces up to 60 degrees by default. The
  // optional visual plane fit below retains its original, shallower limit.
  double minimumNormalY=.5;
  // Legacy imported meshes can have inconsistent winding. For a consistently
  // outward/upward-wound collision mesh, set false to exclude downward-facing
  // bridge/ceiling undersides from suspension support. This is not a volume
  // collision index and cannot infer which side of a two-sided face is solid.
  bool twoSided=true;
};
struct Hit { double height;GeometryPoint normal;uint32_t triangle; };
namespace detail {
inline void require(bool value,const char* why){if(!value)throw std::invalid_argument(why);}
inline bool finite(GeometryPoint p){return std::isfinite(p.x)&&std::isfinite(p.y)&&std::isfinite(p.z);}
inline GeometryPoint plus(GeometryPoint a,GeometryPoint b){return {a.x+b.x,a.y+b.y,a.z+b.z};}
inline GeometryPoint times(GeometryPoint a,double s){return {a.x*s,a.y*s,a.z*s};}
inline double dot(GeometryPoint a,GeometryPoint b){return a.x*b.x+a.y*b.y+a.z*b.z;}
inline GeometryPoint cross(GeometryPoint a,GeometryPoint b){return {a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x};}
inline std::optional<GeometryPoint> unit(GeometryPoint p){double l=std::hypot(p.x,p.y,p.z);if(!std::isfinite(l)||l<1e-12)return {};return times(p,1/l);}
inline GeometryPoint transform(const Matrix& m,GeometryPoint p){return {m[0]*p.x+m[4]*p.y+m[8]*p.z+m[12],m[1]*p.x+m[5]*p.y+m[9]*p.z+m[13],m[2]*p.x+m[6]*p.y+m[10]*p.z+m[14]};}
inline void validate(const Limits& l){
  require(std::isfinite(l.cellSize)&&l.cellSize>=.25&&l.cellSize<=1024&&std::isfinite(l.maxCoordinate)&&l.maxCoordinate>0&&l.maxCoordinate<=1e7,"surface_grid_limits");
  require(l.maxTriangles&&l.maxTriangles<=1000000&&l.maxCells&&l.maxCells<=262144&&l.maxReferences&&l.maxReferences<=8000000&&l.maxCellsPerTriangle&&l.maxCellsPerTriangle<=65536&&l.maxReferencesPerCell&&l.maxReferencesPerCell<=65536&&l.maxInputTriangles&&l.maxInputTriangles<=2000000&&l.maxSections&&l.maxSections<=65536,"surface_resource_limits");
  require(std::isfinite(l.minimumNormalY)&&l.minimumNormalY>=.1&&l.minimumNormalY<=1,"surface_normal_limit");
}
inline void validate(const Matrix& m){
  for(float v:m)require(std::isfinite(v),"surface_mount_finite");
  require(m[3]==0&&m[7]==0&&m[11]==0&&m[15]==1,"surface_affine_mount");
  const auto d=dot({m[0],m[1],m[2]},cross({m[4],m[5],m[6]},{m[8],m[9],m[10]}));
  require(std::isfinite(d)&&std::abs(d)>1e-12,"surface_singular_mount");
}
}

// Immutable projected up-face index. Owns compact transformed geometry only;
// never retains MeshAsset, RGBA arrays, section pointers or source vertex data.
class SurfaceIndex {
  struct Triangle { double ax,az,bx,bz,cx,cz,ay,sx,sz,invDen; };
  using Cell=std::pair<int32_t,int32_t>;
  Limits limits_;
  std::vector<Triangle> triangles_;
  std::map<Cell,std::vector<uint32_t>> cells_;
  size_t references_=0,input_=0,sections_=0,peakCellReferences_=0;
  explicit SurfaceIndex(Limits limits):limits_(limits){detail::validate(limits);}
  Cell cell(double x,double z)const{return {int32_t(std::floor(x/limits_.cellSize)),int32_t(std::floor(z/limits_.cellSize))};}
  std::optional<Hit> sampleRange(double x,double z,double minimumY,double maximumY)const {
    if(!std::isfinite(x)||!std::isfinite(z)||!std::isfinite(minimumY)||!std::isfinite(maximumY)||minimumY>maximumY||std::abs(x)>limits_.maxCoordinate||std::abs(z)>limits_.maxCoordinate)return {};
    auto it=cells_.find(cell(x,z));if(it==cells_.end())return {};
    std::optional<Hit> result;
    for(auto id:it->second){const auto&t=triangles_[id];
      if(x<std::min({t.ax,t.bx,t.cx})||x>std::max({t.ax,t.bx,t.cx})||z<std::min({t.az,t.bz,t.cz})||z>std::max({t.az,t.bz,t.cz}))continue;
      const double a=((t.bz-t.cz)*(x-t.cx)+(t.cx-t.bx)*(z-t.cz))*t.invDen;
      const double b=((t.cz-t.az)*(x-t.cx)+(t.ax-t.cx)*(z-t.cz))*t.invDen;
      if(a< -1e-10||b< -1e-10||a+b>1+1e-10)continue;
      const double y=t.ay+t.sx*(x-t.ax)+t.sz*(z-t.az);
      if(!std::isfinite(y)||y<minimumY||y>maximumY)continue;
      if(!result||y>result->height)result=Hit{y,*detail::unit({-t.sx,1,-t.sz}),id};
    }
    return result;
  }
public:
  class Builder;
  size_t triangleCount()const noexcept{return triangles_.size();}
  size_t cellCount()const noexcept{return cells_.size();}
  size_t referenceCount()const noexcept{return references_;}
  size_t inputTriangleCount()const noexcept{return input_;}
  size_t peakCellReferences()const noexcept{return peakCellReferences_;}
  double coordinateLimit()const noexcept{return limits_.maxCoordinate;}
  // Highest face within the caller's explicit reference band. No nearest-cell,
  // neighbor, last-pose or uncovered-plane extrapolation. Barycentric 1e-10
  // tolerance is for edge arithmetic only, within each exact closed face AABB.
  std::optional<Hit> sample(double x,double z,double referenceY,double window=.75)const {
    if(!std::isfinite(referenceY)||!std::isfinite(window)||window<0||window>.75)return {};
    return sampleRange(x,z,referenceY-window,referenceY+window);
  }
  // A bounded downward suspension query. Each wheel queries independently;
  // a missing hit means no support, including holes and edges. Never select a
  // bridge/ceiling above the ray origin or a lower deck outside suspension reach.
  std::optional<Hit> sampleBelow(double x,double z,double maxHeight,double maxDrop)const {
    if(!std::isfinite(maxHeight)||!std::isfinite(maxDrop)||maxDrop<0)return {};
    return sampleRange(x,z,maxHeight-maxDrop,maxHeight);
  }
};

class SurfaceIndex::Builder {
  SurfaceIndex index_;
  bool finished_=false;
public:
  explicit Builder(Limits limits={}):index_(limits){}
  void add(const MeshAsset& asset,const Matrix& mount=identity){
    detail::require(!finished_,"surface_builder_finished");detail::validate(mount);
    const auto& l=index_.limits_;
    detail::require(asset.triangles.size()%3==0,"surface_triangle_list");
    const size_t input=asset.triangles.size()/3;
    detail::require(input<=l.maxInputTriangles-index_.input_&&asset.sections.size()<=l.maxSections-index_.sections_,"surface_input_budget");
    std::vector<bool> seen(input,false);
    std::vector<Triangle> pending;
    std::map<Cell,std::vector<uint32_t>> cells;
    size_t references=0,newCells=0,peakCellReferences=index_.peakCellReferences_;
    for(const auto& section:asset.sections){
      detail::require(section.first%3==0&&section.count%3==0&&section.first<=asset.triangles.size()&&section.count<=asset.triangles.size()-section.first,"surface_section_range");
      for(size_t i=section.first;i<size_t(section.first)+section.count;i+=3){
        detail::require(!seen[i/3],"surface_section_overlap");seen[i/3]=true;
        if(section.blend||section.mask)continue;
        std::array<GeometryPoint,3> p;
        for(size_t j=0;j<3;++j){const auto& v=asset.triangles[i+j];p[j]=detail::transform(mount,{v.x,v.y,v.z});detail::require(detail::finite(p[j])&&std::max({std::abs(p[j].x),std::abs(p[j].y),std::abs(p[j].z)})<=l.maxCoordinate,"surface_position_bounds");}
        auto u=detail::plus(p[1],detail::times(p[0],-1)),v=detail::plus(p[2],detail::times(p[0],-1));const auto normal=detail::unit(detail::cross(u,v));
        if(!normal||(l.twoSided?std::abs(normal->y):normal->y)<l.minimumNormalY)continue;
        const double den=(p[1].z-p[2].z)*(p[0].x-p[2].x)+(p[2].x-p[1].x)*(p[0].z-p[2].z);
        if(std::abs(den)<1e-12)continue;
        detail::require(index_.triangles_.size()+pending.size()<l.maxTriangles,"surface_triangle_budget");
        const auto low=index_.cell(std::min({p[0].x,p[1].x,p[2].x}),std::min({p[0].z,p[1].z,p[2].z}));
        const auto high=index_.cell(std::max({p[0].x,p[1].x,p[2].x}),std::max({p[0].z,p[1].z,p[2].z}));
        const uint64_t count=uint64_t(int64_t(high.first)-low.first+1)*uint64_t(int64_t(high.second)-low.second+1);
        detail::require(count<=l.maxCellsPerTriangle&&count<=l.maxReferences-index_.references_-references,"surface_reference_budget");
        const auto id=uint32_t(index_.triangles_.size()+pending.size());
        for(int64_t x=low.first;x<=high.first;++x)for(int64_t z=low.second;z<=high.second;++z){
          const Cell key{int32_t(x),int32_t(z)};
          if(!cells.contains(key)&&!index_.cells_.contains(key)){detail::require(newCells<l.maxCells-index_.cells_.size(),"surface_cell_budget");++newCells;}
          const auto old=index_.cells_.find(key);const size_t existing=old==index_.cells_.end()?0:old->second.size();
          auto& ids=cells[key];detail::require(ids.size()<l.maxReferencesPerCell-existing,"surface_cell_reference_budget");ids.push_back(id);peakCellReferences=std::max(peakCellReferences,existing+ids.size());++references;
        }
        pending.push_back({p[0].x,p[0].z,p[1].x,p[1].z,p[2].x,p[2].z,p[0].y,-normal->x/normal->y,-normal->z/normal->y,1/den});
      }
    }
    // Reserve all throwing allocations before committing logical contents.
    index_.triangles_.reserve(index_.triangles_.size()+pending.size());
    for(const auto&[key,ids]:cells)if(auto it=index_.cells_.find(key);it!=index_.cells_.end())it->second.reserve(it->second.size()+ids.size());
    index_.triangles_.insert(index_.triangles_.end(),pending.begin(),pending.end());
    for(auto it=cells.begin();it!=cells.end();)if(auto old=index_.cells_.find(it->first);old!=index_.cells_.end()){old->second.insert(old->second.end(),it->second.begin(),it->second.end());it=cells.erase(it);}else ++it;
    index_.cells_.merge(cells);index_.references_+=references;index_.input_+=input;index_.sections_+=asset.sections.size();index_.peakCellReferences_=peakCellReferences;
  }
  SurfaceIndex finish(){detail::require(!finished_,"surface_builder_finished");finished_=true;return std::move(index_);}
};
struct MountedMesh {const MeshAsset* asset;Matrix mount=identity;};
inline SurfaceIndex build(std::span<const MountedMesh> meshes,Limits limits={}){
  SurfaceIndex::Builder builder(limits);for(const auto& m:meshes){detail::require(m.asset,"surface_null_mesh");builder.add(*m.asset,m.mount);}return builder.finish();
}

// Own the index for as long as the simulation callback exists. Friction and
// rollingResistance are multipliers on the vehicle's calibrated tyre settings.
// An empty mesh hit is deliberately not replaced by an infinite ground plane.
inline RoadSampler makeRoadSampler(std::shared_ptr<const SurfaceIndex> index,
                                   double friction=1,double rollingResistance=1){
  detail::require(index&&std::isfinite(friction)&&friction>=0&&friction<=4&&
                  std::isfinite(rollingResistance)&&rollingResistance>=0&&rollingResistance<=10,
                  "surface_road_sampler");
  return [index=std::move(index),friction,rollingResistance](double x,double z,double maxHeight,double maxDrop)
      ->std::optional<RoadSample>{
    const auto hit=index->sampleBelow(x,z,maxHeight,maxDrop);
    if(!hit)return {};
    return RoadSample{hit->height,hit->normal,friction,rollingResistance};
  };
}

struct WheelContact {GeometryPoint ground,rendered;Hit hit;double error;};
struct GroundFrame {
  Matrix body=identity;
  double elevation=0,groundElevation=0,maxFitError=0;
  std::array<WheelContact,4> contacts{};
};
struct FitOptions {double window=.75,maxFitError=.04,convergence=1e-5;unsigned iterations=8;};
namespace detail {
inline std::optional<std::array<double,3>> plane(const std::array<WheelContact,4>& p,double x,double z){
  double m[3][4]{};
  for(const auto& c:p){const double a[3]={c.ground.x-x,c.ground.z-z,1};for(int i=0;i<3;++i){for(int j=0;j<3;++j)m[i][j]+=a[i]*a[j];m[i][3]+=a[i]*c.ground.y;}}
  double scale=0;for(auto&row:m)for(int i=0;i<3;++i)scale=std::max(scale,std::abs(row[i]));
  for(int k=0;k<3;++k){int pivot=k;for(int i=k+1;i<3;++i)if(std::abs(m[i][k])>std::abs(m[pivot][k]))pivot=i;if(std::abs(m[pivot][k])<1e-12*std::max(1.,scale))return {};for(int j=0;j<4;++j)std::swap(m[k][j],m[pivot][j]);const double d=m[k][k];for(int j=k;j<4;++j)m[k][j]/=d;for(int i=0;i<3;++i)if(i!=k){const double q=m[i][k];for(int j=k;j<4;++j)m[i][j]-=q*m[k][j];}}
  std::array<double,3> result{m[0][3],m[1][3],m[2][3]};for(double v:result)if(!std::isfinite(v))return {};return result;
}
}
// Four complete wheel-bottom samples only. The plane is visual placement, not
// suspension, native collision or physics. Caller reference is ground Y near
// the body origin (use groundElevation for subsequent reference bands).
inline std::optional<GroundFrame> fit(const SurfaceIndex& index,const VehicleGeometry& geometry,double heading,double x,double z,double referenceY,FitOptions options={}){
  detail::require(geometry.valid()&&std::isfinite(heading)&&std::isfinite(x)&&std::isfinite(z)&&std::isfinite(referenceY),"surface_vehicle_pose");
  detail::require(std::isfinite(options.window)&&options.window>=0&&options.window<=.75&&std::isfinite(options.maxFitError)&&options.maxFitError>=0&&options.maxFitError<=.25&&std::isfinite(options.convergence)&&options.convergence>=1e-8&&options.convergence<=1e-3&&options.iterations>=2&&options.iterations<=12,"surface_fit_options");
  if(std::abs(x)>index.coordinateLimit()||std::abs(z)>index.coordinateLimit()||std::abs(referenceY)>index.coordinateLimit()+options.window)return {};
  const double sh=std::sin(heading),ch=std::cos(heading);GroundFrame frame;
  frame.body={float(ch),0,float(-sh),0,0,1,0,0,float(sh),0,float(ch),0,float(x),float(referenceY),float(z),1};
  double bottom=0;for(const auto&w:geometry.wheels)bottom+=w.center.y-w.radius;bottom/=4;
  bool converged=false;
  for(unsigned iteration=0;iteration<options.iterations;++iteration){
    for(size_t i=0;i<4;++i){const auto&w=geometry.wheels[i];const auto p=detail::transform(frame.body,{w.center.x,w.center.y-w.radius,w.center.z});const auto hit=index.sample(p.x,p.z,referenceY,options.window);if(!hit)return {};frame.contacts[i]={{p.x,hit->height,p.z},p,*hit,p.y-hit->height};}
    const auto p=detail::plane(frame.contacts,x,z);if(!p)return {};
    const auto up=detail::unit({-(*p)[0],1,-(*p)[1]});if(!up||up->y<=.9)return {};
    const auto forward=detail::unit({sh,(*p)[0]*sh+(*p)[1]*ch,ch});if(!forward)return {};
    const auto right=detail::unit(detail::cross(*up,*forward));if(!right)return {};
    const double elevation=(*p)[2]-bottom/up->y;
    if(!std::isfinite(elevation)||std::abs(elevation)>std::numeric_limits<float>::max())return {};
    Matrix next{float(right->x),float(right->y),float(right->z),0,float(up->x),float(up->y),float(up->z),0,float(forward->x),float(forward->y),float(forward->z),0,float(x),float(elevation),float(z),1};
    for(float value:next)if(!std::isfinite(value))return {};
    double change=0;for(size_t i=0;i<next.size();++i)change=std::max(change,std::abs(double(next[i])-frame.body[i]));frame.body=next;frame.elevation=elevation;frame.groundElevation=(*p)[2];
    if(iteration&&change<=options.convergence){converged=true;break;}
  }
  if(!converged)return {};
  frame.maxFitError=0;
  // Resample the actual float matrix positions: tilting a wheel shifts XZ.
  for(size_t i=0;i<4;++i){const auto&w=geometry.wheels[i];const auto p=detail::transform(frame.body,{w.center.x,w.center.y-w.radius,w.center.z});const auto hit=index.sample(p.x,p.z,referenceY,options.window);if(!hit)return {};const double error=p.y-hit->height;frame.contacts[i]={{p.x,hit->height,p.z},p,*hit,error};frame.maxFitError=std::max(frame.maxFitError,std::abs(error));}
  if(frame.maxFitError>options.maxFitError)return {};
  return frame;
}
// Chassis pose that rests the four wheel bottoms on the road under (x,z): origin
// height plus pitch (nose up positive) and roll (right side down positive), in the
// simulation's conventions. Teleporting a car with pitch=roll=0 onto a slope leaves
// the uphill wheels above their suspension query band, so the car is wedged into the
// road; use this for resets and test starts. Empty when the road is uncovered or
// steeper than the visual fit accepts (the caller then keeps its flat placement).
struct RestingPose {double y,pitch,roll;};
inline std::optional<RestingPose> restingPose(const SurfaceIndex& index,const VehicleGeometry& geometry,double heading,double x,double z,double referenceY){
  const auto frame=fit(index,geometry,heading,x,z,referenceY);
  if(!frame)return {};
  const auto& m=frame->body; // columns: right (0-2), up (4-6), forward (8-10)
  return RestingPose{frame->elevation,std::atan2(double(m[9]),std::hypot(double(m[8]),double(m[10]))),std::atan2(-double(m[1]),double(m[5]))};
}
// Local Y is the receiver normal; caller vertices supply the small offset.
// Unlike the vehicle body plane, this plane belongs to this tire's actual hit.
inline Matrix footprintMatrix(GeometryPoint ground,GeometryPoint normal,double heading,double halfWidth,double halfLength){
  detail::require(detail::finite(ground)&&detail::finite(normal)&&std::isfinite(heading)&&std::isfinite(halfWidth)&&halfWidth>0&&std::isfinite(halfLength)&&halfLength>0,"surface_footprint_pose");
  const auto up=detail::unit(normal);detail::require(up&&up->y>=.1,"surface_footprint_normal");
  const double sh=std::sin(heading),ch=std::cos(heading);
  const auto forward=detail::unit({sh,(-up->x*sh-up->z*ch)/up->y,ch});
  const auto right=detail::cross(*up,*forward);
  const std::array<double,16> values{right.x*halfWidth,right.y*halfWidth,right.z*halfWidth,0,up->x,up->y,up->z,0,forward->x*halfLength,forward->y*halfLength,forward->z*halfLength,0,ground.x,ground.y,ground.z,1};
  Matrix result;for(size_t i=0;i<16;++i){detail::require(std::isfinite(values[i])&&std::abs(values[i])<=std::numeric_limits<float>::max(),"surface_footprint_overflow");result[i]=float(values[i]);}return result;
}
inline void wheelMatrix(float* output,const GroundFrame& frame,const VehicleGeometry& geometry,size_t wheel,double steering,double spin,bool rolling=true){
  detail::require(output,"surface_wheel_output");for(float v:frame.body)detail::require(std::isfinite(v),"surface_body_finite");
  detail::validate(frame.body);
  for(size_t a=0;a<3;++a)for(size_t b=0;b<3;++b){double dot=0;for(size_t k=0;k<3;++k)dot+=double(frame.body[a*4+k])*frame.body[b*4+k];detail::require(std::abs(dot-(a==b?1.:0.))<1e-4,"surface_body_orthonormal");}
  detail::require(detail::dot({frame.body[0],frame.body[1],frame.body[2]},detail::cross({frame.body[4],frame.body[5],frame.body[6]},{frame.body[8],frame.body[9],frame.body[10]}))>0,"surface_body_orientation");
  Matrix result;float local[16];wheelRenderTransform(local,geometry,wheel,0,0,0,steering,spin,rolling);
  for(size_t column=0;column<4;++column)for(size_t row=0;row<4;++row){double v=0;for(size_t k=0;k<4;++k)v+=double(frame.body[k*4+row])*local[column*4+k];detail::require(std::isfinite(v)&&std::abs(v)<=std::numeric_limits<float>::max(),"surface_wheel_overflow");result[column*4+row]=float(v);}
  std::copy(result.begin(),result.end(),output);
}
} // namespace racer::surfaceFollow
