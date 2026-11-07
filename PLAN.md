# Racer: make the garage and test loop clear

## Active goal — imported car models and physical scale

The active goal is the user's sequential car-model checklist: extract source car files with REA, import them, adapt them for Racer, complete runtime integration, then verify alignment with physics. The public `nicolas-found42/carmodels` catalog is one source, not proof that every car is supported. Latest requirements add multi-angle city-driving references, source/manufacturer dimension metadata, and explicit Juiced 2 extraction from `../raw/juiced-2/juiced-2.iso`. Work autonomously and headless, preserving existing behavior and retained evidence.

| Requirement | Verified state / remaining work |
|---|---|
| Extract source models | Pinned catalog inventory and bounded verified acquisition; GT4, MC3, MCLA and Ford pilots decoded/prepared; GT1/Redline subsequently excluded by user; assembled SLRR exterior retained. Juiced 2 ISO geometry/assembly recovered, native-rendered and installed with explicit tyre/brake limits. No all-car extraction claim. |
| Import and adapt | Strict local descriptor/GLB pipeline, source/prepared hashes, axes/metres, body bounds, four wheel pivots/radii/widths, material and texture subset. Two GT4 defaults install reproducibly; Ford, MCLA Roadster, Juiced 2, MC3 Corvette and SLRR Furrano reviewed preparations also install locally with explicit authored-fit limits. MCLA ambient is traffic-only; GT1/Redline excluded. |
| Runtime integration | Normal startup uses real NSX geometry; Garage cycles installed cars; source-derived wheelbase, steer/roll and oriented boundary envelope, geometry-based record identity and schema-v2 compatibility. Steering/reverse/reset, failed model load, selection save failure/retry/reload, livery and immutable comparisons verified. |
| Canonical proportions | Eight attributed manufacturer records, two qualified source-game records and 52 retained size/preparation rows (13 player, one deferred traffic, 38 research); 17 game frames plus two real-city photographs retained. Identical metric fixtures and camera; MC3/Ford factory track fitting, Juiced 2 tyre filtering and SLRR fixed body pose explicitly authored and reviewed. Unknown dimensions remain unknown. |
| Preserve and verify | The retained 73b640… checkpoint passed 58 targets and eleven fresh keyboard loops. Diagnostic hardening passed 59 targets, seven fresh hidden native cases, then focused checks after a Python-only repair and a final seven-image motion check on 26f179…. Both Focus tuning loops pass (37 reviewed captures each at 720p/1080p); exact builds remain distinct. No source-game runtime or human acceptance invented. |
| Continuous evidence | REA, Firecrawl and all 12 Jev capabilities used with retained decisions/reviews and explicit uncertainty. All 12 capability results indexed; low-confidence judgments remain reviewed evidence, not completion. Final integration review and remaining source/model work must precede goal closure. |

Current follow-up: [car coverage](findings/car-coverage.md), [expanded acceptance](experiments/2026-11-06-expanded-acceptance/README.md), [asset failure context](experiments/2026-11-06-asset-failure-context/coverage.md), [native coverage](experiments/2026-11-06-native-coverage/README.md), [tool coverage](experiments/2026-11-06-tool-coverage/README.md) and [verifier coverage](experiments/2026-11-06-verifier-coverage/README.md). Eleven cars passed the earlier hidden native garage/test loops; later Lightning and Ford GT acceptance is recorded separately below; exact builds and historical versus current results are retained. GT1/Redline exclusions apply throughout active work. MCLA ambient source IDs cannot be promoted by editing role flags. The remaining source corpus, held adaptations, human lap and physical hardware checks are unfinished.

Current records: [car models](experiments/2026-11-05-car-models/README.md), [catalog/installer](experiments/2026-11-05-car-catalog/README.md), [city scale](experiments/2026-11-05-city-scale/README.md), [dimension rules and retrieval](findings/car-scale.md). Keep this goal active while required implementation and verification remain.

## Historical expanded game direction — paused

This earlier broad goal was subsequently paused and replaced by the car-model checklist below. Preserve its design direction and historical evidence; do not resume unrelated feature expansion.

On2026-11-05 the user confirmed the corrected steering looked right and expanded the goal to **all remaining milestones**, with exhaustive needed-data extraction from all five donor families and reverse-engineer-anything/Jev/TypeSafe throughout decisions. This supersedes the earlier instruction to stop after feedback or leave Juiced2/MC LA queued. The earlier scope, evidence and unchecked human cases remain below as historical acceptance records; they do not prevent independent work on the expanded goal. No human lap/time or missed-gate report is inferred from “looked correct.”

Implementation breakdown preserves the full game direction in README and accepted donor contributions. Each row requires integrated behavior, persistence, regression checks and retained visual/runtime evidence; a parser/header/manual alone does not complete it.

