#pragma once
#include "career.h"
#include "document_store.h"
#include <array>
#include <vector>
namespace racer {
struct CareerMarker {
  std::string id;
  double x = 0, z = 0;
};
enum class CareerBoardResult { Stay, StartHandling, Return };
class CareerFlow {
public:
  explicit CareerFlow(const std::filesystem::path &profilePath,
                      Diagnostics *diagnostics = nullptr);
  const Career &state() const { return career_; }
  const DocumentStore &store() const { return store_; }
  const std::array<CareerMarker, 2> &markers() const { return markers_; }
  const CareerMarker &selectedMarker() const { return markers_[destination_]; }
  void context(uint64_t attempt) {
    parent_ = attempt;
    store_.context(attempt);
  }
  void updatePosition(double x, double z);
  // direction -1/+1 adjusts selector row0; direction0 activates a row.
  CareerBoardResult action(int row, int direction, double x, double z);
  std::vector<std::string> lines(int menu) const;
  bool canStart(double x, double z) const;
  bool start();
  bool restart();
  bool checkpoint(std::size_t index);
  CareerFinish finish(bool valid, double seconds);
  void cancel();
  bool retrySave();
  uint64_t revision() const { return revision_; }
  const std::string &message() const { return message_; }

private:
  Career career_;
  DocumentStore store_;
  Diagnostics *diagnostics_;
  std::array<CareerMarker, 2> markers_{
      {{"grid-intro", 0, 0}, {"club-loop", 100, 100}}};
  std::size_t board_ = 0, destination_ = 0;
  uint64_t revision_ = 0, parent_ = 0;
  double x_ = 0, z_ = 0;
  std::string message_;
  std::string retryEvent_;
  bool persist();
  void changed(const char *cause);
};
} // namespace racer
