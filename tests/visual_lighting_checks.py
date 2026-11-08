#!/usr/bin/env python3
"""Execute actual scalar Metal lighting functions as C++ numeric regression probes.

This checks lighting weights, not Metal compilation, pixels or donor equivalence.
"""
from pathlib import Path
import re
import subprocess
import tempfile

root=Path(__file__).resolve().parents[1]
surface=(root/'src/visual_shader.h').read_text()
post=(root/'src/post_process.h').read_text()
source=surface+'\n'+post
functions=[]
for name in ('fresnelWeight','directLobe','diffuseWeight','hazeAmount','reflectionLod','displayToLinear','hdrDisplay','bloomWeight','shadowBias'):
    match=re.search(r'float '+name+r'\([^)]*\)\s*\{[^{}]*\}',source)
    if not match: raise AssertionError('missing actual shader function '+name)
    functions.append(match.group())
# Ensure the exercised weights are wired into the actual surface/coat shading.
for required in ('directFresnel*spec*','*diffuseWeight(metal)',
                 'coatDirectF*coatHighlight*','*2.0*ndl*visibility','float fog=hazeAmount(distance)',
                 'level(reflectionLod(rough))','level(reflectionLod(coatRough))'):
    if required not in source: raise AssertionError('lighting integration missing: '+required)
# Facade atlas: ids 8-10 sample tiles 4/5/7 of the 2048-high atlas, signs use tile 6, foliage stays 6-7.
for required in ('in.uv.y>5.5 && in.uv.y<7.5', 'surface>7.5 && surface<10.5', '(tile*256+(top?wrapped.y:1-wrapped.y)*254+1)/2048',
                 '(6*256+(1-w.y)*254+1)/2048', '.375+(clamp(in.uv.y-6,0.0,1.0)*254+1)/2048', 'lit+=night*facadeGlow*1.15'):
    if required not in source: raise AssertionError('facade atlas integration missing: '+required)
if '/1024' in surface: raise AssertionError('stale 1024-high atlas addressing remains in the surface shader')
# Daylight colour balance from the recovered MCLA colorcorrect, faded by night amount carried in u_post.x.
if 'float3(1.072,1.072,.943)/1.063' not in post or 'config.x-3.0' not in post or '{3.f+night_,' not in post:
    raise AssertionError('day colour balance / night fade missing from the post pass')
# Rough surfaces (asphalt) must not mirror the sun/moon disc, and grazing Fresnel is roughness-limited.
for required in ('sky(reflect(-v,n),_mtl_u.u_headlight.w,1-smoothstep(.25,.55,rough))',
                 'max(float3(1.0-rough),f0)-f0'):
    if required not in source: raise AssertionError('rough-surface sun reflection guard missing: '+required)
for forbidden in ('lit=lit/(lit+.72)','float fog=1-exp(', 'pow(max(s_environment.sample'):
    if forbidden in surface: raise AssertionError('obsolete LDR scene path: '+forbidden)
for required in ('float4(max(lit,float3(0)),ghostAlpha>0?ghostAlpha*base.a:base.a)', 'linearDisplay(overlay.rgb),overlay.a',
                 'linearDisplay(s_texColor.sample(smp,in.uv).rgb)*2.0', 'linearDisplay(c)*2.0'):
    if required not in surface: raise AssertionError('linear scene boundary missing: '+required)
if 'blurWeight*=1.0-.9*smoothstep(120.0,260.0,s_postDepth.sample(speedDepthSampler,in.uv).r)' not in post:
    raise AssertionError('speed blur must fade out on far sky (stars smear into dashes otherwise)')
if 'float3 linear=max(scene,float3(0))' not in post or 'if(config.w>.5) return float4(display,1)' not in post:
    raise AssertionError('neutral HDR mapping missing')
packed=re.search(r'float3 sourceBumpNormal\([^)]*\)\s*\{[^{}]*\}',surface)
if not packed: raise AssertionError('actual packed normal kernel absent')
for required in ('o.bitangent=cross(o.tangent.xyz,o.normal)*o.tangent.w',
                 'sourceBumpNormal(in.normal,in.tangent.xyz,in.bitangent,packed.r,packed.a)'):
    if required not in surface: raise AssertionError('raw source frame integration missing '+required)