| Milestone | Required outcome / completion evidence | State |
|---|---|---|
| M0 Existing grid/garage/test feedback | Preserve controls, handling, presets, measurements, comparisons and corrected orientation. Record remaining human/hardware observations honestly. | Implemented; human steering appearance confirmed; other human cases remain unreported. |
| M1 All-family evidence and vehicle asset pipeline | Account for needed data in bothSLRRversions, GT4, MC3, Juiced2, MC LA. Decode validated vehicle geometry/material/resource/scale/orientation references into a reproducible local import path; render/test selected vehicles, wheels, collision and attachment points. Keep exact provenance and unsupported branches. | Active: source/native and package decoding; partial data recovered, not complete. |
| M2 Modular building, parts and upgrades | Vehicle/part definitions, explicit compatibility/fitment, install/remove and inventory, persisted configurations and measurable effects; UI explains failures and preserves drafts/cancel/save behavior. Compare bothSLRRversions; native/script boundaries remain evidence-backed. | Pending M1 definitions/geometry. |
| M3 Vehicle dynamics and structured feedback | Understand handling/drivetrain/tire/suspension/tuning data needed for supported vehicles; implement and validate source-informed behavior with deterministic driving tests, immutable vehicle/setup identity and comparable feedback. Preserve accepted prototype targets and revision result identities when behavior changes. | Research active; runtime integration pending. |
| M4 Layered customization and performance classes | Juiced2-informed layer selection/order/transforms/apply/cancel/persistence and supported decal/material rendering; meaningful class/rating behavior tied to measured vehicle configuration. Verify actual decoded data versus authored rules. | Scripts/decal extraction active; behavior/formulas not yet verified. |
| M5 Routes, checkpoints and racing | MC3-informed route definitions/creation, garage-to-driving transitions, ordered directional checkpoints, start/finish/results and retry/cancel; integrated racing activities with invalidation/recovery and persisted records. | Existing fixed course is foundation; broader route/racing work pending. |
| M6 Exploration, events and career | MC LA-informed world/map navigation, discovery/eligibility/start/cancel/return for events/street challenges; connected roads/districts/garages, rewards, vehicle ownership and persistent progress/economy. Integrate car building/tuning/upgrades/racing/exploration without discarding existing free drive. | Package/event research active; implementation pending. |
| M7 Whole-game integration and acceptance | Complete connected exploration→event→reward→garage/build/tune/customize→test/compare→race→save/reload flows; keyboard and available gamepad, both sizes/resize, performance, failure recovery, telemetry/history and artifact provenance. Finish required human playtests; classify unavailable hardware/runtime evidence explicitly. | Pending earlier rows. |

All-family [execution and extraction ledger](experiments/2026-11-05-all-milestones/README.md) links per-family experiments and next unresolved questions. Use bounded hypothesis-driven extraction and reusable saved state, not bulk disc duplication or claims of full recovery while needed containers remain undecoded. Existing offline native C++20/SDL3/bgfx/Metal and no-Godot decisions remain; no multiplayer expansion was requested. Direct asset selection/provenance decisions remain individual and reviewable; analysis/extraction is authorized by the expanded goal.

---

## Earlier feedback milestone and evidence

Updated 2026-11-05. **Current state: feedback implemented; human testing exposed a render-heading defect, now corrected with retained diagnostic coverage. Human-course acceptance remains pending.** This revision records the implementation and remaining acceptance limits. The delivered scope and acceptance checklist are preserved in the [garage plan archive](findings/plans/2026-11-05-garage-tests.md); the original grid plan is [also archived](findings/plans/2026-11-05-first-playable.md).

## Completion assessment

| Area | Assessment | Evidence and limits |
|---|---|---|
| Driving foundation | Implemented and locally verified | Native macOS C++20/CMake, SDL3/bgfx Metal; independent 120 Hz simulation. Default 0–100 km/h remains 8 s and 100–0 stopping distance 38.8737 m. |
| Garage and persistence | Implemented and locally verified | A/B/C applied setups, isolated draft, Apply/Discard/Defaults, versioned atomic profile writes, malformed-file preservation and restart loading. |
| Test and comparison loop | Implemented and locally verified | Automatic acceleration/braking, five directional gates, frozen setup snapshots, valid-result storage, exact-configuration comparisons, retry and invalidation. |
| Input and integration | Keyboard and SDL virtual gamepad verified | Live loop, held-control release, focus loss and disconnect checks passed. Physical controller remains unverified. |
| Presentation | Implemented and reviewed | State-derived draft/applied/persistence/validity text, setup values/provenance/deltas, frozen test phases, offscreen heading and gate tags; dedicated panels. 83 final images include both requested drawable sizes, error/reload and resize evidence. |
| Course playability | Synthetic native completion verified; human completion unverified | Final native loops finish all five gates with left/right guidance and pause/resume; default no-capture traversal is 75.2119 s. No human lap or human miss/backtrack/boundary test is claimed. |
| Performance and sizes | Both sizes and bounded native performance verified | 1920×1080 and 1280×720 loops reviewed; live native resize/scaling inspected. No-capture drive/garage/stationary/moving samples average 119.77–120 FPS; max intervals 9.90/16.51/16.94/17.39 ms. Capture and resize stalls are separately retained, including 295.9 ms during window zoom/restore. |
| Donor contributions | Documentation/static-source directions established | No donor runtime mechanics, usable asset importer, realistic drivetrain, fitment system, career or livery system has been implemented or verified. |

Evidence: [implementation and checks](experiments/2026-11-05-garage-tests/README.md), [22-screen review and gallery](experiments/2026-11-05-garage-visual-review/README.md), [source-to-design note](findings/garage-evidence.md). The historical planning assessment reran all five then-existing CTest checks successfully and rehashed its executable to `61217ed9499e3b5294dee6dd339544b94b0d8595373c661bd32fcd7048ad44c3`, matching the reviewed build. Those planning results are retained historical evidence; the final implementation checks below supersede them. [Assessment record](experiments/2026-11-05-feedback-milestone-plan/README.md).

