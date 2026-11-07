#pragma once
#include "diagnostics.h"
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <string>
#include <string_view>
namespace racer {
enum class DocumentComponent { Parts, Livery, Career, Vehicle };
enum class DocumentStatus { Missing, Loaded, Saved, Failed, Disabled };
enum class DocumentStage {
  Open, Metadata, Read, Size, CreateDirectory, TemporaryOpen, Write, Sync,
  Close, Rename, Disabled
};
struct DocumentOutcome {
  DocumentStatus status = DocumentStatus::Missing;
  DocumentStage stage = DocumentStage::Open;
  int error = 0;
  explicit operator bool() const {
    return status == DocumentStatus::Missing || status == DocumentStatus::Loaded ||
           status == DocumentStatus::Saved;
  }
};
const char *documentStageName(DocumentStage stage);
// Independent sidecar I/O. Caller owns semantic decoding and may disable writes
// after rejecting a document. No cross-file transaction or directory-fsync claim.
class DocumentStore {
public:
  explicit DocumentStore(std::filesystem::path path, DocumentComponent component,
                         size_t maxBytes = 65536, Diagnostics *diagnostics = nullptr);
  // Missing and failed loads leave destination unchanged; Missing means defaults.
  // A successful load/missing result permits writes again; callers must reject
  // semantic failures explicitly after every successful byte load.
  DocumentOutcome load(std::string &destination);
  DocumentOutcome save(std::string_view text);
  void disableWrites();
  void context(uint64_t parentOperation) { parent_ = parentOperation; }
  bool writable() const { return writable_; }
  size_t maxBytes() const { return maxBytes_; }
  const DocumentOutcome &outcome() const { return last_; }
  const std::filesystem::path &path() const { return path_; }
private:
  std::filesystem::path path_;
  DocumentComponent component_;
  size_t maxBytes_;
  Diagnostics *diagnostics_;
  std::string identity_ = "unavailable";
  bool writable_ = true;
  uint64_t operation_ = 0, parent_ = 0;
  DocumentOutcome last_;
  void begin(const char *event, DocumentStage stage);
  DocumentOutcome finish(const char *event, DocumentStatus status, DocumentStage stage, int error = 0);
  void trace(const char *event, DocumentOutcome outcome) noexcept;
};
} // namespace racer
