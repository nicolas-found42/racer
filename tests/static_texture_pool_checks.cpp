#include "static_texture_pool.h"
#include <iostream>
#include <set>

namespace mock {
int calls=0,fail=0;bool raises=false;uint16_t next=1;std::set<uint16_t> live;
bgfx::TextureHandle upload(const racer::AssetImage&) {
  ++calls;if(calls==fail){if(raises)throw std::runtime_error("upload_failed");return BGFX_INVALID_HANDLE;}
  const auto id=next++;live.insert(id);return {id};
}
void reset(){if(!live.empty())throw std::runtime_error("leaked texture");calls=fail=0;raises=false;next=1;}
}
namespace bgfx {void destroy(TextureHandle h){if(mock::live.erase(h.idx)!=1)throw std::runtime_error("double texture destroy");}}
void require(bool value,const char* why){if(!value)throw std::runtime_error(why);}
template<class F>void rejected(F&& f){bool threw=false;try{f();}catch(const std::exception&){threw=true;}require(threw,"expected rejection");}
racer::AssetImage image(unsigned w=2,unsigned h=2,uint8_t byte=70,racer::ImageRole role=racer::ImageRole::Color){return {w,h,std::vector<uint8_t>(size_t(w)*h*4,byte),role};}

int main()try {
  mock::reset();
  racer::TextureRef survivor;
  {
    racer::StaticTexturePool pool(mock::upload,128);
    auto a=pool.acquire({image(),image()});auto b=pool.acquire({image()});
    require(a[0]==a[1]&&a[0]==b[0]&&mock::calls==1&&pool.decodedBytes()==16,"same pixels share across assets and within asset");
    auto distinct=pool.acquire({image(1,4),image(2,2,71),image(2,2,70,racer::ImageRole::Normal)});
    require(pool.textureCount()==4&&pool.decodedBytes()==64&&mock::calls==4,"dimensions, actual pixels and normal role distinguish uploads");
    require(distinct[0]!=a[0]&&distinct[1]!=a[0]&&distinct[2]!=a[0],"no cross-role or shape alias");
    survivor=a[0];a.clear();b.clear();require(mock::live.size()==4,"pool owns cache after mesh release");
  }
  require(mock::live.size()==1,"shared mesh reference survives pool release");survivor.reset();require(mock::live.empty(),"final owner releases exactly once");
  mock::reset();
  {
    racer::StaticTexturePool pool(mock::upload,16);auto a=pool.acquire({image()});
    rejected([&]{pool.acquire({image(2,2,72),image(2,2,73)});});
    require(mock::calls==1&&pool.decodedBytes()==16&&pool.textureCount()==1,"budget rejects whole incoming batch before uploading");
    auto alias=pool.acquire({image(),image()});require(mock::calls==1&&alias[0]==a[0],"cache aliases need no remaining budget");
    rejected([&]{pool.acquire({image(0,1)});});auto bad=image();bad.rgba.pop_back();rejected([&]{pool.acquire({bad});});
    rejected([&]{pool.acquire(std::vector<racer::AssetImage>(129,image(1,1)));});
    require(mock::calls==1,"invalid image rejected before GPU work");
  }
  for(bool raises:{false,true}) {
    mock::reset();mock::fail=2;mock::raises=raises;
    {
      racer::StaticTexturePool pool(mock::upload,64);
      rejected([&]{pool.acquire({image(),image(2,2,71)});});
      require(pool.decodedBytes()==16&&pool.textureCount()==1&&mock::live.size()==1,"partial failure retains only successful owned upload");
      mock::fail=0;auto retry=pool.acquire({image(),image(2,2,71)});
      require(mock::calls==3&&pool.decodedBytes()==32&&retry.size()==2,"retry reuses successful prefix and uploads missing image");
    }
    require(mock::live.empty(),"failure and retry release all owners");
  }
  mock::reset();
  {
    racer::StaticTexturePool pool(mock::upload,48);
    auto roles=pool.acquire({image(),image(2,2,70,racer::ImageRole::Normal),image(2,2,70,racer::ImageRole::PackedHeightSpec)});
    require(pool.textureCount()==3&&pool.decodedBytes()==48&&roles[0]!=roles[1]&&roles[1]!=roles[2]&&roles[0]!=roles[2],"three semantic roles cannot alias identical pixels");
    auto badRole=image();badRole.role=static_cast<racer::ImageRole>(99);rejected([&]{pool.acquire({badRole});});
    auto alias=pool.acquire({image(2,2,70,racer::ImageRole::PackedHeightSpec)});
    require(alias[0]==roles[2]&&mock::calls==3,"packed role cache hit needs no budget");
    rejected([&]{pool.acquire({image(2,2,71,racer::ImageRole::PackedHeightSpec)});});
    require(mock::calls==3,"packed role bytes obey unchanged pool cap");
  }
  rejected([]{racer::StaticTexturePool pool(nullptr);});
  std::cout<<"PASS: static pixel/shape/role sharing, unique-byte preflight, shared ownership, upload failure/throw cleanup and retry\n";
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
