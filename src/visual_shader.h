#pragma once
#include <bgfx/bgfx.h>
#include <cstdint>
#include <stdexcept>
#include <string_view>
#include <vector>

namespace racer {
// Metal source packaged for the pinned bgfx v12 container. Layout follows
// shaderc_metal.cpp writeUniformArray and renderer_mtl.cpp ShaderMtl::create.
// This is authored Racer shading, not a recovered donor shader.
inline std::vector<uint8_t> visualShader(bool fragment, bool shadow=false) {
  constexpr std::string_view vertex=R"MSL(#include <metal_stdlib>
using namespace metal;
struct Globals { float4x4 u_modelViewProj; float4x4 u_model; };
struct Input {
 float3 a_position [[attribute(0)]]; float4 a_color0 [[attribute(1)]];
 float2 a_texcoord0 [[attribute(2)]]; float3 a_normal [[attribute(3)]];
 float2 a_texcoord1 [[attribute(4)]];
 float4 a_tangent [[attribute(5)]];
};
struct Varying {
 float4 position [[position]]; float4 color [[user(locn0)]];
 float2 uv [[user(locn1)]]; float3 world [[user(locn2)]];
 float3 normal [[user(locn3)]];
 float occlusion [[user(locn4)]];
 float4 tangent [[user(locn5)]];
 float3 bitangent [[user(locn6)]];
};
vertex Varying xlatMtlMain(Input in [[stage_in]], constant Globals& _mtl_u [[buffer(0)]]) {
 Varying o; o.position=_mtl_u.u_modelViewProj*float4(in.a_position,1);
 o.world=(_mtl_u.u_model*float4(in.a_position,1)).xyz;
 o.normal=(_mtl_u.u_model*float4(in.a_normal,0)).xyz;
 o.color=in.a_color0; o.color.a*=in.a_texcoord1.y;
 o.uv=in.a_texcoord0; o.occlusion=in.a_texcoord1.x;
 float handed=determinant(float3x3(_mtl_u.u_model[0].xyz,_mtl_u.u_model[1].xyz,_mtl_u.u_model[2].xyz))<0?-1.0:1.0;
 o.tangent=float4((_mtl_u.u_model*float4(in.a_tangent.xyz,0)).xyz,in.a_tangent.w*handed);
 o.bitangent=cross(o.tangent.xyz,o.normal)*o.tangent.w;return o;
}
)MSL";
  constexpr std::string_view pixel=R"MSL(#include <metal_stdlib>
using namespace metal;
constant uint bgfx_sampleMask [[function_constant(0)]];
constant bool bgfx_sampleMaskEnabled=is_function_constant_defined(bgfx_sampleMask);
struct Globals { float4 u_visualCamera; float4 u_visualMaterial; float4x4 u_shadowMatrix; float4 u_reflectionState; float4 u_visualCoat; float4 u_headlight; };
struct Varying {
 float4 position [[position]]; float4 color [[user(locn0)]];
 float2 uv [[user(locn1)]]; float3 world [[user(locn2)]];
 float3 normal [[user(locn3)]];
 float occlusion [[user(locn4)]];
 float4 tangent [[user(locn5)]];
 float3 bitangent [[user(locn6)]];
};
struct Output {
 uint mask [[sample_mask, function_constant(bgfx_sampleMaskEnabled)]];
 float4 color [[color(0)]];
 float4 depth [[color(1)]]; // eye distance in metres for depth of field; ignored by single-target passes
};
float displayToLinear(float channel) { return pow(max(channel,0.0),2.2); }
float3 linearDisplay(float3 rgb) { return float3(displayToLinear(rgb.r),displayToLinear(rgb.g),displayToLinear(rgb.b)); }
float hash(float2 p) { return fract(sin(dot(p,float2(127.1,311.7)))*43758.5453); }
float noise(float2 p) {
 float2 i=floor(p),f=fract(p); f=f*f*(3-2*f);
 return mix(mix(hash(i),hash(i+float2(1,0)),f.x),mix(hash(i+float2(0,1)),hash(i+1),f.x),f.y);
}
// Stars and moon for the night sky (radiance). The moon sits where the day sun does so shadows agree.
float3 nightSkyExtras(float3 ray) {
 float3 moonDir=normalize(float3(-.55,.34,.70)); float d=dot(ray,moonDir);
 float2 sp=ray.xz/max(ray.y,.08)*70.0;
 float star=step(.9972,hash(floor(sp)))*(.4+.6*hash(floor(sp)+7.3))*smoothstep(.0,.2,ray.y);
 float moon=smoothstep(.99955,.99985,d)*7.0+pow(max(d,0.0),500.0)*.5+pow(max(d,0.0),30.0)*.03;
 return float3(.8,.85,1.0)*star*3.0+float3(.78,.84,1.0)*moon;
}
float3 daySky(float3 ray) {
 float h=max(ray.y,0.0); float3 c=mix(float3(.72,.77,.78),float3(.18,.36,.57),pow(h,.42));
 float3 sun=normalize(float3(-.55,.34,.70)); float d=max(dot(ray,sun),0.0);
 float2 p=ray.xz/max(.16,ray.y+.26)*2.3;
 float cloud=noise(p)*.55+noise(p*2.1)*.28+noise(p*4.3)*.17;
 float cover=smoothstep(.54,.76,cloud)*smoothstep(0.0,.15,ray.y)*.60;
 c=mix(c,float3(.90,.87,.81),cover);
 // The sun is added after the clouds so it is never painted over; cloud only dims it.
 c+=float3(1,.77,.44)*(pow(d,350.0)*2.0+pow(d,14.0)*.12)*(1-.7*cover);
 // Authored display-RGB sky convention converted to linear radiance.
 return linearDisplay(c)*2.0;
}
// night in [0,1]: 0 day, ~.45 dusk (warm horizon, dimmer sky), 1 night (stars and moon). Authored.
float3 sky(float3 ray,float night) {
 float3 day=daySky(ray);
 if(night<.01) return day;
 float h=max(ray.y,0.0);
 float t=smoothstep(.3,.9,night),dusk=night*(1-night)*4.0;
 float3 ns=mix(float3(.012,.018,.036),float3(.003,.006,.020),pow(h,.5))+nightSkyExtras(ray);
 float3 horizon=float3(1.0,.42,.16)*dusk*pow(1-h,5.0)*1.6;
 return mix(day*mix(1.0,.35,night)*mix(float3(1),float3(1.0,.78,.62),dusk),ns,t)+horizon;
}
float filteredShadow(texture2d<float> depth, sampler smp, float2 uv, float reference, float2 gradient) {
 float2 p=uv*2048.0-.5,base=floor(p),f=fract(p);
 float2 aUV=(base+float2(.5,.5))/2048.0,bUV=(base+float2(1.5,.5))/2048.0;
 float2 cUV=(base+float2(.5,1.5))/2048.0,dUV=(base+float2(1.5,1.5))/2048.0;
 float a=reference+dot(aUV-uv,gradient)<=depth.sample(smp,aUV).r?1.0:0.0;
 float b=reference+dot(bUV-uv,gradient)<=depth.sample(smp,bUV).r?1.0:0.0;
 float c=reference+dot(cUV-uv,gradient)<=depth.sample(smp,cUV).r?1.0:0.0;
 float d=reference+dot(dUV-uv,gradient)<=depth.sample(smp,dUV).r?1.0:0.0;
 return mix(mix(a,b,f.x),mix(c,d,f.x),f.y);
}
// Authored lighting weights, not a recovered donor BRDF. Keep the direct
// lobe colored by the same interface reflectance as the environment lobe.
float fresnelWeight(float cosine) { return pow(1-clamp(cosine,0.0,1.0),5.0); }
float directLobe(float rough,float nDotH,float nDotL) {
 return pow(clamp(nDotH,0.0,1.0),mix(180.0,6.0,rough))*mix(3.6,.10,rough)*max(nDotL,0.0);
}
float diffuseWeight(float metal) { return 1-clamp(metal,0.0,1.0); }
// 256px cube has levels0..8. This box-mip roughness curve is authored,
// not a GGX convolution or native material formula.
float reflectionLod(float rough) {
 float r=clamp(rough,0.0,1.0);return r*(1.7-.7*r)*8.0;
}
// Projection spans399m along the light axis. Receiver-plane PCF already
// compensates sampled depth gradients; keep the remaining safety offset at
// about8..24mm rather than the former200..400mm that erased low shadows.
float shadowBias(float nDotL) {
 return max(.00002,.00006*(1-clamp(nDotL,0.0,1.0)));
}
float hazeAmount(float distance) {
 // Preserve near-field material contrast; distant silhouettes still converge.
 return 1-exp(-max(distance-40.0,0.0)*.00065);
}
// Selected CityBumpSpec VS/PS kernel, normal channel only. Packed G/B stay
// unmodified in the texture; original specular composition is not implemented.
float3 sourceBumpNormal(float3 N,float3 T,float3 B,float R,float A) {
 float3 result=N-(2*A-1)*B-(2*R-1)*T;
 float squared=dot(result,result),baseSquared=dot(N,N);
 // Racer robustness for degenerate interpolation; native zero-RSQ is unknown.
 return isfinite(squared)&&squared>1e-20?result*rsqrt(squared):
   isfinite(baseSquared)&&baseSquared>1e-20?N*rsqrt(baseSquared):float3(0,1,0);
}
float3 detailNormal(float3 world,float2 uv,float3 normal,float4 authored,float3 encoded,float scale) {
 float3 tangent,bitangent;
 if(abs(authored.w)>.5) {
  tangent=authored.xyz-normal*dot(normal,authored.xyz);float squared=dot(tangent,tangent);
  if(!isfinite(squared)||squared<1e-20)return normal;
  tangent*=rsqrt(squared);bitangent=cross(normal,tangent)*(authored.w<0?-1.0:1.0);
 }else {
 float3 px=dfdx(world),py=dfdy(world);float2 tx=dfdx(uv),ty=dfdy(uv);
 float uvScale=max(max(abs(tx.x),abs(tx.y)),max(abs(ty.x),abs(ty.y)));
 float worldScale=max(max(max(abs(px.x),abs(px.y)),abs(px.z)),max(max(abs(py.x),abs(py.y)),abs(py.z)));
 if(!isfinite(uvScale)||!isfinite(worldScale)||uvScale<1e-30||worldScale<1e-30)return normal;
 tx/=uvScale;ty/=uvScale;px/=worldScale;py/=worldScale;
 float determinant=tx.x*ty.y-tx.y*ty.x;
 if(!isfinite(determinant)||abs(determinant)<1e-8)return normal;
 tangent=(px*ty.y-py*tx.y)/determinant;
 bitangent=(py*tx.x-px*ty.x)/determinant;
 tangent-=normal*dot(normal,tangent);float squared=dot(tangent,tangent);
 if(!isfinite(squared)||squared<1e-12||!all(isfinite(bitangent)))return normal;
 tangent*=rsqrt(squared);
 float3 crossAxis=cross(normal,tangent);
 bitangent=crossAxis*(dot(crossAxis,bitangent)<0?-1.0:1.0);
 }
 float3 mapped=encoded*2-1;mapped.xy*=scale;
 float3 result=tangent*mapped.x+bitangent*mapped.y+normal*mapped.z;
 float lengthSquared=dot(result,result);
 return isfinite(lengthSquared)&&lengthSquared>1e-12?result*rsqrt(lengthSquared):normal;
}
// Night street lighting: lamps follow the 100 m street grid (poles at +-7.7 m from road centres,
// every 25 m, none within 12.5 m of an intersection, only within +-200 m); the same table builds the
// lamp meshes in world_scene.h. Analytic, unshadowed point lights; authored values.
void lampLight(float3 p,float3 n,float3 v,float rough,thread float3& diff,thread float3& spec) {
 const float3 color=float3(1.0,.66,.32)*4.2;
 for(int axis=0;axis<2;++axis) {
  float lat=axis==0?p.x:p.z,along=axis==0?p.z:p.x;
  float road=round(lat/100.0)*100.0;
  if(abs(road)>200.0||abs(lat-road)>34.0) continue;
  float k0=floor((along-12.5)/25.0);
  for(int dk=-1;dk<=2;++dk) {
   float k=k0+float(dk),m=k-4.0*floor(k/4.0),s=25.0*k+12.5;
   if(m<.5||abs(s)>200.0) continue;
   for(int side=-1;side<=1;side+=2) {
    float latPos=road+float(side)*7.7;
    float3 lamp=axis==0?float3(latPos,7.9,s):float3(s,7.9,latPos);
    float3 L=lamp-p;float d2=dot(L,L);float3 l=L*rsqrt(d2);
    float atten=1.0/(1.0+d2/30.0)*(1-smoothstep(700.0,1400.0,d2));
    float cone=smoothstep(.2,.7,l.y);
    float ndl=max(dot(n,l),0.0);
    diff+=color*(ndl*atten*cone);
    float3 h=normalize(l+v);
    spec+=color*directLobe(rough,dot(n,h),ndl)*(atten*cone*.12);
   }
  }
 }
}
// Light cast by the corner neon pylons (world_scene.h neonPylon): same intersection table
// (25 corners, +-10 m from the crossing, colour palette by (ix*5+iz*3) mod 3). Unshadowed; authored.
void neonLight(float3 p,float3 n,thread float3& diff) {
 float2 cell=round(p.xz/100.0);
 if(abs(cell.x)>2.0||abs(cell.y)>2.0) return;
 float v=(cell.x+3.0)*5.0+(cell.y+3.0)*3.0;
 for(int i=0;i<2;++i) {
  float s=i==0?1.0:-1.0,vv=v+float(i),pal=vv-3.0*floor(vv/3.0);
  float3 col=pal<.5?float3(1.0,.16,.67):(pal<1.5?float3(1.0,.59,.12):float3(.24,1.0,.63));
  float3 L=float3(cell.x*100.0+s*10.0,5.0,cell.y*100.0+s*10.0)-p;
  float d2=dot(L,L);
  diff+=col*(3.4*max(dot(n,L*rsqrt(d2)),0.0)/(1.0+d2/60.0))*(1-smoothstep(900.0,1600.0,d2));
 }
}
// Player headlights: a forward cone from the car's nose, lighting road, kerbs and facades ahead.
void headLight(float3 p,float3 n,float4 hl,thread float3& diff) {
 float2 rel=p.xz-hl.xy;float2 fwd=float2(sin(hl.z),cos(hl.z)),right=float2(cos(hl.z),-sin(hl.z));
 float along=dot(rel,fwd),lateral=dot(rel,right);
 if(along<-1.0||along>55.0) return;
 float width=1.4+.36*max(along,0.0);
 float cone=smoothstep(width,width*.4,abs(lateral))*smoothstep(1.0,5.0,along)*(1-smoothstep(28.0,55.0,along));
 float3 lp=float3(hl.x+fwd.x*2.2,.75,hl.y+fwd.y*2.2);
 float3 L=lp-p;float d2=dot(L,L);float ndl=max(dot(n,L*rsqrt(d2)),0.0);
 diff+=float3(1.0,.95,.82)*(20.0*ndl*cone/(1.0+d2/90.0));
}
fragment Output xlatMtlMain(Varying in [[stage_in]], constant Globals& _mtl_u [[buffer(0)]],
 texture2d<float> s_texColor [[texture(0)]], sampler smp [[sampler(0)]],
 texture2d<float> s_shadow [[texture(1)]], sampler shadowSampler [[sampler(1)]],
 texture2d<float> s_surfaces [[texture(2)]], sampler surfaceSampler [[sampler(2)]],
 texturecube<float> s_environment [[texture(3)]], sampler environmentSampler [[sampler(3)]],
 texture2d<float> s_normal [[texture(4)]], sampler normalSampler [[sampler(4)]]) {
 Output o={}; if(bgfx_sampleMaskEnabled) o.mask=bgfx_sampleMask;
 o.depth=float4(length(_mtl_u.u_visualCamera.xyz-in.world),0,0,1);
 float mode=_mtl_u.u_visualMaterial.w;
 if(mode>4.5) {
  float4 overlay=s_texColor.sample(smp,in.uv)*in.color;
  o.color=float4(linearDisplay(overlay.rgb),overlay.a);return o;
 }
 // The photographic sky has the same authored decode/exposure as procedural sky.
 if(mode>3.5) {
  // Photographic sky has no sun at the authored light direction; add the same sun lobe so the
  // visible disc agrees with shadows and the road highlight. Authored, not recovered.
  float3 ray=normalize(in.world-_mtl_u.u_visualCamera.xyz);
  float d=max(dot(ray,normalize(float3(-.55,.34,.70))),0.0);
  float3 sun=float3(1,.77,.44)*(pow(d,700.0)*2.4+pow(d,60.0)*.10+pow(d,10.0)*.04);
  float3 dayColor=linearDisplay(s_texColor.sample(smp,in.uv).rgb)*2.0+linearDisplay(sun)*2.0;
  if(_mtl_u.u_headlight.w>.01) {
   float nt=_mtl_u.u_headlight.w,t=smoothstep(.3,.9,nt),dusk=nt*(1-nt)*4.0;
   float3 nightCol=linearDisplay(s_texColor.sample(smp,in.uv).rgb)*float3(.010,.016,.040)+nightSkyExtras(ray);
   float3 dim=dayColor*mix(1.0,.35,nt)*mix(float3(1),float3(1.0,.78,.62),dusk);
   float3 horizon=float3(1.0,.42,.16)*dusk*pow(1-max(ray.y,0.0),5.0)*1.6;
   o.color=float4(mix(dim,nightCol,t)+horizon,1); return o;
  }
  o.color=float4(dayColor,1); return o;
 }
 if(mode>1.5 && mode<2.5) { o.color=float4(sky(normalize(in.world-_mtl_u.u_visualCamera.xyz),_mtl_u.u_headlight.w),1); return o; }
 if(mode>2.5) { o.color=float4(linearDisplay(in.color.rgb),in.color.a); return o; }
 if(mode>.5 && in.uv.y<-1.5) { // lamp head: display colour by day, hot emitter at night
  o.color=float4(linearDisplay(in.color.rgb)*mix(1.0,7.0,_mtl_u.u_headlight.w),1);return o; // emitter keeps its own colour (lamps warm, neon coloured)
 }
 float night=_mtl_u.u_headlight.w;
 float4 sampled=_mtl_u.u_visualMaterial.z>.5?s_texColor.sample(smp,in.uv):float4(1);
 float4 base=in.color*sampled;
 bool foliage=mode>.5 && in.uv.y>5.5;
 bool leaf=mode>.5 && in.uv.y<-.5 && in.uv.y>-1.5;
 if(foliage) {
  float2 uv=float2(clamp(in.uv.x,0.0,1.0)*254.0/256+1.0/256,
    .75+(clamp(in.uv.y-6,0.0,1.0)*254+1)/1024);
  base=in.color*s_surfaces.sample(surfaceSampler,uv);
  if(base.a<.4) discard_fragment();
 }
 if(leaf) {
  // Street-tree leaf card: clumped cut-out from world-space noise, denser toward the card centre.
  float r=length(in.tangent.xy-.5)*2;
  float cluster=noise(in.world.xz*3.1+in.world.y*2.3)*.55+noise(in.world.xz*8.7-in.world.y*5.9)*.45;
  if(cluster<.14+.46*r) discard_fragment();
  base=float4(in.color.rgb*(.62+.9*cluster),1);
 }
 if(base.a<_mtl_u.u_visualCamera.w) discard_fragment();
 float3 n=normalize(in.normal); float3 v=normalize(_mtl_u.u_visualCamera.xyz-in.world);
 bool reverseNormal=dot(n,v)<0;
 if(mode<.5 && _mtl_u.u_visualCoat.z>1.5) {
  float4 packed=s_normal.sample(normalSampler,in.uv);
  n=sourceBumpNormal(in.normal,in.tangent.xyz,in.bitangent,packed.r,packed.a);
 } else if(mode<.5 && _mtl_u.u_visualCoat.z>.5)
  n=detailNormal(in.world,in.uv,n,in.tangent,s_normal.sample(normalSampler,in.uv).rgb,_mtl_u.u_visualCoat.w);
 if(reverseNormal) n=-n;
 float3 l=normalize(float3(-.55,.34,.70)); float3 h=normalize(l+v);
 float rough=clamp(_mtl_u.u_visualMaterial.x,.08,1.0),metal=clamp(_mtl_u.u_visualMaterial.y,0.0,1.0);
 if(mode>.5) { rough=in.uv.x>.01?clamp(in.uv.x,.08,1.0):.95; metal=in.uv.y>4.5?.18:0.0; }
 if(foliage || leaf) { rough=1;metal=0; }
 // glTF factors are linear; decoded base-color texture bytes are sRGB.
 // Authored world vertex colors use the usual display RGB convention.
 float3 albedo=mode<.5?in.color.rgb*linearDisplay(sampled.rgb):
   linearDisplay(base.rgb);
 if(mode>.5) {
  float surface=round(in.uv.y);
  if(surface>0 && surface<4.5 && _mtl_u.u_visualMaterial.z>1.5) {
   float tile=surface-1,scale=surface<1.5?2.0:3.0;
   float2 uv=abs(n.y)>.5?in.world.xz/scale:abs(n.x)>.5?in.world.zy/scale:in.world.xy/scale;
   // Keep the atlas selection inside its tile while retaining correct mip
   // gradients across wrap seams. These are authored mappings, not donor UVs.
   float2 wrapped=fract(uv);
   float2 atlasUV=float2((wrapped.x*254+1)/256,(tile*256+wrapped.y*254+1)/1024);
   float2 dx=dfdx(uv)*float2(254.0/256,254.0/1024),dy=dfdy(uv)*float2(254.0/256,254.0/1024);
   float3 tex=s_surfaces.sample(surfaceSampler,atlasUV,gradient2d(dx,dy)).rgb;
   float3 textured=linearDisplay(tex);
   albedo=surface<1.5?textured*.24:mix(albedo,textured,.68);
  }
  float2 p=in.world.xz*38.0,q=in.world.xy*29.0;
  float fade=1-smoothstep(.25,1.0,max(length(dfdx(p)),length(dfdy(p))));
  float grain=mix(.5,noise(p)*.5+noise(q)*.5,fade);
  albedo*=.87+.26*grain;
  if(n.y>.85 && in.world.y<.08) {
   float wear=noise(in.world.xz*.35);
   albedo*=.82+.35*wear;
  }
  // Authored wet-road model after the parameter set seen in the MCLA road shader (REA names only:
  // grime, puddle and reflection samplers, Fresnel/specular exponents, water parameters). Wheel-track
  // grime and polish follow the 3 m lane grid; puddles come from low-frequency noise; this is not
  // the native formula.
  if(surface>.5 && surface<1.5 && n.y>.85 && in.world.y<.1) {
   float ax=abs(in.world.x-100.0*round(in.world.x/100.0)),az=abs(in.world.z-100.0*round(in.world.z/100.0));
   float lateral=(ax<6.0 && az>=6.0)?ax:((az<6.0 && ax>=6.0)?az:99.0);
   float d=abs(fmod(lateral,3.0)-1.5);
   float tracks=exp(-pow((d-.85)/.28,2.0))*step(lateral,6.0);
   float pn=noise(in.world.xz*.11)*.6+noise(in.world.xz*.37)*.4;
   float puddle=smoothstep(.68,.74,pn)*.9;
   albedo*=1-.20*tracks*(1-puddle);
   // Hairline cracks: thin zero-crossings of two noise octaves, sparse by a low-frequency mask,
   // faded with screen-space derivatives so distant asphalt does not shimmer.
   float2 cp=in.world.xz*.85;
   float ridge=abs(noise(cp)*.65+noise(cp*2.3)*.35-.5);
   float crackFade=1-smoothstep(.15,.6,max(length(dfdx(cp)),length(dfdy(cp))));
   float crack=(1-smoothstep(.0,.03,ridge))*smoothstep(.40,.58,noise(in.world.xz*.06))*crackFade;
   albedo*=1-.5*crack*(1-puddle);
   albedo=mix(albedo,albedo*.5,puddle);
   rough=mix(rough,.52,tracks*.55*(1-puddle));
   rough=mix(rough,.06,puddle);
  }
 }
 // Optional saturated paint for clear-coated exterior sections: keeps the texture's luminance
 // (panel gaps, shading) and replaces its hue. u_reflectionState.z = hue (<0 black), .w = strength.
 if(mode<.5 && _mtl_u.u_visualCoat.x>0 && _mtl_u.u_reflectionState.w>.01) {
  float lum=dot(albedo,float3(.2126,.7152,.0722));
  float hue=_mtl_u.u_reflectionState.z;
  float3 rgb=clamp(abs(fract(hue+float3(0,2.0/3.0,1.0/3.0))*6.0-3.0)-1.0,0.0,1.0);
  float3 painted=hue<0?float3(lum*.22):rgb*rgb*(lum*3.0+.03);
  albedo=mix(albedo,painted,_mtl_u.u_reflectionState.w);
 }
 float ndl=max(dot(n,l),0.0),ndv=max(dot(n,v),0.0);
 float3 f0=mix(float3(.04),albedo,metal);
 float3 fresnel=f0+(1-f0)*fresnelWeight(ndv);
 float3 directFresnel=f0+(1-f0)*fresnelWeight(max(dot(v,h),0.0));
 float3 reflected=sky(reflect(-v,n),_mtl_u.u_headlight.w);
 if(_mtl_u.u_reflectionState.x>.5 && (mode<.5 || rough<.3)) {
  float3 local=max(s_environment.sample(environmentSampler,reflect(-v,n),level(reflectionLod(rough))).rgb,float3(0));
  reflected=local;
 }
 // Diffuse skylight, warm sun, Fresnel environment and a broad clearcoat lobe.
 float3 ambient=mix(float3(.045,.055,.070),float3(.14,.19,.27),n.y*.5+.5);
 float3 sunColor=float3(1,.86,.66)*2.2,specColor=float3(1,.87,.69);
 // World geometry only: ground-bounced light and sky fill on vertical faces, so shaded walls are
 // not near-black. Authored; cars keep their hemispheric ambient.
 if(mode>.5 || mode<-.5) ambient+=float3(.080,.072,.066)*(1-abs(n.y));
 // Night: moonlight replaces the sun, ambient collapses to a deep blue floor.
 ambient=mix(ambient,mix(float3(.004,.006,.012),float3(.010,.016,.036),n.y*.5+.5),night);
 float dusk=night*(1-night)*4.0;
 sunColor=mix(sunColor,float3(1.0,.50,.26)*1.6,dusk*.85);
 sunColor=mix(sunColor,float3(.28,.38,.80)*.85,smoothstep(.3,.9,night));specColor=mix(specColor,float3(.10,.13,.24),night);
 float4 light=_mtl_u.u_shadowMatrix*float4(in.world,1);
 float3 coord=light.xyz/light.w;
 float2 shadowUV=float2(coord.x*.5+.5,.5-coord.y*.5);
 // Compare against the receiver plane at each sampled texel, not the depth
 // at the pixel center. Constant-depth PCF self-shadows sloping streets.
 float2 dx=dfdx(shadowUV),dy=dfdy(shadowUV);
 float zx=dfdx(coord.z),zy=dfdy(coord.z),det=dx.x*dy.y-dx.y*dy.x;
 float2 gradient=float2(0);
 if(abs(det)>1e-12) {
  float2 candidate=float2(zx*dy.y-zy*dx.y,zy*dx.x-zx*dy.x)/det;
  if(all(isfinite(candidate))) gradient=clamp(candidate,float2(-16),float2(16));
 }
 float visibility=1.0;
 if(all(shadowUV>float2(0)) && all(shadowUV<float2(1)) && coord.z>0 && coord.z<1) {
  float bias=shadowBias(ndl),sum=0;
  for(int y=-1;y<=1;++y) for(int x=-1;x<=1;++x) {
   float2 offset=float2(x,y)*1.5/2048.0;
   sum+=filteredShadow(s_shadow,shadowSampler,shadowUV+offset,coord.z+dot(offset,gradient)-bias,gradient);
  }
  float edge=min(min(shadowUV.x,shadowUV.y),min(1-shadowUV.x,1-shadowUV.y));
  visibility=mix(1.0,sum/9.0,smoothstep(0.0,.06,edge));
 }
 float3 lit=albedo*(ambient*clamp(in.occlusion,0.0,1.0)+sunColor*ndl*visibility)*diffuseWeight(metal);
 float spec=directLobe(rough,dot(n,h),ndl);
 lit+=fresnel*reflected*mix(1.1,.20,rough)+directFresnel*spec*specColor*visibility;
 if(night>.01) {
  float3 lampDiffuse=float3(0),lampSpec=float3(0);
  lampLight(in.world,n,v,rough,lampDiffuse,lampSpec);
  neonLight(in.world,n,lampDiffuse);
  headLight(in.world,n,_mtl_u.u_headlight,lampDiffuse);
  lit+=night*(albedo*lampDiffuse*diffuseWeight(metal)+fresnel*lampSpec);
  // Lit windows on the authored skyline (surface 5): hashed per window cell.
  if(mode>.5 && round(in.uv.y)==5) {
   float2 cell=floor(float2((abs(n.x)>.5?in.world.z:in.world.x)/2.6,in.world.y/3.7));
   lit+=night*float3(1.0,.75,.42)*(hash(cell)>.42?1.6:0.0);
  }
 }
 if(mode<.5 && _mtl_u.u_visualCoat.x>0) {
  float coat=_mtl_u.u_visualCoat.x,coatRough=clamp(_mtl_u.u_visualCoat.y,.05,1.0);
  float coatF=.04+.96*fresnelWeight(ndv);
  float coatDirectF=.04+.96*fresnelWeight(max(dot(v,h),0.0));
  // Orange peel: a fine, low-amplitude noise perturbation of the coat normal (u_reflectionState.y < 0
  // carries the strength; positive values mark wheel ghosts). Authored. Breaks up mirror-perfect reflections.
  float peel=max(-_mtl_u.u_reflectionState.y,0.0);
  float2 peelUV=in.uv*150.0;
  float3 peelNormal=normalize(n+(float3(noise(peelUV),noise(peelUV+17.3),noise(peelUV+41.7))-.5)*.05*peel);
  float3 coatReflect=reflect(-v,peelNormal);
  float3 coatEnvironment=sky(coatReflect,_mtl_u.u_headlight.w);
  if(_mtl_u.u_reflectionState.x>.5)
   coatEnvironment=max(s_environment.sample(environmentSampler,coatReflect,level(reflectionLod(coatRough))).rgb,float3(0));
  float coatHighlight=pow(max(dot(peelNormal,h),0.0),mix(500.0,8.0,coatRough))*2.0*ndl*visibility;
  // Metallic flake: per-texel random micro-normals sparkle where they catch the half vector. Authored.
  float2 flakeCell=floor(in.uv*260.0);
  float3 flakeRnd=float3(hash(flakeCell),hash(flakeCell+3.1),hash(flakeCell+7.7))-.5;
  float3 flakeNormal=normalize(n+flakeRnd*.9);
  coatHighlight+=pow(max(dot(flakeNormal,h),0.0),90.0)*step(.55,hash(flakeCell+11.3))*ndl*visibility*2.2;
  lit=lit*(1-coat*coatF)+coat*(coatF*coatEnvironment+coatDirectF*coatHighlight*specColor);
 }
 if(foliage) lit+=albedo*.12;
 float distance=length(_mtl_u.u_visualCamera.xyz-in.world);
 float fog=hazeAmount(distance);
 lit=mix(lit,mix(linearDisplay(float3(.67,.73,.77)),float3(.006,.010,.022),night),fog);
 // Preserve linear HDR through blending, capture and bloom; display mapping is final-only.
 // u_reflectionState.y > 0 marks a motion-blur ghost of a spinning wheel: fixed translucent alpha.
 float ghostAlpha=_mtl_u.u_reflectionState.y;
 o.color=float4(max(lit,float3(0)),ghostAlpha>0?ghostAlpha*base.a:base.a); return o;
}
)MSL";
  constexpr std::string_view shadowPixel=R"MSL(#include <metal_stdlib>
