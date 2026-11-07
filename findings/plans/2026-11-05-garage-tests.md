# Racer: garage setups and driving tests — delivered

Updated 2026-11-05. **Implemented and locally validated.** The user's implementation request authorized this milestone. The original first-playable confirmation remains in the [archived plan](../../findings/plans/2026-11-05-first-playable.md). This document retains the delivered scope and acceptance criteria; the next proposed work is below. Evidence: [implementation experiment](../../experiments/2026-11-05-garage-tests/README.md).

## Starting point (before this milestone)

Racer already builds and runs natively on this arm64 Mac using C++20/CMake, SDL3 and bgfx/Metal. It has a 1 km grid, one placeholder car, independent 120 Hz simulation, interpolated chase camera, mph HUD, keyboard/gamepad input, reset and pause handling. Resume requires focus and released controls.

[Recorded validation](../../experiments/2026-11-05-plan-validation/README.md) measured 0–100 km/h in 8 s, a 38.8737 m stop, 160/30 km/h forward/reverse caps, and matching simulation results at 30/60/144 Hz. The final 14 s 1080p run averaged 119.997 FPS after warmup, with a 17.3017 ms longest interval. These are bounded historical results, not guarantees for the next build. Physical gamepad testing remains unverified.

There is no garage setup editor, persistent preset system or player-facing driving-test loop yet. Handling constants are embedded in `src/simulation.cpp`; the existing checks measure behavior outside the player flow. The current grid and placeholder geometry are sufficient for the next milestone.

## Milestone outcome

**A player can enter the garage, edit and save a setup, run a repeatable driving test, compare results, and return to revise the setup.** The same setup also works in free driving and survives restarting the application.

This advances tuning and structured driving feedback using the accepted SLRR and GT4 directions. It also creates a place to measure later upgrades and part changes before expanding the car-building system. It does not establish a permanent priority among the project's longer-term activities.

### Included

- One existing car and grid; a simple garage panel accessible from the pause menu.
- Three per-car setup slots, A/B/C, initialized to the current default handling.
- Editable prototype handling settings with Apply, Cancel and Restore Defaults.
- Two automatic straight-line measurements and one player-driven handling course.
- Results tied to the exact setup used, with meaningful comparisons.
- Local persistence for applied setups and valid test records.
- Full keyboard and gamepad navigation through the new loop.

### Deferred

Modular part installation/fitment, purchasing/upgrades/economy, multiple cars, realistic drivetrain/tyre/suspension simulation, donor assets, livery editing, opponents, race career, event discovery/map, route editor, ghosts/replay, larger world, visual editor, wheel input and multiplayer. The five accepted donor directions remain in [donor findings](../../findings/donor-contributions.md); this milestone does not require a feature from every donor.

## Player behavior

### Garage and setup editing

1. Choose **Garage** from Pause. This ends any active test without a result and places the car stationary at the central spawn, with its camera reset. Simulation stays stopped while the panel is open.
2. Select A, B or C and edit a draft. Display each setting's value, units or multiplier, valid range and short effect description.
3. Apply validates the whole draft and commits it to that slot. Cancel/back discards the draft. Switching slots with pending edits requires an explicit Apply or Discard choice. Restore Defaults changes the draft until Apply.
4. Drive or Run Test uses the selected slot's applied values. Never apply a setup midway through a simulation step or test. Leaving a menu rearms input so the confirming button or held trigger cannot launch the car.

The first controls are deliberately authored handling adjustments compatible with the current simulation:

| Setting | Proposed range | Effect |
|---|---|---|
| Acceleration strength | 0.8–1.2×, default 1.0 | Scales the current forward/reverse acceleration term; speed caps remain unchanged. |
| Brake strength | 0.8–1.2×, default 1.0 | Scales the active braking term in both directions; coast drag is unchanged. |
| Steering response | 0.8–1.2×, default 1.0 | Scales steering convergence speed; steering lock and speed sensitivity remain unchanged. |

These names and ranges are proposed Racer design values, not recovered donor specifications. Do not label them engine horsepower, tyre pressure or final drive: the simulation does not model those quantities. Preserve the existing default behavior exactly before testing variants. Later mechanical parameters should replace or extend this model only when their effects can be implemented and measured honestly.

