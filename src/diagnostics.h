#pragma once
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <deque>
#include <filesystem>
#include <initializer_list>
#include <mutex>
#include <string>
#include <thread>
#include <variant>
#include <concepts>
namespace racer {
struct Field {
  const char *key;
  std::variant<double, bool, std::string> value;
  Field(const char *k, double v) : key(k), value(v) {}
  Field(const char *k, bool v) : key(k), value(v) {}
  template <std::integral T> Field(const char *k, T v) : key(k), value(double(v)) {}
  Field(const char *k, const char *v) : key(k), value(std::string(v)) {}
  Field(const char *k, const std::string &v) : key(k), value(v) {}
};
// Local, bounded, non-throwing sink. Call sites supply only allowlisted state,
// never raw keys, paths, exception messages, file contents or environment values.
class Diagnostics {
public:
  explicit Diagnostics(const std::filesystem::path &directory,
                       size_t runLimit = 4 * 1024 * 1024) noexcept;
  ~Diagnostics();
  Diagnostics(const Diagnostics &) = delete;
  void event(const char *name, std::initializer_list<Field> fields = {},
             uint64_t operation = 0) noexcept;
  uint64_t operation() noexcept { return ++operations; }
  void flush() noexcept;
  bool enabled() const noexcept { return healthy; }
  const std::string &runId() const { return id; }
  const std::filesystem::path &directory() const { return root; }
  static std::string identity(const std::string &value);
  static std::string fileHash(const std::filesystem::path &file, size_t maxBytes = 256*1024*1024) noexcept;
private:
  std::filesystem::path root;
  std::string id;
  int fd = -1;
  size_t limit, written = 0;
  std::atomic<bool> healthy{false};
  std::atomic<uint64_t> operations{0}, lost{0};
  uint64_t sequence = 0;
  std::chrono::steady_clock::time_point start = std::chrono::steady_clock::now();
  std::mutex mutex;
  std::condition_variable wake, drained;
  std::deque<std::string> queue;
  bool stopping = false, busy = false;
  std::thread writer;
  void work() noexcept;
};
}
