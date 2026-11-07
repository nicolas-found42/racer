# Vehicle fit, source exclusions and retained diagnostics

Current checkpoint: **seven local player cars installed; overall car-model goal remains active**. All work used hidden native windows and isolated profiles. No desktop focus, physical input, donor-game execution, Git staging or commit was performed.

## Question, identity and bounds

Can the remaining authored fit candidates render coherently from multiple angles, follow ordinary Racer steering/test/persistence behavior, and retain enough evidence to reconstruct failures later? A successful capture alone never grants eligibility.

Exact input mesh and descriptor SHA-256, executable identity and native commands are recorded in each manifest. The source-family experiments retain canonical input identities and REA evidence; this experiment reuses those artifacts without duplicating discs or changing originals. Initial candidates were MC3 factory-track Corvette, three SLRR compression comparisons, and MCLA Roadster v4. The SLRR minimum-travel candidate was already a known clearance failure and remained rejected.

Predeclared bounds: at most 128 MiB new output in this leaf, at least 20 GiB free, no command over 300 seconds. Capture batches have a 240-second deadline and 15-second process watchdog. Initial free space was 420 GiB and existing Racer standard outputs were about 1 GiB. Native garage checks were bounded to seven processes, 40 seconds each and 285 seconds total. All original assets, failed poses, logs and saved analysis remain retained.

## Accepted local preparations

| Source | Prepared mesh SHA-256 | Explicit adaptation and evidence |
|---|---|---|
| MCLA 2006 350Z Roadster | `71a6d4ab044ba95673582f34eb9a11621fe89aeda488bea914964a2e1e6e7bd6` | Factory-assisted tyre radii and exact glass shader allowlist; complete front wheel groups/pivots lowered 9 mm for flat ground. Independent comparison of all 91,675 positions preserves body, rear wheels, radii, widths and X/Z. |
| MC3 Corvette Z06 | `bf016ebbec38b035e17896873d7b447b5d80a88969e55f21d979b71f7acb4a3f` | Seven missing stock parts recovered by exact native joins. Uniform factory wheelbase calibration plus explicit wheel-mount X fitting to factory tracks; independent 10,174-position comparison preserves shapes, body, binary data and materials. |
| SLRR Furrano | `e2a0ef6440d2634438446d1c2254099086852939f088abea5afc75c211597025` | Fixed authored body drop 0.135724125 m with all wheel world geometry unchanged. Independently checked triangle clearance at 1,101 steering samples with a 5 mm expanded envelope. Neutral material/glass approximations and incomplete native component assembly remain visible limits. |

The two GT4 defaults, Ford Mustang and recovered Juiced 2 350Z remain installed. Juiced 2 discs roll and calipers follow the hub/steering without rolling. Original procedural tyre interpolation and donor dynamics remain unproved.

SLRR v4 changes only the incorrect `extras.racerParkedCompression.native_equilibrium` text from v3 (`fa11fb11…`). Root independently verified whole BIN equality and complete GLTF equality after removing that one field. Descriptor changes are content-address updates only. Earlier v3 still has accurate structured selected-length data; the text erratum is retained explicitly. New v4 was loaded under its actual hash in the native steering and final scale batches.

Repository-curated approval in `assets/catalog/prepared-sizes.json` is explicit Racer fit acceptance. Immutable preparation-time candidate flags remain historical records; approval does not imply donor equilibrium, shader parity, collision-free internal topology or whole-catalog coverage. `output/promotion-decision.json` selected this bounded publication option with probability .97/confidence .96 and three supported requirements. An initial tool request exceeded its three-requirement input limit and was rejected before judgment; it was corrected once. Previous broader integration/SLRR escalations remain retained, not rerolled or replaced.

## Actual verification