### Tests and feedback

| Test | Execution | Result |
|---|---|---|
| 0–100 km/h acceleration | Clearly labeled automatic benchmark: reset to a fixed straight start, then apply full throttle at a simulation-step boundary. | Time to the exact threshold crossing, displayed alongside the mph equivalent. |
| 100–0 km/h braking | Automatic lead-in to 100 km/h, then full brake; exclude lead-in from the measured segment. | Distance and elapsed time from brake onset to rest, plus actual initial speed. |
| Handling course | Player drives a fixed ordered course of visible gates on the existing grid after a countdown. | Elapsed time for a valid finish; show the next gate and progress during the run. |

Author the handling route within the grid with at least four gates and both left and right turns. Define gate direction, width, start pose and finish in data. Detect segment crossings between simulation positions so fast movement cannot skip a gate; wrong-order or wrong-direction crossings do not advance progress. This is a fixed practice course, not a route editor or open-world race system.

Use simulation time for countdowns and measurements. Pause, focus loss and active-controller removal freeze the test. Resume retains the established focus/release protections. Reset, Garage, early exit or boundary contact invalidates the attempt and cannot save a best result; retry starts a fresh run. Add a bounded timeout to automatic tests so an unreachable target cannot hang the session. Player input cannot alter an automatic benchmark; Cancel remains available.

Results show test name, setup slot and immutable setup snapshot, measurements, validity and delta against a comparable prior result. Store best valid results per car, test/course revision, handling-model revision and exact setup values. Editing a slot must not relabel an old result as a run with the new values. Automatic A/B/C comparisons use identical input schedules; manual handling-course comparisons are explicitly player runs and cannot establish that a setup alone caused a better time. No medal targets or donor-equivalent performance claims are needed.

### Save and navigation behavior

- Save applied A/B/C setups, selected slot and valid records in a versioned local profile outside source and canonical donor directories; document its path.
- Validate ranges, finite numbers, IDs and schema version on load. Missing profiles use defaults; malformed/unsupported profiles produce a visible explanation without overwriting the original. Writes use a temporary file and atomic replacement; write failure preserves the last good file and reports unsaved changes.
- Keyboard arrows/Enter/Escape and gamepad D-pad/South/East operate all garage, test and result actions. Left/right adjusts a focused value; show button hints. Preserve existing driving bindings and pause behavior.

## Evidence and REA research boundary

Reuse the [donor inventory](../../experiments/2026-11-05-donor-inventory/README.md), [source identity manifest](../../references/source-inputs.json) and retained `output/rea-evidence.json`. The planning pass found the old REA record absent from the current server ledger but present in the exported bundle; do not repeat artifact scans just to recreate that session.

| Question | Existing support | Next bounded investigation |
|---|---|---|
| How should draft/apply/cancel and persistence behave? | SLRR-231 `Tyre.java` and `Transmission.java` expose saved values and apply/cancel paths in shipped source. | Revalidate selected source hashes and read the exact paths; compare corresponding behavior in the supplied SLRR-221 tree/manual. Record differences or unavailable correspondence. |
| Why three per-car presets and measured feedback? | Retained GT4 manual notes describe A/B/C setups and driving comparisons. | Preserve the cited sections and edition/OCR limits. Racer's UI and tests are authored here; exact GT4 runtime replication is not required. |
| Can donor formulas or binary behavior be reused? | Source notes identify native dyno/fitment calls; current REA evidence establishes artifact identity/imports, not those mechanics. | Keep this unresolved for this milestone. Any later claim about native effects requires focused static analysis and, for execution claims, a declared runtime probe on the matching build. |

The retained SLRR-231 import record is `ev_7a1bbca51932b9245a466ee590d6b32154ed6990576a426829936a9a98f9b0d2`; it is an identity/import reference only. Shipped Java excerpts have their own file hashes and citations in `output/slrr-source-findings.md`, not runtime authority from that REA record. Both output paths above are relative to the donor-inventory experiment.

Before new donor investigation, create `experiments/<id>/README.md` with one bounded question, canonical build/hash, commands/provider, time/output limits and evidence retention. Use source tools for available source; use REA only where artifact or runtime evidence answers the question. Reuse saved state, retain limitations and close any native session opened. If a required runtime is unavailable, record that limit and continue the authored Racer behavior above; do not invent donor results or silently install a new emulation stack.

