Latest: [partial-throttle stall fixed](2026-11-09-partial-throttle-stall/README.md): the diagnosed 5–24 % analog-trigger dead zone is gone — rpm-proportional engine braking plus a sqrt pedal map (full throttle/keyboard unchanged); regression test in `driving_checks` (10 % must keep accelerating with the engine off the governor, 25 % must launch), 0 STALL flags on the 29-car probe, 106/106 ctest after re-measuring the acceleration-time pins per repo convention. Still open: human analog-trigger drive (started with the user on 2026-11-09); low-throttle upshift scheduling. Merged to `main` 2026-11-09 via [PR #5](https://github.com/nicolas-found42/racer/pull/5) (merge `9e46a69`; Before/After probe evidence pixel-verified on the saved PR); stale branches pruned — `feat/ui-hud-fidelity`, `debug/wheel-clip`, `feat/vehicle-physics` deleted, `backup/ui-hud-wip-chronology` archived at `origin` (3 superseded UI commits, conflicts with the rebuilt HUD).
- [vehicle physics patch series applied and renderer wired](2026-11-09-vehicle-physics-patches/README.md): force-based chassis/drivetrain/tyre model, ctest 106/106, 29-car terrain/benchmark/wall/slope-tyre checks, placement and low-car fixes, screenshots of six cars at several angles; chase camera tilted up to 5° and tyre smoke lightened (before/after screenshots, headless parallel capture matrix); hand drive test still open.
- [Theo workflow-video research](2026-11-09-theo-workflow-video/README.md): full transcript + primary-source deep-pass on repos shown in "Coding Isn't About Code Anymore" (t3code PR 22557 test purge, thread-transfer gate, tstack, t3code AGENTS.md); verified screenshots in evidence/screens/; two candidate adoptions (smoke gate, test audit) pending approval, no Racer code changed.
- [UI/HUD raw proof](2026-11-09-ui-hud-raw-proof/README.md): all 36 Racer HUD/UI elements paired with 119 shipped assets from MC3, GT4, SLRR and MCLA, one screenshot sheet per element, 119/119 provenance hashes pass, jev element likelihood mean 0.848 (24 likely, 12 uncertain, 0 unlikely, the uncertain ones being elements no donor ships), and MC3 gauge anchors/sweeps extracted verbatim.

# Experiments

Latest: [facade-v4 close-out: night lighting, smoke/sparks, streaks, reflectors](2026-11-08-facade-v4/README.md): sparks, stronger wet-road streaks, dusk-gated day green trim, night road studs; measured night saturation .492→.427 (city .405), day G−R +.054→+.012 vs MCLA; adversarial re-review gate exits 0. Console parity remains unmet; world density is the dominant residual.

Earlier: [comparison matrix and console-reference catalog](2026-11-07-comparison-matrix/README.md): 262 named reference crops from MCLA/GT4/MC3/Juiced 2 paired against 82 Racer frames with before/after and category sheets; still-substantial gaps catalogued per category.

Earlier: [asset mining: road, wheels, tyre marks/smoke, trees, night](2026-11-07-asset-mining/README.md); earlier: [visual resume, lens finish pass](2026-11-07-visual-resume/README.md): sun-anchored glare, filmic grade, vignette; in-game glare unverified; visual goal remains unmet.

Active source-backed material continuation: [native materials](2026-11-07-native-materials/README.md). Selected signed R/A normal kernel and actual curb comparisons; visual goal remains unmet.

- [Source streets, HDR and graded placement, active resume](2026-11-07-source-street/README.md): three qualified source blocks, exact façade restoration, shared texture admission, linear HDR and four-wheel visual placement. Fresh actual MCLA comparisons still show substantial visual gaps.

- [Rough reflection and streetscape, current resume](2026-11-07-reflection-street/README.md): source-qualified four-house city, static signals, filtered reflections, guarded paint/trim and actual reference comparisons. Console visual target remains unmet.

- [City art, current resume](2026-11-07-city-art/README.md): source-derived residential props, renderer slope correction and actual assembled-town comparisons; console visual target remains unmet.

- [Visual calibration, current resume](2026-11-07-visual-calibration/README.md): source-bound sky, exact alpha/material fixes, isolated native shadow regression, lighting/filtering review. Console visual parity remains unmet.
- [Native world visual fidelity](2026-11-07-world-visual-fidelity/README.md): shared MCLA textures and source road-marking overlays; opt-in tile-boundary pilot with missing adjacent world.

- [Visual fidelity, active](2026-11-07-visual-fidelity/README.md): all six raw inputs inspected with REA; actual source-game screenshot comparisons, authored city/material/lighting/HUD changes, local source surfaces, native fix-and-compare evidence. Console visual parity remains unresolved; review ledger stays active.

## 2026-11-06 follow-up

- [Car source coverage](2026-11-06-car-coverage/README.md): active corpus inventory, held geometry defects and eleven installed players.
- [Expanded native acceptance](2026-11-06-expanded-acceptance/README.md): ten/eleven-car checkpoints, complete Focus loops, Juiced2 template cleanup and exact retained inputs.
- [Import recovery](2026-11-06-import-recovery/README.md): native corrupted-load/save-failure/retry/restart reconstruction.
- [Asset failure context](2026-11-06-asset-failure-context/README.md): shared load-stage/input/descriptor hashes, fresh review and native verification.
- [Native coverage](2026-11-06-native-coverage/README.md): observer/capture failure isolation, transient boundary events, fresh hidden input/steering/interruption checks and retained pixel review.
- [Offline tool coverage](2026-11-06-tool-coverage/README.md): hash-bound source inventory, mixed-generation report fix and bounded compiled-data failure checks.
- [Verifier coverage](2026-11-06-verifier-coverage/README.md): retained verifier lifecycle, timeout attribution repair and aggregated first-party boundary inspection inventory.
- Source-family expansions: [GT4](2026-11-06-gt4-coverage/README.md), [Ford](2026-11-06-ford-expansion/README.md), [MCLA](2026-11-06-mcla-expansion/README.md), [MC3](2026-11-06-mc3-coverage/README.md), [Juiced2](2026-11-06-juiced2-expansion/README.md), [SLRR](2026-11-06-slrr-coverage/README.md). Metadata/source configurations remain separate from playable acceptance.

- [Fit review and seven-car publication](2026-11-06-fit-review/README.md): retained candidate/maximum-steer/motion views, strict source exclusions, explicit authored fits and local native acceptance.
- [SLRR rest fit](2026-11-06-slrr-rest-fit/README.md): exact source spring audit, rejected compression poses and independently checked fixed-pose clearance.
- [Observability coverage delta](2026-11-06-observability-delta/README.md): career/parts/livery save-state identities, failure/retry/restart reconstruction and explicit coverage limits.

- [Car pipeline stages](2026-11-06-car-stages/README.md): all52curated rows reconciled into discovered/extracted/prepared/validated/integrated/runtime-reviewed/blocked with per-row provenance;13players integrated,15runtime-reviewed,919public rows discovered-not-extracted.

- [Juiced2 wheel args](2026-11-06-juiced2-wheel-args/README.md): per-car stock TyreCode from the retained94-record handling archive;all five held cars (350Z/ChargerRT/Koenigsegg/Z4M/MINI) attributed against sourced factory specs — MINI via an R56 gearbox-ratio match (4 of 6 ratios identical, all within 0.003); committed generator imports the audited kernel; f4 origin and multiplier-writer bounded traces; four retained negative joins; no geometry or inventory change.

- [Verification pass](2026-11-06-verification-pass/README.md): current-build matrix —71tests, controls, keyboard/gamepad garage loops, three120FPS no-capture scene samples, vehicle_validate, hub checker PASS, fresh reviewed pixels, retained-evidence retrieval spot checks; capture overhead excluded from performance.

- [Held GLB publication](2026-11-06-held-glb-publication/README.md): storage limits doubled on user instruction; Z4, Cooper S, Charger R/T and CCX published (17-car library) with Racer-authored stock tyre fits; native views, motion/carrier, 37-capture 1080p garage loops and new-process selection reload passed; human lap and physical controller pending.

- [Juiced 2 native sizing trace](2026-11-06-juiced2-native-sizing/README.md): static PPC trace shows wheel context+684 is the 9672-byte car object whose +176/+192 default to 1.0 in its constructor; a later pass shows f4 is data-driven per car record (defaults 1.0/0.5), so f4=1 is an unverified assumption; authored tyre fit unchanged.

- [Adversarial code review](2026-11-07-adversarial-code-review/README.md): 19 findings in the new stage/wheel/fit/reload scripts and 17-player docs repaired (never-failing radius check, empty-evidence acceptance, prefix SHA pins, MINI 4/6 gear overclaim); five new CTest suites (76 pass); the Jev semantic checkpoints were blocked by an unconfigured provider at that pass (see the second pass below).

- [Adversarial code review, second pass](2026-11-07-adversarial-code-review/README.md): a CI-operator persona found a further series of defects, mostly low severity (exact tally in the review record), in the same stage/wheel/fit/reload scripts, trace tools, tests and docs — truncated-capture sweep abort, malformed or empty handling archives, cross-car tyre fit, an unreproducible multiplier-scan claim, a mislabelled attribution confidence/unit, stale counts, suite-wide skips on a clean checkout, a non-atomic manifest — all repaired with targeted regression tests across the five suites (76/76 CTest); `jev_verify`/`jev_gate` checkpoints now ran (typesafe/jev-1.14 via OpenRouter) with limits stated in the record.

Every investigation, including a small one-off probe, starts at `<id>/README.md`. Use the hub's templates/experiment/README.md; name IDs YYYY-MM-DD-short-question, adding a suffix when repeated. Keep commands, observations, evidence, retention, and next action together. Larger outputs may stay at established tool-required paths, linked from this record and counted in the same resource budget.

- [Current lighting/material finish](2026-11-07-lighting-finish/README.md): actual lamp-cover failure/fix, source-qualified rim finish, bounded authored LDR postprocessing and continuous terrain. Six-reference screenshot comparisons still show substantial unresolved quality gaps; no completion gate.
- [Current responsive HUD and surface detail](2026-11-07-hud-surface/README.md): actual small/wide window failure/fix, source secondary-map qualification, authored packed-normal preview, supplied tangents and native orientation fixtures; visual goal remains unmet.

- [2026-11-05-car-models](2026-11-05-car-models/README.md): active car extraction/import/runtime/physics checklist; real default cars and native integration verification.
- [2026-11-05-city-scale](2026-11-05-city-scale/README.md): city-driving reference images, canonical manufacturer/source dimensions, shared metric fixtures and seven-car native review.
- [2026-11-05-car-catalog](2026-11-05-car-catalog/README.md): pinned 1,435-entry catalog, bounded verified acquisition, reproducible two-car installer and GT4 preparation.
- [2026-11-05-mcla-vehicle](2026-11-05-mcla-vehicle/README.md): native-bone-verified 350Z preparation and explicit source-unit limits.
- [2026-11-05-ford-vehicle](2026-11-05-ford-vehicle/README.md): assembled 1973 Mustang, configured tyre fit, resource limits and independent review.
- [2026-11-05-other-car-families](2026-11-05-other-car-families/README.md): historical pilot adapters; GT1/Redline are now excluded, and later MC3 authored fitting is recorded in the current fit review.
- [2026-11-05-slrr-assembled](2026-11-05-slrr-assembled/README.md): source-slot assembled Furrano exterior and runtime preparation underway.
- [2026-11-05-juiced2-data](2026-11-05-juiced2-data/README.md): retained native archive/scripts data; separate from the newly requested mesh extraction.

- [2026-11-05-milestone-acceptance](2026-11-05-milestone-acceptance/README.md): original requirements audit,82 image hashes revalidated, corrected-build85s no-capture full-course verification; human acceptance remains blocked.
- [2026-11-05-observability-preservation](2026-11-05-observability-preservation/README.md): repeat audit; corrupt-only evidence visibility, bounded whole-run/capture bundles, moved-store retrieval and new hidden interruption verification.
- [2026-11-05-observability](2026-11-05-observability/README.md): human steering incident, render-boundary fix, codebase coverage audit, bounded retained recorder, retrieval and failure/lifecycle verification.
- [2026-11-05-feedback-implementation](2026-11-05-feedback-implementation/README.md): truthful state/comparisons, phases and course guidance; native two-size loop, verification and remaining human/hardware limits.
- [2026-11-05-slrr-feedback](2026-11-05-slrr-feedback/README.md): revalidated source/manual accept/cancel and persistence evidence.
- [2026-11-05-gt4-comparisons](2026-11-05-gt4-comparisons/README.md): setup/comparison manual context, local hashes and runtime/edition limits.
- [2026-11-05-mc3-guidance](2026-11-05-mc3-guidance/README.md): garage/checkpoint manual intent, xemu configuration blocker and edition uncertainty.
- [2026-11-05-feedback-milestone-plan](2026-11-05-feedback-milestone-plan/README.md): completion assessment; planned presentation milestone, bounded donor research and verification matrix.
- [2026-11-05-garage-visual-review](2026-11-05-garage-visual-review/README.md): 22 screenshots of the complete tuning loop; prioritized UI findings and gallery.
- [2026-11-05-garage-tests](2026-11-05-garage-tests/README.md): implemented; persisted garage setups, measured tests, native keyboard/gamepad loop and validation.
- [2026-11-05-next-milestone-plan](2026-11-05-next-milestone-plan/README.md): historical planning; proposed garage setup and measured-test loop from the completed grid.
- [2026-11-05-plan-validation](2026-11-05-plan-validation/README.md): historical; plan revalidation, focus/resume fixes and regression evidence.
- [2026-11-05-first-playable](2026-11-05-first-playable/README.md): implemented; C++/SDL3/bgfx Metal driving grid and verification.
- [2026-11-05-donor-inventory](2026-11-05-donor-inventory/README.md): current; source inventory, initial REA evidence and requirements interview.
- [2026-11-05-project-setup](2026-11-05-project-setup/README.md): completed documentation scaffold.

## Latest cohort continuation —2026-11-06

- [Root acceptance](2026-11-06-cohort-acceptance/README.md):12players,184 reviewed static images,37-image Lightning loop, actual post-retry reload,65tests and164-file boundary inventory.
- [Ford](2026-11-06-ford-cohort/README.md): all35inputs/33ordinary+1optionalEX candidates; INDIGO held.
- [Juiced2](2026-11-06-juiced2-cohort/README.md):94configuration rechecks and4new source assemblies.
- [MC3](2026-11-06-mc3-cohort/README.md):4native body/sharedwheel assemblies plus optionalglass; sharedexhaust/unit holds.
- [F150](2026-11-06-f150-contact/README.md): source pivot/contact and exactFlareside variant remain unresolved.

[MC3 attachments](2026-11-06-mc3-attachments/README.md) and [native acceptance](2026-11-06-mc3-attachment-acceptance/README.md): two source-informed exhaust candidates, 22 reviewed images, 66 passing targets, repaired failure attribution; twelve players unchanged. Exact variant/size holds remain.

## Latest preparation registry and GT continuation

- [Preparation registry](2026-11-06-preparation-registry/README.md): forty CPU-audited candidates, 37 research additions, preserved active conflicts, dry-run evidence and early-input failure repair; 68 regression targets and 169-file boundary inventory.
- [Ford GT reference](2026-11-06-ford-gt-reference/README.md): bounded original brochure and actual table-pixel review, explicit year/trim/width qualifications.
- [Ford GT native acceptance](2026-11-06-ford-gt-native/README.md): thirteen reviewed captures, motion/full-lock/keyboard, player-thirteen publication and actual new-process saved-selection reload; previous twelve entries preserved.

- [Inventory capacity continuation](2026-11-06-inventory-capacity/README.md): shared bounded metadata across four readers, actual over256KiB acceptance, full-corpus-shaped in-memory fixtures, bounded four-model selection snapshot, retained read/write failure ownership,70tests and172-source inventory. Current13players unchanged.

- [Juiced2 wheel consumer](2026-11-06-juiced2-wheel-consumer/README.md): current ISO/XEX pairing, pre-import memory-layout qualification, native12-anchor profile scan and setter/matrix/material/input bridge; bounded audit/kernel, four research evidence annotations,71tests,174-source inventory. No model promotion or new GPU acceptance.

- [MCLA tuning data](2026-11-08-mcla-city-textures/README.md): REA extraction of 941 tune files (lighting, post-processing, glow, cameras, sky) from the retail disc; recovered colorcorrect applied as a day-weighted colour balance, measured against 21+4+5 MCLA reference frames. World textures were not found by name.
- [Juiced 2 / GT4 / MC3 effect strings](2026-11-08-juiced2-rea/README.md): XEX decoded to a PPC carrier and searched with REA; GT4 ELF searched; MC3 XBE rejected by REA (string scan only). Names and addresses of the effect systems each game ships; no numeric defaults found.
- [Facade window grids and sign boards](2026-11-08-facade-windows/README.md): 16-tile RCRSURF4 atlas with procedural window grids, curtain glass and sign artwork on mid/high-rise walls; near <3-storey facades and world density remain the dominant residuals.
- [UI/HUD rebuild vs six source games](2026-11-08-ui-hud/README.md): structured menu/HUD renderer (view model, arc speedometer, street-grid radar, waypoint marker, test HUD banners, showroom camera, event map, compact rebuild), 188 reference screenshots, 12 element comparison sheets, manual strict-review ledger; Jev MCP unavailable (no key). Next: lit garage interior.
- [UI source extracts](2026-11-08-ui-source-extracts/README.md): decoded UI/HUD resources from MCLA, MC3, GT4, Juiced 2 and SLRR (193 MiB ignored output).
- [2026-11-09-garage-wheel-clip](2026-11-09-garage-wheel-clip/README.md) — garage floor layers buried tyres 7.6 cm; stage lowered below y=0
