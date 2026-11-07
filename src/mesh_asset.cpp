#include "mesh_asset.h"
#include "vehicle_look.h"
#include "source_bump.h"
#define CGLTF_IMPLEMENTATION
#include "cgltf.h"
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <limits>
#include <memory>
#include <stdexcept>
#include <unordered_set>
#include <unordered_map>
#include <bimg/decode.h>
#include <bx/allocator.h>
#include <CommonCrypto/CommonDigest.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
namespace racer {
namespace {
constexpr size_t maxFile = 32*1024*1024, maxMemory = 128*1024*1024;
constexpr size_t maxVertices = 1500000;
struct Budget { size_t live = 0; };
struct alignas(std::max_align_t) Allocation { size_t size; };
void *allocate(void *user, cgltf_size size) {
  auto &budget = *static_cast<Budget *>(user);
  if (size > maxMemory || budget.live > maxMemory-size) return nullptr;
  auto *block = static_cast<Allocation *>(std::malloc(sizeof(Allocation)+size));
  if (!block) return nullptr;
  block->size=size; budget.live+=size; return block+1;
}
void release(void *user, void *pointer) {
  if (!pointer) return;
  auto *block=static_cast<Allocation *>(pointer)-1;
  static_cast<Budget *>(user)->live-=block->size; std::free(block);
}
[[noreturn]] void fail(const char *reason) { throw MeshAssetError(reason); }
// Establish arithmetic bounds before the library validator reads index data.
// Subtraction/division keep malformed counts and offsets from wrapping size_t.
void preflight(const cgltf_data &data) {
  for (size_t i=0;i<data.buffer_views_count;++i) {
    const auto &view=data.buffer_views[i];
    if (!view.buffer || view.offset>view.buffer->size ||
        view.size>view.buffer->size-view.offset || view.has_meshopt_compression)
      fail("asset_buffer_view_bounds");
  }
  for (size_t i=0;i<data.accessors_count;++i) {
    const auto &a=data.accessors[i];
    if (a.is_sparse || !a.buffer_view || !a.count || a.count>maxVertices)
      fail("asset_accessor_unsupported");
    const auto element=cgltf_calc_size(a.type,a.component_type);
    const auto available=a.buffer_view->size;
    if (!element || a.stride<element || a.offset>available ||
        element>available-a.offset ||
        a.count-1>(available-a.offset-element)/a.stride)
      fail("asset_accessor_bounds");
  }
}
AssetImage decodeImage(const cgltf_image &image,const cgltf_options &options) {
  auto freeBuffer=[&](void *p) { if (p) options.memory.free_func(options.memory.user_data,p); };
  std::unique_ptr<void,decltype(freeBuffer)> payload(nullptr,freeBuffer);
  const uint8_t *bytes=nullptr;size_t size=0;
  if (image.uri) {
    const std::string_view uri=image.uri,prefix="data:image/png;base64,";
    if (!uri.starts_with(prefix)) fail("asset_image_embedded_png_required");
    auto encoded=uri.substr(prefix.size());
    if (encoded.empty() || encoded.size()%4 || encoded.size()>12*1024*1024) fail("asset_image_base64");
    const size_t padding=encoded.ends_with("==") ? 2 : encoded.ends_with("=") ? 1 : 0;
    for (size_t i=0;i<encoded.size()-padding;++i) {
      const char c=encoded[i];
      if (!((c>='A' && c<='Z') || (c>='a' && c<='z') || (c>='0' && c<='9') || c=='+' || c=='/'))
        fail("asset_image_base64");
    }
    size=encoded.size()/4*3-padding;
    if (size>8*1024*1024) fail("asset_image_png_header");
    void *decoded=nullptr;
    if (cgltf_load_buffer_base64(&options,size,encoded.data(),&decoded)!=cgltf_result_success) fail("asset_image_base64");
    payload.reset(decoded);bytes=static_cast<const uint8_t *>(decoded);
  } else {
    if (!image.buffer_view || !image.buffer_view->buffer->data) fail("asset_image_embedded_png_required");
    bytes=static_cast<const uint8_t *>(cgltf_buffer_view_data(image.buffer_view));size=image.buffer_view->size;
  }
  static constexpr uint8_t signature[]={137,80,78,71,13,10,26,10};
  if (size<33 || size>8*1024*1024 || !std::equal(std::begin(signature),std::end(signature),bytes) ||
      std::string_view(reinterpret_cast<const char *>(bytes+12),4)!="IHDR") fail("asset_image_png_header");
  auto big=[&](size_t at) { return uint32_t(bytes[at])<<24 | uint32_t(bytes[at+1])<<16 | uint32_t(bytes[at+2])<<8 | bytes[at+3]; };
  const auto width=big(16),height=big(20);
  if (!width || !height || width>2048 || height>2048) fail("asset_image_dimensions");
  bx::DefaultAllocator allocator;
  std::unique_ptr<bimg::ImageContainer,decltype(&bimg::imageFree)> decoded(
      bimg::imageParse(&allocator,bytes,uint32_t(size),bimg::TextureFormat::RGBA8),bimg::imageFree);
  if (!decoded || decoded->m_width!=width || decoded->m_height!=height || decoded->m_numLayers!=1 ||
      decoded->m_numMips!=1 || decoded->m_cubeMap || decoded->m_size!=width*height*4) fail("asset_image_decode");
  const auto *data=static_cast<const uint8_t *>(decoded->m_data);
  return {width,height,{data,data+decoded->m_size}};
}
std::string imageIdentity(const cgltf_image &image) {
  const void *data=nullptr;size_t size=0;char kind='b';
  if (image.uri) {data=image.uri;size=std::strlen(image.uri);kind='u';}
  else if (image.buffer_view && image.buffer_view->buffer->data) {
    data=cgltf_buffer_view_data(image.buffer_view);size=image.buffer_view->size;
  }
  if (!data || !size || size>12*1024*1024) fail("asset_image_embedded_png_required");
  unsigned char digest[CC_SHA256_DIGEST_LENGTH];CC_SHA256(data,CC_LONG(size),digest);
  return std::string(1,kind)+std::string(reinterpret_cast<const char *>(digest),sizeof(digest));
}
std::uint32_t color(const float *rgba, double shade) {
  if (!std::isfinite(rgba[3])) fail("asset_material_nonfinite");
  std::uint32_t result=std::uint32_t(std::clamp(double(rgba[3]),0.,1.)*255)<<24;
  for (int i=0;i<3;++i) {
    if (!std::isfinite(rgba[i])) fail("asset_material_nonfinite");
    result |= std::uint32_t(std::clamp(double(rgba[i])*shade,0.,1.)*255) << (8*i);
  }
  return result;
}
}
AssetDigest assetBytesDigest(std::string_view bytes) noexcept {
  AssetDigest result{};
  // Callers use bounded mesh/descriptor reads. Never silently truncate a length.
  if (bytes.size()>std::numeric_limits<CC_LONG>::max()) return result;
  unsigned char digest[CC_SHA256_DIGEST_LENGTH];
  CC_SHA256(bytes.data(),CC_LONG(bytes.size()),digest);
  constexpr char hex[]="0123456789abcdef";
  for (size_t i=0;i<sizeof(digest);++i) {result[i*2]=hex[digest[i]>>4];result[i*2+1]=hex[digest[i]&15];}
  return result;
}
AssetDigest assetDigestFromHex(std::string_view hex) noexcept {
  AssetDigest result{};
  if (hex.size()!=64 || !std::all_of(hex.begin(),hex.end(),[](char c){return (c>='0'&&c<='9')||(c>='a'&&c<='f');})) return result;
  std::copy(hex.begin(),hex.end(),result.begin());return result;
}
const char *assetLoadStageName(AssetLoadStage stage) noexcept {
  switch(stage) {
  case AssetLoadStage::Definition:return "definition";
  case AssetLoadStage::Open:return "open";
  case AssetLoadStage::Read:return "read";
  case AssetLoadStage::Parse:return "parse";
  case AssetLoadStage::Buffers:return "buffers";
  case AssetLoadStage::Validation:return "validation";
  case AssetLoadStage::Geometry:return "geometry";
  case AssetLoadStage::Images:return "images";
  case AssetLoadStage::Identity:return "identity";
  case AssetLoadStage::Containment:return "containment";
  case AssetLoadStage::Upload:return "upload";
  case AssetLoadStage::Physics:return "physics";
  case AssetLoadStage::Complete:return "complete";
  }
  return "unknown";
}
const char *assetInputIdentity(const AssetLoadContext &context) noexcept {
  if (!context.actualMeshSHA256[0]) return "unavailable";
  if (!context.expectedMeshSHA256[0]) return "unqualified";
  return context.actualMeshSHA256==context.expectedMeshSHA256 ? "match" : "mismatch";
}
MeshAsset loadMeshAsset(const std::filesystem::path &path,const std::vector<MeshNodeBinding> &bindings,
                        AssetLoadContext *context) {
  AssetLoadContext local;
  auto &trace=context ? *context : local;
  trace.stage=AssetLoadStage::Open;trace.actualMeshSHA256={};trace.inputBytes=0;
  struct File { int fd; ~File() { if (fd>=0) ::close(fd); } } file{
      ::open(path.c_str(),O_RDONLY|O_NOFOLLOW|O_NONBLOCK)};
  struct stat status{};
  if (file.fd<0 || ::fstat(file.fd,&status)!=0 || !S_ISREG(status.st_mode)) fail("asset_not_regular");
  if (status.st_size<=0 || uint64_t(status.st_size)>maxFile) fail("asset_file_budget");
  trace.stage=AssetLoadStage::Read;
  std::vector<char> bytes(size_t(status.st_size));
  size_t consumed=0;
  while (consumed<bytes.size()) {
    const auto count=::read(file.fd,bytes.data()+consumed,bytes.size()-consumed);
    if (count<0 && errno==EINTR) continue;
    if (count<=0) fail("asset_read");
    consumed+=size_t(count);
  }
  char extra;
  if (::read(file.fd,&extra,1)!=0) fail("asset_changed_during_read");
  trace.actualMeshSHA256=assetBytesDigest({bytes.data(),bytes.size()});trace.inputBytes=bytes.size();
  trace.stage=AssetLoadStage::Parse;
  Budget budget;
  cgltf_options options{};
  options.memory={allocate,release,&budget};
  cgltf_data *raw=nullptr;
  auto parsed=cgltf_parse(&options,bytes.data(),bytes.size(),&raw);
  std::unique_ptr<cgltf_data,decltype(&cgltf_free)> data(raw,cgltf_free);
  if (parsed!=cgltf_result_success) fail("asset_parse");
  if (data->nodes_count>4096 || data->meshes_count>4096 || data->buffers_count>1024)
    fail("asset_structure_budget");
  std::vector<std::optional<uint32_t>> packedTextures(data->materials_count);
  for(size_t i=0;i<data->materials_count;++i) {
    const auto& material=data->materials[i];
    bool found=false;
    for(size_t j=0;j<material.extensions_count;++j) {
      const auto& extension=material.extensions[j];
      if(!extension.name||std::strcmp(extension.name,"RACER_source_bump_spec")!=0)continue;
      if(found||!extension.data)fail("asset_source_bump_extension");
      found=true;
      const auto texture=sourceBumpTexture(extension.data);
      if(!texture||*texture>=data->textures_count)fail("asset_source_bump_extension");
      if(material.normal_texture.texture)fail("asset_source_bump_conflict");
      packedTextures[i]=*texture;
    }
  }
  trace.stage=AssetLoadStage::Buffers;
  // cgltf's normal file loader is deliberately never reached for external URIs.
  size_t decodedBytes=0;
  for (size_t i=0;i<data->buffers_count;++i) {
    const auto &b=data->buffers[i];
    if (!b.size || b.size>maxFile || decodedBytes>maxFile-b.size ||
        (b.uri && std::string_view(b.uri).find("data:")!=0))
      fail("asset_external_or_large_buffer");
    decodedBytes+=b.size;
  }
  // Classify tangent shape before the generic validator's count checks.
  for(size_t mi=0;mi<data->meshes_count;++mi) for(size_t pi=0;pi<data->meshes[mi].primitives_count;++pi) {
    const auto& primitive=data->meshes[mi].primitives[pi];
    const cgltf_accessor* positions=nullptr;const cgltf_accessor* tangents=nullptr;
    for(size_t ai=0;ai<primitive.attributes_count;++ai) {
      const auto& attribute=primitive.attributes[ai];
      if(attribute.type==cgltf_attribute_type_position)positions=attribute.data;
      if(attribute.type==cgltf_attribute_type_tangent)tangents=attribute.data;
    }
    if(tangents&&(!positions||tangents->type!=cgltf_type_vec4||tangents->component_type!=cgltf_component_type_r_32f||
       tangents->normalized||tangents->is_sparse||tangents->count!=positions->count))fail("asset_tangent_unsupported");
  }
  preflight(*data);
  if (cgltf_load_buffers(&options,data.get(),nullptr)!=cgltf_result_success)
    fail("asset_buffer_decode");
  trace.stage=AssetLoadStage::Validation;
  if (cgltf_validate(data.get())!=cgltf_result_success) fail("asset_validation");
  trace.stage=AssetLoadStage::Geometry;
  if (!data->scenes_count) fail("asset_scene_missing");
  auto *scene=data->scene ? data->scene : &data->scenes[0];
  std::vector<cgltf_node *> pending(scene->nodes,scene->nodes+scene->nodes_count);
  std::unordered_set<cgltf_node *> visited;
  MeshAsset result;
  result.sourceSHA256=trace.actualMeshSHA256.data();
  std::unordered_map<uint32_t,MeshNodeBinding> nodeBindings;
  for (const auto &binding:bindings) {
    if (binding.node>=data->nodes_count || binding.wheel< -1 || binding.wheel>3 ||
        !nodeBindings.emplace(binding.node,binding).second) fail("asset_node_binding");
    for (auto value:binding.pivot) if (!std::isfinite(value)) fail("asset_node_binding");
  }
  std::unordered_set<uint32_t> boundNodes;
  std::unordered_map<const cgltf_image *,std::array<int,3>> imageIndices;
  size_t imageBytes=0;
  std::unordered_map<std::string,int> imageContentIndices;
  auto loadTexture=[&](const cgltf_texture_view& view,const cgltf_accessor* uv,ImageRole role,int& wrapU,int& wrapV) {
    auto *texture=view.texture;
    if(!texture||!uv||view.texcoord!=0||view.has_transform||!texture->image)
      fail("asset_texture_unsupported");
    if(texture->sampler) {
      wrapU=int(texture->sampler->wrap_s);wrapV=int(texture->sampler->wrap_t);
      for(auto mode:{wrapU,wrapV})if(mode!=10497&&mode!=33071&&mode!=33648)fail("asset_sampler_unsupported");
    }
    auto [entry,inserted]=imageIndices.try_emplace(texture->image,std::array<int,3>{-1,-1,-1});
    auto& index=entry->second[size_t(role)];
    if(index>=0)return index;
    trace.stage=AssetLoadStage::Images;
    // The same encoded image can serve three semantic roles, whose mip filters
    // differ. Keep those GPU images separate while deduplicating within a role.
    const auto identity=imageIdentity(*texture->image)+char('0'+int(role));
    if(const auto existing=imageContentIndices.find(identity);existing!=imageContentIndices.end())index=existing->second;
    else {
      if(result.images.size()>=128)fail("asset_image_budget");
      auto image=decodeImage(*texture->image,options);image.role=role;
      if(imageBytes+image.rgba.size()>32*1024*1024)fail("asset_image_budget");
      imageBytes+=image.rgba.size();index=int(result.images.size());imageContentIndices[identity]=index;
      result.images.push_back(std::move(image));
    }
    trace.stage=AssetLoadStage::Geometry;return index;
  };
  result.minimum.fill(std::numeric_limits<float>::infinity());
  result.maximum.fill(-std::numeric_limits<float>::infinity());
  while (!pending.empty()) {
    auto *node=pending.back();pending.pop_back();
    if (!visited.insert(node).second) fail("asset_repeated_node");
    if (visited.size()>4096) fail("asset_node_budget");
    for (size_t c=0;c<node->children_count;++c) pending.push_back(node->children[c]);
    if (!node->mesh) continue;
    const auto nodeIndex=uint32_t(node-data->nodes);
    auto binding=nodeBindings.find(nodeIndex);
    if (!bindings.empty() && binding==nodeBindings.end()) fail("asset_unbound_mesh");
    if (binding!=nodeBindings.end()) boundNodes.insert(nodeIndex);
    if (node->skin || node->weights_count) fail("asset_skin_or_morph_unsupported");
    size_t depth=0;
    for (auto *parent=node;parent;parent=parent->parent)
      if (++depth>64) fail("asset_transform_depth");
    float matrix[16];cgltf_node_transform_world(node,matrix);
    for (float v:matrix) if (!std::isfinite(v)) fail("asset_transform_nonfinite");
    for (size_t p=0;p<node->mesh->primitives_count;++p) {
      const auto &primitive=node->mesh->primitives[p];
      if (primitive.type!=cgltf_primitive_type_triangles || primitive.targets_count || primitive.has_draco_mesh_compression)
        fail("asset_primitive_unsupported");
      const cgltf_accessor *position=nullptr,*uv=nullptr,*normal=nullptr,*occlusion=nullptr,*tangent=nullptr;
      for (size_t a=0;a<primitive.attributes_count;++a) {
        if (primitive.attributes[a].type==cgltf_attribute_type_position) position=primitive.attributes[a].data;
        if (primitive.attributes[a].type==cgltf_attribute_type_normal) normal=primitive.attributes[a].data;
        if (primitive.attributes[a].type==cgltf_attribute_type_tangent) tangent=primitive.attributes[a].data;
        if(primitive.attributes[a].type==cgltf_attribute_type_custom && primitive.attributes[a].name &&
           std::strcmp(primitive.attributes[a].name,"_RACER_OCCLUSION")==0) occlusion=primitive.attributes[a].data;
        if (primitive.attributes[a].type==cgltf_attribute_type_texcoord && primitive.attributes[a].index==0)
          uv=primitive.attributes[a].data;
      }
      if (!position || position->type!=cgltf_type_vec3 || position->is_sparse)
        fail("asset_positions_unsupported");
      if (primitive.indices && primitive.indices->is_sparse) fail("asset_indices_unsupported");
      if (uv && (uv->type!=cgltf_type_vec2 || uv->count!=position->count)) fail("asset_uv_unsupported");
      if (normal && (normal->type!=cgltf_type_vec3 || normal->count!=position->count || normal->is_sparse)) fail("asset_normal_unsupported");
      if(occlusion && (occlusion->type!=cgltf_type_scalar || occlusion->count!=position->count || occlusion->is_sparse))
        fail("asset_occlusion_unsupported");
      size_t count=primitive.indices ? primitive.indices->count : position->count;
      if (count%3 || count>maxVertices-result.triangles.size()) fail("asset_triangle_budget");
      float rgba[4]={1,1,1,1};
      AssetSection section{uint32_t(result.triangles.size()),uint32_t(count)};
      if(primitive.material) {
        const auto packed=packedTextures[size_t(primitive.material-data->materials)];
        if(packed) {
          if(!uv||!normal||!tangent)fail("asset_source_bump_frame");
          // The recovered gradient kernel uses source basis magnitudes. Only
          // rigid node transforms preserve them, including mirrored frames.
          if(std::abs(matrix[3])>1e-6||std::abs(matrix[7])>1e-6||std::abs(matrix[11])>1e-6||std::abs(matrix[15]-1)>1e-6)
            fail("asset_source_bump_transform");
          for(unsigned a=0;a<3;++a)for(unsigned b=0;b<3;++b) {
            double dot=0;for(unsigned k=0;k<3;++k)dot+=double(matrix[a*4+k])*matrix[b*4+k];
            if(std::abs(dot-(a==b?1.:0.))>1e-5)fail("asset_source_bump_transform");
          }
          section.sourceBump=true;
          cgltf_texture_view detail{};detail.texture=&data->textures[*packed];
          section.normalImage=loadTexture(detail,uv,ImageRole::PackedHeightSpec,section.normalWrapU,section.normalWrapV);
          result.texturesPresent=true;
        }
      }
      section.metallic=1;
      if (binding!=nodeBindings.end()) {
        section.wheel=binding->second.wheel;section.rolling=binding->second.rolling;
      }
      if(primitive.material && primitive.material->has_clearcoat) {
        section.clearcoat=primitive.material->clearcoat.clearcoat_factor;
        section.coatRoughness=primitive.material->clearcoat.clearcoat_roughness_factor;
        for(float factor:{section.clearcoat,section.coatRoughness})
          if(!std::isfinite(factor) || factor<0 || factor>1) fail("asset_material_factor");
      }
      if (primitive.material) {
        section.mask=primitive.material->alpha_mode==cgltf_alpha_mode_mask;
        section.blend=primitive.material->alpha_mode==cgltf_alpha_mode_blend;
        section.alphaCutoff=primitive.material->alpha_cutoff;
        if (!std::isfinite(section.alphaCutoff) || section.alphaCutoff<0 || section.alphaCutoff>1) fail("asset_alpha_cutoff");
        const auto& detail=primitive.material->normal_texture;
        if(detail.texture) {
          if(!std::isfinite(detail.scale)||std::abs(detail.scale)>8)fail("asset_normal_scale");
          section.normalScale=detail.scale;
          section.normalImage=loadTexture(detail,uv,ImageRole::Normal,section.normalWrapU,section.normalWrapV);
          result.texturesPresent=true;
        }
      }
      if (primitive.material && primitive.material->has_pbr_metallic_roughness) {
        const auto &material=primitive.material->pbr_metallic_roughness;
        section.roughness=material.roughness_factor; section.metallic=material.metallic_factor;
        for(float factor:{section.roughness,section.metallic})
          if(!std::isfinite(factor) || factor<0 || factor>1) fail("asset_material_factor");
        std::copy_n(material.base_color_factor,4,rgba);
        result.texturesPresent |= material.base_color_texture.texture!=nullptr;
        if(material.base_color_texture.texture)
          section.image=loadTexture(material.base_color_texture,uv,ImageRole::Color,section.wrapU,section.wrapV);
      }
      if(!std::isfinite(rgba[3]) || rgba[3]<0 || rgba[3]>1) fail("asset_material_factor");
      const float opacity=rgba[3];rgba[3]=1;
      if(primitive.material && primitive.material->name) {
        if(const auto look=vehicleLook(trace.actualMeshSHA256.data(),primitive.material->name,section.wheel)) {
          section.roughness=look->roughness;section.metallic=look->metallic;section.clearcoat=look->clearcoat;
        }
      }
      result.sections.push_back(section);
      for (size_t index=0;index<count;index+=3) {
        float point[3][3],texcoord[3][2]{},ambient[3]={1,1,1}; double normals[3][3]{},tangents[3][4]{};
        for (int corner=0;corner<3;++corner) {
          auto vertex=primitive.indices ? cgltf_accessor_read_index(primitive.indices,index+corner) : index+corner;
          float value[3];
          if (vertex>=position->count || !cgltf_accessor_read_float(position,vertex,value,3)) fail("asset_vertex_index");
          if(occlusion && (!cgltf_accessor_read_float(occlusion,vertex,&ambient[corner],1) ||
             !std::isfinite(ambient[corner]) || ambient[corner]<0 || ambient[corner]>1)) fail("asset_occlusion_invalid");
          if(tangent) {
            float local[4];
            if(!cgltf_accessor_read_float(tangent,vertex,local,4))fail("asset_tangent_invalid");
            for(float component:local)if(!std::isfinite(component))fail("asset_tangent_invalid");
            if(local[3]!=1&&local[3]!=-1)fail("asset_tangent_invalid");
            // Without NORMAL glTF requires ignoring the supplied frame.
            if(normal) {
              double m[16];std::copy_n(matrix,16,m);
              const double det=m[0]*(m[5]*m[10]-m[9]*m[6])-m[4]*(m[1]*m[10]-m[9]*m[2])+m[8]*(m[1]*m[6]-m[5]*m[2]);
              if(!std::isfinite(det)||std::abs(det)<=1e-20)fail("asset_tangent_transform");
              for(unsigned axis=0;axis<3;++axis)
                tangents[corner][axis]=m[axis]*local[0]+m[4+axis]*local[1]+m[8+axis]*local[2];
              tangents[corner][3]=local[3]*(det<0?-1:1);
            }
          }
          if(normal) {
            float local[3];
            if(!cgltf_accessor_read_float(normal,vertex,local,3)) fail("asset_normal_invalid");
            for(float component:local) if(!std::isfinite(component)) fail("asset_normal_invalid");
            // Inverse transpose, expressed as cofactors so nonuniform node
            // scale preserves the surface direction. Normalize below.
            double transform[16];std::copy_n(matrix,16,transform);
            const double det=transform[0]*(transform[5]*transform[10]-transform[9]*transform[6])-
              transform[4]*(transform[1]*transform[10]-transform[9]*transform[2])+transform[8]*(transform[1]*transform[6]-transform[5]*transform[2]);
            if(std::abs(det)>1e-20) {
              normals[corner][0]=((transform[5]*transform[10]-transform[9]*transform[6])*local[0]+(transform[9]*transform[2]-transform[1]*transform[10])*local[1]+(transform[1]*transform[6]-transform[5]*transform[2])*local[2])/det;
              normals[corner][1]=((transform[8]*transform[6]-transform[4]*transform[10])*local[0]+(transform[0]*transform[10]-transform[8]*transform[2])*local[1]+(transform[4]*transform[2]-transform[0]*transform[6])*local[2])/det;
              normals[corner][2]=((transform[4]*transform[9]-transform[8]*transform[5])*local[0]+(transform[8]*transform[1]-transform[0]*transform[9])*local[1]+(transform[0]*transform[5]-transform[4]*transform[1])*local[2])/det;
            }
          }
          if (uv && (!cgltf_accessor_read_float(uv,vertex,texcoord[corner],2) ||
                     !std::isfinite(texcoord[corner][0]) || !std::isfinite(texcoord[corner][1])))
            fail("asset_uv_invalid");
          for (int axis=0;axis<3;++axis) {
            point[corner][axis]=matrix[axis]*value[0]+matrix[4+axis]*value[1]+matrix[8+axis]*value[2]+matrix[12+axis];
            if (!std::isfinite(point[corner][axis]) || std::abs(point[corner][axis])>10000)
              fail("asset_position_nonfinite_or_range");
            result.minimum[axis]=std::min(result.minimum[axis],point[corner][axis]);
            result.maximum[axis]=std::max(result.maximum[axis],point[corner][axis]);
            if (section.wheel>=0) point[corner][axis]-=binding->second.pivot[axis];
          }
        }
        double ax=point[1][0]-point[0][0],ay=point[1][1]-point[0][1],az=point[1][2]-point[0][2];
        double bx=point[2][0]-point[0][0],by=point[2][1]-point[0][1],bz=point[2][2]-point[0][2];
        double nx=ay*bz-az*by,ny=az*bx-ax*bz,nz=ax*by-ay*bx;
        double length=std::sqrt(nx*nx+ny*ny+nz*nz);
        for (unsigned corner=0;corner<3;++corner) {
          double magnitude=std::hypot(normals[corner][0],normals[corner][1],normals[corner][2]);
          if(section.sourceBump) {
            const double tangentLength=std::hypot(tangents[corner][0],tangents[corner][1],tangents[corner][2]);
            double dot=0;for(unsigned a=0;a<3;++a)dot+=normals[corner][a]*tangents[corner][a];
            if(!std::isfinite(magnitude)||!std::isfinite(tangentLength)||magnitude<.98||magnitude>1.02||
               tangentLength<.98||tangentLength>1.02||std::abs(dot)>.05*magnitude*tangentLength)
              fail("asset_source_bump_frame");
          } else {
            if(magnitude<1e-12) {
              normals[corner][0]=length>1e-12?float(nx/length):0;
              normals[corner][1]=length>1e-12?float(ny/length):1;
              normals[corner][2]=length>1e-12?float(nz/length):0;
            } else for(double &component:normals[corner]) component/=magnitude;
            if(tangent&&normal) {
              const double originalLength=std::hypot(tangents[corner][0],tangents[corner][1],tangents[corner][2]);
              double projection=0;
              for(unsigned axis=0;axis<3;++axis)projection+=normals[corner][axis]*tangents[corner][axis];
              for(unsigned axis=0;axis<3;++axis)tangents[corner][axis]-=projection*normals[corner][axis];
              const double tangentLength=std::hypot(tangents[corner][0],tangents[corner][1],tangents[corner][2]);
              if(!std::isfinite(tangentLength)||!std::isfinite(originalLength)||originalLength==0||tangentLength<=originalLength*1e-12)fail("asset_tangent_invalid");
              for(unsigned axis=0;axis<3;++axis)tangents[corner][axis]/=tangentLength;
            }
          }
          result.triangles.push_back({point[corner][0],point[corner][1],point[corner][2],
            color(rgba,1),texcoord[corner][0],texcoord[corner][1],float(normals[corner][0]),float(normals[corner][1]),float(normals[corner][2]),ambient[corner],opacity,
            float(tangents[corner][0]),float(tangents[corner][1]),float(tangents[corner][2]),float(tangents[corner][3])});
        }
      }
    }
  }
  if (result.triangles.empty()) fail("asset_empty_scene");
  if (boundNodes.size()!=bindings.size()) fail("asset_unused_node_binding");
  trace.stage=AssetLoadStage::Complete;
  return result;
}
}