program=r'''
#include <algorithm>
#include <cmath>
#include <cassert>
using std::pow;using std::exp;using std::isfinite;
struct float3 { double x,y,z; float3(double a,double b,double c):x(a),y(b),z(c){} };
float3 operator-(float3 a,float3 b){return {a.x-b.x,a.y-b.y,a.z-b.z};}
float3 operator+(float3 a,float3 b){return {a.x+b.x,a.y+b.y,a.z+b.z};}
float3 operator*(double a,float3 b){return {a*b.x,a*b.y,a*b.z};}
float3 operator*(float3 b,double a){return a*b;}
double dot(float3 a,float3 b){return a.x*b.x+a.y*b.y+a.z*b.z;}
float3 cross(float3 a,float3 b){return {a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x};}
double rsqrt(double v){return 1/std::sqrt(v);}

double clamp(double v,double a,double b){return std::clamp(v,a,b);}
double max(double a,double b){return std::max(a,b);}
double mix(double a,double b,double t){return a*(1-t)+b*t;}
double smoothstep(double a,double b,double x){double t=clamp((x-a)/(b-a),0,1);return t*t*(3-2*t);}
'''+ '\n'.join(functions)+packed.group()+r'''
int main(){
 auto same=[](float3 a,float3 b){return std::abs(a.x-b.x)<1e-6&&std::abs(a.y-b.y)<1e-6&&std::abs(a.z-b.z)<1e-6;};
 const float3 N(0,1,0),T(1,0,0),B(0,0,1);
 assert(same(sourceBumpNormal(N,T,B,.5,.5),N));
 const double inverse=1/std::sqrt(.36+1+.16);
 assert(same(sourceBumpNormal(N,T,B,.8,.3),float3(-.6*inverse,inverse,.4*inverse)));
 assert(same(sourceBumpNormal(N,T,-1*B,.8,.3),float3(-.6*inverse,inverse,-.4*inverse)));
 assert(same(sourceBumpNormal(N,T,B,.2,.7),float3(.6*inverse,inverse,-.4*inverse)));
 // Preserve native magnitudes instead of conditioning basis before the kernel.
 const float3 rawN(0,.99,0),rawT(.995,.005,0),rawB=cross(rawT,rawN);
 const auto expected=rawN+.4*rawB-.6*rawT;
 assert(same(sourceBumpNormal(rawN,rawT,rawB,.8,.3),expected*rsqrt(dot(expected,expected))));
 // Native VS computes B at vertices, then rasterization interpolates it.
 const float3 nAverage(0,2./3,1./3),tAverage(2./3,1./3,0),bAverage(1./3,0,2./3);
 const auto interpolated=sourceBumpNormal(nAverage,tAverage,bAverage,.8,.3);
 const auto recrossed=sourceBumpNormal(nAverage,tAverage,cross(tAverage,nAverage),.8,.3);
 assert(dot(interpolated-recrossed,interpolated-recrossed)>.001);
 const auto independent=nAverage+.4*bAverage-.6*tAverage;
 assert(same(interpolated,independent*rsqrt(dot(independent,independent))));
 assert(same(sourceBumpNormal(N,N,B,1,.5),N)); // zero-result fallback
 assert(same(sourceBumpNormal(float3(0,0,0),float3(0,0,0),float3(0,0,0),.5,.5),N));

 assert(displayToLinear(0)==0 && displayToLinear(1)==1 && displayToLinear(-1)==0);
 assert(std::abs(displayToLinear(.5)-.2176376408)<1e-6);
 assert(hdrDisplay(0)==0 && hdrDisplay(-1)==0);
 assert(std::abs(hdrDisplay(1)-std::pow(1/1.72,1/2.2))<1e-6);
 assert(hdrDisplay(4)>hdrDisplay(1) && hdrDisplay(4)<1);
 assert(bloomWeight(.99)==0 && bloomWeight(1)==0 && bloomWeight(2)==1);
 assert(std::abs(bloomWeight(1.5)-.5)<1e-6);
 assert(4*bloomWeight(4)==4); // No pre-bloom clipping of four-unit radiance.
 // Linear alpha composite is mapped only after blending, rather than blending display values.
 assert(std::abs(hdrDisplay(4*.5)-std::pow(2/2.72,1/2.2))<1e-6);
 assert(hdrDisplay(4*.5)>hdrDisplay(4)*.5+.3);
 for(int i=0;i<=65504;i+=257)assert(std::isfinite(hdrDisplay(i))&&hdrDisplay(i)>=0&&hdrDisplay(i)<=1);
 assert(reflectionLod(0)==0 && reflectionLod(1)==8 && reflectionLod(-1)==0 && reflectionLod(2)==8);
 assert(std::abs(reflectionLod(.24)-2.94144)<1e-5);
 assert(std::abs(reflectionLod(.1)-1.304)<1e-5);
 for(int i=1;i<=100;i++)assert(reflectionLod(i/100.f)>reflectionLod((i-1)/100.f));
 assert(std::abs(shadowBias(1)-.00002)<1e-9 && std::abs(shadowBias(0)-.00006)<1e-9);
 assert(shadowBias(-2)==shadowBias(0) && shadowBias(3)==shadowBias(1));
 // Independent projection geometry: offset times399m and the actual unit sunY.
 const double lightY=.34/std::sqrt(.55*.55+.34*.34+.70*.70);
 const double verticalThreshold=shadowBias(lightY)*399*lightY;
 assert(verticalThreshold>.005 && verticalThreshold<.006);
 assert(fresnelWeight(1)==0 && fresnelWeight(0)==1);
 assert(std::abs(fresnelWeight(.5)-.03125)<1e-7);
 assert(fresnelWeight(-3)==1 && fresnelWeight(3)==0);
 assert(diffuseWeight(1)==0 && diffuseWeight(0)==1 && diffuseWeight(.25)==.75);
 // A fully metallic red surface receives zero blue direct reflection at normal incidence.
 float fRed=1+(1-1)*fresnelWeight(1),fBlue=0+(1-0)*fresnelWeight(1);
 assert(fRed==1 && fBlue==0);
 // Direct light cannot illuminate the back side, even at a perfect half-vector.
 assert(directLobe(.08,1,0)==0 && directLobe(.08,1,-1)==0);
 assert(std::abs(directLobe(1,1,1)-.1)<1e-6);
 assert(std::abs(directLobe(1,1,.5)-.05)<1e-6);
 // Dielectric and coat highlights have 4% normal-incidence interface reflectance.
 assert(std::abs((.04+.96*fresnelWeight(1))*2-.08)<1e-6);
 assert(hazeAmount(0)==0 && hazeAmount(40)==0 && hazeAmount(-1)==0);
 assert(std::abs(hazeAmount(100)-.0382492909)<1e-6);
 assert(std::abs(hazeAmount(300)-.1554910966)<1e-6);
 float previous=0;
 for(int i=0;i<=1600;i++){
  float haze=hazeAmount(i);assert(std::isfinite(haze)&&haze>=previous&&haze<1);previous=haze;
  for(int j=0;j<=10;j++){
   float rough=.08f+.092f*j;float lobe=directLobe(rough,.7,.4);
   assert(std::isfinite(lobe)&&lobe>=0);
  }
 }
}
'''
with tempfile.TemporaryDirectory(prefix='racer-lighting-checks-') as temp:
    path=Path(temp);(path/'checks.cpp').write_text(program)
    subprocess.run(['c++','-std=c++20',str(path/'checks.cpp'),'-o',str(path/'checks')],check=True,timeout=30)
    subprocess.run([str(path/'checks')],check=True,timeout=10)
print('actual shader scalar lighting: Fresnel tint, metallic diffuse, light-side support, restrained haze, linear HDR/bloom/final mapping PASS')
