#pragma once
#include <array>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <cerrno>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#include <stdexcept>
#include <string_view>
#include <vector>
namespace racer {
// Fixed-size prepared input, never an unbounded image decoder. Missing local
// proprietary data permits the authored shading fallback; malformed data fails.
inline std::vector<uint8_t> readWorldSurfaces(const std::filesystem::path& path,bool* foliage=nullptr) {
  if(foliage)*foliage=false;
  struct File {int fd;~File(){if(fd>=0)::close(fd);}} file{::open(path.c_str(),O_RDONLY|O_NOFOLLOW|O_NONBLOCK)};
  if(file.fd<0 && errno==ENOENT) {
    std::error_code error;
    if(std::filesystem::is_symlink(std::filesystem::symlink_status(path,error)))
      throw std::runtime_error("world_surface_input");
    return {};
  }
  constexpr size_t bytes=256*1024*4;
  struct stat status{};
  if(file.fd<0 || ::fstat(file.fd,&status)!=0 || !S_ISREG(status.st_mode) || status.st_size!=bytes+8)
    throw std::runtime_error("world_surface_input");
  auto read=[&](void* data,size_t size) {
    size_t count=0;
    while(count<size) {
      auto n=::read(file.fd,static_cast<uint8_t*>(data)+count,size-count);
      if(n<0 && errno==EINTR)continue;
      if(n<=0)throw std::runtime_error("world_surface_read");
      count+=size_t(n);
    }
  };
  std::array<char,8> magic{};read(magic.data(),magic.size());
  const auto version=std::string_view(magic.data(),magic.size());
  if(version!="RCRSURF1" && version!="RCRSURF2") throw std::runtime_error("world_surface_read");
  if(foliage)*foliage=version=="RCRSURF2";
  std::vector<uint8_t> result(bytes);read(result.data(),bytes);
  char extra;
  if(::read(file.fd,&extra,1)!=0)
    throw std::runtime_error("world_surface_read");
  return result;
}
}
