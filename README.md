# Racer

UI/HUD rebuild (branch `feat/ui-hud-fidelity`, not yet merged): see [UI/HUD experiment](experiments/2026-11-08-ui-hud/README.md); next action there is a Jev-backed review once its key is available. Active visual work in the Codex worktree: [source streets, HDR and graded placement](experiments/2026-11-07-source-street/README.md), [rough reflection and streetscape](experiments/2026-11-07-reflection-street/README.md), [responsive HUD and surface detail](experiments/2026-11-07-hud-surface/README.md), [lighting and material finish](experiments/2026-11-07-lighting-finish/README.md), [city art](experiments/2026-11-07-city-art/README.md), [visual calibration](experiments/2026-11-07-visual-calibration/README.md) and [original six-game investigation](experiments/2026-11-07-visual-fidelity/README.md). The city, source-bound sky, lighting/material pipeline, directional shadows, local reflection probe and HUD are being compared with actual source-game screenshots. The large-budget Xbox360/PS3 visual target remains unmet; passing tests do not certify it. Existing canonical checkout changes/assets are preserved.

The authored optical finish now uses bounded RGBA16F MSAA scene targets, linear HDR bloom and final-only tone mapping before the HUD. `--post-neutral` disables bloom/grading while retaining the final HDR display mapping; it is no longer an identity copy. An actual native shared-post probe distinguishes 1/4/8-unit radiance and linear alpha blending. This is authored rendering, not a recovered donor pipeline or visual-quality acceptance. Local prepared city scenery now includes authored ambient occlusion and a finish limited to qualified dedicated window materials. Optional guarded silver/crimson paint and exact trim finishes are available through `scripts/prepare_mcla_lamp_preview.py --authored-rims --authored-paint crimson --authored-trim` with its pinned input arguments and a fresh output path. These palettes are authored; they do not recover the native palette. The separate Roadster lamp/rim preview is selected with `--vehicle-library assets/visual-local/roadster-finish-v2/catalog.racer` and an isolated `--profile`; it has not replaced the canonical vehicle catalog. Native lamp palettes, refraction and rim subslot BRDF remain unknown.

The HUD uses an aspect-correct safe area and compact presentation in small windows. Medium driving views retain corner cards with enlarged secondary text; menus page earlier. Local reflections use complete generated cube mips and explicit base/coat roughness levels; this box-filtered linear HDR approximation does not establish native or GGX equivalence. The asset renderer accepts bounded embedded UV0 normal textures, filters their mips as linear vectors and preserves supplied tangent frames; absent frames use an authored derivative approximation. A separate source-bound city detail preview is available through `--scenery-mesh assets/visual-local/city-detail-v1/city.glb`. Its R/A reconstruction is explicitly authored; native channel packing and shader behavior are unresolved. The reviewed four-house variant, including authored stairs, AO and this normal detail, is now the owned local default city. The original city is retained under `assets/visual-local/city-ao-before-variety`; canonical assets are unchanged.

The optional source-neighborhood preview accepts up to four `--world-mesh` files with an authored `--world-heading`/`--world-origin` mount. Static textures share exact decoded-pixel/dimension/data-role identities within the existing 64MiB unique RGBA limit. `--follow-ground` requires an explicit world and imported vehicle, fits all four wheel bottoms to eligible opaque up-facing triangles, and applies the same rigid pose to car, wheels, shadows, camera and reflection center. Missing or inconsistent support stops the preview with diagnostics; it does not extrapolate a road. This is visual placement, not suspension or native collision physics. The current source street still has visible open boundaries and has not replaced the default city.

The separate [source material investigation](experiments/2026-11-07-native-materials/README.md) adds an optional `RACER_source_bump_spec` normal-only profile for exact qualified CityBumpSpec primitives. It preserves signed source tangent W, computes the bitangent per vertex and samples source R/A as linear data; packed G/B remain unapplied. Standard glTF normal maps retain their existing path. This selected compiled shader reconstruction does not establish original runtime declarations, lighting, mips or pixel equivalence. Actual running curb before/after and reference comparisons are retained; the scene still falls short of the visual target.

Optional local surface preparation uses the user's supplied SLRR input and keeps all prepared pixels ignored:

```sh
python3 scripts/prepare_world_surfaces.py --source /Users/nicolas/Documents/github/reverse-engineering/games/raw/slrr-231/maps/textures
```

The hash-pinned version2 atlas includes asphalt, paving, masonry and alpha-masked palm crowns. Without it the authored city uses procedural surfaces and geometric foliage. `--world-surfaces /absolute/path/surfaces.rgba` selects a retained preparation; a missing file uses that fallback, and malformed files fail explicitly. These mappings and material responses are authored adaptations; original donor shader behavior and redistribution permission remain unverified. Use `scripts/capture_visual_review.py --help` for hidden multi-view comparisons with a frozen executable/model/shader/atlas snapshot.

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