| Check | Retained evidence | Actual result |
|---|---|---|
| Final regression suite | `output/ctest-final45.log` | 45/45 CTest targets pass in 5.41 s. Optional NumPy surface tests also ran separately; a default environment explicitly skips those subtests. |
| Initial candidate comparison | `output/native-v1/manifest.json` | 20 hidden 1280×720 views in 70.92 s, exact asset hashes accepted. All five four-view contact sheets reviewed. Frozen executable SHA `7c4b8e878d2dfb69e51d0e646e17abbbb14b7037384fe17483a5cf5774c614e6`. |
| Candidate motion | `output/motion-mc3-v1`, `motion-slrr-v1`, `motion-mcla-v4` | Three runs each pass nine checks with seven captures: left/right, reverse, reset, numeric model alignment, sampled wheel pose and no drops. All 21 captures reviewed. Synthetic controls are explicit. |
| Maximum steering | `output/steer-v2/manifest.json` | 21 captures across seven cars at 2560×1440, stationary at 0/±0.55 rad. Actual limits and exact asset hashes confirmed; all views reviewed. No obvious outer-fender eruption or exploded parts. |
| Seven native garage workflows | `output/live-seven-v1/manifest.json` | All seven pass keyboard SDL edit/apply/test/compare, persisted load, retry/cancel and focus freeze/resume in 96.47 s total. Frozen executable `9d7dbf2cc4179822b90e0eda5ce1c44268c24e2a69b4e71c4d166d55f85c1c01`. |
| Current seven-car scale gallery | `../2026-11-05-city-scale/output/eligible-seven-v3/manifest.json` | 28 four-angle views pass in 98.21 s on executable `7a42fc7c1d3b3d8a854afe25ca453fcb7c3f51a8066086d6eb0c216ed0833f21`. All 28 reviewed; exact models, executable, histories, commands and PNG hashes retained together. |
| Parts/livery/test visual loop | `../2026-11-06-observability-delta/output/native-features-v1` | 11 screens at each of 720p/1080p, both native exits and retrieval pass. All 22 reviewed: no-engine rejection, upgrade, draft/order/apply/save, test/result/compare. Actual 6.957 s at authored 1.15× acceleration agrees with the displayed target. Build `b4636909…` predates the last career-transient/render-frame payload fields. |
| Native workflow/render correlation | `../2026-11-06-observability-delta/output/native-frame-final-retrieved.json` | Latest executable emits `workflow_state` and `livery_render` at frame 1 with matching canonical hash and vehicle identity; query exit 0. Earlier seven native runs contain 91 workflow snapshots and seven initial render events. |
| Local publication | `output/install-seven-player.json` | Seven entries pass native validation. Old assets/catalogs retained. Model upgrades now preserve Garage cycle order. |
| Source policy | `output/active-catalog-inventory-v2.json`, family test logs | Raw 1,435-row catalog unchanged; 470 GT1/Redline entries excluded from active inventory/acquisition, leaving 965 including 41 deferred traffic cars. Importer/installer/publisher checks pass 15/13/7. |

No-capture mixed-workflow samples on the seven-car garage build measured 12.51–12.61 seconds per car, 119.994–120.009 FPS, longest interval 12.1564 ms and no intervals above 16.67 ms. These are bounded local observations, not worst-case driving or capture performance. Earlier 37-state tuning loops at both sizes retain their own hashes and cannot silently be called the latest build.

The updated city gallery verifies hashes for 19 references, 28 current metric views and 21 steering captures. Factory comparisons in `output/{mc3-track,mcla-v4}-scale.json` pass the declared tolerances. References support spatial context; perspective screenshots do not establish metres.

## Failures, independent review and diagnostic usefulness

The first capture verifier queried nonexistent `mesh_sha256` instead of event `sha256`. Its false flags and exit 1 are retained in `manifest-before-query-correction.json`. Root corrected the query against the same frozen identities and raw events; all 20 pass. No native captures/events were altered or rerun for favorable flags. The first steering script parsed the catalog count as a filename; its empty `steer-v1` output is retained. The schema offset was fixed before native capture.

SLRR's most compressed pose fails clearance and remains rejected regardless of its side-view appearance. Clearance is nonmonotonic across body poses, so unsafe intermediate suspension travel is not certified. A stronger independent review reproduced 445,208 alternative triangle checks and 45,012 primitive-accessor positions, reconciling the low-confidence Jev contradiction without rerolling it. Shared loader/constants/broadphase are explicit limits.

