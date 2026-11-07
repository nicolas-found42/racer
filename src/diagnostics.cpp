#include "diagnostics.h"
#include <CommonCrypto/CommonDigest.h>
#include <cmath>
#include <algorithm>
#include <cstdio>
#include <fcntl.h>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <sys/file.h>
#include <sys/stat.h>
#include <unistd.h>
namespace racer {
namespace {
std::string hex(const unsigned char *bytes, size_t count) {
  std::ostringstream out;
  for (size_t i = 0; i < count; ++i)
    out << std::hex << std::setw(2) << std::setfill('0') << unsigned(bytes[i]);
  return out.str();
}
std::string quote(const std::string &value) {
  std::string out = "\"";
  // Enforce small schema values; no unbounded strings or raw dependency text.
  for (unsigned char c : value.substr(0, 160)) {
    if (c == '"' || c == '\\') { out += '\\'; out += char(c); }
    else if (c < 32) out += '?';
    else out += char(c);
  }
  return out + '"';
}
bool writeAll(int fd, const std::string &line) {
  size_t offset = 0;
  while (offset < line.size()) {
    auto n = ::write(fd, line.data() + offset, line.size() - offset);
    if (n < 0 && errno == EINTR) continue;
    if (n <= 0) return false;
    offset += size_t(n);
  }
  return true;
}
}
std::string Diagnostics::identity(const std::string &value) {
  unsigned char sum[CC_SHA256_DIGEST_LENGTH];
  CC_SHA256(value.data(), CC_LONG(value.size()), sum);
  return hex(sum, sizeof(sum));
}
std::string Diagnostics::fileHash(const std::filesystem::path &path,size_t maxBytes) noexcept {
  try {
    struct File { int fd;~File() { if (fd>=0) ::close(fd); } } file{
        ::open(path.c_str(),O_RDONLY|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC)};
    struct stat before{},after{};
    if (file.fd<0 || ::fstat(file.fd,&before)!=0 || !S_ISREG(before.st_mode) ||
        before.st_size<0 || uint64_t(before.st_size)>maxBytes) return "unavailable";
    CC_SHA256_CTX ctx; CC_SHA256_Init(&ctx);
    char bytes[16384];
    size_t consumed=0;
    for (;;) {
      auto count=::read(file.fd,bytes,sizeof(bytes));
      if (count<0 && errno==EINTR) continue;
      if (count<0) return "unavailable";
      if (!count) break;
      if (size_t(count)>maxBytes-consumed) return "unavailable";
      consumed+=size_t(count);CC_SHA256_Update(&ctx,bytes,CC_LONG(count));
    }
    if (::fstat(file.fd,&after)!=0 || consumed!=uint64_t(before.st_size) || before.st_size!=after.st_size ||
        before.st_mtimespec.tv_sec!=after.st_mtimespec.tv_sec || before.st_mtimespec.tv_nsec!=after.st_mtimespec.tv_nsec)
      return "unavailable";
    unsigned char sum[CC_SHA256_DIGEST_LENGTH]; CC_SHA256_Final(sum, &ctx);
    return hex(sum, sizeof(sum));
  } catch (...) { return "unavailable"; }
}
Diagnostics::Diagnostics(const std::filesystem::path &directory, size_t runLimit) noexcept
    : root(directory), limit(std::clamp(runLimit, size_t(4096), size_t(4 * 1024 * 1024))) {
  int lock = -1;
  try {
    if (root.empty()) return;
    std::filesystem::create_directories(root);
    lock = ::open((root / ".quota.lock").c_str(), O_CREAT | O_RDWR | O_NOFOLLOW, 0600);
    if (lock < 0 || flock(lock, LOCK_EX | LOCK_NB) != 0) throw 1;
    size_t logs = 0, bytes = 0;
    for (const auto &item : std::filesystem::directory_iterator(root)) {
      if (item.is_symlink()) continue;
      if (item.path().extension() == ".jsonl") ++logs;
      if (item.is_regular_file()) bytes += item.file_size();
    }
    // Reserve a full 4 MiB per run. No eviction of historical evidence.
    if (logs >= 16 || bytes + 4 * 1024 * 1024 > 64 * 1024 * 1024) throw 1;
    auto epoch = std::chrono::duration_cast<std::chrono::microseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
    id = std::to_string(epoch) + "-" + std::to_string(getpid());
    fd = ::open((root / (id + ".jsonl")).c_str(), O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, 0600);
    if (fd < 0) throw 1;
    flock(lock, LOCK_UN); close(lock); lock = -1;
    healthy = true;
    writer = std::thread([this] { work(); });
    event("recorder_start", {{"schema", 1}, {"run_limit_bytes", limit},
          {"max_runs", 16}, {"sample_hz", 10}, {"queue_limit", 512}});
  } catch (...) {
    if (lock >= 0) { flock(lock, LOCK_UN); close(lock); }
    if (fd >= 0) { close(fd); fd = -1; }
    healthy = false;
    std::fputs("Racer diagnostics unavailable (access, quota or initialization); play continues.\n", stderr);
  }
}
void Diagnostics::event(const char *name, std::initializer_list<Field> fields,
                        uint64_t operation) noexcept {
  if (!healthy) return;
  try {
    std::unique_lock guard(mutex);
    if (queue.size() >= 512) { ++lost; return; }
    const auto wall = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
    const auto mono = std::chrono::duration<double, std::milli>(
        std::chrono::steady_clock::now() - start).count();
    std::ostringstream out;
    out << std::setprecision(17) << "{\"schema\":1,\"run\":" << quote(id)
        << ",\"seq\":" << ++sequence << ",\"utc_ms\":" << wall
        << ",\"mono_ms\":" << mono << ",\"operation\":" << operation
        << ",\"dropped\":" << lost.load() << ",\"event\":" << quote(name);
    for (const auto &f : fields) {
      out << ',' << quote(f.key) << ':';
      if (auto n = std::get_if<double>(&f.value)) {
        if (std::isfinite(*n)) out << *n; else out << "null";
      } else if (auto b = std::get_if<bool>(&f.value)) out << (*b ? "true" : "false");
      else out << quote(std::get<std::string>(f.value));
    }
    out << "}\n";
    if (out.tellp() > 8192) { ++lost; return; }
    queue.push_back(out.str()); wake.notify_one();
  } catch (...) { ++lost; }
}
void Diagnostics::work() noexcept {
  try {
    for (;;) {
      std::string line;
      {
        std::unique_lock guard(mutex);
        wake.wait(guard, [this] { return stopping || !queue.empty(); });
        if (queue.empty() && stopping) break;
        line = std::move(queue.front()); queue.pop_front(); busy = true;
      }
      if (healthy) {
        if (written + line.size() + 1024 > limit) {
          // Preserve the tail's stop reason instead of silently truncating it.
          auto stop = "{\"schema\":1,\"run\":" + quote(id) +
                      ",\"event\":\"recording_stopped\",\"reason\":\"run_quota\"}\n";
          writeAll(fd, stop); healthy = false;
          std::fputs("Racer diagnostic run quota reached; history is incomplete.\n", stderr);
        } else if (!writeAll(fd, line)) {
          healthy = false;
          std::fputs("Racer diagnostic write failed; history is incomplete.\n", stderr);
        } else written += line.size();
      }
      {
        std::lock_guard guard(mutex); busy = false;
        if (queue.empty()) drained.notify_all();
      }
    }
    fsync(fd);
  } catch (...) { healthy = false; }
}
void Diagnostics::flush() noexcept {
  try {
    std::unique_lock guard(mutex);
    drained.wait_for(guard, std::chrono::milliseconds(100), [this] { return queue.empty() && !busy; });
  } catch (...) {}
}
Diagnostics::~Diagnostics() {
  if (writer.joinable()) {
    event("recorder_end", {{"dropped_total", lost.load()}});
    { std::lock_guard guard(mutex); stopping = true; }
    wake.notify_all(); writer.join();
  }
  if (fd >= 0) close(fd);
}
}
