#pragma once
#include "setup.h"
#include "diagnostics.h"
#include <filesystem>
#include <string>
#include <vector>
namespace racer {
struct StoredResult {
  std::string carId = "prototype", testId;
  int testRevision = 1, modelRevision = 1;
  std::size_t slot = 0;
  VehicleSetup setup;
  double seconds = 0, distance = 0, initialSpeed = 0;
  bool valid() const;
  bool comparable(const StoredResult &) const;
  bool operator==(const StoredResult &) const = default;
};
struct Profile {
  GarageState garage;
  std::vector<StoredResult> records;
  // Retains one best valid result per exact configuration, not per slot label.
  bool record(const StoredResult &result);
  const StoredResult *best(const StoredResult &result) const;
};
enum class Persistence { New, Loaded, Saved, Failed, Disabled };
class ProfileStore {
public:
  explicit ProfileStore(std::filesystem::path path, Diagnostics *diagnostics = nullptr);
  void context(uint64_t attempt) { parentOperation = attempt; }
  bool load(Profile &profile);
  bool save(const Profile &profile);
  const std::string &message() const { return status; }
  Persistence persistence() const { return persistence_; }
  bool writable() const { return allowWrite; }
  const std::filesystem::path &path() const { return location; }

private:
  Diagnostics *diagnostics;
  std::string profileId;
  uint64_t ioOperation = 0, parentOperation = 0;
  void trace(const char *event, const char *stage, bool success, int error = 0);
  std::filesystem::path location;
  std::string status;
  bool allowWrite = true;
  Persistence persistence_ = Persistence::New;
};
} // namespace racer