The garage functionality and feedback implementation pass their stated local/virtual-device checks. Presentation findings were addressed and recaptured; the human-course acceptance item remains open. Do not assign a completion percentage that mixes delivered features with the much larger long-term game direction.

## Implemented milestone: understandable tuning feedback and course guidance

**Outcome:** a player can tell what is drafted, applied and saved; identify the setup and phase being tested; understand where comparison results came from; and follow the handling course through a valid finish without consulting source code.

Prioritize the four P2 findings from the screenshot review, then the P3 visual hierarchy. Keep the existing single car, grid, handling equations, test schedules, profile schema and exact-configuration best-record semantics. Keep C++20/CMake, SDL3/bgfx Metal and pinned dependencies; Godot remains excluded. No donor assets, new physics parameters, part installation, economy, car importer, route editor, ghost/replay or career work belongs to this milestone.

### 1. Make state and save feedback truthful

Present draft state, applied setup persistence and attempt validity as distinct facts. Derive visible status from current state instead of retaining an unrelated last-success footer.

| Situation | Required visible meaning |
|---|---|
| Clean garage after load | Selected applied setup is loaded; no pending draft edits. |
| Edited draft or dirty-transition dialog | Draft not applied. Any saved-profile message explicitly refers to the previously applied setup. |
| Apply succeeds | Applied setup saved, with the selected slot identified. |
| Apply succeeds in memory but disk write fails | Applied for driving, not saved to disk; retain Retry Save and the error. |
| Malformed/unsupported profile | Original file preserved; saving disabled for this run, with recovery instructions. |
| Invalid/cancelled attempt | Attempt not saved, with the reason. It must not look like a successful result save. |
| Valid result retained or no new best | Distinguish valid completion from whether the best record changed and whether persistence succeeded. |

Back/Discard/Defaults/Keep Editing must retain their existing semantics. Result-save failure must not erase a valid on-screen result or falsely promise restart persistence.

### 2. Explain comparisons and immutable result identity

- Mark the selected slot that will run next. Show acceleration/brake/steering multipliers beside each applied A/B/C row.
- Preserve matching by car, test/course revision, handling-model revision and exact setup values. Show the originating record slot when another slot shares the values: for example, C at defaults may say “matching setup, recorded as A.” Do not imply C was driven.
- Show a clear no-comparable-result state. Do not reuse a record from different values or revisions, or relabel an old result after editing a slot.
- Show a signed delta against a named reference, with units and an explicit meaning such as “−1.333 s, faster than A.” Lower is better for the current time/distance metrics. Never compare unlike tests or automatic and player-driven results.
- Keep result snapshots frozen. Identify manual course times as player runs, whose differences do not establish a setup-only effect.

### 3. Identify the active test and phase

Show test name, setup slot and frozen values throughout countdown, running and results. Use phase-specific text: countdown; acceleration measurement; braking lead-in to 100 km/h; braking measurement; course running; valid/invalid finish. Remove “Countdown 0.0” after countdown. Make time/distance and units prominent, and show only relevant controls, including pause/cancel while automatic inputs own the car.

### 4. Make the course navigable

Identify the next gate with number/progress, distance and a heading cue that works when the gate is off-screen. Distinguish the active gate from later gates using more than height or color alone. Keep crossing direction visible and avoid obscuring the road/horizon with help panels. Derive guidance from the existing gate data and car pose; leave gate positions, crossing rules and course revision unchanged. A route change would require a separately recorded revision and invalidation of old course comparisons.

### 5. Give the loop a readable visual hierarchy

Use a dedicated garage/test/result layout, a conspicuous selected row, clear primary metric, readable setup values, distinct valid/error/unsaved states and context-specific controls. Verify at 1920×1080 and a 1280×720 drawable, including display scaling and resizing. Text must remain readable without clipping; status must not depend on color alone. Prefer a small presentation module over adding state rules to `main.cpp`; a new UI framework is not required.

## Explore the source games with bounded questions

The accepted five donor directions remain in [donor findings](findings/donor-contributions.md). **For this milestone, investigate SLRR, GT4 and MC3 only to inform state feedback, comparison context and navigation.** Juiced 2 and MC LA have queued recipes below for their later milestones; researching all five is not a prerequisite to fixing Racer's observed UI problems.

### Common procedure and evidence contract

