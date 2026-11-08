#include "texture_upload.h"
#include <iostream>
#include <array>
void require(bool v,const char* message){if(!v)throw std::runtime_error(message);}
namespace mock {
std::vector<std::vector<uint8_t>> uploads;
std::vector<std::array<uint16_t,3>> levels;
bool live=false,failCreate=false;unsigned attempts=0,destroys=0,failUpdate=0;
}
namespace bgfx {
const Memory* copy(const void* data,uint32_t size){static Memory memory;memory.data=const_cast<uint8_t*>(static_cast<const uint8_t*>(data));memory.size=size;return &memory;}
TextureHandle createTexture2D(uint16_t width,uint16_t height,bool mips,uint16_t layers,TextureFormat::Enum format,uint64_t flags,const Memory*,uint64_t){
  ++mock::attempts;require(!mock::live&&width&&height&&mips&&layers==1&&format==TextureFormat::RGBA8&&flags==0,"asset texture allocation contract");
  mock::uploads.clear();mock::levels.clear();if(mock::failCreate)return BGFX_INVALID_HANDLE;mock::live=true;return {7};
}
void updateTexture2D(TextureHandle h,uint16_t layer,uint8_t level,uint16_t x,uint16_t y,uint16_t width,uint16_t height,const Memory* memory,uint16_t){
  require(mock::live&&h.idx==7&&layer==0&&x==0&&y==0&&memory->size==uint32_t(width)*height*4,"mip upload dimensions and ownership");
  if(mock::failUpdate&&mock::uploads.size()+1==mock::failUpdate)throw std::runtime_error("mock_upload_failure");
  mock::levels.push_back({level,width,height});mock::uploads.emplace_back(memory->data,memory->data+memory->size);
}
void destroy(TextureHandle h){require(mock::live&&h.idx==7,"asset texture released exactly once");mock::live=false;++mock::destroys;}
}
int main()try{
  const racer::AssetImage checker{2,2,{0,0,0,0,255,255,255,255,255,255,255,255,0,0,0,0}};
  const auto mean=racer::colorMip(checker);
  require(mean.width==1&&mean.height==1,"mip reduces dimensions");
  require(mean.rgba==std::vector<uint8_t>{186,186,186,128},"linear-light mean and linear alpha coverage");
  const racer::AssetImage odd{3,1,{0,0,0,0,0,0,0,0,255,255,255,255}};
  require(racer::colorMip(odd).rgba==std::vector<uint8_t>{155,155,155,85},"odd final column contributes full area");
  auto vertical=odd;vertical.width=1;vertical.height=3;
  require(racer::colorMip(vertical).rgba==std::vector<uint8_t>{155,155,155,85},"odd final row contributes full area");
  racer::AssetImage corner{5,3,std::vector<uint8_t>(60,0)};
  for(unsigned c=0;c<4;++c)corner.rgba[56+c]=255;
  const auto cornerMip=racer::colorMip(corner);
  require(cornerMip.width==2&&cornerMip.height==1&&cornerMip.rgba[0]==0&&cornerMip.rgba[4]==102&&cornerMip.rgba[7]==34,"odd two-axis footprint retains final corner");
  auto strip=racer::AssetImage{1,4,{40,90,120,255,40,90,120,255,40,90,120,255,40,90,120,255}};
  for(int i=0;i<3;++i){strip=racer::colorMip(strip);require(strip.rgba[0]==40&&strip.rgba[1]==90&&strip.rgba[2]==120&&strip.rgba[3]==255,"constant color retained through thin mip chain");}
  for(auto bad:{racer::AssetImage{},racer::AssetImage{4096,1,{}},racer::AssetImage{2,2,{0}}}){
    bool rejected=false;try{racer::colorMip(bad);}catch(const std::invalid_argument&){rejected=true;}require(rejected,"invalid image rejected before mip reads");
  }
  const racer::AssetImage neutral{2,2,{128,128,255,255,128,128,255,255,128,128,255,255,128,128,255,255},racer::ImageRole::Normal};
  const auto neutralMip=racer::normalMip(neutral);
  require(neutralMip.role==racer::ImageRole::Normal&&neutralMip.rgba==std::vector<uint8_t>{128,128,255,255},"neutral normal and image role retained");
  auto checkDirection=[](const racer::AssetImage& image,unsigned pixel,double x,double y,double z) {
    const double nx=image.rgba[pixel*4]/127.5-1,ny=image.rgba[pixel*4+1]/127.5-1,nz=image.rgba[pixel*4+2]/127.5-1;
    const double length=std::hypot(nx,ny,nz),expected=std::hypot(x,y,z);
    require(std::abs(length-1)<.01,"encoded mip normal unit length within byte quantization");
    require((nx*x+ny*y+nz*z)/(length*expected)>.9999,"mip normal direction matches independent expected vector");
  };
  const racer::AssetImage mixed{2,1,{255,128,128,0,128,255,128,255},racer::ImageRole::Normal};
  const auto diagonal=racer::normalMip(mixed);
  require(diagonal.rgba==std::vector<uint8_t>{218,218,128,128},"known linear-vector average differs from gamma color filtering");
  checkDirection(diagonal,0,1,1,0);
  const racer::AssetImage cancel{2,1,{255,128,128,40,0,127,127,80},racer::ImageRole::Normal};
  require(racer::normalMip(cancel).rgba==std::vector<uint8_t>{128,128,255,60},"opposite vectors cancel to positive-Z with linear alpha");
  racer::AssetImage oddNormal{3,1,{255,128,128,0,255,128,128,0,128,255,128,255},racer::ImageRole::Normal};
  const auto oddNormalMip=racer::normalMip(oddNormal);
  checkDirection(oddNormalMip,0,2+1./255,1+2./255,3./255);
  require(oddNormalMip.rgba[3]==85,"odd normal final column contributes alpha and vector area");
  oddNormal.width=1;oddNormal.height=3;
  require(racer::normalMip(oddNormal).rgba==oddNormalMip.rgba,"odd normal final row has identical weights");
  racer::AssetImage fractional{5,1,{255,128,128,0,255,128,128,0,128,255,128,255,255,128,128,0,255,128,128,0},racer::ImageRole::Normal};
  const auto fractionalMip=racer::normalMip(fractional);
  require(fractionalMip.width==2&&fractionalMip.role==racer::ImageRole::Normal,"fractional normal mip dimensions and role");
  require(std::vector<uint8_t>(fractionalMip.rgba.begin(),fractionalMip.rgba.begin()+4)==
          std::vector<uint8_t>(fractionalMip.rgba.begin()+4,fractionalMip.rgba.end()),"middle texel splits equally between fractional footprints");
  checkDirection(fractionalMip,0,2+.5/255,.5+2./255,2.5/255);
  require(fractionalMip.rgba[3]==51,"half-covered alpha texel contributes one fifth");
  auto chain=neutral;
  for(int i=0;i<3;++i){chain=racer::normalMip(chain);require(chain.role==racer::ImageRole::Normal&&chain.rgba==std::vector<uint8_t>{128,128,255,255},"normal role and neutral direction survive terminal mip chain");}
  for(auto bad:{racer::AssetImage{},racer::AssetImage{4096,1,{}},racer::AssetImage{2,2,{0}}}){
    bool rejected=false;try{racer::normalMip(bad);}catch(const std::invalid_argument&){rejected=true;}require(rejected,"invalid normal image rejected before reads");
  }
  const racer::AssetImage packed{3,1,{0,30,100,0,60,90,160,60,240,240,250,255},racer::ImageRole::PackedHeightSpec};
  const auto packedMean=racer::packedMip(packed);
  require(packedMean.role==racer::ImageRole::PackedHeightSpec&&packedMean.rgba==std::vector<uint8_t>{100,120,170,105},"packed odd extent averages four independent linear lanes, including alpha");
  auto packedColumn=packed;packedColumn.width=1;packedColumn.height=3;
  require(racer::packedMip(packedColumn).rgba==packedMean.rgba,"packed odd row same area weights");
  auto packedFractional=fractional;packedFractional.role=racer::ImageRole::PackedHeightSpec;
  require(racer::packedMip(packedFractional).rgba==std::vector<uint8_t>{230,153,128,51,230,153,128,51},"packed fractional coverage does not normalize RGB or gamma encode");
  auto packedTexture=racer::uploadAssetTexture(packed);
  require(mock::uploads[0]==packed.rgba&&mock::uploads[1]==packedMean.rgba,"packed upload preserves source bytes and chooses linear RGBA mips");bgfx::destroy(packedTexture);
  for(auto bad:{racer::AssetImage{},racer::AssetImage{3,1,{0}}}){
    bool rejected=false;try{racer::packedMip(bad);}catch(const std::invalid_argument&){rejected=true;}require(rejected,"packed invalid dimensions reject");
  }
  auto uploaded=racer::uploadAssetTexture(mixed);
  require(mock::levels==std::vector<std::array<uint16_t,3>>{{0,2,1},{1,1,1}}&&mock::uploads[0]==mixed.rgba&&mock::uploads[1]==std::vector<uint8_t>{218,218,128,128},"normal uploader retains base and uses linear vector terminal mip");
  bgfx::destroy(uploaded);
  uploaded=racer::uploadAssetTexture(checker);
  require(mock::uploads[1]==std::vector<uint8_t>{186,186,186,128},"color uploader retains existing gamma mip path");bgfx::destroy(uploaded);
  const auto before=mock::destroys;mock::failUpdate=2;bool failed=false;
  try{racer::uploadAssetTexture(mixed);}catch(const std::runtime_error&){failed=true;}
  require(failed&&!mock::live&&mock::destroys==before+1,"partial mip upload failure releases texture");mock::failUpdate=0;
  mock::failCreate=true;failed=false;
  try{racer::uploadAssetTexture(mixed);}catch(const std::runtime_error&){failed=true;}
  require(failed&&!mock::live&&mock::destroys==before+1,"invalid allocation is not destroyed twice");mock::failCreate=false;
  auto badRole=checker;badRole.role=static_cast<racer::ImageRole>(99);failed=false;
  try{racer::uploadAssetTexture(badRole);}catch(const std::invalid_argument&){failed=true;}require(failed,"unsupported role rejected before allocation");
  const auto attempts=mock::attempts;failed=false;
  try{racer::uploadAssetTexture({4096,1,{}});}catch(const std::invalid_argument&){failed=true;}
  require(failed&&mock::attempts==attempts,"invalid image rejected before GPU allocation");
  std::cout<<"PASS: color/normal area mips, vector direction/cancellation/role, upload branch/levels and failure cleanup\n";
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
