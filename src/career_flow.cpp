#include "career_flow.h"
#include <cmath>
#include <iomanip>
#include <sstream>
namespace racer {
CareerFlow::CareerFlow(const std::filesystem::path &profile, Diagnostics *sink)
    : career_({{"grid-intro", {}, "prototype", 5, 5000},
               {"club-loop", {"grid-intro"}, "touring", 5, 1000}},
              {{"prototype", 0}, {"touring", 3000}}, "grid-events-1"),
      store_(profile.string() + ".career", DocumentComponent::Career, 65536,
             sink),
      diagnostics_(sink) {
  std::string text;
  auto outcome = store_.load(text);
  if (outcome.status == DocumentStatus::Loaded && !career_.restore(text)) {
    store_.disableWrites();
    message_ = "Malformed career: original preserved; saving disabled.";
  } else if (!outcome)
    message_ = "Career unavailable: saving disabled this run.";
  else if (outcome.status == DocumentStatus::Loaded)
    message_ = "Career loaded.";
  else
    message_ = "New career: discover event markers while driving.";
  for (std::size_t i = 0; i < markers_.size(); ++i)
    if (career_.selection() == markers_[i].id)
      board_ = destination_ = i;
  changed("load");
}
void CareerFlow::changed(const char *cause) {
  ++revision_;
  if (diagnostics_)
    try {
      diagnostics_->event("career_state",
                          {{"cause", cause},
                           {"revision", revision_},
                           {"selection", markers_[destination_].id},
                           {"running", career_.running()},
                           {"checkpoint", career_.nextCheckpoint()},
                           {"credits", career_.credits()},
                           {"touring_owned",career_.owns("touring")},
                           {"intro_complete",career_.completed("grid-intro")},
                           {"club_complete",career_.completed("club-loop")},
                           {"persistence", int(store_.outcome().status)},
                           {"parent_operation", parent_}},
                          parent_);
    } catch (...) {
    }
}
bool CareerFlow::persist() {
  bool saved = bool(store_.save(career_.serialize()));
  if (!saved)
    message_ = "Career UNSAVED: progress in memory. Retry save.";
  return saved;
}
bool CareerFlow::retrySave() {
  bool saved = persist();
  if (saved)
    message_ = "Career saved.";
  changed("retry_save");
  return saved;
}
void CareerFlow::updatePosition(double x, double z) {
  if (!std::isfinite(x) || !std::isfinite(z))
    return;
  x_ = x;
  z_ = z;
  bool discovered = false;
  for (const auto &marker : markers_)
    if (!career_.discovered(marker.id) &&
        std::hypot(x - marker.x, z - marker.z) <= 25) {
      career_.discover(marker.id);
      discovered = true;
    }
  if (discovered) {
    message_ = "Event marker discovered.";
    persist();
    changed("discover");
  }
}
bool CareerFlow::canStart(double x, double z) const {
  const auto &marker = selectedMarker();
  return std::isfinite(x) && std::isfinite(z) && !career_.running() &&
         career_.eligible(marker.id) &&
         std::hypot(x - marker.x, z - marker.z) <= 25;
}
CareerBoardResult CareerFlow::action(int row, int direction, double x,
                                     double z) {
  updatePosition(x, z);
  if (row == 5 && direction == 0)
    return CareerBoardResult::Return;
  if (career_.running()) {
    message_ = "Finish or cancel the active event first.";
    return CareerBoardResult::Stay;
  }
  if (row == 0) {
    board_ = direction < 0 ? (board_ + markers_.size() - 1) % markers_.size()
                           : (board_ + 1) % markers_.size();
    changed("board_selection");
  } else if (direction == 0 && row == 1) {
    destination_ = board_;
    if (career_.eligible(selectedMarker().id))
      career_.select(selectedMarker().id);
    message_ = "Destination set: " + selectedMarker().id;
    persist();
    changed("destination");
  } else if (direction == 0 && row == 2) {
    destination_ = board_;
    if (canStart(x, z)) {
      career_.select(selectedMarker().id);
      persist();
      changed("start_requested");
      return CareerBoardResult::StartHandling;
    }
    message_ = "Start requires eligibility and arrival within 25 m.";
    changed("start_rejected");
  } else if (direction == 0 && row == 3) {
    if (career_.buy("touring")) {
      message_ =
          "Touring ownership unlocked; prototype visuals/handling retained.";
      persist();
      changed("buy");
    } else {
      message_ = "Touring requires 3000 credits; owned vehicles charge once.";
      changed("buy_rejected");
    }
  } else if (direction == 0 && row == 4)
    retrySave();
  return CareerBoardResult::Stay;
}
bool CareerFlow::start() {
  if (!canStart(x_, z_) || !career_.select(selectedMarker().id) ||
      !career_.start())
    return false;
  retryEvent_.clear();
  changed("start");
  return true;
}
bool CareerFlow::restart() {
  if (retryEvent_.empty() || career_.running() ||
      career_.selection() != retryEvent_ ||
      selectedMarker().id != retryEvent_ || !career_.eligible(retryEvent_) ||
      !career_.start())
    return false;
  retryEvent_.clear();
  changed("explicit_retry");
  return true;
}
bool CareerFlow::checkpoint(std::size_t index) {
  bool accepted = career_.checkpoint(index);
  if (accepted)
    changed("checkpoint");
  return accepted;
}
CareerFinish CareerFlow::finish(bool valid, double seconds) {
  if (career_.running())
    retryEvent_ = career_.selection();
  auto result = career_.finish(valid, seconds);
  if (result.valid) {
    message_ = result.firstCompletion
                   ? "Valid finish: first-completion reward " +
                         std::to_string(result.reward)
                   : "Valid repeat: no additional completion reward.";
    persist();
  } else
    message_ = "Invalid/unfinished career attempt: no reward.";
  changed("finish");
  return result;
}
void CareerFlow::cancel() {
  retryEvent_.clear();
  if (!career_.running())
    return;
  career_.cancel();
  message_ = "Event cancelled: no reward.";
  changed("cancel");
}
std::vector<std::string> CareerFlow::lines(int menu) const {
  const auto &marker = markers_[board_];
  std::ostringstream distance;
  distance << std::fixed << std::setprecision(0)
           << std::hypot(x_ - marker.x, z_ - marker.z);
  std::vector<std::string> text = {
      "EVENT BOARD / RACER-AUTHORED GRID EVENTS",
      "Credits: " + std::to_string(career_.credits()),
      "Both events use the existing five-gate handling course.",
      "Event: " + marker.id + " [Left / Right]",
      "Set destination",
      "Start nearby event (within 25 m)",
      "Buy Touring ownership / 3000 credits",
      "Retry career save",
      "Return"};
  for (int row = 0; row < 6; ++row)
    text[3 + row] = (row == menu ? "> " : "  ") + text[3 + row];
  text.push_back(
      "Marker distance: " + distance.str() + " m / " +
      (career_.discovered(marker.id) ? "discovered" : "undiscovered"));
  text.push_back(career_.eligible(marker.id)
                     ? "Eligible: arrive at the marker to start."
                     : "Locked: discover marker, finish Grid Intro, own "
                       "required vehicle.");
  text.push_back(
      "Touring is an ownership unlock; distinct car content is pending.");
  text.push_back(message_);
  if (store_.outcome().status == DocumentStatus::Disabled)
    text.push_back(
        "Saving disabled: original preserved. Move aside and restart.");
  else if (store_.outcome().status == DocumentStatus::Failed)
    text.push_back("UNSAVED / career disk state is unchanged.");
  return text;
}
} // namespace racer