using namespace metal;
struct Globals { float4 u_visualCamera; float4 u_visualMaterial; };
struct Varying {
 float4 position [[position]]; float4 color [[user(locn0)]];
 float2 uv [[user(locn1)]]; float3 world [[user(locn2)]]; float3 normal [[user(locn3)]];
 float4 tangent [[user(locn5)]];
 float3 bitangent [[user(locn6)]];
};
float hash(float2 p) { return fract(sin(dot(p,float2(127.1,311.7)))*43758.5453); }
float noise(float2 p) {
 float2 i=floor(p),f=fract(p); f=f*f*(3-2*f);
 return mix(mix(hash(i),hash(i+float2(1,0)),f.x),mix(hash(i+float2(0,1)),hash(i+1),f.x),f.y);
}
fragment float4 xlatMtlMain(Varying in [[stage_in]], constant Globals& _mtl_u [[buffer(0)]],
 texture2d<float> s_texColor [[texture(0)]], sampler smp [[sampler(0)]],
 texture2d<float> s_surfaces [[texture(2)]], sampler surfaceSampler [[sampler(2)]]) {
 float alpha=in.color.a;
 if(_mtl_u.u_visualMaterial.w>.5 && in.uv.y<-.5 && in.uv.y>-1.5) {
  float r=length(in.tangent.xy-.5)*2;
  float cluster=noise(in.world.xz*3.1+in.world.y*2.3)*.55+noise(in.world.xz*8.7-in.world.y*5.9)*.45;
  if(cluster<.14+.46*r) discard_fragment();
 } else if(_mtl_u.u_visualMaterial.w>.5 && in.uv.y>5.5) {
  float2 uv=float2(clamp(in.uv.x,0.0,1.0)*254.0/256+1.0/256,
    .75+(clamp(in.uv.y-6,0.0,1.0)*254+1)/1024);
  alpha*=s_surfaces.sample(surfaceSampler,uv).a;
  if(alpha<.4) discard_fragment();
 } else if(_mtl_u.u_visualMaterial.z>.5 && _mtl_u.u_visualMaterial.w<.5) alpha*=s_texColor.sample(smp,in.uv).a;
 if(alpha<_mtl_u.u_visualCamera.w) discard_fragment();
 return float4(in.position.z,0,0,1);
}
)MSL";
  std::vector<uint8_t> b;
  auto u8=[&](uint8_t n){b.push_back(n);};
  auto u16=[&](uint16_t n){u8(uint8_t(n));u8(uint8_t(n>>8));};
  auto u32=[&](uint32_t n){u16(uint16_t(n));u16(uint16_t(n>>16));};
  auto uniform=[&](std::string_view name,uint8_t type,uint16_t offset,uint16_t registers){
    u8(uint8_t(name.size()));b.insert(b.end(),name.begin(),name.end());
    u8(type|(fragment?0x10:0));u8(1);u16(offset);u16(registers);u16(0);u16(0);
  };
  u8(fragment?'F':'V');u8('S');u8('H');u8(12);
  constexpr uint32_t interface=0x52414345;
  u32(fragment?interface:0);u32(fragment?0:interface);u32(0);u32(0);
  u16(fragment?(shadow?4:11):2);
  if(fragment) {
    uniform("u_visualCamera",bgfx::UniformType::Vec4,0,1);
    uniform("u_visualMaterial",bgfx::UniformType::Vec4,16,1);
    uniform("s_texColor",bgfx::UniformType::Sampler|0x20,0,1);
    if(shadow) uniform("s_surfaces",bgfx::UniformType::Sampler|0x20,2,1);
    if(!shadow) {
      uniform("u_shadowMatrix",bgfx::UniformType::Mat4,32,4);
      uniform("s_shadow",bgfx::UniformType::Sampler|0x20,1,1);
      uniform("s_surfaces",bgfx::UniformType::Sampler|0x20,2,1);
      uniform("u_reflectionState",bgfx::UniformType::Vec4,96,1);
      uniform("u_visualCoat",bgfx::UniformType::Vec4,112,1);
      uniform("u_headlight",bgfx::UniformType::Vec4,128,1);
      uniform("s_environment",bgfx::UniformType::Sampler|0x20,3,1);
      uniform("s_normal",bgfx::UniformType::Sampler|0x20,4,1);
    }
  } else {
    uniform("u_modelViewProj",bgfx::UniformType::Mat4,0,4);
    uniform("u_model",bgfx::UniformType::Mat4,64,4);
  }
  const auto source=fragment?(shadow?shadowPixel:pixel):vertex;u32(uint32_t(source.size()));
  b.insert(b.end(),source.begin(),source.end());u8(0);
  u8(fragment?0:6);
  if(!fragment){u16(0x0001);u16(0x0005);u16(0x0010);u16(0x0002);u16(0x0011);u16(0x0003);}
  u16(fragment?(shadow?48:128):128);
  return b;
}
}