This folder is an independent Git repository with its own private remote, `https://github.com/nicolas-found42/racer`. The lab hub ignores the checkout and registers it in [projects.json](../../projects.json) and [PROJECTS.md](../../PROJECTS.md).

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

The historical garage milestone had nine CTest targets. The retained car checkpoint passed 58 targets; the 2026-11-06 cohort/harness checkpoint passed 65 targets (the current build passes **76/76** as of 2026-11-07, adding the car_stages, juiced2_stock_tyre_fit, juiced2_wheel_state, juiced2_native_sizing and verify_selection_reload suites; the visual-fidelity branch adds a further 25 suites for **101/101** on the merged tree (96/96 on the branch alone), 2026-11-08), including strict review-key rejection, source cohort guards and capture identity regressions. Checks include render orientation, diagnostic storage/query, setup/storage, test sessions, playable flow and presentation state/error/provenance. Native keyboard and virtual-gamepad checks complete edit → apply → test → compare → retry/cancel → garage and read back the profile. Run them against a fresh isolated path:

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

Normal startup uses the imported GT4 Acura NSX. This checkout installs seventeen player cars (the thirteen below plus Juiced 2 Z4, Cooper S, Charger R/T and CCX, published 2026-11-07 with Racer-authored stock tyre fits): GT4 NSX, 350Z, Dodge RAM and Midget II; Ford Racing 2 Mustang, SVT Focus, SVT Lightning and GT; MCLA 350Z Roadster; ISO-extracted Juiced 2 350Z; MC3 Corvette Z06 and 350Z; and assembled SLRR Furrano. Use Garage → Car [Left/Right]. Wheels use source-derived pivots, steer with the front axle, and roll from signed travel. The simulation uses each car's wheelbase and a conservative body/wheel envelope at world boundaries. Acceleration and braking remain authored Racer handling; original donor dynamics are not claimed.

`python3 scripts/install_cars.py` installs/resumes the two defaults. The pinned source catalog has 1,435 entries; `--list` filters out the user-excluded GT1/Redline families (965 in-scope entries) and defers 41 MCLA ambient traffic models. It marks adapter eligibility and does not import every entry. Other reviewed source-family pilots are tested separately, with unresolved scale/material/assembly limitations retained. Juiced 2 actual body, interior, panels, wheels and 14 textures are recovered from the user's ISO; its fitted native Toyo tyres are an explicit adaptation; recovered stock discs roll and calipers follow steering without rolling. Native procedural tyre interpolation remains unproven. Original-game handling is not reproduced.

Canonical dimensions, source units, hashes, cross-car measurements and city screenshots are documented in [vehicle/world scale](findings/car-scale.md). Five earlier player preparations passed 20 hidden native GPU views against identical metre-scale fixtures. A newer fit review retained 20 candidate views, 21 moving-car views and 21 maximum-steering views at 1440p. MC3 uses an explicit factory wheelbase/track mount adaptation; SLRR uses an explicitly authored fixed body pose. Source originals, rejected poses and internal mesh-contact witnesses remain retained. Factory-size agreement is established only where attributed evidence supports it.

The retained 73b640… checkpoint passed **58 CTest targets**, including imported mesh bindings/hash/containment, geometry-based physics identity, profile-v2 roundtrip, cross-car comparison isolation, wheelbase-dependent turning, reverse travel and reset. Eleven fresh keyboard loops, two Focus tuning loops (37 reviewed captures each at 720p/1080p), motion captures and failed-load/save-retry/new-process reload scenarios are retained in [expanded acceptance](experiments/2026-11-06-expanded-acceptance/README.md), [import recovery](experiments/2026-11-06-import-recovery/README.md) and [asset context](experiments/2026-11-06-asset-failure-context/README.md). New diagnostic hardening is tracked separately in the [native coverage pass](experiments/2026-11-06-native-coverage/README.md); exact executable/capture hashes are recorded per run.

The user is using this computer. All unattended native checks use `--background`; do not activate windows or send desktop input. A hidden Metal window still renders and captures the actual game. Human course acceptance and physical-controller behavior remain unverified; scripted traversal cannot establish those criteria.

When recording a silent native suite through REA and the review runner, set an explicit idle deadline as well as the overall deadline. The retained twelve-case standard-normal suite took about53s: a95s overall budget,90s idle budget and2s finalization completed, while the default30s idle deadline terminated its earlier partial run. Preserve failed captures and distinguish recorder termination from a renderer assertion.

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

