#include "mesh_asset.h"
#include "source_bump.h"
#include <bit>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <unistd.h>
void require(bool value,const char *reason) { if (!value) throw std::runtime_error(reason); }
std::string base64(const std::vector<uint8_t> &bytes) {
  constexpr char alphabet[]="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  std::string result;
  for (size_t i=0;i<bytes.size();i+=3) {
    const uint32_t word=uint32_t(bytes[i])<<16 |
      (i+1<bytes.size()?uint32_t(bytes[i+1])<<8:0) | (i+2<bytes.size()?bytes[i+2]:0);
    result+=alphabet[(word>>18)&63];result+=alphabet[(word>>12)&63];
    result+=i+1<bytes.size()?alphabet[(word>>6)&63]:'=';
    result+=i+2<bytes.size()?alphabet[word&63]:'=';
  }
  return result;
}
std::string normalFixture(const std::array<float,9> &normals,const std::string &nodeFields="") {
  std::vector<uint8_t> bytes;
  auto append=[&](float value) {
    const auto bits=std::bit_cast<uint32_t>(value);
    for (unsigned shift=0;shift<32;shift+=8) bytes.push_back(uint8_t(bits>>shift));
  };
  for (float value:std::array<float,9>{0,0,0,1,0,0,0,0,1}) append(value);
  for (float value:normals) append(value);
  return R"({"asset":{"version":"2.0"},"scene":0,"scenes":[{"nodes":[0]}],"nodes":[{"mesh":0)"+
    nodeFields+R"(}],"meshes":[{"primitives":[{"attributes":{"POSITION":0,"NORMAL":1}}]}],"buffers":[{"byteLength":72,"uri":"data:application/octet-stream;base64,)"+
    base64(bytes)+R"("}],"bufferViews":[{"buffer":0,"byteLength":36},{"buffer":0,"byteOffset":36,"byteLength":36}],"accessors":[{"bufferView":0,"componentType":5126,"count":3,"type":"VEC3"},{"bufferView":1,"componentType":5126,"count":3,"type":"VEC3"}]})";
}
std::string tangentFixture(const std::array<float,12>& tangents,const std::string& nodeFields="",bool includeNormal=true,
                           std::array<float,3> normal={0,0,1}) {
  std::vector<uint8_t> bytes;
  const auto append=[&](float value){const auto bits=std::bit_cast<uint32_t>(value);for(unsigned shift=0;shift<32;shift+=8)bytes.push_back(uint8_t(bits>>shift));};
  for(float v:std::array<float,9>{0,0,0,1,0,0,0,1,0})append(v);
  for(int i=0;i<3;++i)for(float v:normal)append(v);
  for(float v:tangents)append(v);
  return R"({"asset":{"version":"2.0"},"scene":0,"scenes":[{"nodes":[0]}],"nodes":[{"mesh":0)"+nodeFields+
    R"(}],"meshes":[{"primitives":[{"attributes":{"POSITION":0,)"+(includeNormal?std::string(R"("NORMAL":1,)"):std::string())+
    R"("TANGENT":2}}]}],"buffers":[{"byteLength":120,"uri":"data:application/octet-stream;base64,)"+base64(bytes)+
    R"("}],"bufferViews":[{"buffer":0,"byteLength":36},{"buffer":0,"byteOffset":36,"byteLength":36},{"buffer":0,"byteOffset":72,"byteLength":48}],"accessors":[{"bufferView":0,"componentType":5126,"count":3,"type":"VEC3"},{"bufferView":1,"componentType":5126,"count":3,"type":"VEC3"},{"bufferView":2,"componentType":5126,"count":3,"type":"VEC4"}]})";
}
std::string packedFixture(std::string payload=R"({"texture":0})",std::string nodeFields="",bool includeNormal=true,bool includeUV=true,bool includeTangent=true,
                          std::array<float,3> normal={0,0,.995f},std::array<float,4> tangent={1,.01f,0,-1},bool mixedW=false) {
  std::vector<uint8_t> bytes;
  auto append=[&](float value){const auto bits=std::bit_cast<uint32_t>(value);for(unsigned shift=0;shift<32;shift+=8)bytes.push_back(uint8_t(bits>>shift));};
  for(float v:std::array<float,9>{0,0,0,1,0,0,0,1,0})append(v);
  for(int i=0;i<3;++i)for(float v:normal)append(v);
  for(int i=0;i<3;++i)for(unsigned k=0;k<4;++k)append(mixedW&&i==1&&k==3?-tangent[k]:tangent[k]);
  for(float v:std::array<float,6>{0,0,1,0,0,1})append(v);
  return R"({"asset":{"version":"2.0"},"scene":0,"scenes":[{"nodes":[0]}],"nodes":[{"mesh":0)"+nodeFields+
    R"(}],"meshes":[{"primitives":[{"material":0,"attributes":{"POSITION":0)"+
    (includeNormal?std::string(R"(,"NORMAL":1)"):std::string())+(includeTangent?std::string(R"(,"TANGENT":2)"):std::string())+
    (includeUV?std::string(R"(,"TEXCOORD_0":3)"):std::string())+
    R"(}}]}],"materials":[{"extensions":{"RACER_source_bump_spec":)"+payload+
    R"(},"pbrMetallicRoughness":{"baseColorTexture":{"index":0}}}],"textures":[{"source":0}],"images":[{"uri":"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAYAAABytg0kAAAAFElEQVR4nGP4z8DwHwRZGME0AwMAPv8GAPpcE7AAAAAASUVORK5CYII="}],"buffers":[{"byteLength":144,"uri":"data:application/octet-stream;base64,)"+base64(bytes)+
    R"("}],"bufferViews":[{"buffer":0,"byteLength":36},{"buffer":0,"byteOffset":36,"byteLength":36},{"buffer":0,"byteOffset":72,"byteLength":48},{"buffer":0,"byteOffset":120,"byteLength":24}],"accessors":[{"bufferView":0,"componentType":5126,"count":3,"type":"VEC3"},{"bufferView":1,"componentType":5126,"count":3,"type":"VEC3"},{"bufferView":2,"componentType":5126,"count":3,"type":"VEC4"},{"bufferView":3,"componentType":5126,"count":3,"type":"VEC2"}]})";
}
void requireTangent(const racer::AssetVertex& v,float x,float y,float z,float w,const char* reason) {
  require(std::isfinite(v.tx)&&std::isfinite(v.ty)&&std::isfinite(v.tz)&&std::isfinite(v.tw),"tangent stays finite");
  require(std::abs(v.tx-x)<1e-5&&std::abs(v.ty-y)<1e-5&&std::abs(v.tz-z)<1e-5&&v.tw==w,reason);
  if(w)require(std::abs(std::hypot(v.tx,v.ty,v.tz)-1)<1e-5&&std::abs(v.tx*v.nx+v.ty*v.ny+v.tz*v.nz)<1e-5,"tangent unit and perpendicular to transformed normal");
}
void requireNormal(const racer::AssetVertex &vertex,float x,float y,float z,const char *reason) {
  require(std::isfinite(vertex.nx) && std::isfinite(vertex.ny) && std::isfinite(vertex.nz),"normal remains finite");
  require(std::abs(vertex.nx-x)<1e-5f && std::abs(vertex.ny-y)<1e-5f && std::abs(vertex.nz-z)<1e-5f,reason);
  require(std::abs(std::hypot(vertex.nx,vertex.ny,vertex.nz)-1)<1e-5f,"normal remains unit length");
}
int main() try {
  char temporary[]="/tmp/racer-mesh-XXXXXX";
  require(mkdtemp(temporary),"temporary directory");
  const auto path=std::filesystem::path(temporary)/"scene.gltf";
  const std::string fixture=R"({"asset":{"version":"2.0"},"scene":0,"scenes":[{"nodes":[0]}],"nodes":[{"mesh":0,"translation":[2,1,3],"scale":[2,2,2]}],"meshes":[{"primitives":[{"attributes":{"POSITION":0},"indices":1,"material":0}]}],"materials":[{"pbrMetallicRoughness":{"baseColorFactor":[1,0,0,1]}}],"buffers":[{"byteLength":42,"uri":"data:application/octet-stream;base64,AAAAAAAAAAAAAAAAAACAPwAAAAAAAAAAAAAAAAAAAAAAAIA/AAABAAIA"}],"bufferViews":[{"buffer":0,"byteOffset":0,"byteLength":36},{"buffer":0,"byteOffset":36,"byteLength":6}],"accessors":[{"bufferView":0,"componentType":5126,"count":3,"type":"VEC3"},{"bufferView":1,"componentType":5123,"count":3,"type":"SCALAR"}]})";
  auto write=[&](const std::string &text) { std::ofstream out(path);out<<text; };
  write(fixture);
  racer::AssetLoadContext context;
  auto mesh=racer::loadMeshAsset(path,{},&context);
  require(context.stage==racer::AssetLoadStage::Complete &&
          std::string(context.actualMeshSHA256.data())==mesh.sourceSHA256 && context.inputBytes==fixture.size(),"successful mesh context");
  require(std::string(racer::assetInputIdentity(context))=="unqualified","inspection has no expected digest");
  require(std::string(racer::assetBytesDigest("abc").data())=="ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad","known SHA256 bytes");
  require(racer::assetDigestFromHex("private/path/not-a-digest")[0]=='\0',"nonhash identity omitted");
  require(mesh.triangles.size()==3,"triangle count");
  require(mesh.minimum==std::array<float,3>{2,1,3} && mesh.maximum==std::array<float,3>{4,1,5},"node transforms");
  require(mesh.triangles[0].color==0xff0000ff,"base color");
  auto scenes=fixture;
  scenes.replace(scenes.find("\"scene\":0"),9,"\"scene\":1");
  scenes.replace(scenes.find("\"scenes\":[{\"nodes\":[0]}]"),24,"\"scenes\":[{\"nodes\":[1]},{\"nodes\":[0]}]");
  const auto nodesEnd=scenes.find("],\"meshes\"");
  scenes.insert(nodesEnd,",{\"mesh\":0,\"translation\":[100,0,0]}");
  write(scenes);const auto activeScene=racer::loadMeshAsset(path);
  require(activeScene.triangles.size()==3&&activeScene.minimum==mesh.minimum&&activeScene.maximum==mesh.maximum,"inactive glTF scenes and nodes do not render or expand bounds");
  auto materialOnly=fixture;
  const auto pbrBegin=materialOnly.find("\"pbrMetallicRoughness\"");
  const auto pbrEnd=materialOnly.find('}',pbrBegin);
  materialOnly.replace(pbrBegin,pbrEnd-pbrBegin+1,"\"alphaMode\":\"MASK\",\"alphaCutoff\":0.25");
  write(materialOnly);const auto maskOnly=racer::loadMeshAsset(path);
  require(maskOnly.sections[0].mask&&maskOnly.sections[0].alphaCutoff==.25f,"alpha properties independent of optional PBR block");
  require(maskOnly.triangles[0].color==0xffffffff&&maskOnly.sections[0].roughness==1&&maskOnly.sections[0].metallic==1,"omitted PBR uses glTF defaults");
  auto blendOnly=materialOnly;blendOnly.replace(blendOnly.find("MASK"),4,"BLEND");
  write(blendOnly);require(racer::loadMeshAsset(path).sections[0].blend,"blend independent of optional PBR block");
  for(const auto *alpha:{"0.4999","0.5","0.5001"}) {
    auto exact=fixture;const auto factor=exact.find("[1,0,0,1]");
    exact.replace(factor,9,std::string("[1,0,0,")+alpha+"]");
    exact.insert(exact.find("\"pbrMetallicRoughness\""),"\"alphaMode\":\"MASK\",\"alphaCutoff\":0.5,");
    write(exact);const auto boundary=racer::loadMeshAsset(path);
    require(boundary.triangles[0].opacity==std::stof(alpha),"factor opacity retains float precision at cutoff");
    require((boundary.triangles[0].color>>24)==255,"packed alpha does not quantize factor opacity");
  }
  auto coated=fixture;
  const auto materialAt=coated.find("\"materials\":[{")+14;
  coated.insert(materialAt,"\"extensions\":{\"KHR_materials_clearcoat\":{\"clearcoatFactor\":0.75,\"clearcoatRoughnessFactor\":0.2}},");
  write(coated);const auto coatMesh=racer::loadMeshAsset(path);
  require(coatMesh.sections[0].clearcoat==.75f && std::abs(coatMesh.sections[0].coatRoughness-.2f)<1e-6,"clearcoat scalar factors retained");
  for (const auto &vertex:mesh.triangles) requireNormal(vertex,0,-1,0,"missing normals use transformed face direction");
  auto reject=[&](std::string text,const char *reason) {
    write(text);
    try { racer::loadMeshAsset(path,{},&context); }
    catch (const std::runtime_error &error) {
      if (std::string(error.what())!=reason) throw std::runtime_error(std::string("expected ")+reason+"; got "+error.what());
      return;
    }
    throw std::runtime_error("accepted invalid asset");
  };
  for(const auto* field:{"clearcoatFactor","clearcoatRoughnessFactor"}) {
    for(const auto* invalid:{"-0.1","1.1","1e1000"}) {
      auto bad=coated;const auto key=bad.find(std::string("\"")+field+"\":");
      const auto value=key+std::strlen(field)+3,end=bad.find_first_of(",}",value);
      bad.replace(value,end-value,invalid);reject(bad,"asset_material_factor");
    }
  }
  auto ambientFixture=fixture;
  auto attributes=ambientFixture.find("\"POSITION\":0");
  ambientFixture.replace(attributes,12,"\"POSITION\":0,\"_RACER_OCCLUSION\":2");
  const auto viewStart=ambientFixture.find("\"bufferViews\"");
  const auto strideAt=ambientFixture.find("\"byteLength\":36",viewStart)+15;
  ambientFixture.insert(strideAt,",\"byteStride\":12");
  ambientFixture.insert(ambientFixture.rfind(']'),",{\"bufferView\":0,\"componentType\":5126,\"count\":3,\"type\":\"SCALAR\"}");
  write(ambientFixture);const auto ambientMesh=racer::loadMeshAsset(path);
  require(ambientMesh.triangles[0].occlusion==0&&ambientMesh.triangles[1].occlusion==1&&ambientMesh.triangles[2].occlusion==0,"explicit source ambient scalar retained independently of node scale");
  auto malformedAmbient=ambientFixture;
  const auto ambientType=malformedAmbient.rfind("SCALAR");malformedAmbient.replace(ambientType,6,"VEC2");
  reject(malformedAmbient,"asset_occlusion_unsupported");
  require(mesh.triangles[0].occlusion==1,"unknown source occlusion defaults to one");
  const auto smoothFixture=normalFixture({1,1,1,1,0,0,0,1,0},
    R"(,"scale":[2,3,4],"rotation":[0,0,0.7071067811865476,0.7071067811865476],"translation":[20,30,40])");
  write(smoothFixture);auto smooth=racer::loadMeshAsset(path);
  const float root61=std::sqrt(61.f);
  // Rz(90) * diag(2,3,4) sends inverse-transpose (1,1,1) to
  // (-1/3,1/2,1/4): expected independently, not copied from loader cofactors.
  requireNormal(smooth.triangles[0],-4/root61,6/root61,3/root61,"inverse transpose preserves smooth normal under rotation/nonuniform scale");
  requireNormal(smooth.triangles[1],0,1,0,"smooth normals retain first independent corner direction");
  requireNormal(smooth.triangles[2],-1,0,0,"smooth normals retain second independent corner direction");
  write(normalFixture({0,0,0,0,0,0,0,0,0}));auto zeroNormals=racer::loadMeshAsset(path);
  for (const auto &vertex:zeroNormals.triangles) requireNormal(vertex,0,-1,0,"zero source normals use finite face fallback");
  static_assert(sizeof(racer::AssetVertex)==60);
  const std::array<float,12> suppliedY{0,1,0,-1,0,1,0,-1,0,1,0,-1};
  const auto supplied=tangentFixture(suppliedY);write(supplied);auto framed=racer::loadMeshAsset(path);
  for(const auto& v:framed.triangles)requireTangent(v,0,1,0,-1,"supplied 90-degree tangent and negative handedness retained");
  require(framed.sourceSHA256==std::string(racer::assetBytesDigest(supplied).data()),"tangent input identity remains exact");
  {std::ifstream input(path);const std::string unchanged((std::istreambuf_iterator<char>(input)),{});require(unchanged==supplied,"loader never rewrites source buffer prefix or JSON");}
  write(tangentFixture(suppliedY,R"(,"scale":[-2,3,4],"rotation":[0,0,0.7071067811865476,0.7071067811865476])"));framed=racer::loadMeshAsset(path);
  for(const auto& v:framed.triangles)requireTangent(v,-1,0,0,1,"reflection flips handedness while rotation/nonuniform scale transforms tangent forward");
  const float invRoot2=1/std::sqrt(2.f),invRoot3=1/std::sqrt(3.f);
  const std::array<float,12> oblique{invRoot2,-invRoot2,0,1,invRoot2,-invRoot2,0,1,invRoot2,-invRoot2,0,1};
  write(tangentFixture(oblique,R"(,"scale":[2,3,4],"rotation":[0,0,0.7071067811865476,0.7071067811865476])",true,{invRoot3,invRoot3,invRoot3}));framed=racer::loadMeshAsset(path);
  for(const auto& v:framed.triangles){requireTangent(v,3/std::sqrt(13.f),2/std::sqrt(13.f),0,1,"forward tangent differs from inverse-transpose normal under nonuniform scale");requireNormal(v,-4/root61,6/root61,3/root61,"tangent handling preserves existing inverse-transpose normals");}
  for(const auto& v:mesh.triangles)requireTangent(v,0,0,0,0,"absent source tangent uses derivative fallback flag");
  write(tangentFixture(suppliedY,"",false));framed=racer::loadMeshAsset(path);
  for(const auto& v:framed.triangles)requireTangent(v,0,0,0,0,"provided tangent ignored when NORMAL absent per glTF");
  auto invalidTangent=suppliedY;invalidTangent[3]=0;reject(tangentFixture(invalidTangent),"asset_tangent_invalid");
  invalidTangent=suppliedY;invalidTangent[3]=.5f;reject(tangentFixture(invalidTangent),"asset_tangent_invalid");
  invalidTangent=suppliedY;invalidTangent[7]=1;write(tangentFixture(invalidTangent));framed=racer::loadMeshAsset(path);
  require(framed.triangles[0].tw==-1&&framed.triangles[1].tw==1&&framed.triangles[2].tw==-1,"mixed corner handedness preserved; glTF defines its tangent space as undefined");
  invalidTangent=suppliedY;invalidTangent[0]=std::numeric_limits<float>::infinity();reject(tangentFixture(invalidTangent),"asset_tangent_invalid");
  invalidTangent=suppliedY;invalidTangent[3]=std::numeric_limits<float>::quiet_NaN();reject(tangentFixture(invalidTangent),"asset_tangent_invalid");
  reject(tangentFixture({0,0,1,1,0,0,1,1,0,0,1,1}),"asset_tangent_invalid");
  reject(tangentFixture(suppliedY,R"(,"scale":[0,1,1])"),"asset_tangent_transform");
  auto malformedTangent=supplied;const auto tangentType=malformedTangent.rfind("VEC4");malformedTangent.replace(tangentType,4,"VEC3");reject(malformedTangent,"asset_tangent_unsupported");
  malformedTangent=supplied;const auto tangentCount=malformedTangent.rfind("\"count\":3");malformedTangent.replace(tangentCount,9,"\"count\":2");reject(malformedTangent,"asset_tangent_unsupported");
  auto wrongNormalShape=normalFixture({0,1,0,0,1,0,0,1,0});
  auto normalType=wrongNormalShape.rfind("VEC3");wrongNormalShape.replace(normalType,4,"VEC2");
  reject(wrongNormalShape,"asset_normal_unsupported");
  auto shortNormals=normalFixture({0,1,0,0,1,0,0,1,0});
  const auto normalCount=shortNormals.rfind("\"count\":3");shortNormals.replace(normalCount,9,"\"count\":2");
  reject(shortNormals,"asset_validation");
  reject(normalFixture({std::numeric_limits<float>::infinity(),0,0,0,1,0,0,1,0}),"asset_normal_invalid");
  reject(normalFixture({std::numeric_limits<float>::quiet_NaN(),0,0,0,1,0,0,1,0}),"asset_normal_invalid");
  write(normalFixture({std::numeric_limits<float>::max(),0,0,1,0,0,1,0,0},R"(,"scale":[1e-10,1,1])"));
  const auto largeNormals=racer::loadMeshAsset(path);
  for (const auto &vertex:largeNormals.triangles) requireNormal(vertex,1,0,0,"finite source normals remain finite after inverse scale");
  auto materialFixture=[&](const std::string &factors) {
    auto text=fixture;const auto at=text.find("\"baseColorFactor\"");text.insert(at,factors+",");return text;
  };
  write(materialFixture("\"roughnessFactor\":0.125,\"metallicFactor\":0.875"));
  const auto materialMesh=racer::loadMeshAsset(path);
  require(materialMesh.sections[0].roughness==.125f && materialMesh.sections[0].metallic==.875f,"explicit PBR material factors retained");
  for (const auto *factor:{"roughnessFactor","metallicFactor"}) {
    for (const auto *invalid:{"-0.01","1.01","1e1000","-1e1000"})
      reject(materialFixture(std::string("\"")+factor+"\":"+invalid),"asset_material_factor");
    for (const auto *valid:{"0","1"}) {
      write(materialFixture(std::string("\"")+factor+"\":"+valid));const auto boundary=racer::loadMeshAsset(path);
      const float actual=std::string(factor)=="roughnessFactor"?boundary.sections[0].roughness:boundary.sections[0].metallic;
      require(actual==float(valid[0]-'0'),"PBR factor inclusive boundary retained");
    }
  }
  reject("{","asset_parse");
  require(context.stage==racer::AssetLoadStage::Parse && context.inputBytes==1 &&
          std::string(context.actualMeshSHA256.data())=="021fb596db81e6d02bf3d2586ee3981fe519f275c0ac9ca76bbcf2ebb4097d96","parse failure retains actual bytes identity");
  auto emptyAccessor=fixture;auto countAt=emptyAccessor.find("\"count\":3");
  emptyAccessor.replace(countAt,9,"\"count\":0");reject(emptyAccessor,"asset_accessor_unsupported");
  auto shortView=fixture;auto viewAt=shortView.find("\"byteLength\":36");
  shortView.replace(viewAt,15,"\"byteLength\":35");reject(shortView,"asset_accessor_bounds");
  auto outsideBuffer=fixture;viewAt=outsideBuffer.find("\"byteOffset\":36");
  outsideBuffer.replace(viewAt,15,"\"byteOffset\":43");reject(outsideBuffer,"asset_buffer_view_bounds");
  auto external=fixture;auto begin=external.find("data:application/");auto end=external.find('"',begin);
  external.replace(begin,end-begin,"../../profile.txt");reject(external,"asset_external_or_large_buffer");
  require(context.stage==racer::AssetLoadStage::Buffers && context.actualMeshSHA256[0],"buffer rejection stage retains input identity");
  auto oversized=fixture;begin=oversized.find("\"byteLength\":42");
  oversized.replace(begin,15,"\"byteLength\":1099511627776");reject(oversized,"asset_external_or_large_buffer");
  auto cycle=fixture;begin=cycle.find("\"mesh\":0");cycle.insert(begin,"\"children\":[0],");reject(cycle,"asset_parse");
  auto topology=fixture;begin=topology.find("\"attributes\"");topology.insert(begin,"\"mode\":1,");reject(topology,"asset_primitive_unsupported");
  const std::string textured=R"TEXTURE({"asset":{"version":"2.0"},"scene":0,"scenes":[{"nodes":[0]}],"nodes":[{"mesh":0}],"meshes":[{"primitives":[{"attributes":{"POSITION":0,"TEXCOORD_0":2},"indices":1,"material":0}]}],"materials":[{"pbrMetallicRoughness":{"baseColorFactor":[1,1,1,1],"baseColorTexture":{"index":0}}}],"textures":[{"source":0}],"images":[{"bufferView":3,"mimeType":"image/png"}],"buffers":[{"byteLength":145,"uri":"data:application/octet-stream;base64,AAAAAAAAAAAAAAAAAACAPwAAAAAAAAAAAAAAAAAAAAAAAIA/AAABAAIAAAAAAAAAAAAAAAAAgD8AAAAAAAAAAAAAgD+JUE5HDQoaCgAAAA1JSERSAAAAAgAAAAIIBgAAAHK2DSQAAAAUSURBVHicY/jPwPAfBFkYwTQDAwA+/wYA+lwTsAAAAABJRU5ErkJggg=="}],"bufferViews":[{"buffer":0,"byteOffset":0,"byteLength":36},{"buffer":0,"byteOffset":36,"byteLength":6},{"buffer":0,"byteOffset":44,"byteLength":24},{"buffer":0,"byteOffset":68,"byteLength":77}],"accessors":[{"bufferView":0,"componentType":5126,"count":3,"type":"VEC3"},{"bufferView":1,"componentType":5123,"count":3,"type":"SCALAR"},{"bufferView":2,"componentType":5126,"count":3,"type":"VEC2"}]})TEXTURE";
  write(textured);auto mapped=racer::loadMeshAsset(path);
  require(mapped.images.size()==1 && mapped.images[0].width==2 && mapped.images[0].height==2,"embedded PNG dimensions");
  require(mapped.images[0].rgba==std::vector<uint8_t>{255,0,0,255,0,255,0,255,0,0,255,255,255,255,255,255},"PNG known pixel order and colors");
  require(mapped.sections.size()==1 && mapped.sections[0].image==0 && mapped.sections[0].first==0 && mapped.sections[0].count==3,"material section binding");
  require(mapped.triangles[1].u==1 && mapped.triangles[2].v==1,"UV per indexed vertex");
  for(const auto* bad:{"{}","null","0",R"({"texture":-1})",R"({"texture":1.0})",R"({"texture":1e0})",R"({"texture":true})",R"({"texture":"0"})",R"({"texture":4294967296})",R"({"texture":0,"texture":0})",R"({"texture":0,"other":0})",R"({"texture":00})",R"({"texture":0} trailing)",R"({"texture":+0})"})
    require(!racer::sourceBumpTexture(bad),"custom single-field grammar rejects unsupported payload");
  require(racer::sourceBumpTexture(" \t{\"texture\": 0}\n")==0&&racer::sourceBumpTexture(R"({"texture":4294967295})")==4294967295u,"strict uint parser permits JSON whitespace and full uint32 range");
  auto packedSource=packedFixture();write(packedSource);const auto packedAsset=racer::loadMeshAsset(path);
  const auto& packedSection=packedAsset.sections[0];
  require(packedSection.sourceBump&&packedSection.detailMode()==2&&packedAsset.images.size()==2&&
    packedAsset.images[packedSection.normalImage].role==racer::ImageRole::PackedHeightSpec&&
    packedAsset.images[packedSection.image].role==racer::ImageRole::Color&&
    packedAsset.images[packedSection.image].rgba==packedAsset.images[packedSection.normalImage].rgba,"same image color/packed roles are distinct while sourceRGBA unchanged");
  for(const auto& v:packedAsset.triangles)require(v.nz==.995f&&v.tx==1&&v.ty==.01f&&v.tw==-1,"packed source N/T magnitudes and handedness preserved without GramSchmidt");
  auto alphaPacked=packedSource;
  const auto pngBegin=alphaPacked.find("data:image/png;base64,")+22;
  const auto pngEnd=alphaPacked.find('"',pngBegin);
  alphaPacked.replace(pngBegin,pngEnd-pngBegin,"iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAYAAABytg0kAAAAGklEQVR4nGNMbqmOdrLijGCSEmJVef7t11sAMJwGt/zIPGkAAAAASUVORK5CYII=");
  write(alphaPacked);const auto alphaAsset=racer::loadMeshAsset(path);
  require(alphaAsset.images[alphaAsset.sections[0].normalImage].rgba==std::vector<uint8_t>{99,132,123,91,165,190,132,179,125,150,128,127,140,180,126,160},"packed PNG loader preserves straight R/G/B/A bytes without premultiplication or gamma");
  write(packedFixture(R"({"texture":0})",R"(,"rotation":[0,0,0.7071067811865476,0.7071067811865476])"));
  for(const auto& v:racer::loadMeshAsset(path).triangles)require(std::abs(v.tx+.01f)<1e-6&&std::abs(v.ty-1)<1e-6&&v.nz==.995f,"packed rigid rotation preserves full source basis");
  for(const auto* payload:{"{}",R"({"texture":1})",R"({"texture":-1})",R"({"texture":0,"texture":0})",R"({"texture":0,"other":0})"})reject(packedFixture(payload),"asset_source_bump_extension");
  reject(packedFixture("null"),"asset_parse");
  reject(packedFixture(R"({"texture":0})","",false),"asset_source_bump_frame");
  reject(packedFixture(R"({"texture":0})","",true,false),"asset_source_bump_frame");
  reject(packedFixture(R"({"texture":0})","",true,true,false),"asset_source_bump_frame");
  reject(packedFixture(R"({"texture":0})",R"(,"scale":[1,2,1])"),"asset_source_bump_transform");
  reject(packedFixture(R"({"texture":0})","",true,true,true,{0,0,.8f}),"asset_source_bump_frame");
  reject(packedFixture(R"({"texture":0})","",true,true,true,{0,0,1},{0,0,1,1}),"asset_source_bump_frame");
  write(packedFixture(R"({"texture":0})","",true,true,true,{0,0,1},{1,0,0,-1},true));
  const auto mixedPacked=racer::loadMeshAsset(path);
  require(mixedPacked.triangles[0].tw==-1&&mixedPacked.triangles[1].tw==1&&mixedPacked.triangles[2].tw==-1,"custom pervertexW is preserved for separately interpolated B");
  reject(packedFixture(R"({"texture":0})","",true,true,true,{0,0,1},{1,0,0,0}),"asset_tangent_invalid");
  auto conflict=packedSource;conflict.insert(conflict.find("\"extensions\":"),"\"normalTexture\":{\"index\":0},");reject(conflict,"asset_source_bump_conflict");
  auto duplicateExtension=packedSource;duplicateExtension.insert(duplicateExtension.find("\"RACER_source_bump_spec\":"),"\"RACER_source_bump_spec\":{\"texture\":0},");reject(duplicateExtension,"asset_source_bump_extension");
  auto normalMapped=textured;
  normalMapped.insert(normalMapped.find("\"pbrMetallicRoughness\""),"\"normalTexture\":{\"index\":0,\"scale\":0.6},");
  write(normalMapped);const auto detailed=racer::loadMeshAsset(path);
  const auto& detail=detailed.sections[0];
  require(detailed.images.size()==2&&detail.normalImage!=detail.image&&detail.normalScale==.6f,"normal and color roles retain separate GPU images and normal scale");
  require(detailed.images.at(detail.normalImage).role==racer::ImageRole::Normal&&detailed.images.at(detail.image).role==racer::ImageRole::Color&&
    detailed.images.at(detail.normalImage).rgba==detailed.images.at(detail.image).rgba,"role separation preserves exact decoded linear data bytes");
  for(const auto* value:{"0","-8","8"}) {
    auto boundary=normalMapped;boundary.replace(boundary.find("0.6"),3,value);write(boundary);
    require(racer::loadMeshAsset(path).sections[0].normalScale==std::stof(value),"bounded normal scale inclusive values");
  }
  for(const auto* value:{"8.01","-8.01","1e1000"}) {
    auto invalid=normalMapped;invalid.replace(invalid.find("0.6"),3,value);reject(invalid,"asset_normal_scale");
  }
  auto secondaryUV=normalMapped;secondaryUV.insert(secondaryUV.find("\"scale\":0.6"),"\"texCoord\":1,");reject(secondaryUV,"asset_texture_unsupported");
  auto separateSamplers=normalMapped;
  separateSamplers.replace(separateSamplers.find("\"textures\":[{\"source\":0}]"),25,
    "\"samplers\":[{\"wrapS\":33071,\"wrapT\":33071},{\"wrapS\":33648,\"wrapT\":10497}],\"textures\":[{\"source\":0,\"sampler\":0},{\"source\":0,\"sampler\":1}]");
  const auto normalIndex=separateSamplers.find("\"normalTexture\":{\"index\":0");
  separateSamplers[normalIndex+std::strlen("\"normalTexture\":{\"index\":")]='1';
  write(separateSamplers);const auto wrap=racer::loadMeshAsset(path).sections[0];
  require(wrap.wrapU==33071&&wrap.wrapV==33071&&wrap.normalWrapU==33648&&wrap.normalWrapV==10497,"normal sampler addressing is independent of base-color sampler");
  auto duplicate=textured;
  auto imageList=duplicate.find("\"images\":[");auto imageEnd=duplicate.find(']',imageList);
  duplicate.insert(imageEnd,",{\"bufferView\":3,\"mimeType\":\"image/png\"}");
  auto textureList=duplicate.find("\"textures\":[");auto textureEnd=duplicate.find(']',textureList);
  duplicate.insert(textureEnd,",{\"source\":1}");
  auto mats=duplicate.find("\"materials\":[");auto matsEnd=duplicate.find("],\"textures\"",mats);
  duplicate.insert(matsEnd,",{\"pbrMetallicRoughness\":{\"baseColorTexture\":{\"index\":1}}}");
  auto primitiveEnd=duplicate.find("}]}],\"materials\"");
  duplicate.insert(primitiveEnd+1,",{\"attributes\":{\"POSITION\":0,\"TEXCOORD_0\":2},\"indices\":1,\"material\":1}");
  write(duplicate);auto shared=racer::loadMeshAsset(path);
  require(shared.images.size()==1 && shared.sections.size()==2 && shared.sections[0].image==shared.sections[1].image,"identical image payloads shared across distinct source image objects");
  auto externalImage=textured;const std::string imageFields="\"bufferView\":3,\"mimeType\":\"image/png\"";
  auto imageAt=externalImage.find(imageFields);
  externalImage.replace(imageAt,imageFields.size(),"\"uri\":\"private.png\"");reject(externalImage,"asset_image_embedded_png_required");
  require(context.stage==racer::AssetLoadStage::Images && context.actualMeshSHA256[0],"image failure retains input identity and stage");
  std::filesystem::remove_all(temporary);
  std::cout<<"PASS: embedded glTF transforms/color, smooth inverse-transpose normals/face fallback, explicit tangent frame/handedness/validation, PBR factor bounds, malformed/cycle/external/budget/topology rejection\n";
} catch (const std::exception &error) {
  std::cerr<<"FAIL: "<<error.what()<<'\n';return 1;
}