## Implementation sequence

1. **Establish the baseline and research note.** Rebuild/run the existing checks and bounded Metal smoke test; record the exact starting executable/dependency identities. Complete the narrow source/documentation comparison above and write an evidence-to-design table. No donor launch or bulk extraction is required for this milestone.
2. **Separate setup data from simulation.** Add a validated `VehicleSetup` model and default preset. Pass applied settings into the independent simulation; keep the 120 Hz tick and existing default checks. Avoid turning `main.cpp` into the owner of garage, persistence and measurement rules.
3. **Implement garage state and storage.** Separate applied slots from the editable draft and make Apply/Cancel/Defaults/slot-switch behavior testable without SDL. Add versioned persistence, error behavior and a simple garage panel using the existing rendering stack.
4. **Implement test sessions.** Own test definitions, start/countdown/running/result/invalid states, automatic input schedules, swept gate crossing and frozen setup snapshots in a rendering-independent module. Author and validate the course within the current bounds.
5. **Connect the playable loop.** Add Pause → Garage → Drive/Test → Results → Retry/Garage navigation, gate rendering, progress/result HUD and controller mappings. Preserve pause/reset/rearm semantics across every transition.
6. **Validate and hand off.** Run the acceptance checks below, inspect the native UI, record performance and capture a complete loop. Update README, experiment/resume entries and this plan's status. Keep the plan forward-looking after the milestone is delivered.

Keep native macOS, C++/CMake, SDL3 and bgfx/Metal; pin any added dependency. Godot remains excluded. The original offline single-player direction, world dimensions, same road/ground traction and baseline driving controls remain in force.

## Acceptance checks

- [x] Default setup passes existing acceleration, braking, caps, reverse transitions, reset, bounds, off-road traction and 30/60/144 Hz checks without retuning the expected baseline.
- [x] Increasing acceleration strength reduces automatic 0–100 time; increasing brake strength reduces automatic stopping distance; steering response changes transient steering convergence. Caps and default values remain stable. Check direction and magnitude against the authored equations, not guessed donor values.
- [x] Apply/Cancel/Defaults and dirty-slot switching preserve the intended draft/applied separation. Invalid or non-finite values never reach simulation.
- [x] Applied setups and correctly attributed results survive restart. Missing, malformed, unsupported and unwritable profiles exercise the documented recovery paths without destroying a previous valid save.
- [x] Automatic measurements agree across 30/60/144 Hz presentation schedules within one 120 Hz tick for time and 0.25 m for stopping distance. Threshold crossings are interpolated within a step.
- [x] Course tests cover correct/wrong-order/reverse crossings, a fast segment crossing, finish, retry, reset/boundary invalidation and pause without time accumulation. Automatic timeout and cancellation never produce a valid record.
- [x] A keyboard user and a virtual gamepad complete edit → apply → test → compare → retry/garage → restart/load. Focus loss, disconnect and held controls are checked inside the new menus and tests. Test physical hardware when available; label virtual-only coverage if it remains unavailable.
- [x] Native 1920×1080 runs cover free driving, garage and the visible handling course, targeting at least 60 average FPS in each bounded sample. Report longest frame intervals and stalls as well as averages; investigate deviations instead of carrying forward the old benchmark.
- [x] Build, CTest, live control checks and `python3 ../../tools/check.py` pass; logs, screenshot evidence, final hashes and unresolved limitations are retained in the implementation experiment.

The persisted tune/test/compare loop is implemented. Hardware coverage is keyboard plus SDL virtual gamepad; no physical controller was available. Native screenshots and local performance samples are retained in the implementation experiment. Donor runtime mechanics remain unverified, as scoped above.

## Next proposed work

1. Playtest the course and garage with a physical controller when available; record readability, navigation and route feedback before changing handling.
2. Use the current measurements to choose the next bounded milestone: richer garage/part compatibility or a vehicle import path. Define one car and one measurable outcome before expanding scope.
3. For donor-derived mechanics or assets, first establish matching build identity and focused evidence/provenance. Preserve existing defaults and revision-keyed records when changing the handling model.

These are future recommendations, not additional work included in the delivered milestone.
