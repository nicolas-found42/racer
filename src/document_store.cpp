#include "document_store.h"
#include <algorithm>
#include <cerrno>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#include <vector>
namespace racer {
namespace {
struct Descriptor {
  int fd;
  ~Descriptor() { if (fd >= 0) ::close(fd); }
  int close() { int value = fd; fd = -1; return ::close(value); }
};
struct Temporary {
  const char *path;
  ~Temporary() { if (path) ::unlink(path); }
};
}
const char *documentStageName(DocumentStage stage) {
  switch (stage) {
  case DocumentStage::Open: return "open";
  case DocumentStage::Metadata: return "metadata";
  case DocumentStage::Read: return "read";
  case DocumentStage::Size: return "size";
  case DocumentStage::CreateDirectory: return "mkdir";
  case DocumentStage::TemporaryOpen: return "temporary_open";
  case DocumentStage::Write: return "write";
  case DocumentStage::Sync: return "fsync";
  case DocumentStage::Close: return "close";
  case DocumentStage::Rename: return "atomic_replace";
  case DocumentStage::Disabled: return "disabled";
  }
  return "unknown";
}
DocumentStore::DocumentStore(std::filesystem::path path, DocumentComponent component,
                             size_t maxBytes, Diagnostics *diagnostics)
    : path_(std::move(path)), component_(component),
      maxBytes_(std::clamp(maxBytes, size_t(1), size_t(1024 * 1024))), diagnostics_(diagnostics) {
  if (diagnostics_) {
    try {
      std::error_code ec;
      auto absolute = std::filesystem::absolute(path_, ec);
      if (!ec) identity_ = Diagnostics::identity(absolute.lexically_normal().string());
    } catch (...) {} // Telemetry identity must never prevent document access.
  }
}
void DocumentStore::trace(const char *event, DocumentOutcome outcome) noexcept {
  if (!diagnostics_) return;
  try {
    const char *component = component_ == DocumentComponent::Parts ? "parts" :
                            component_ == DocumentComponent::Livery ? "livery" :
                            component_ == DocumentComponent::Career ? "career" : "vehicle";
    diagnostics_->event(event, {{"component", component},
      {"document", identity_}, {"stage", documentStageName(outcome.stage)},
      {"success", bool(outcome)}, {"status", int(outcome.status)}, {"errno", outcome.error},
      {"parent_operation", parent_}}, operation_);
  } catch (...) {} // Includes Field/string construction outside the sink itself.
}
void DocumentStore::begin(const char *event, DocumentStage stage) {
  operation_ = diagnostics_ ? diagnostics_->operation() : 0;
  trace(event, {DocumentStatus::Loaded, stage, 0});
}
DocumentOutcome DocumentStore::finish(const char *event, DocumentStatus status, DocumentStage stage, int error) {
  last_ = {status, stage, error}; trace(event, last_); return last_;
}
void DocumentStore::disableWrites() {
  writable_ = false;
  finish("document_writes_disabled", DocumentStatus::Disabled, DocumentStage::Disabled);
}
DocumentOutcome DocumentStore::load(std::string &destination) {
  begin("document_load_begin", DocumentStage::Open);
  auto fail = [&](DocumentStage stage, int error) {
    writable_ = false;
    return finish("document_load_end", DocumentStatus::Failed, stage, error);
  };
  if (path_.empty()) return fail(DocumentStage::Open, EINVAL);
  Descriptor file{::open(path_.c_str(), O_RDONLY | O_NOFOLLOW | O_CLOEXEC | O_NONBLOCK)};
  if (file.fd < 0) {
    int error = errno;
    if (error == ENOENT) {
      writable_ = true;
      return finish("document_load_end", DocumentStatus::Missing, DocumentStage::Open);
    }
    return fail(DocumentStage::Open, error);
  }
  struct stat metadata{};
  if (fstat(file.fd, &metadata) != 0) return fail(DocumentStage::Metadata, errno);
  if (!S_ISREG(metadata.st_mode)) return fail(DocumentStage::Metadata, EINVAL);
  if (metadata.st_size < 0 || uint64_t(metadata.st_size) > maxBytes_)
    return fail(DocumentStage::Size, EFBIG);
  std::string candidate;
  char buffer[4096];
  for (;;) {
    auto count = ::read(file.fd, buffer, std::min(sizeof(buffer), maxBytes_ + 1 - candidate.size()));
    if (count < 0 && errno == EINTR) continue;
    if (count < 0) return fail(DocumentStage::Read, errno);
    if (!count) break;
    candidate.append(buffer, size_t(count));
    if (candidate.size() > maxBytes_) return fail(DocumentStage::Size, EFBIG);
  }
  if (file.close() != 0) return fail(DocumentStage::Close, errno);
  destination = std::move(candidate); writable_ = true;
  return finish("document_load_end", DocumentStatus::Loaded, DocumentStage::Read);
}
DocumentOutcome DocumentStore::save(std::string_view text) {
  begin("document_save_begin", DocumentStage::Size);
  auto fail = [&](DocumentStage stage, int error) {
    return finish("document_save_end", DocumentStatus::Failed, stage, error);
  };
  if (!writable_) return finish("document_save_end", DocumentStatus::Disabled, DocumentStage::Disabled);
  if (path_.empty()) return fail(DocumentStage::Open, EINVAL);
  if (text.size() > maxBytes_) return fail(DocumentStage::Size, EFBIG);
  struct stat existing{};
  if (::lstat(path_.c_str(), &existing) == 0) {
    if (!S_ISREG(existing.st_mode)) return fail(DocumentStage::Metadata, EINVAL);
  } else if (errno != ENOENT) return fail(DocumentStage::Metadata, errno);
  std::error_code ec;
  if (!path_.parent_path().empty()) std::filesystem::create_directories(path_.parent_path(), ec);
  if (ec) return fail(DocumentStage::CreateDirectory, ec.value());
  std::string pattern = path_.string() + ".tmp.XXXXXX";
  std::vector<char> name(pattern.begin(), pattern.end()); name.push_back('\0');
  Descriptor file{::mkstemp(name.data())};
  if (file.fd < 0) return fail(DocumentStage::TemporaryOpen, errno);
  Temporary temporary{name.data()};
  size_t offset = 0;
  while (offset < text.size()) {
    auto count = ::write(file.fd, text.data() + offset, text.size() - offset);
    if (count < 0 && errno == EINTR) continue;
    if (count <= 0) return fail(DocumentStage::Write, count < 0 ? errno : EIO);
    offset += size_t(count);
  }
  if (::fsync(file.fd) != 0) return fail(DocumentStage::Sync, errno);
  if (file.close() != 0) return fail(DocumentStage::Close, errno);
  if (::rename(name.data(), path_.c_str()) != 0) return fail(DocumentStage::Rename, errno);
  temporary.path = nullptr;
  return finish("document_save_end", DocumentStatus::Saved, DocumentStage::Rename);
}
} // namespace racer