1. Start a new `experiments/YYYY-MM-DD-<game>-<question>/README.md`. State one question, the exact canonical path, platform/build evidence, full SHA-256, tool/provider version, intended actions and stop conditions. Use [source-inputs.json](references/source-inputs.json) and the hub [input manifest](../INPUTS.json); paths in the table below are relative to `../raw/` from Racer's root. Filenames are not proof of edition.
2. Revalidate selected input existence and hashes before analysis. Reuse retained `disc-probes/`, source excerpts, manual notes and `rea-evidence.json` in the [donor inventory](experiments/2026-11-05-donor-inventory/README.md). Do not duplicate canonical discs or re-extract retained members merely to recreate a session. Selected-file digests do not identify whole installation trees.
3. Preflight free space and existing output. Bound each experiment/batch to 300 s and 256 MiB generated output with at least 20 GiB free; use tool timeouts and size limits. For initial extraction keep the earlier stricter 16 MiB/member, 32 MiB total limit. Stop on a limit or unsupported format and record what remains unknown. Preserve originals and saved analysis state under the hub storage policy.
4. Start from available source/documentation. For unfamiliar behavioral discovery read the Jevgrep skill, preview with `jg files <explicit-root> --list`, then `jg "<one behavioral question>" <explicit-root> --max-requests 8000 --concurrency 20 --max-output-bytes 20000` under a 120 s process timeout. Read excerpts and incomplete notices; wait for completion and read exact cited files. Use exact-path reads/`rg` for follow-up. Keep the configured Jev 1.14 provider pin.
5. For artifact-only questions use the shared REA tool whose schema answers that question, starting with bounded summaries and retained extracts. Reuse saved databases/exports; open analysis databases that require upgrades only on a copy. Record actual provider/version, evidence IDs, limits and commands; close native sessions. The old SLRR import record is identity/import evidence, not tuning proof, and need not be recreated if absent from the server ledger.
6. Runtime probes are conditional: first verify an existing compatible runtime and exact game build, record its version/configuration and launch command, and use a separate save/profile. Declare a short action sequence and capture only its decision states. Record unavailable runtime as a current blocker; do not infer gameplay from a manual, silently install an emulator, or change unrelated legacy projects. A donor runtime blocker does not block authored Racer presentation fixes supported by current screenshots.
7. Retain an evidence table: question → exact file/line or manual page/screenshot → observation → inference → unknown → proposed Racer behavior → verification case. Label publisher intent, static source and observed runtime separately. Hash captures and selected files, record save/reload outcomes, and keep provenance/redistribution status. No asset import is authorized by a design reference.
8. Use Jev to verify factual conclusions against the retained evidence before promoting them to `findings/`. For screenshots/transcriptions, inspect pixels directly and follow Jev's transcript screen/audit process; a text cross-check is not independent pixel proof. Update the experiment/resume entry with the next bounded action, including a blocked result when applicable.

### Per-game investigations

| Game and canonical target | Bounded question and inspection | Conditional runtime sequence and deliverable |
|---|---|---|
| **SLRR 221 and 231** — `slrr-221/StreetLegal_Redline.exe`, `slrr-231/StreetLegal_Redline.exe` | How do tuning edits become accepted/cancelled, persisted and testable? Rehash the two 231 source paths below; read Tyre lines 336–400 and Transmission 219–305. Compare 221 bundled `SLR Manual_files/Garage_Menu_Screens.htm`, items 2/9/11/13, and Main Menu save/load notes. The earlier exact-filename search found no matching loose 221 Tyre/Transmission source; packaged equivalents remain unknown. | On each available matching build: enter garage → open one tuning control → change one value → cancel → reopen; repeat with accept → test/records → save/reload. Capture before/draft/cancel/accept/test/reload and record displayed values. Deliver a two-version state-transition table; explicitly separate Tyre's draft path from Transmission's temporary mutations. Racer keeps its isolated draft; no native dyno/fitment formula claim. |
| **GT4** — `gran-turidmo-4.iso` (retain this canonical spelling); retained `gt4-SCUS_973.28` and `gt4-SYSTEM.CNF` | How are selected A/B/C settings and comparable driving feedback communicated? Check retained Sony/SCEA manual notes under “Race Settings,” “Time Trial / Ghost / Analyzer,” and Circuit practice/free-run. Match boot/serial/region evidence before attributing the manual to the local disc; SYSTEM.CNF VER=2.00 alone is not a release identifier. If refreshing the cited scan, inspect the relevant pages visually and record printed/PDF page numbers and edition. A security page supplies no evidence. | With one car and unchanged course/start: select A → edit B → return/reopen → run a practice/time trial → inspect result/comparison → reload. Capture setup identity, units, reference result and unavailable-record states. Deliver a comparison-field/provenance table, documenting features not found. Do not claim GT4 itself has Racer's automatic acceleration/braking schedules. |
| **MC3** — `mc3.iso`; retained `mc3-default.xbe` | Which garage/back/confirm cues and checkpoint indicators make a route understandable? Inspect retained Rockstar Xbox DUB manual, The Garage pp.24–25 and Race Editor pp.22–23. Resolve or preserve the conflict between original DUB metadata/manual and the historical Remix label before attributing behavior to an edition. | Navigate garage → one change → back/confirm/cancel → return to driving. Separately inspect one existing route's checkpoint sequence and, if accessible, editor start/checkpoint/finish feedback. Capture straight approach, off-screen turn, crossing, missed/wrong-way gate and finish within a bounded session. Deliver navigation/wayfinding observations mapped to Racer's fixed course; do not build a route editor in this milestone. |
| **Juiced 2 — queued** — `juiced-2/Juiced 2 - Hot Import Nights (World) (En,Fr,De,Es,It).iso`; retained `juiced2-default.xex` | Before a later livery/class milestone, establish build metadata against THQ Xbox360 manual Car Rating p.7 and Decal Editor p.8. Ask separately how layer order/selection persists and how displayed class changes after one upgrade. Do not unpack the 7z carrier when the canonical image/extract already answers the question. | One car: add/reorder/hide or remove one layer where supported → cancel/apply → save/reload; separately capture before/after rating for one upgrade. Deliver observed controls and persistence/class constraints, with unavailable operations marked unknown. No rating formula or livery importability follows from the manual. |
| **MC LA — queued** — `midnight-club-la/Midnight Club - Los Angeles - Complete Edition (USA, Europe).iso`; retained `mcla-default.xex` | Before a later world/event milestone, identify local build/edition against Rockstar manual Getting Around pp.8–9 and Career Mode pp.10–11. Ask how map markers, selected destinations and street-challenge prompts move the player into an event. Filename/manual “Complete Edition” is not independent local edition proof. | On an available build: open map → choose an event → return to street → approach/start/cancel a challenge → return to exploration. Capture marker meaning, eligibility/locked state and return path. Deliver an event-state/navigation table; do not infer an economy, route graph or career implementation from UI alone. |

