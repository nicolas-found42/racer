#pragma once
#include "play_flow.h"
#include <array>
#include <string>
namespace racer {
// Main-thread, change-only bridge between UI/domain revisions and retained
// canonical memory identities. No document text, paths or arbitrary UI text.
class WorkflowObservation {
public:
  explicit WorkflowObservation(Diagnostics *sink) : sink_(sink) {}
  void observe(const PlayFlow &flow, uint64_t frame) noexcept {
    if (!sink_ || !sink_->enabled()) return;
    try {
      const auto &parts=flow.features.partsStore();
      const auto &livery=flow.features.liveryStore();
      const auto &career=flow.career.store();
      const auto status=[](const DocumentStore &s) {
        return std::array<int,4>{int(s.outcome().status),int(s.outcome().stage),s.outcome().error,int(s.writable())};
      };
      Guard next{flow.features.partsRevision(),flow.features.liveryRevision(),flow.features.draftRevision(),
        flow.career.revision(),flow.attempt,int(flow.screen),status(parts),status(livery),status(career)};
      if (seen_ && next==last_ && flow.vehicleId==lastVehicle_) return;
      // Consume this guard before fallible work: a failed observation must
      // not retry serialization/hash allocation on every idle render frame.
      last_=next;lastVehicle_=flow.vehicleId;seen_=true;
      // Bounded canonical documents; hashing is performed only after the cheap
      // revision/outcome guard changes, never for each idle render frame.
      const auto partText=flow.features.parts().serialize();
      const auto applied=flow.features.livery().serializedApplied();
      const auto draft=encodeLivery(flow.features.livery().draft());
      const auto careerText=flow.career.state().serialize();
      if (partText.size()>parts.maxBytes() || applied.size()>livery.maxBytes() ||
          draft.size()>livery.maxBytes() || careerText.size()>career.maxBytes()) {
        if (!failed_) sink_->event("workflow_observation_failed",{{"cause","canonical_budget"}},flow.attempt);
        failed_=true;return;
      }
      const auto partHash=Diagnostics::identity(partText),appliedHash=Diagnostics::identity(applied),
        draftHash=Diagnostics::identity(draft),careerHash=Diagnostics::identity(careerText);
      std::error_code ec;
      const auto absolute=std::filesystem::absolute(flow.store.path(),ec);
      const auto profile=ec ? std::string("unavailable") : Diagnostics::identity(absolute.lexically_normal().string());
      const auto operation=sink_->operation();
      sink_->event("workflow_state",{{"frame",frame},{"profile",profile},{"parent_operation",flow.attempt},
        {"vehicle_id",flow.vehicleId},{"screen",int(flow.screen)},{"parts_revision",next.parts},{"livery_revision",next.livery},
        {"draft_revision",next.draft},{"career_revision",next.career},
        {"parts_memory",partHash},{"applied_livery_memory",appliedHash},{"draft_livery_memory",draftHash},
        {"career_memory",careerHash},{"parts_owned",flow.features.parts().inventory().size()},
        {"applied_layers",flow.features.livery().applied().layers.size()},{"draft_layers",flow.features.livery().draft().layers.size()},
        {"livery_dirty",flow.features.livery().dirty()},{"career_running",flow.career.state().running()},
        {"career_credits",flow.career.state().credits()},
        {"career_checkpoint",flow.career.state().nextCheckpoint()},{"career_selection",flow.career.state().selection()},
        {"parts_status",int(parts.outcome().status)},{"parts_stage",documentStageName(parts.outcome().stage)},
        {"parts_errno",parts.outcome().error},{"parts_writable",parts.writable()},
        {"livery_status",int(livery.outcome().status)},{"livery_stage",documentStageName(livery.outcome().stage)},
        {"livery_errno",livery.outcome().error},{"livery_writable",livery.writable()},
        {"career_status",int(career.outcome().status)},{"career_stage",documentStageName(career.outcome().stage)},
        {"career_errno",career.outcome().error},{"career_writable",career.writable()}},operation);
    } catch (...) {
      // Diagnostics must never change gameplay behavior when serialization or
      // allocation fails. A single bounded marker is best effort, too.
      if (!failed_) {
        try { sink_->event("workflow_observation_failed",{{"cause","state_unavailable"}},flow.attempt); }
        catch (...) {}
      }
      failed_=true;
    }
  }
private:
  struct Guard {
    uint64_t parts,livery,draft,career,attempt;
    int screen;
    std::array<int,4> partsSave,liverySave,careerSave;
    bool operator==(const Guard &) const = default;
  };
  Diagnostics *sink_;
  Guard last_{};
  std::string lastVehicle_;
  bool seen_=false,failed_=false;
};
} // namespace racer
