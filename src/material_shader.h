#pragma once
#include <cmath>
#include <cstdint>
#include <cstring>
#include <iomanip>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
namespace racer {
// The pinned bgfx Metal container embeds source MSL, not opaque machine code.
// Preserve its reflection/interface and replace only the bounded source block.
// No new shader binding is introduced. The backend compiles the resulting MSL.
inline std::vector<uint8_t> alphaMaskShader(const uint8_t *input,size_t size,float cutoff) {
  if (!input || size>65536 || !std::isfinite(cutoff) || cutoff<0 || cutoff>1)
    throw std::invalid_argument("material_shader_input");
  const std::string bytes(reinterpret_cast<const char *>(input),size);
  const auto start=bytes.find("#include <metal_stdlib>");
  if (start==std::string::npos || start<4) throw std::invalid_argument("material_shader_source");
  uint32_t length=0;
  for (unsigned i=0;i<4;++i) length|=uint32_t(input[start-4+i])<<(i*8);
  if (length>size-start || start+length>=size || input[start+length]!=0)
    throw std::invalid_argument("material_shader_bounds");
  auto source=bytes.substr(start,length);
  const std::string marker="    return out;";
  const auto at=source.find(marker);
  if (at==std::string::npos || source.find(marker,at+1)!=std::string::npos ||
      source.find("out.bgfx_FragData0 = s_texColor.sample")==std::string::npos)
    throw std::invalid_argument("material_shader_interface");
  std::ostringstream threshold;threshold<<std::setprecision(9)<<std::fixed<<cutoff;
  source.insert(at,"    if (out.bgfx_FragData0.a < "+threshold.str()+") discard_fragment();\n");
  std::vector<uint8_t> result(input,input+start);
  const auto newLength=uint32_t(source.size());
  for (unsigned i=0;i<4;++i) result[start-4+i]=uint8_t(newLength>>(i*8));
  result.insert(result.end(),source.begin(),source.end());
  result.insert(result.end(),input+start+length,input+size);
  return result;
}
}
