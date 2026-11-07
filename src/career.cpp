#include "career.h"
#include <algorithm>
#include <cmath>
#include <functional>
#include <iomanip>
#include <sstream>
#include <stdexcept>
namespace racer {
namespace {
bool identifier(const std::string &s) {
  return !s.empty() && s != "-" && s.size() <= 64 &&
         std::all_of(s.begin(), s.end(), [](unsigned char c) {
           return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
                  (c >= '0' && c <= '9') || c == '_' || c == '-';
         });
}
} // namespace
const CareerEvent *Career::event(const std::string &id) const {
  auto it = std::find_if(events.begin(), events.end(),
                         [&](const auto &e) { return e.id == id; });
  return it == events.end() ? nullptr : &*it;
}
Career::Career(std::vector<CareerEvent> input, std::vector<VehicleOffer> offers,
               std::string rev)
    : events(std::move(input)), vehicles(std::move(offers)),
      revision(std::move(rev)) {
  if (!identifier(revision) || events.size() > 128 || vehicles.empty() ||
      vehicles.size() > 128)
    throw std::invalid_argument("career catalog bounds");
  std::set<std::string> ids;
  for (const auto &v : vehicles)
    if (!identifier(v.id) || !ids.insert(v.id).second || v.price < 0 ||
        v.price > maxCredits)
      throw std::invalid_argument("vehicle catalog");
  if (!ids.contains("prototype"))
    throw std::invalid_argument("prototype required");
  owned.insert("prototype");
  ids.clear();
  for (const auto &e : events)
    if (!identifier(e.id) || !ids.insert(e.id).second ||
        !std::any_of(vehicles.begin(), vehicles.end(),
                     [&](const auto &v) { return v.id == e.vehicle; }) ||
        e.checkpoints == 0 || e.checkpoints > 1024 || e.reward < 0 ||
        e.reward > maxCredits || e.prerequisites.size() > 128)
      throw std::invalid_argument("event catalog");
  std::map<std::string, int> color;
  std::function<void(const CareerEvent &)> visit = [&](const CareerEvent &e) {
    if (color[e.id] == 1)
      throw std::invalid_argument("event prerequisite cycle");
    if (color[e.id] == 2)
      return;
    color[e.id] = 1;
    std::set<std::string> prerequisites;
    for (const auto &p : e.prerequisites) {
      auto target = event(p);
      if (!target || !prerequisites.insert(p).second)
        throw std::invalid_argument("event prerequisite");
      visit(*target);
    }
    color[e.id] = 2;
  };
  for (const auto &e : events)
    visit(e);
}
bool Career::discover(const std::string &id) {
  if (!event(id))
    return false;
  seen.insert(id);
  return true;
}
bool Career::eligible(const std::string &id) const {
  auto e = event(id);
  return e && seen.contains(id) && owns(e->vehicle) &&
         std::all_of(e->prerequisites.begin(), e->prerequisites.end(),
                     [&](const auto &p) { return done.contains(p); });
}
bool Career::select(const std::string &id) {
  if (active || !eligible(id))
    return false;
  selected = id;
  progress = 0;
  return true;
}
bool Career::start() {
  if (active || !eligible(selected))
    return false;
  active = true;
  progress = 0;
  return true;
}
bool Career::checkpoint(std::size_t index) {
  auto e = event(selected);
  if (!active || !e || index != progress || progress >= e->checkpoints)
    return false;
  ++progress;
  return true;
}
void Career::cancel() {
  active = false;
  progress = 0;
}
CareerFinish Career::finish(bool valid, double seconds) {
  auto e = event(selected);
  CareerFinish result;
  if (!active)
    return result;
  bool accepted = e && valid && progress == e->checkpoints &&
                  std::isfinite(seconds) && seconds > 0 && seconds <= 86400;
  cancel();
  if (!accepted)
    return result;
  const bool first = !done.contains(e->id);
  if (first && e->reward > maxCredits - money)
    return result;
  result.valid = true;
  result.firstCompletion = first;
  result.reward = first ? e->reward : 0;
  auto prior = best.find(e->id);
  result.newBest = prior == best.end() || seconds < prior->second;
  if (result.newBest)
    best[e->id] = seconds;
  done.insert(e->id);
  money += result.reward;
  return result;
}
bool Career::buy(const std::string &id) {
  auto v = std::find_if(vehicles.begin(), vehicles.end(),
                        [&](const auto &offer) { return offer.id == id; });
  if (active || v == vehicles.end() || owns(id) || v->price > money)
    return false;
  money -= v->price;
  owned.insert(id);
  return true;
}
double Career::bestSeconds(const std::string &id) const {
  auto b = best.find(id);
  return b == best.end() ? 0 : b->second;
}
std::string Career::serialize() const {
  std::ostringstream out;
  out << std::setprecision(17) << "RACER_CAREER 1 " << revision << '\n'
      << money << '\n'
      << (selected.empty() ? "-" : selected) << '\n';
  for (const auto *set : {&owned, &seen, &done}) {
    out << set->size() << '\n';
    for (const auto &id : *set)
      out << id << '\n';
  }
  out << best.size() << '\n';
  for (const auto &[id, time] : best)
    out << id << ' ' << time << '\n';
  return out.str();
}
bool Career::restore(const std::string &text) {
  if (text.size() > 65536)
    return false;
  Career restored = *this;
  restored.owned.clear();
  restored.seen.clear();
  restored.done.clear();
  restored.best.clear();
  restored.cancel();
  std::istringstream in(text);
  std::string magic, rev;
  int version = 0;
  if (!(in >> magic >> version >> rev) || magic != "RACER_CAREER" ||
      version != 1 || rev != revision || !(in >> restored.money) ||
      restored.money < 0 || restored.money > maxCredits ||
      !(in >> restored.selected))
    return false;
  if (restored.selected == "-")
    restored.selected.clear();
  else if (!event(restored.selected))
    return false;
  for (auto *set : {&restored.owned, &restored.seen, &restored.done}) {
    std::size_t count = 0;
    if (!(in >> count) || count > 128)
      return false;
    for (std::size_t i = 0; i < count; ++i) {
      std::string id;
      if (!(in >> id) || !identifier(id) || !set->insert(id).second)
        return false;
      if (set == &restored.owned) {
        if (!std::any_of(vehicles.begin(), vehicles.end(),
                         [&](const auto &v) { return v.id == id; }))
          return false;
      } else if (!event(id))
        return false;
    }
  }
  if (!restored.owns("prototype"))
    return false;
  for (const auto &id : restored.done) {
    auto e = event(id);
    if (!restored.seen.contains(id) || !restored.owns(e->vehicle) ||
        !std::all_of(e->prerequisites.begin(), e->prerequisites.end(),
                     [&](const auto &p) { return restored.done.contains(p); }))
      return false;
  }
  std::size_t count = 0;
  if (!(in >> count) || count != restored.done.size())
    return false;
  for (std::size_t i = 0; i < count; ++i) {
    std::string id;
    double time;
    if (!(in >> id >> time) || !restored.done.contains(id) ||
        !std::isfinite(time) || time <= 0 || time > 86400 ||
        !restored.best.emplace(id, time).second)
      return false;
  }
  if (!restored.selected.empty() && !restored.eligible(restored.selected))
    return false;
  in >> std::ws;
  if (!in.eof())
    return false;
  *this = std::move(restored);
  return true;
}
} // namespace racer
