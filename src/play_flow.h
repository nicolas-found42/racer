#pragma once
#include "profile.h"
#include "garage_features.h"
#include "career_flow.h"
#include "test_session.h"
#include <optional>
#include <string>
#include <vector>
namespace racer {
enum class Screen { Drive, Pause, Garage, Pending, Tests, Results, Parts, Livery, Events };
enum class Action { Up, Down, Left, Right, Accept, Back, Pause, Reset, Map };
class PlayFlow {
public:
  explicit PlayFlow(const std::string &path, Diagnostics *diagnostics = nullptr);
  uint64_t attempt = 0;
  void observe(const char *cause) noexcept;
  Simulation sim;
  Profile profile;
  ProfileStore store;
  TestSession session;
  GarageFeatures features;
  CareerFlow career;
  bool careerAttempt = false;
  std::string vehicleId="prototype",vehicleName="Prototype car",vehicleSaveStatus;
  int vehicleCycleRequest=0;
  bool vehicleSaveRetryRequest=false;
  bool configureVehicle(const std::string &id,const std::string &name,const VehicleGeometry &geometry);
  Screen screen = Screen::Drive;
  bool paused = false, rearming = false, focus = true, quit = false;
  int menu = 0;
  unsigned poseRevision = 0;
  std::optional<double> prior;
  std::optional<StoredResult> priorRecord;
  enum class Retention { None, NewBest, Unchanged, Full };
  Retention retention = Retention::None;
  void action(Action);
  void suspend();
  void tick(Input);
  void garage();
  void startTest(TestKind);
  VehicleSetup effectiveSetup(size_t slot) const;
  std::vector<std::string> lines() const;
  // Number of selectable menu entries on the current screen (view-model split).
  int menuCount() const { return count(); }

private:
  Diagnostics *diagnostics;
  std::string lastObservation;
  uint64_t observationFailures = 0;
  bool previousBoundaryContact = false;
  void observeBoundary(Input input) noexcept;
  void actionImpl(Action);
  int pendingSlot = -1;
  Screen eventReturn = Screen::Drive;
  TestKind lastTest = TestKind::Acceleration;
  void show(Screen);
  void drive();
  void resetPose();
  void save();
  int count() const;
  void beginCareer(bool retry = false);
  void cancelCareer();
};
} // namespace racer