Latest resume: [facade-v4 close-out](experiments/2026-11-08-facade-v4/README.md) closes the G2-G4/G8 lane on the visual-fidelity branch: chassis spark particles (Juiced 2 `chassis_sparks` analogue), stronger wet-road lamp streaks, a dusk-gated day green trim (×0.93, post-trim day G−R +.012 vs MCLA −.013, dusk untouched) and night road studs (MC3 `roadreflectors`/`fx_reflector` analogues). Measured: main-set night saturation .492→.427, city-set .405; 33 before/after pairs + 162 console pairs sheeted. ctest 96/96; hub check PASS. Adversarial re-review since `5735fa2` (persona Otto) found two issues, both fixed, deterministic gate exits 0. Limitations: console parity remains unmet — world density/city canyons is the dominant residual; brake/tail-light glow, headlight cone sprite, per-window glass glow, auto exposure numeric defaults unlocated; garage/cockpit not attempted; MCLA city art still blocked on the `CSR` tag. Unexecuted checks: 9 asset-dependent ctest targets skip without local source assets; jev_gate rounds escalate on confidence with zero final contradictions. Merged into `main` 2026-11-08: docs conflicts in README/PLAN/experiments index resolved semantically; merged tree builds and passes 101/101 ctest. Next: world re-bake for density; locate Juiced 2/MC3 numeric effect defaults; identify tail-light mesh sections.

Previous resume (2026-11-06 continuation): the wheel-contract checkpoint is closed (final review, 9/9 + 71/71 fresh checks, full storage accounting). [Per-car stages](experiments/2026-11-06-car-stages/README.md) reconcile all 52 curated rows (13 integrated players, 15 runtime-reviewed, 46 blocked, 919 public rows discovered-not-extracted at that report — the regenerated report after the 2026-11-07 publication is 17/19/46, `experiments/2026-11-06-car-stages/output/car-stages-v4.json` after the second review pins the final tool hash with data identical to v3; v2 report after review: `discovered` derived from public catalog / SLRR native-audit alias / experiment evidence, installed join content-hashed). [Juiced2 wheel args](experiments/2026-11-06-juiced2-wheel-args/README.md) recovers per-car stock TyreCode from the retained 94-record handling archive and attributes 350Z/Charger R/T/Koenigsegg against sourced factory specs with native sizing outputs at f4=1; f4 origin, context+684 and the missing 0x824CBE70 writer are traced (context+684 is the owner/car object, not NULL; f4 is per-car data so f4=1 is unverified); Z4 M is attributed to record 517 against BMW manufacturer specs (3246 cc exact, stock 225/45R18+255/40R18, power rpm/redline exact); MINI is resolved via an R56 gearbox-ratio match, 4 of 6 ratios identical and all six within 0.003 (record 962, all five held cars now attributed); no geometry or inventory change. An independent review found the published `extra_424` values used an unaudited term; they were recomputed bit-exact against the audited kernel (`attributions-v2.json`, v1 retained as the rejected calculation) and all four findings were repaired and re-verified (71/71 CTest, 9/9 kernel checks, stages v2, checker PASS at 13,490,046 B headroom 2026-11-07T02:34Z). [Verification pass](experiments/2026-11-06-verification-pass/README.md): 71/71 CTest, controls/garage/keyboard/gamepad checks, three 120 FPS no-capture scene samples, vehicle_validate, hub checker PASS, fresh reviewed pixels, retained-evidence retrieval verified. Previous checkpoint: [Juiced2 wheel contract](findings/juiced2-wheel-contract.md) links the current ISO executable to retained native analysis, recovers the12-of13 anchor scan and sizing/matrix/material paths, and implements a bounded audit/kernel with nine tests. Actual ISO audit and71-target regression pass. Four held Juiced2 rows gain source evidence only; all remain ineligible and the13-player catalog is unchanged. Incoming per-car/resource state, mutable multiplier and shader deformation still block native stock-wheel application. Storage headroom (~13.1 MiB checker) blocked new player publications until the 2026-11-07 allowance doubling, after which four Juiced 2 cars were published (seventeen players above); human lap and physical-controller acceptance remain pending. No game geometry/physics changed this phase. Second adversarial code review (2026-11-07): a further series of defects (tally in the review record) in the stage/wheel/fit/reload scripts, trace tools, tests and these records were repaired with targeted regression tests across the five suites (76/76 CTest); the Jev `jev_verify`/`jev_gate` checkpoints now ran and the [review record](experiments/2026-11-07-adversarial-code-review/README.md) states their limits and the final gate outcome. No installed asset, inventory pin or game code changed.
