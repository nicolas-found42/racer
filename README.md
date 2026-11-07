# Racer

Racer is an original C++ open-world racing project with a working driving grid and persisted garage setup/test loop. The idea is to extract and study other racing games for car models, physics, menus, career systems, and customization, then bring supported assets and understood behavior into one coherent game.

## Original first playable milestone (historical)

Build a small, freely explorable grid before expanding the world:

- A flat ground plane with a simple road grid and visible scale markers.
- One placeholder car with acceleration, braking, steering, and reverse.
- A chase camera, speed display, and reset-to-spawn control.
- Repeatable driving checks for straight-line acceleration, braking, turning, and recovery after leaving the roads.

Completion means a player can launch the prototype, drive around the grid, and reset the car. Record the engine version, launch command, controls, and verified behavior here when implemented. The implemented grid is 1 km square with 12 m roads at 100 m spacing, authored grip handling, SDL3 input and bgfx/Metal rendering.

## Planned systems

| Area | Direction |
|---|---|
| World | Start with the driving grid; grow into connected roads, districts, garages, and event locations. |
| Cars | Establish a repeatable import path for models, materials, scale, wheels, collision, and attachment points. |
| Physics | Study handling, drivetrain, tires, suspension, and tuning; validate observations with repeatable driving scenarios. |
| Menus | Study navigation and garage flows; implement a consistent interface for Racer. |
| Career | Add events, rewards, unlocks, vehicle ownership, and persistent progress after the driving foundation works. |
| Customization | Support visual parts and performance tuning with explicit vehicle compatibility. |

The five agreed donor directions are documented in [donor contributions](findings/donor-contributions.md). The original first playable used placeholder geometry; normal startup now uses imported cars.

## Extraction and research

For each source game, record the platform, edition/build, acquisition/provenance, original size, and SHA-256 in the hub's [games/INPUTS.json](../INPUTS.json). Keep originals at `../raw/<game>.<extension>` or `../raw/<game>/`, following the [input layout](../README.md). Experiments reference those canonical originals rather than duplicating them.

Each extraction or behavior investigation starts with `experiments/<id>/README.md`: state one question, the exact input/build/hash, commands, tool/provider versions, resource limits, evidence, and result. Use the shared REA installation described in [the toolchain guide](../../docs/toolchain.md) for shipped-artifact analysis. Track provenance and redistribution permissions for imported assets; keep source-game files and unreviewed extracts local. Publish reviewed, redistributable outputs separately.

Treat menus, career, customization, and physics as systems to investigate individually. An extracted file or plausible decompilation does not establish runtime behavior or compatibility with Racer.

## Repository layout

This folder is an independent Git repository, ignored by the lab hub. The hub registers it in [projects.json](../../projects.json) and [PROJECTS.md](../../PROJECTS.md).

- `experiments/`: tracked investigation records; generated `output/` trees are ignored.
- `scripts/`: reusable extraction and conversion tools, created when needed.
- `findings/`: verified conclusions linked to experiment evidence, created when needed.
- `references/`: donor citations and asset provenance, created when needed.
- `analysis/`: ignored durable tool databases, created when needed.

Place game source and asset integration under the structure chosen for the engine. Follow the hub's [workflow](../../docs/workflow.md) and [storage policy](../../docs/storage.md) before producing captures, extracts, or databases.

## Build and play

Prerequisites on Apple Silicon: CMake, Ninja, a C++20 compiler/Command Line Tools, and SDL3 (verified with Homebrew SDL3 3.4.18). The bootstrap downloads pinned bgfx/bx/bimg sources and the bgfx CMake build wrapper. The bootstrap also installs two reviewed, hash-pinned local car preparations (GT4 NSX and 350Z). Game assets remain ignored local data; the game itself performs no network requests.

```sh
cd /Users/nicolas/Documents/github/reverse-engineering/games/racer
./scripts/bootstrap.sh
./build/racer
```

Keyboard: W/S or Up/Down for throttle and brake/reverse; A/D or Left/Right for steering; R resets; Esc pauses. Hold brake to stop, then release and press it again to reverse. Use the same release/press transition to go forward again.

Gamepad: left stick steers, right trigger accelerates, left trigger brakes/selects reverse, Y/Triangle resets, Menu/Start pauses. Pause menu: arrows/D-pad select Resume, Quit or Garage; Enter/South confirms. During a test it also offers Cancel Test. Focus loss or active-controller removal pauses automatically; release controls before resuming motion. Every Resume path requires window focus and fresh control release, including controls pressed while paused.

The chase camera stays behind in reverse. HUD speed is mph; geometry uses meters. Reset returns to the central intersection facing north. White posts along the central roads mark 100 m intervals. Roads and surrounding ground share traction; the marked boundary stops the car without damage.

