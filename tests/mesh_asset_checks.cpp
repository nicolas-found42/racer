#include "mesh_asset.h"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <unistd.h>
void require(bool value,const char *reason) { if (!value) throw std::runtime_error(reason); }
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
  auto reject=[&](std::string text,const char *reason) {
    write(text);
    try { racer::loadMeshAsset(path,{},&context); }
    catch (const std::runtime_error &error) {
      if (std::string(error.what())!=reason) throw std::runtime_error(std::string("expected ")+reason+"; got "+error.what());
      return;
    }
    throw std::runtime_error("accepted invalid asset");
  };
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
  std::cout<<"PASS: embedded glTF transforms/color, malformed/cycle/external/budget/topology rejection\n";
} catch (const std::exception &error) {
  std::cerr<<"FAIL: "<<error.what()<<'\n';return 1;
}
