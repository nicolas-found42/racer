#pragma once
#include <cstdint>
#include <map>
#include <set>
#include <string>
#include <vector>
namespace racer {
struct CareerEvent {
  std::string id;
  std::vector<std::string> prerequisites;
  std::string vehicle = "prototype";
  std::size_t checkpoints = 5;
  int64_t reward = 0;
};
struct VehicleOffer {
  std::string id;
  int64_t price = 0;
};
struct CareerFinish {
  bool valid = false, firstCompletion = false, newBest = false;
  int64_t reward = 0;
};
class Career {
public:
  static constexpr int64_t maxCredits = 1000000000000LL;
  Career(std::vector<CareerEvent> events, std::vector<VehicleOffer> vehicles,
         std::string revision = "1");
  bool discover(const std::string &id);
  bool eligible(const std::string &id) const;
  bool select(const std::string &id);
  bool start();
  bool checkpoint(std::size_t index);
  void cancel();
  CareerFinish finish(bool valid, double seconds);
  bool buy(const std::string &vehicle);
  bool completed(const std::string &id) const { return done.contains(id); }
  bool owns(const std::string &id) const { return owned.contains(id); }
  bool discovered(const std::string &id) const { return seen.contains(id); }
  int64_t credits() const { return money; }
  bool running() const { return active; }
  std::size_t nextCheckpoint() const { return progress; }
  const std::string &selection() const { return selected; }
  const std::vector<CareerEvent> &catalog() const { return events; }
  double bestSeconds(const std::string &id) const;
  std::string serialize() const;
  // Transactional durable restore; in-progress attempts are cancelled.
  bool restore(const std::string &text);

private:
  std::vector<CareerEvent> events;
  std::vector<VehicleOffer> vehicles;
  std::string revision, selected;
  std::set<std::string> seen, done, owned;
  std::map<std::string, double> best;
  int64_t money = 0;
  bool active = false;
  std::size_t progress = 0;
  const CareerEvent *event(const std::string &) const;
};
} // namespace racer