Exact 231 source paths relative to `../raw/slrr-231/parts/scripts/`:

- `rgearpart/reciprocatingrgearpart/SRC/Tyre.java`, SHA-256 `7cea735bbed7b7135bfae4e99fa502bcaa57562edea0c4b1f30e33976872bb57`.
- `enginepart/slidingenginepart/reciprocatingenginepart/SRC/Transmission.java`, SHA-256 `bbf7cb991786251a732b914415e1e6401d070baf4fb559eddc47c4f9a454b60b`.

Manual links and retained note paths are in [donor findings](findings/donor-contributions.md); full disc/executable/extract digests are in the manifest. A research pass is complete when its narrow question has either cited observations or a verified blocker, and its Racer implications are explicitly labeled design choices. It need not reverse engineer an entire game.

## Implementation order

1. Create a feedback implementation experiment; record Git status, dependency pins, baseline executable/source hashes, build and five CTest results. Use isolated profiles and preserve current dirty/staged work. Reproduce review screenshots 07/08/18/05/16/19/20/21 before changing behavior.
2. Complete the bounded SLRR/GT4/MC3 source/manual passes above, reusing existing evidence where it already answers the question. Write a small evidence-to-UI decision table. Conditional runtime findings enrich this note; unavailable runtime does not stall the milestone.
3. Define presentation state from garage/profile/session facts. Add focused checks for draft/applied/save-error/invalid combinations, matching-record provenance and phase labels. Keep state/storage/measurement rules in `setup`, `profile`, `test_session` and `play_flow`; keep rendering concerns separate.
4. Implement save and comparison feedback first, then test-phase identity, then course guidance and layout. Do not alter handling equations, schema, result matching or course geometry to fix presentation. If a necessary behavior change arises, document its reason and revision/migration implications before proceeding.
5. Run the verification matrix below, capture the whole loop at both sizes, review every image, fix findings and recapture changed states. Update this plan's checkboxes only with evidence, then leave a resume entry with unresolved hardware/runtime limitations.

## Verification and completion gate

Commands below remain reproducible verification instructions; actual final commands, exits and isolated paths are recorded in the implementation experiment. Run from Racer's root. Create a fresh experiment output directory and choose a distinct absolute profile path for every modifying native check; do not reuse the normal player profile or fabricate best records for screenshot evidence.

```sh
cmake -S . -B build -G Ninja
cmake --build build -j 8
ctest --test-dir build --output-on-failure
./build/racer --verify-controls --profile /absolute/new-output/controls/profile.txt
./build/racer --verify-garage keyboard --benchmark --profile /absolute/new-output/keyboard/profile.txt
./build/racer --verify-garage gamepad --benchmark --profile /absolute/new-output/gamepad/profile.txt
./build/racer --smoke 14 --benchmark --autodrive --profile /absolute/new-output/perf-drive/profile.txt
./build/racer --smoke 14 --benchmark --scene garage --profile /absolute/new-output/perf-garage/profile.txt
./build/racer --smoke 14 --benchmark --scene course --profile /absolute/new-output/perf-course/profile.txt
shasum -a 256 build/racer
python3 ../../tools/check.py
git diff --check
```

Replace `/absolute/new-output` before running. A normal non-benchmark window is needed for the smaller drawable; record the actual measured drawable dimensions rather than assuming outer-window size. Each native check needs a <=300 s watchdog/bound; retain stdout, exit status, build hash and source manifest. `--scene course` is a stationary visibility sample; add a bounded no-capture moving-course run through the turns and identify its input method separately.