A fresh all-car diagnostic found that filled wheel cylinders overlap legitimate internal suspension and wheelwell parts. Such reports cannot automatically reject player cars. Exact surface tests and coordinates are retained in `output/clearance-v1/`; Ford contacts begin at sampled absolute steer .45 on an inboard X=±.5 m plane, versus the outer fender around ±.95 m. No arbitrary pivot, tyre or physics clamp hides these witnesses.

Independent review caught two bugs in the new surface diagnostic: endpoint-only touch was labeled a proper crossing, and zero-pair paths could skip deadlines. Exact regressions now pass. Corrected `surfaces-v3` reports retain 432 Ford and 9,211 MC3 proper contacts; a separate scalar checker verified all 9,643 positive intersection intervals, minimum 2.427e−6 m above the 1e−8 tolerance. Earlier reports remain superseded, not deleted. Closure: `output/source-clearance-fix-closure.json`. This does not establish that mechanically intended contacts are source defects.

A publisher order test initially upgraded the last entry and could miss remove/append reordering. The strengthened first-of-two fixture now passes seven tests; an isolated reintroduction of old code fails the order assertion. Evidence: `publisher-first-of-two-{green,red}.log`. Earlier fixture setup mistakes (descriptor display name, missing second baseline entry) remain retained and are not application incidents.

The exact default-store summary query returned exit 1/no matching events (`output/default-store-query.json`). It cannot reconstruct the original human session; isolated experimental histories remain accessible. New instrumentation cannot recover unretained history. The observability delta verifies save failure → same memory state → retry → new-run reload using canonical hashes, operation links and status/stage/errno, with explicit retention/privacy limits.

## Retrieval and retention

```sh
cd /Users/nicolas/Documents/github/reverse-engineering/games/racer
./build/vehicle_validate assets/local/vehicles/catalog.racer
python3 scripts/diagnostics.py --root experiments/2026-11-06-fit-review/output/live-seven-v1/6/history --event asset_load_end --event workflow_state --event state
python3 scripts/diagnostics.py --root experiments/2026-11-05-city-scale/output/eligible-seven-v3/0-rear/history --event executable --event workflow_state --event livery_render
python3 scripts/verify_vehicle_scale.py /absolute/fresh-scale-output --limit 7
```

Exact command manifests identify which frozen assets/executable to use for reproduction. `output/final-build` preserves the latest executable, allowlisted working-tree sources and named shaders with no reported issues; it is not an atomic backup or proof of all vendor/runtime dependency correspondence. Game assets are preserved separately under `city-scale/output/eligible-seven-v3/models`. Recorder storage remains bounded and fail-open, with no calendar guarantee or automatic diagnosis. Source inputs, saved analysis, failed outputs, ownership receipts and old asset catalogs remain local and retained.

## Remaining work and resume

The complete car-model goal remains active. Remaining limits include all unreviewed catalog variants and dimensions; donor handling/suspension/shader/full component parity; continuous suspension travel; physical controller and human course acceptance; OS/GPU crash history and maximum-catalog performance. The coverage delta marks focused inspection, historical evidence and uninspected/inaccessible areas separately; no current codebase-wide completion is claimed.

Resume from the exact seven-car checkpoint. Expand source variants with bounded acquisition, primary dimension evidence and actual rendered/physics checks. Keep traffic/source exclusions enforced. Investigate intermittent failures using the updated diagnostic runbook and retained hashes before changing models or repeating old work.

## Playable local app checkpoint

`output/RacerModels.app` contains the current 7a42fc7c… executable. Its direct executable passed a three-second hidden smoke using the normal seven-car library and an isolated profile/history (`output/app-check.json`). The app was left unopened; Finder launch was not observed. It depends on this checkout's local assets/shaders and installed runtime libraries, so it is not a portable redistribution package. The older feedback/diagnostic app remains unchanged.

Final bounded claim verification returned two supported claims without contradiction (`output/checkpoint-claim-verification.json`); this verifies the stated source-exclusion/seven-car checkpoint against supplied evidence, not whole-goal completion. Hub checker and whitespace checks pass; new-document local links resolve.
