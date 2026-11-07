#include "document_store.h"
#include <cerrno>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <map>
#include <regex>
#include <sstream>
#include <sys/stat.h>
#include <unistd.h>
using namespace racer;
void check(const auto &value, const char *message) {
  if (!value) { std::cerr << "FAIL: " << message << '\n'; std::exit(1); }
}
std::string read(const std::filesystem::path &path) {
  std::ifstream in(path, std::ios::binary);
  return {std::istreambuf_iterator<char>(in), {}};
}
int main() {
  char temporary[] = "/tmp/racer-documents-XXXXXX";
  check(mkdtemp(temporary), "fixture directory");
  std::filesystem::path root(temporary), target = root/"player-SECRET.livery";
  std::filesystem::create_directory(root/"storage");
  target = root/"storage/player-SECRET.livery";
  {
    Diagnostics diagnostics(root/"history");
    DocumentStore store(target, DocumentComponent::Livery, 32, &diagnostics);
    store.context(91);
    std::string destination = "untouched";
    auto result = store.load(destination);
    check(result.status == DocumentStatus::Missing && destination == "untouched", "missing means caller defaults without mutation");
    check(store.save("SECRET original"), "first atomic save");
    check(read(target) == "SECRET original", "saved exact bytes");
    check(store.load(destination) && destination == "SECRET original", "restart byte load");
    store.disableWrites();
    check(store.save("overwrite").status == DocumentStatus::Disabled && read(target) == destination, "semantic rejection disables replacement");
    check(store.load(destination), "successful explicit reload permits writes");
    check(!store.save(std::string(33, 'x')) && read(target) == destination, "oversized save preserves bytes");
    // Real filesystem denial, not an injected error result.
    check(geteuid() != 0, "permission fixture requires ordinary user");
    check(chmod(target.parent_path().c_str(), 0500) == 0, "lock fixture directory");
    result = store.save("retry value");
    check(!result && result.stage == DocumentStage::TemporaryOpen && result.error == EACCES, "actual unwritable destination outcome");
    check(read(target) == "SECRET original", "last good file survives denial");
    check(chmod(target.parent_path().c_str(), 0700) == 0, "unlock fixture directory");
    check(store.save("retry value") && read(target) == "retry value", "retry after repaired access");
    for (const auto &entry : std::filesystem::directory_iterator(target.parent_path()))
      check(entry.path() == target, "temporary sibling cleanup");
    check(chmod(target.c_str(), 0000) == 0, "make document unreadable");
    destination = "unchanged"; result = store.load(destination);
    check(!result && result.error == EACCES && destination == "unchanged" && !store.writable(), "unreadable source preserves live state and disables writes");
    check(chmod(target.c_str(), 0600) == 0, "restore source access");
    check(store.load(destination), "reload after read repair");
    std::ofstream(target, std::ios::binary) << std::string(33,'z');
    destination = "keep live"; result = store.load(destination);
    check(!result && result.stage == DocumentStage::Size && result.error == EFBIG && destination == "keep live", "oversized source preserved");
    check(store.save("no").status == DocumentStatus::Disabled && read(target).size() == 33, "oversized source cannot be silently replaced");
    // Nonregular files must fail without blocking on FIFO input.
    auto fifo = root/"fifo"; check(mkfifo(fifo.c_str(), 0600) == 0, "fifo fixture");
    DocumentStore nonregular(fifo, DocumentComponent::Parts);
    check(!nonregular.load(destination) && nonregular.outcome().stage == DocumentStage::Metadata, "nonregular load rejected without blocking");
    auto link = root/"link"; std::filesystem::create_symlink(target, link);
    DocumentStore linked(link, DocumentComponent::Parts);
    check(!linked.load(destination) && !linked.writable(), "symlink load refused");
    check(!linked.save("no") && read(target).size() == 33, "symlink target preserved");
  }
  std::string history;
  for (const auto &entry : std::filesystem::directory_iterator(root/"history"))
    if (entry.path().extension() == ".jsonl") history += read(entry.path());
  check(history.find("SECRET") == std::string::npos && history.find(root.string()) == std::string::npos, "telemetry omits content and raw path");
  check(history.find("\"event\":\"document_load_begin\"") != std::string::npos && history.find("\"event\":\"document_load_end\"") != std::string::npos, "load boundary events retained");
  check(history.find("\"event\":\"document_save_begin\"") != std::string::npos && history.find("\"event\":\"document_save_end\"") != std::string::npos, "save boundary events retained");
  check(history.find("\"parent_operation\":91") != std::string::npos && history.find("\"component\":\"livery\"") != std::string::npos, "allowlisted component and parent correlation");
  std::map<uint64_t, std::pair<int,int>> boundaries;
  std::regex boundary(R"REGEX("operation":([0-9]+).*"event":"document_(load|save)_(begin|end)")REGEX");
  std::istringstream lines(history);
  for (std::string line; std::getline(lines, line);) {
    std::smatch match;
    if (std::regex_search(line, match, boundary)) {
      auto &pair = boundaries[std::stoull(match[1])];
      if (match[3] == "begin") ++pair.first; else ++pair.second;
    }
  }
  check(boundaries.size() >= 5, "distinct operation identities retained");
  for (const auto &[id, counts] : boundaries)
    check(id && counts.first == 1 && counts.second == 1, "every observed operation has one matching begin/end");
  // A genuinely unavailable recorder must not prevent successful sidecar I/O.
  std::ofstream(root/"blocked") << "not a directory";
  Diagnostics unavailable(root/"blocked/history");
  DocumentStore independent(root/"parts.txt", DocumentComponent::Parts, 64, &unavailable);
  check(independent.save("parts data"), "recorder initialization failure isolation");
  std::string restored;
  check(independent.load(restored) && restored == "parts data", "read works with disabled recorder");
  std::filesystem::remove_all(root);
  std::cout << "PASS: bounded document missing/load/save, actual permission failure/retry, preservation/disabled writes, nonregular refusal, telemetry privacy and failure isolation\n";
}