| Required verification | Evidence and pass condition |
|---|---|
| Existing behavior | All five CTest targets and live control/keyboard/virtual-pad checks pass. Default 8 s / 38.8737 m and tuning effects/caps remain unchanged; automatic measurements remain within one 120 Hz tick and 0.25 m across 30/60/144 Hz schedules. Preserve timeout, pause/focus/disconnect, wrong-order/reverse/fast crossing and invalidation coverage. |
| Status combinations | Check dirty draft after a previous successful save, Apply/Discard/Keep Editing, defaults pending Apply, valid non-best result, invalid/reset/cancel result, malformed/unsupported profile and actual unwritable save destination. Verify visible truth and saved-file bytes; use isolated fixtures and preserve the last good file. Retry Save clears the failure only after a successful write. |
| Comparison provenance | Run default A, set B acceleration to 1.20× and run B; leave C equal to A. Expect about 8.000 s / 6.667 s, active B marked, C explicitly linked to the matching record from A. Change C values and verify no comparable result until run. Check mismatched revisions and immutable prior snapshots with focused tests; verify signed delta and units. |
| Active phases | Capture acceleration countdown/running/result and braking countdown/lead-in/measuring/result. Test name, slot and frozen values remain visible; countdown disappears when finished; automatic control hints are accurate. Retry produces a fresh session and a comparable prior-best delta. |
| Complete human course | Drive all five gates through left and right turns without source/map assistance; inspect on-screen/off-screen guidance and valid finish. Also miss/backtrack a gate, pause/resume, reset and cross the boundary. Confirm invalid attempts never save a best. Synthetic feasibility remains separate evidence. |
| Persistence/rearm | Exit and launch a new process; verify selected slot, applied values and valid records. A draft never silently persists. Test held confirm/pedals on menu transitions, focus loss and active-pad removal during the loop. |
| Visual evidence | At 1920×1080 and 1280×720, capture Pause, clean garage, edited draft, dirty choice, applied save, test choice/comparison empty and populated, all test phases, valid result, retry delta, invalid result, save error/recovery, course guidance and return/reload. Review every capture for clipping, selection, units, state and horizon visibility. Record native drawable and image dimensions. |
| Physical controller | When present, record model/backend and complete the same navigation, tuning, course and rearm checks. If absent, explicitly mark this unverified; do not describe a virtual-pad pass as hardware coverage. |
| Performance | Separate no-capture samples for drive/garage/stationary course and moving course. Target >=60 average FPS at 1080p; report longest intervals and stalls, not just averages. Investigate regressions against the current build. Capture overhead must remain separately labeled. |

`--capture-loop` captures only the first visit to each principal screen; it cannot establish dirty/applied, A/B, phase or populated-compare coverage by itself. Use deliberate native screenshots or extend capture tooling to address those states. Retain a gallery with ordered captions, file hashes, action sequence, isolated profile, logs and before/after pairs for every review finding.

Milestone checklist (evidence: [feedback implementation and full matrix](experiments/2026-11-05-feedback-implementation/README.md)):

- [x] Save/draft/validity wording passes the state matrix, including errors and recovery.
- [x] Comparisons show active setup, values, provenance, missing results and meaningful deltas.
- [x] Active tests show identity and phase-specific metrics/controls.
- [ ] Course guidance supports a complete **human-driven** valid lap and invalidation cases. Synthetic native five-gate completion, reset/cancel and focused miss/boundary rules pass; human playtest remains unverified.
- [x] Both drawable sizes pass a whole-loop screenshot review; controls and primary metrics are readable.
- [x] Baseline, persistence, keyboard/virtual-pad and no-capture performance checks pass on the final build; physical hardware status is explicit.
- [x] Bounded source evidence/limitations, final hashes, logs/gallery and resume entries are retained; hub and documentation checks pass.


## Final implementation evidence — 2026-11-05

Final executable SHA-256: `3b432aed7b7f15cfc2ac22c868a497fe88f3bf2372cd87326ef3ae4f921c1725`. Six CTest targets pass, including a new presentation state/error/provenance target; the five baseline test sources and physics/setup/course/gamepad source are byte-identical to the initial manifest. Profile schema and exact-configuration record matching remain unchanged.

The [implementation experiment](experiments/2026-11-05-feedback-implementation/README.md) records every verification row, exact commands, profiles, hashes, results and limitations. Its [83-image gallery](experiments/2026-11-05-feedback-implementation/output/gallery.html) covers the full garage → tune → test → compare → return/reload loop at both sizes. A/B acceleration is 8.000/6.667 s; matching default C is explicitly recorded as A. Invalid attempts say not saved; real write failures preserve valid results and Retry Save recovery is verified. Native keyboard/virtual-pad rearm, focus loss and disconnect pass separately from the screenshot driver. A native scaled-window zoom/restore checks the live resize path.

[Source evidence-to-UI choices](findings/feedback-source-evidence.md) completes the bounded SLRR/GT4/MC3 questions using fresh hashes, retained source/manual notes and current runtime blockers. No donor gameplay, edition resolution, formula or importability claim was added. Juiced 2 and MC LA remain queued.

**Acceptance limits:** a human course lap without source/map assistance and physical-controller checks are not established. A synthetic course driver is explicitly labeled and does not satisfy the human checkbox. An intermediate 1080p capture timed out and is retained as failed evidence; final runs pass. The transient instrumentation-only baseline capture binary was not separately hashed; final evidence is fully hash-attributed. Keep the human item open until that playtest is recorded.

Before declaring completion, use Jev verification on factual research/validation claims and a single `jev_gate` on the final patch, actual test logs and completion claims. Correct contradictions, investigate uncertain findings and record how they were resolved; a judgment cannot replace running checks or inspecting pixels. Keep old evidence and report any unfinished acceptance item directly.

After this milestone, choose one bounded part/fitment or vehicle-import outcome using the accepted donor directions. Keep Juiced 2 livery/classes and MC LA exploration/events as separate future milestones until their own evidence and verification criteria are defined.

## Human incident and observability follow-up — 2026-11-05

