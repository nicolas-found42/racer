#include "world_surfaces.h"
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <new>
#include <string>
#include <unistd.h>

namespace {
constexpr size_t payloadBytes=256*1024*4;
bool watchAllocations=false;
size_t largeAllocations=0;
void require(bool value,const char *reason) {
  if (!value) throw std::runtime_error(reason);
}
struct TemporaryDirectory {
  std::filesystem::path path;
  TemporaryDirectory() {
    char pattern[]="/tmp/racer-surfaces-XXXXXX";
    require(mkdtemp(pattern),"create owned temporary directory");path=pattern;
  }
  ~TemporaryDirectory() {
    std::error_code error;std::filesystem::remove_all(path,error);
  }
};
}

// Observe the vector allocation directly, rather than inferring its absence
// from a successful size check. Ordinary path/error-message allocations remain allowed.
void *operator new(std::size_t bytes) {
  if (watchAllocations && bytes>=payloadBytes) ++largeAllocations;
  if (void *result=std::malloc(bytes?bytes:1)) return result;
  throw std::bad_alloc();
}
void operator delete(void *memory) noexcept {std::free(memory);}
void operator delete(void *memory,std::size_t) noexcept {std::free(memory);}

int main() try {
  TemporaryDirectory directory;
  const auto path=directory.path/"surfaces.rgba";
  require(racer::readWorldSurfaces(path).empty(),"missing optional surface file uses authored fallback");
  require(racer::readWorldSurfaces(directory.path/"absent"/"surfaces.rgba").empty(),"missing optional parent uses authored fallback");
  std::vector<uint8_t> expected(payloadBytes);
  for (size_t i=0;i<expected.size();++i) expected[i]=uint8_t(i*37+i/251);
  auto write=[&](const std::string &magic,size_t bytes,bool extra=false) {
    std::ofstream output(path,std::ios::binary|std::ios::trunc);
    output.write(magic.data(),std::streamsize(magic.size()));
    output.write(reinterpret_cast<const char*>(expected.data()),std::streamsize(bytes));
    if (extra) output.put('x');
    require(bool(output),"write bounded surface fixture");
  };
  auto reject=[&](const std::filesystem::path &input,const char *reason) {
    try {racer::readWorldSurfaces(input);}
    catch (const std::runtime_error &error) {
      require(std::string(error.what())==reason,"surface rejects with expected diagnostic");return;
    }
    throw std::runtime_error("invalid surface accepted");
  };
  write("RCRSURF1",payloadBytes);
  largeAllocations=0;watchAllocations=true;
  const auto actual=racer::readWorldSurfaces(path);
  watchAllocations=false;
  require(actual==expected,"fixed-size RGBA payload preserved byte for byte");
  require(largeAllocations==1,"allocation observation detects one valid payload allocation");
  bool foliage=true;
  require(racer::readWorldSurfaces(path,&foliage)==expected && !foliage,"version1 retains authored foliage fallback");
  write("RCRSURF2",payloadBytes);
  require(racer::readWorldSurfaces(path,&foliage)==expected && foliage,"version2 enables the alpha-palm tile explicitly");
  require(racer::readWorldSurfaces(directory.path/"absent",&foliage).empty() && !foliage,"missing data clears foliage availability");
  write("RCRSURF1",payloadBytes-1);reject(path,"world_surface_input");
  write("RCRSURF1",0);reject(path,"world_surface_input");
  write("BADMAGIC",payloadBytes);reject(path,"world_surface_read");
  write("RCRSURF1",payloadBytes,true);
  largeAllocations=0;watchAllocations=true;
  reject(path,"world_surface_input");
  watchAllocations=false;
  require(largeAllocations==0,"oversized input rejected before payload allocation");
  reject(directory.path,"world_surface_input");
  write("RCRSURF1",payloadBytes);
  const auto link=directory.path/"link.rgba";
  std::filesystem::create_symlink(path,link);reject(link,"world_surface_input");
  const auto dangling=directory.path/"dangling.rgba";
  std::filesystem::create_symlink(directory.path/"missing.rgba",dangling);
  reject(dangling,"world_surface_input");
  std::cout<<"PASS: optional surfaces fallback, exact RGBA preservation, bounded allocation, malformed/type/symlink rejection\n";
} catch (const std::exception &error) {
  watchAllocations=false;std::cerr<<"FAIL: "<<error.what()<<'\n';return 1;
}
