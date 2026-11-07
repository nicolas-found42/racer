#pragma once
#include <charconv>
#include <cstdint>
#include <optional>
#include <string_view>

namespace racer {
// Deliberately narrow custom extension grammar; not a general JSON parser.
// Unknown/duplicate fields, escapes, signs, fractions and trailing data reject.
inline std::optional<uint32_t> sourceBumpTexture(std::string_view json) {
  if(json.size()>128)return std::nullopt;
  size_t at=0;
  auto space=[&]{while(at<json.size()&&(json[at]==' '||json[at]=='\t'||json[at]=='\n'||json[at]=='\r'))++at;};
  auto token=[&](std::string_view value){space();if(json.substr(at,value.size())!=value)return false;at+=value.size();return true;};
  if(!token("{")||!token("\"texture\"")||!token(":"))return std::nullopt;
  space();const size_t begin=at;
  while(at<json.size()&&json[at]>='0'&&json[at]<='9')++at;
  if(at==begin||(at-begin>1&&json[begin]=='0'))return std::nullopt;
  uint32_t index=0;
  const auto parsed=std::from_chars(json.data()+begin,json.data()+at,index);
  if(parsed.ec!=std::errc{}||parsed.ptr!=json.data()+at||!token("}"))return std::nullopt;
  space();if(at!=json.size())return std::nullopt;
  return index;
}
}