## Garage and driving tests

Pause → **Garage** resets to spawn and stops simulation. Select A/B/C with left/right on the setup row. Adjust acceleration, brakes and steering response in 0.05 increments (0.80–1.20×). Apply saves; Cancel Edits discards; Restore Defaults edits only the draft. Dirty slot/Drive/Test transitions offer Apply, Discard or Keep Editing. Escape/East leaves the garage and discards the draft.

Choose **Run Test / Compare** for automatic 0–100 km/h acceleration, automatic 100–0 km/h braking, or the player-driven five-gate handling course. Tests have a three-second simulation countdown. The HUD identifies the next gate, its distance, relative turn and required crossing direction. The active gate has a projected NEXT label when visible; ground arrows mark crossing direction. A missed gate points back to its approach side. The route goes north, east, north, west, north. Countdown, acceleration measurement, braking lead-in and braking measurement each identify the frozen setup. Results distinguish valid completion, a changed best, and disk persistence, with a signed delta against the named prior best for that exact setup. The comparison panel shows applied A/B/C values, marks the next slot, and identifies the originating record slot when values match. Like-test comparisons show a signed delta against applied A; lower is better. Player runs also depend on driving skill.

Pause, focus loss and active-controller removal freeze tests. Resume/Drive/Test requires focus and released pedals, steering and confirmation buttons. Reset, Cancel Test, Garage, boundary contact or timeout invalidates the attempt. Retry starts fresh. Automatic tests ignore player driving inputs.

