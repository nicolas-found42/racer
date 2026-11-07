#include "material_shader.h"
#include "fs_debugdraw_fill_texture.bin.h"
#include <algorithm>
#include <iostream>
#include <limits>
void require(bool value,const char *message) {if(!value)throw std::runtime_error(message);}
template<class F>void rejects(F action) {try{action();}catch(const std::invalid_argument &){return;}throw std::runtime_error("malformed shader accepted");}
uint32_t length(const std::vector<uint8_t> &bytes,size_t source) {
  uint32_t n=0;for(unsigned i=0;i<4;++i)n|=uint32_t(bytes[source-4+i])<<(8*i);return n;
}
int main() try {
  const std::vector<uint8_t> original(std::begin(fs_debugdraw_fill_texture_mtl),std::end(fs_debugdraw_fill_texture_mtl));
  const std::string old(reinterpret_cast<const char *>(original.data()),original.size());const auto at=old.find("#include <metal_stdlib>");require(at>=4 && at<original.size(),"pinned source exists");
  for(float cutoff:{0.f,.247058824f,1.f}) {
    const auto adapted=racer::alphaMaskShader(original.data(),original.size(),cutoff);
    const auto count=length(adapted,at);const std::string source(reinterpret_cast<const char *>(adapted.data()+at),count);
    require(source.find("discard_fragment();")!=std::string::npos,"alpha cutoff emitted");
    require(source.find("out.bgfx_FragData0.a < ")<source.find("return out;"),"discard follows texture/vertex alpha and precedes output");
    require(std::equal(original.begin(),original.begin()+at-4,adapted.begin()),"reflection/interface prefix unchanged");
    require(std::equal(original.begin()+at+length(original,at),original.end(),adapted.begin()+at+count,adapted.end()),"NUL and reflection trailer preserved");
    require(adapted[at+count]==0,"source terminator preserved");
    if(cutoff==0)require(source.find("< 0.000000000")!=std::string::npos,"zero cutoff exact");
    if(cutoff==1)require(source.find("< 1.000000000")!=std::string::npos,"one cutoff exact");
  }
  rejects([&]{racer::alphaMaskShader(nullptr,0,.5);});
  for(float bad:{-.1f,1.1f,std::numeric_limits<float>::quiet_NaN()})rejects([&]{racer::alphaMaskShader(original.data(),original.size(),bad);});
  auto broken=original;for(unsigned i=0;i<4;++i)broken[at-4+i]=255;
  rejects([&]{racer::alphaMaskShader(broken.data(),broken.size(),.5);});
  broken=original;broken[at+length(original,at)]=1;
  rejects([&]{racer::alphaMaskShader(broken.data(),broken.size(),.5);});
  broken=original;const auto marker=old.find("    return out;");broken[marker]='X';
  rejects([&]{racer::alphaMaskShader(broken.data(),broken.size(),.5);});
  std::cout<<"PASS: pinned Metal alpha-cutoff insertion, boundaries, interface/trailer preservation, malformed input rejection\n";
}catch(const std::exception &e){std::cerr<<"FAIL: "<<e.what()<<'\n';return 1;}