The user reported that turning rotates the camera correctly but the car oppositely. The earlier screenshot review did not prove moving-car orientation. A regression test against the actual shared bx transform reproduced both steering signs and the gate-arrow mismatch; negating heading at that rendering boundary corrects it without changing physics or course rules. A controlled reintroduction of the old sign was rendered in a hidden window and detected by the new recorder, including an automatic anomaly screenshot. This is a new reproduction, not recovered history of the human session.

The [observability experiment](experiments/2026-11-05-observability/README.md) and [coverage inventory](experiments/2026-11-05-observability/coverage.md) cover all first-party components, dependency boundaries, priorities, implemented signals and evidence limits. The [runbook](findings/diagnostic-runbook.md) provides time/run/attempt/profile queries. Completed follow-up checks cover nine passing CTest targets, regression preservation, redaction, quota/open/write failures, restart/kill, missing shaders, failed screenshots, hidden native input checks, corrupted-log retrieval, callback-race TSan red/green and two renewed37-state loop captures on final build35fad0a5. Their [ordered gallery](experiments/2026-11-05-observability/output/final-gallery.html) includes explicit mirrored steering review. Actual outcomes and exact hashes belong to the experiment record; old results above remain historical evidence. The Jev gate escalated; stronger code review found and verified the callback-race fix. This is not described as an automatic gate pass.

Keep the human-course checkbox open until a new human lap and invalidation cases are observed. The user is using the computer: all agent-native checks must use `--background`; do not take focus. Physical-controller and donor-runtime limitations remain explicit.

## Current completion audit — 2026-11-05

The [requirement-by-requirement audit](experiments/2026-11-05-milestone-acceptance/README.md) rechecks original scope, source findings, runtime identities, all82 retained final-image hashes and both37-state loop manifests. It closes a remaining local performance gap with a fresh85s hidden no-capture traversal on corrected build35fad0a5:5 gates, valid75.2119s,120FPS, longest10.8655ms, no intervals above16.67ms. Whole-run telemetry confirms both steering directions and no capture requests. The latest [preservation pass](experiments/2026-11-05-observability-preservation/README.md) changes only offline Python tooling/tests; current C++/runtime remains hash-identical to the reviewed build.

**The milestone is blocked on human-course acceptance.** No corrected-build human report yet establishes an unassisted valid lap, missed-gate/backtrack guidance or the requested invalidation cases. The user has been asked for these observations, and the corrected app remains unopened under the no-focus constraint. Do not close the checkbox or move to another milestone until that evidence arrives or the user explicitly revises the criterion. Existing hardware/donor-runtime limits remain reported separately.

## Verified cohort continuation — 2026-11-06

- [x] Retain all 35 Ford inputs and native PS2 witnesses; 33 ordinary preparations plus one optional EX static-suspension candidate, independently preserved.
- [x] Recover four more actual Juiced 2 assemblies (Z4/MINI/Charger RT/Koenigsegg) and four MC3 assemblies (Fleetline/Saleen/Viper/Esprit); independently trace native body/wheel positions.
- [x] Review 184 static images, 37 Lightning flow captures, 14 motion captures and the new-process comparison. Retain harness failures separately.
- [x] Append year-free Ford SVT Lightning as player 12; preserve prior 11 catalog entries/order/history. Platform dimensions qualified; width convention/year/trim unresolved.
- [x] Close research capture identity collision; reject unsupported review keys with redacted correlated evidence. All 65 CTest targets pass. Current 164-source inventory retains selected-boundary scopes.
- [ ] Every in-scope car: 965 public rows are not 965 complete cars. GT1/Redline excluded; 41 MCLA ambient entries traffic-only. Native shader/unit/default activation, missing assemblies and source handling remain per-family work.
- [ ] Human unaided lap and physical controller. Scripted gate/time overrides cannot satisfy these.

[The cohort experiment](experiments/2026-11-06-cohort-acceptance/README.md) retains exact hashes, queries, failed-run dispositions and next checks. This is progress, not completion of the all-car goal.

MC3 attachment continuation: two native-page/named-anchor assemblies (Saleen/Esprit), original geometry preserved; Viper placement held. Twenty-two new images and both motion checks pass. Two research inventory rows remain ineligible; current player library stays twelve. The shared same-phase checkpoint repairs first-car write-failure attribution; current 66-target regression and 166-source inventory are retained in [the experiment](experiments/2026-11-06-mc3-attachment-acceptance/README.md). Every-car, canonical-size and original handling requirements remain open.

## Preparation registry and Ford GT checkpoint — 2026-11-06

- [x] Register 37 retained preparations as ineligible research rows, preserving all prior fifteen rows and three conflicting active Ford revisions. Audit all forty selected candidates with the actual CPU loader.
- [x] Add a bounded dry registrar with exact input snapshots, source/evidence hashes, conflict outcomes and fail-open lifecycle context. Fresh review reproduced indistinguishable early input failures; the repair and three failure paths are covered by thirteen registrar tests.
- [x] Review the original Ford GT brochure table and source/model year discrepancy; add platform-qualified dimensions and a year-free display name without whole-car scaling or changed power/handling.
- [x] Review thirteen native GT captures; verify motion, carrier, full-lock physical steering, keyboard garage loop and actual production-library new-process saved-selection reload. Append player thirteen while preserving all prior entries/order/history.
- [x] Pass 68/68 regression targets and retain a 169-file exact-hash selected-boundary inventory, with vendor/runtime boundaries explicit.
- [ ] Finish the remaining in-scope source corpus, unresolved assembly/unit/material/tyre consumers, per-car acceptance and physics compatibility. A registered research candidate is not a player. Human lap and physical-controller acceptance stay unverified.