Profiles preserve version 1 prototype records and use version 2 when imported-car records are present; records are separated by exact vehicle geometry identity. Profiles live at `~/Library/Application Support/Racer/Racer/profile.txt` on this Mac (SDL's preference directory; the exact path is printed at launch). Applied setups, selected slot and best valid records are saved through a temporary sibling and atomic replacement. A missing profile starts with defaults. Malformed/unsupported files are preserved and saving is disabled for that run: move the original aside yourself and restart to recover. Failed writes show **Unsaved changes**; use Garage → Retry Save after fixing access. `--profile /absolute/path` selects an isolated profile for checks. No donor directory is used for saves.

## Verification

```sh
ctest --test-dir build --output-on-failure
./build/racer --verify-controls
./build/racer --smoke 14 --benchmark --autodrive
```

`--benchmark` fixes the Metal drawable at 1920×1080 even on a smaller desktop. Normal play follows the actual window dimensions. `--smoke` exits after the supplied seconds; `--autodrive` exercises acceleration, turning off-road and braking; `--verify-controls` exercises the live SDL event loop using a virtual gamepad, focus events and menu inputs. `--screenshot /absolute/path.ppm` saves one renderer capture after two seconds.

Verified on this Mac: 0–100 km/h in 8 s, 100–0 km/h in 38.9 m, 160/30 km/h forward/reverse caps, steering, boundaries, reset, deliberate direction changes, matching 30/60/144 Hz simulation results, and virtual gamepad analog controls/disconnection. The live event loop passed drive/reset, focus/disconnect pause, Resume and Quit checks. A 14 s 1920×1080 Metal run averaged **120.0 FPS** after one second of warmup in the final validation run; its longest measured frame interval was 17.3 ms. Physical gamepad behavior remains unverified because no controller was connected. This is a short local performance sample, not a guarantee for later content.

The historical garage milestone had nine CTest targets. The retained car checkpoint passed 58 targets; the latest cohort/harness checkpoint passes 65 targets, including strict review-key rejection, source cohort guards and capture identity regressions. Checks include render orientation, diagnostic storage/query, setup/storage, test sessions, playable flow and presentation state/error/provenance. Native keyboard and virtual-gamepad checks complete edit → apply → test → compare → retry/cancel → garage and read back the profile. Run them against a fresh isolated path:

```sh
./build/racer --verify-garage keyboard --profile /tmp/racer-keyboard-new/profile.txt
./build/racer --verify-garage gamepad --profile /tmp/racer-gamepad-new/profile.txt
./build/racer --smoke 14 --benchmark --scene garage
./build/racer --smoke 14 --benchmark --scene course
```

`--verify-garage` requires an explicit profile path and modifies that profile. Use a new path for each check. `--capture-loop /absolute/directory` retains one screenshot per principal screen, including tests and results. Renderer captures can cause short stalls; measure performance without captures.

Garage milestone performance: separate 14-second 1080p samples averaged about 120 FPS for free driving, garage and visible course. Longest frame intervals were 9.05, 13.52 and 16.64 ms respectively. Screenshot-producing checks reached approximately 53 ms; equivalent no-capture samples did not show that stall. These are bounded local observations. [Current evidence and limitations](experiments/2026-11-05-garage-tests/README.md). Historical resume regressions: [plan validation](experiments/2026-11-05-plan-validation/README.md).

Detailed evidence and limitations: [first-playable experiment](experiments/2026-11-05-first-playable/README.md). Dependency pins and licenses: [third-party references](references/dependencies.md).

## Current car implementation — 2026-11-06

Normal startup uses the imported GT4 Acura NSX. This checkout installs thirteen player cars: GT4 NSX, 350Z, Dodge RAM and Midget II; Ford Racing 2 Mustang, SVT Focus, SVT Lightning and GT; MCLA 350Z Roadster; ISO-extracted Juiced 2 350Z; MC3 Corvette Z06 and 350Z; and assembled SLRR Furrano. Use Garage → Car [Left/Right]. Wheels use source-derived pivots, steer with the front axle, and roll from signed travel. The simulation uses each car's wheelbase and a conservative body/wheel envelope at world boundaries. Acceleration and braking remain authored Racer handling; original donor dynamics are not claimed.

`python3 scripts/install_cars.py` installs/resumes the two defaults. The pinned source catalog has 1,435 entries; `--list` filters out the user-excluded GT1/Redline families (965 in-scope entries) and defers 41 MCLA ambient traffic models. It marks adapter eligibility and does not import every entry. Other reviewed source-family pilots are tested separately, with unresolved scale/material/assembly limitations retained. Juiced 2 actual body, interior, panels, wheels and 14 textures are recovered from the user's ISO; its fitted native Toyo tyres are an explicit adaptation; recovered stock discs roll and calipers follow steering without rolling. Native procedural tyre interpolation remains unproven. Original-game handling is not reproduced.

Canonical dimensions, source units, hashes, cross-car measurements and city screenshots are documented in [vehicle/world scale](findings/car-scale.md). Five earlier player preparations passed 20 hidden native GPU views against identical metre-scale fixtures. A newer fit review retained 20 candidate views, 21 moving-car views and 21 maximum-steering views at 1440p. MC3 uses an explicit factory wheelbase/track mount adaptation; SLRR uses an explicitly authored fixed body pose. Source originals, rejected poses and internal mesh-contact witnesses remain retained. Factory-size agreement is established only where attributed evidence supports it.

The retained 73b640… checkpoint passed **58 CTest targets**, including imported mesh bindings/hash/containment, geometry-based physics identity, profile-v2 roundtrip, cross-car comparison isolation, wheelbase-dependent turning, reverse travel and reset. Eleven fresh keyboard loops, two Focus tuning loops (37 reviewed captures each at 720p/1080p), motion captures and failed-load/save-retry/new-process reload scenarios are retained in [expanded acceptance](experiments/2026-11-06-expanded-acceptance/README.md), [import recovery](experiments/2026-11-06-import-recovery/README.md) and [asset context](experiments/2026-11-06-asset-failure-context/README.md). New diagnostic hardening is tracked separately in the [native coverage pass](experiments/2026-11-06-native-coverage/README.md); exact executable/capture hashes are recorded per run.

The user is using this computer. All unattended native checks use `--background`; do not activate windows or send desktop input. A hidden Metal window still renders and captures the actual game. Human course acceptance and physical-controller behavior remain unverified; scripted traversal cannot establish those criteria.

Retained diagnostics and the [investigation runbook](findings/diagnostic-runbook.md) support bounded local history, operation/attempt IDs, input/pose/model/camera samples, dependency outcomes, storage failures and evidence bundles. Imported cars add source/prepared/physics identity, wheelbase and signed travel. New instrumentation cannot recover events that were never retained.

Historical feedback/orientation evidence remains in [observability](experiments/2026-11-05-observability/README.md), [preservation](experiments/2026-11-05-observability-preservation/README.md) and [human acceptance audit](experiments/2026-11-05-milestone-acceptance/README.md). These older builds do not certify the new car code.

Next: resolve the held source variants and remaining source-family coverage using their exact native evidence, then complete outstanding whole-goal checks. See [coverage and prioritized holds](findings/car-coverage.md). Gran Turismo 1 and Redline are excluded entirely from active work. Ambient MCLA cars remain traffic-only. No Git staging, reset or commit was performed.

Local reviewed preparation installation (after the native validator is built):

```sh
python3 scripts/install_prepared_cars.py --id ford-racing-2/MACH1_SIXTY --id juiced-2/350Z
./build/vehicle_validate assets/local/vehicles/catalog.racer
```

This command consumes the retained local preparations referenced by `assets/catalog/prepared-sizes.json`; it does not obtain proprietary data on a clean checkout. Reproduce Juiced 2 from the canonical ISO with the [extraction commands](experiments/2026-11-05-juiced2-vehicle/README.md). Bootstrap only obtains the two reviewed GT4 defaults. Local publisher validates hashes, role/scale eligibility and native mesh containment before atomically replacing the catalog; prior versions/receipts remain retained.

Current fit and observability follow-up: [fit review](experiments/2026-11-06-fit-review/README.md), [asset context](experiments/2026-11-06-asset-failure-context/coverage.md), [native](experiments/2026-11-06-native-coverage/README.md), [offline tools](experiments/2026-11-06-tool-coverage/README.md) and [verifier lifecycle](experiments/2026-11-06-verifier-coverage/README.md). Canonical parts/livery/career memory identities bridge save failures, retries and reloads. Mesh/library failures retain same-read input identity and stage; verifier failures retain a separate bounded lifecycle record. No whole-catalog, donor-runtime, hardware-controller or human-lap completion is claimed.

The retained app checkpoint is `experiments/2026-11-06-native-coverage/output/RacerModels.app`, executable `26f179…`. Its direct launcher passed a hidden smoke from `/tmp` with the eleven-car library and MC3 350Z; actual garage pixels and runtime identities are retained. It requires this checkout's assets/shaders and installed dependencies; Finder activation, signing and standalone packaging are untested. Historical seven-car and 73b640… apps remain unchanged in their experiment directories. No app was visibly opened while the computer was in use.

Previous cohort checkpoint: [cohort acceptance](experiments/2026-11-06-cohort-acceptance/README.md) retains all 35 Ford inputs and 34 authored candidates including optional EX; four new actual Juiced 2 assemblies; and four MC3 native body/wheel assemblies with optional glass. Twelve players are installed; other candidates remain research holds. Lightning has a reviewed 37-image garage/test/compare loop, sampled motion and actual new-process reload. Its year/trim, visible-width convention and original handling remain unverified. That checkpoint has 164 exact-hash selected-boundary reviews; [observability](findings/observability.md) records vendor/runtime and failed-converter limitations. GT1/Redline stay excluded and MCLA ambient stays traffic-only. All native work stayed hidden.

Previous attachment checkpoint: [MC3 acceptance](experiments/2026-11-06-mc3-attachment-acceptance/README.md) adds source-backed optional exhaust assemblies for Saleen SR and Esprit, preserves their previous geometry, and verifies 22 new images plus sampled motion. Both remain ineligible research rows with unresolved canonical dimensions. Twelve playable cars are unchanged. All 66 regression targets pass; current selected-boundary inventory covers 166 first-party files. A reproduced write-failure attribution defect is repaired with shared lifecycle checkpoints.

Previous registry/GT checkpoint: [retained-preparation registry](experiments/2026-11-06-preparation-registry/README.md) now records 52 exact preparations: 13 players, one retained traffic preparation and 38 research candidates. Thirty-seven previously invisible preparations were registered without promoting them; three active Ford revisions were preserved on conflict. The separately reviewed [year-free Ford GT](experiments/2026-11-06-ford-gt-native/README.md) is appended as player thirteen, with 13 reviewed images, motion/carrier/full-lock and keyboard checks plus actual production-library selection/save/new-process reload. Previous twelve catalog entries/order remain unchanged. All 68 regression targets pass; 169 first-party files have selected-boundary inspection records. Registrar missing-input, late-write and unavailable-diagnostics failures are now exercised; historical evidence and remaining limits are in the [runbook](findings/diagnostic-runbook.md). GT1/Redline remain excluded, MCLA ambient remains traffic-only, and the all-car goal remains unfinished. All native runs remained hidden.

Previous capacity checkpoint: [inventory capacity](experiments/2026-11-06-inventory-capacity/README.md) gives all four preparation readers a shared strict16MiB/3000-record format while retaining small processing/publication/capture batches. Actual files above the former256KiB limit pass each consumer; 1200 large research rows fit in memory without any new player approval. The selection verifier stages four pinned scenario models rather than every historical asset, with64MiB model and128MiB aggregate read bounds plus retained read/write ownership. Current inventory/catalog remain52rows/13players. All70 regression targets pass; current first-party selected-boundary inventory has172files. Fresh CPU validation of the actual four selected models and a retained injected late-write failure pass; the updated verifier's GPU flow was mocked, not freshly rendered. The full car corpus and source/human/hardware acceptance remain unfinished.

Latest resume: [Juiced2 wheel contract](findings/juiced2-wheel-contract.md) links the current ISO executable to retained native analysis, recovers the12-of13 anchor scan and sizing/matrix/material paths, and implements a bounded audit/kernel with nine tests. Actual ISO audit and71-target regression pass. Four held Juiced2 rows gain source evidence only; all remain ineligible and the13-player catalog is unchanged. Incoming per-car/resource state, mutable multiplier and shader deformation still block native stock-wheel application. No game geometry/physics or new GPU acceptance changed this phase.
