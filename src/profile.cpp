#include "profile.h"
#include <algorithm>
#include <cmath>
#include <fcntl.h>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <system_error>
#include <unistd.h>
namespace racer {
namespace {
constexpr std::size_t maxRecords = 4096;
bool finiteRange(double v, double lo, double hi) {
  return std::isfinite(v) && v >= lo && v <= hi;
}
bool readSetup(std::istream &in, VehicleSetup &s) {
  return bool(in >> s.acceleration >> s.brake >> s.steering) && s.valid();
}
void writeSetup(std::ostream &out, const VehicleSetup &s) {
  out << s.acceleration << ' ' << s.brake << ' ' << s.steering;
}
double metric(const StoredResult &r) {
  return r.testId == "braking" ? r.distance : r.seconds;
}
} // namespace
bool StoredResult::valid() const {
  const bool imported=carId.size()==72 && carId.starts_with("vehicle-") &&
      std::all_of(carId.begin()+8,carId.end(),[](char c){return (c>='0'&&c<='9')||(c>='a'&&c<='f');});
  return ((carId == "prototype" && modelRevision==1) || (imported && modelRevision==2)) &&
         (testId == "acceleration" || testId == "braking" ||
          testId == "handling") &&
         // Revision 1: retired kinematic model; revision 2: force-based model.
         // comparable() never mixes them, and old records stay loadable.
         (testRevision == 1 || testRevision == 2) && slot < 3 && setup.valid() &&
         finiteRange(seconds, .000001, 3600) &&
         finiteRange(distance, 0, 100000) &&
         finiteRange(initialSpeed, 0, 160.0 / 3.6 + .01);
}
bool StoredResult::comparable(const StoredResult &other) const {
  return carId == other.carId && testId == other.testId &&
         testRevision == other.testRevision &&
         modelRevision == other.modelRevision && setup == other.setup;
}
const StoredResult *Profile::best(const StoredResult &result) const {
  for (const auto &r : records)
    if (r.comparable(result))
      return &r;
  return nullptr;
}
bool Profile::record(const StoredResult &result) {
  if (!result.valid())
    return false;
  for (auto &r : records) {
    if (r.comparable(result)) {
      if (metric(result) < metric(r))
        r = result;
      return true;
    }
  }
  if (records.size() >= maxRecords)
    return false;
  records.push_back(result);
  return true;
}
ProfileStore::ProfileStore(std::filesystem::path path, Diagnostics *sink)
    : diagnostics(sink), profileId("unavailable"), location(std::move(path)) {
  if (diagnostics) {
    try {
      std::error_code ec;
      auto absolute = std::filesystem::absolute(location, ec);
      if (!ec) profileId = Diagnostics::identity(absolute.lexically_normal().string());
    } catch (...) {} // Identity collection cannot prevent profile access.
  }
}
void ProfileStore::trace(const char *event, const char *stage, bool success, int error) {
  if (diagnostics)
    diagnostics->event(event, {{"profile", profileId}, {"stage", stage},
       {"success", success}, {"parent_operation", parentOperation}, {"errno", error}, {"persistence", int(persistence_)}}, ioOperation);
}
bool ProfileStore::load(Profile &profile) {
  ioOperation = diagnostics ? diagnostics->operation() : 0;
  trace("profile_load_begin", "open", true);
  allowWrite = true;
  status.clear();
  persistence_ = Persistence::New;
  std::error_code ec;
  const bool exists = std::filesystem::exists(location, ec);
  if (ec) {
    status = "Profile unavailable: " + ec.message() + ". Original preserved.";
    allowWrite = false;
    persistence_ = Persistence::Disabled;
    trace("profile_load_end", "exists", false, ec.value());
    return false;
  }
  if (!exists) {
    profile = {};
    status = "New profile: default setups.";
    trace("profile_load_end", "missing_defaults", true);
    return true;
  }
  const char *loadStage = "file_metadata";
  auto reject = [&]() {
    status = "Malformed or unsupported profile. Original preserved; saving "
             "disabled.";
    allowWrite = false;
    persistence_ = Persistence::Disabled;
    trace("profile_load_end", loadStage, false);
    return false;
  };
  if (!std::filesystem::is_regular_file(location, ec) || ec ||
      std::filesystem::file_size(location, ec) > 1024 * 1024 || ec)
    return reject();
  std::ifstream in(location);
  std::string magic;
  int version = 0;
  Profile loaded;
  std::size_t count = 0;
  loadStage = "header";
  if (!(in >> magic >> version) || magic != "RACER_PROFILE" || (version != 1 && version != 2) ||
      !(in >> loaded.garage.selected) || loaded.garage.selected >= 3)
    return reject();
  loadStage = "setups";
  for (auto &s : loaded.garage.applied)
    if (!readSetup(in, s))
      return reject();
  loaded.garage.discard();
  loadStage = "record_count";
  if (!(in >> count) || count > maxRecords)
    return reject();
  loadStage = "record";
  for (std::size_t i = 0; i < count; ++i) {
    StoredResult r;
    if (!(in >> r.carId >> r.testId >> r.testRevision >> r.modelRevision >>
          r.slot) ||
        !readSetup(in, r.setup) ||
        !(in >> r.seconds >> r.distance >> r.initialSpeed) || !r.valid() ||
        loaded.best(r) || (version==1 && r.carId!="prototype"))
      return reject();
    loaded.records.push_back(r);
  }
  loadStage = "trailing_data";
  in >> std::ws;
  if (!in.eof())
    return reject();
  profile = std::move(loaded);
  persistence_ = Persistence::Loaded;
  status = "Profile loaded.";
  trace("profile_load_end", "loaded", true);
  return true;
}
bool ProfileStore::save(const Profile &profile) {
  ioOperation = diagnostics ? diagnostics->operation() : 0;
  trace("profile_save_begin", "validate", true);
  if (!allowWrite) {
    trace("profile_save_end", "disabled", false);
    return false;
  }
  const char *saveStage = "validate";
  int saveError = 0;
  auto failure = [&](const std::string &why) {
    persistence_ = Persistence::Failed;
    trace("profile_save_end", saveStage, false, saveError);
    status = "Unsaved changes: " + why + ". Last good profile preserved.";
    return false;
  };
  if (!profile.garage.valid() || profile.records.size() > maxRecords)
    return failure("invalid profile");
  for (std::size_t i = 0; i < profile.records.size(); ++i) {
    if (!profile.records[i].valid())
      return failure("invalid result");
    for (std::size_t j = 0; j < i; ++j)
      if (profile.records[i].comparable(profile.records[j]))
        return failure("duplicate result");
  }
  std::ostringstream data;
  const bool importedRecords=std::any_of(profile.records.begin(),profile.records.end(),[](const auto &r){return r.carId!="prototype";});
  data << std::setprecision(17) << "RACER_PROFILE " << (importedRecords ? 2 : 1) << '\n'
       << profile.garage.selected << '\n';
  for (const auto &s : profile.garage.applied) {
    writeSetup(data, s);
    data << '\n';
  }
  data << profile.records.size() << '\n';
  for (const auto &r : profile.records) {
    data << r.carId << ' ' << r.testId << ' ' << r.testRevision << ' '
         << r.modelRevision << ' ' << r.slot << ' ';
    writeSetup(data, r.setup);
    data << ' ' << r.seconds << ' ' << r.distance << ' ' << r.initialSpeed
         << '\n';
  }
  std::error_code ec;
  if (!location.parent_path().empty())
    std::filesystem::create_directories(location.parent_path(), ec);
  if (ec) {
    saveStage = "mkdir"; saveError = ec.value();
    return failure(ec.message());
  }
  // A unique sibling keeps replacement on one filesystem and avoids clobbering
  // another process's temporary save. fsync completes before the atomic rename.
  std::string pattern = location.string() + ".tmp.XXXXXX";
  std::vector<char> temp(pattern.begin(), pattern.end());
  temp.push_back('\0');
  int fd = mkstemp(temp.data());
  if (fd < 0) {
    saveStage = "temporary_open"; saveError = errno;
    return failure("cannot create temporary profile");
  }
  const auto text = data.str();
  std::size_t offset = 0;
  bool ok = true;
  while (offset < text.size()) {
    auto n = ::write(fd, text.data() + offset, text.size() - offset);
    if (n <= 0) {
      saveStage = "write"; saveError = errno;
      ok = false;
      break;
    }
    offset += std::size_t(n);
  }
  if (ok && fsync(fd) != 0) { saveStage = "fsync"; saveError = errno; ok = false; }
  if (close(fd) != 0) { saveStage = "close"; saveError = errno; ok = false; }
  if (ok && ::rename(temp.data(), location.c_str()) != 0) { saveStage = "rename"; saveError = errno; ok = false; }
  if (!ok) {
    ::unlink(temp.data());
    return failure("atomic profile write failed");
  }
  persistence_ = Persistence::Saved;
  status = "Profile saved.";
  trace("profile_save_end", "atomic_replace", true);
  return true;
}
} // namespace racer