Evidence: [registry](experiments/2026-11-06-preparation-registry/README.md), [primary reference](experiments/2026-11-06-ford-gt-reference/README.md), [GT native acceptance](experiments/2026-11-06-ford-gt-native/README.md). Active inventory: 52 rows, 13 players, one traffic preparation, 38 research candidates; active catalog SHA `3da5f93bb8a18355877d4614c7ecb4c6fb79273d67c286aa9eee602719e7327c`. The pinned public scope remains 965 entries including 41 deferred MCLA traffic entries, plus separate local ISO conversions. GT1 and Redline are completely excluded from active acquisition/adaptation/publication.

Next bounded action: address inventory capacity before expanding the remaining corpus (current 245,114-byte inventory versus 256 KiB reader limit), then resolve an attributable held source assembly/scale contract. Recheck the retained output budget before any producer; no unapproved storage increase or evidence deletion. Original donor behavior, exact Ford GT year/trim/width convention and native tyre profiles remain unproved. The full goal remains active.

## Corpus capacity continuation — 2026-11-06

- [x] Replace four independent256KiB preparation readers with shared strict16MiB/3000-record metadata handling. Keep schema1 and legacy missing-schema read shape, opaque fields, exact input bytes/hashes, role/source checks and all batch caps.
- [x] Account for both registrar inventory snapshots, report/selection and largest immutable temporary in its bounded output peak. Model64, selection256KiB, processing128MiB, publisher16 and capture7 remain separate limits.
- [x] Prove all four old readers reject the same >256KiB valid fixtures and current readers accept them. Decode/encode971 and1200 largest-observed-row-shaped research fixtures in memory; no actual corpus registration/promotion follows from this test.
- [x] Remove selection verifier all-history copytree; pin/stage only its four scenario models, cap selected payload64MiB and all reads128MiB. Retain original indices/catalog/input hashes and exact read/write failure owner. Validate actual four-model subset with native CPU loader and retrieve a controlled errno28 staging failure in a separate process.
- [x] Pass70/70 regression targets after updating an obsolete copytree failure fixture to the actual catalog-read boundary. Retain first failed test run, corrected10 lifecycle cases, source hashes and172-file selected-boundary inventory.
- [ ] Complete the remaining actual car extraction/adaptation/integration/physics work. Inventory capacity is not970 accepted cars; current13 installed players and52 preparation rows are unchanged. New GPU selection flow remains unrerun; earlier exact-model render evidence remains separate.

Evidence: [capacity experiment](experiments/2026-11-06-inventory-capacity/README.md). No game C++ or player assets changed. A319-byte research subset catalog is retained for actual CPU validation; active catalog remains `3da5f93bb8a18355877d4614c7ecb4c6fb79273d67c286aa9eee602719e7327c`. Next: resolve an attributable held native tyre/rim, source pose or canonical-scale contract before player promotion, using retained inputs and rechecking the small remaining output allowance before any new producer. All-car goal stays active; GT1/Redline excluded, MCLA ambient traffic-only.

## Juiced2 native wheel contract — 2026-11-06

- [x] Freshly resolve current ISO XEX identity; reuse retained decoded memory/translations without another extraction/database. Record `.rdata`43-byte discrepancy and unexported `.reloc`; do not confuse PE raw-file and memory layouts.
- [x] Trace type3 packed profile loader/getter to constructor:13 stored knots, flag0,12 integer-anchor samples. Recover actual min/max fields and paired sizing/matrix/material consumers with selected raw-byte corroboration.
- [x] Implement bounded audit/kernel preserving setter rounding order; nine fixtures compare against a restricted native-word interpreter and exercise malformed/domain/missing-input/late-write diagnostics. Actual ISO audit passes; full71-target regression passes.
- [x] Retain the TyreCode parser→renderer bridge and caller adjustments; mark demonstration callee registers separately from unverified per-car/upgrade state and mutable overrides.
- [x] Annotate four existing held Juiced2 rows with exact source evidence, preserving every old field, other48rows, all13 player entries and all GLB geometry. No eligibility change.
- [ ] Establish actual per-car inputs/resource state and continuous curve/shader construction; implement and review the resulting wheel geometry before promotion. Existing sharedToyo fit remains authored. Human/controller/source-game runtime and the remaining corpus are unfinished.

Evidence: [wheel contract](findings/juiced2-wheel-contract.md), [experiment](experiments/2026-11-06-juiced2-wheel-consumer/README.md). Current inventory52rows/13players SHA `3fb258cfeddaaa854e2c456176221cc2b69249caa1b0d32af40b7f2e12f23c4f`; active catalog remains `3da5f93bb8a18355877d4614c7ecb4c6fb79273d67c286aa9eee602719e7327c`. New source inventory174files at selected boundaries, with171unchanged hashes inherited. No Ghidra target or original game process was used. Next trace actual per-car TyreCode/resource f4/runtime override selection and verify native geometry construction, within a new measured reservation. Keep all-car goal active, GT1/Redline excluded and MCLAambient traffic-only.
