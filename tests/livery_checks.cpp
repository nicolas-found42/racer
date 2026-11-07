#include "livery.h"
#include <cstdlib>
#include <iostream>
#include <limits>
using namespace racer;
void check(const auto &value, const char *message) {
  if (!value) { std::cerr << "FAIL: " << message << '\n'; std::exit(1); }
}
int main() {
  LiveryEditor editor;
  check(!editor.dirty() && editor.draft().valid(), "initial valid empty state");
  check(editor.add("authored_stripe"), "add first layer");
  auto first = editor.draft().selected;
  check(editor.applied().layers.empty() && editor.dirty(), "draft isolated from applied");
  check(editor.add("authored_roundel"), "add second layer");
  auto second = editor.draft().selected;
  check(second != first, "stable unique identifiers");
  check(editor.moveSelected(-1), "reorder towards back");
  check(editor.draft().layers.front().id == second && editor.draft().selected == second, "selection survives reorder");
  auto before = editor.draft();
  check(editor.moveSelected(-1).error == LiveryError::OutOfRange && editor.draft() == before, "edge move transactional");
  check(editor.moveSelected(2).error == LiveryError::OutOfRange, "reject ambiguous reorder");
  DecalTransform transform{.25,-.5,.5,2,90,.125};
  check(editor.setTransform(transform), "edit transform");
  check(editor.setVisible(false), "hide layer");
  check(editor.apply() && !editor.dirty(), "apply complete snapshot");
  auto encoded = editor.serializedApplied();
  LiveryEditor loaded;
  check(loaded.loadApplied(encoded) && loaded.applied() == editor.applied(), "roundtrip every ordered field");
  check(loaded.serializedApplied() == encoded, "canonical stable roundtrip");
  check(editor.removeSelected(), "remove selected");
  check(editor.draft().selected == first && editor.applied().layers.size() == 2, "remove chooses neighbor and preserves applied");
  check(editor.cancel() && editor.serializedApplied() == encoded && !editor.dirty(), "cancel restores order selection transforms visibility");
  auto invalid = transform; invalid.opacity = std::numeric_limits<double>::quiet_NaN();
  before = editor.draft();
  check(editor.setTransform(invalid).error == LiveryError::InvalidTransform && editor.draft() == before, "nonfinite edit rejected without mutation");
  invalid = transform; invalid.scaleX = 0;
  check(editor.setTransform(invalid).error == LiveryError::InvalidTransform, "degenerate scale rejected");
  check(editor.add("../../private").error == LiveryError::InvalidDecal && editor.draft() == before, "catalog key is not path");
  auto applied = editor.applied();
  for (const std::string bad : {
        "RACER_LIVERY 2\n1 0 0\nEND\n", "RACER_LIVERY 1\n-1 0 0\nEND\n",
        "RACER_LIVERY 1\n2 0 1\n1 stripe 0 0 1 1 0 1 1\nEND\n",
        "RACER_LIVERY 1\n3 1 2\n1 stripe 0 0 1 1 0 1 1\n1 stripe 0 0 1 1 0 1 1\nEND\n",
        "RACER_LIVERY 1\n2 1 1\n1 stripe 0 0 1 1 0 nan 1\nEND\n",
        "RACER_LIVERY 1\n2 1 1\n1 stripe 0 0 1 1 0 1 2\nEND\n",
        "RACER_LIVERY 1\n1 0 33\nEND\n"}) {
    check(!editor.loadApplied(bad), "reject malformed/versioned document");
    check(editor.applied() == applied && editor.draft() == before, "failed load preserves both snapshots");
  }
  check(!editor.loadApplied(encoded + "trailing"), "reject trailing data");
  check(!editor.loadApplied(std::string(maxLiveryDocumentBytes + 1, 'x')), "bounded input");
  LiveryState destination = applied;
  check(!decodeLivery(encoded.substr(0, encoded.size()/2), destination) && destination == applied, "free decoder also rolls back");
  check(editor.clearDraft() && editor.dirty() && editor.applied() == applied, "clear is draft-only");
  check(editor.apply() && editor.applied().layers.empty(), "apply clear");
  check(editor.removeSelected().error == LiveryError::NoSelection, "empty removal");
  for (size_t i=0; i<maxLiveryLayers; ++i) check(editor.add("stripe"), "fill bounded layers");
  before = editor.draft();
  check(editor.add("stripe").error == LiveryError::LayerLimit && editor.draft() == before, "cap preserves valid draft");
  check(editor.draft().valid(), "all operations retain invariant");
  LiveryEditor exhausted;
  check(exhausted.loadApplied("RACER_LIVERY 1\n4294967295 0 0\nEND\n"), "load exhausted but valid ID state");
  check(exhausted.add("stripe").error == LiveryError::IdentifierExhausted && !exhausted.dirty(), "identifier exhaustion rejects without mutation");
  std::cout << "PASS: livery draft/apply/cancel, stable order and IDs, transforms/visibility, roundtrip and malformed-load rollback\n";
}
