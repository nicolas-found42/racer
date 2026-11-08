# City art — active visual comparison

The unchanged goal is Racer quality indistinguishable from a large-budget Xbox360/PS3 racer. Earlier all-six-input REA evidence and failed/partial native pilots remain in the preceding2026-11-07 experiments. The goal is unmet. This is the current continuation after renderer calibration, not a clean review or native-game reconstruction claim.

Current independent worktree: `/Users/nicolas/.codex/worktrees/4314/racer`; canonical checkout and its ongoing import changes are preserved. Review ledger `/tmp/racer-visual-review-20261107/state/review.json`, Martin persona, active iteration1. No completion gate. Native runs remain hidden, isolated-profile, no desktop activation/input. This leaf output cap256MiB; four-view producer<=64MiB and30s/run. Source prop preparation<=120s, inputs<=4MiB each, outputGLB<=12MiB,RGBA<=8MiB,vertices<=500,000,images<=64. The capture helper reserves36MiB for rendered evidence and limits frozen inputs to28MiB before writes. A four-world negative probe rejected before launch with24,813,276 retained input bytes and zeroPPMs.

## Renderer and car continuation

The previous neutral caster/receiver test exposed missing Metal shadowY inversion. A subsequent untextured slope exposed a second error: all neighboring PCF samples compared against the same receiverdepth. The actual slope-before capture failed with highpassRMS1.170554 and561 pixels above2; receiver-plane gradient correction passed withRMS.166352 and84 pixels. The exact before/after native images and manifests remain in `../2026-11-07-visual-calibration/output/slope-{before,after}/`; durable native checks are `tests/native_shadow_checks.py` and `tests/native_shadow_slope_checks.py`. Current MASK caster still passes. Independent10,000-case Jacobian/negativeY/offset math checks passed; singular/clamped/edge behavior remains bounded, not universally proven.

Actual joined MCLA tile captures after correction remove the fine road ripple, but native shader layering, street coverage and composition remain incomplete. Source tile pilot stays opt-in. Exact sourceCPU rays found54/58 nearby road receivers unoccluded, supporting the renderer investigation rather than deleting city geometry. Forcing visibility1 was a temporary isolation probe; source was restored and the real gradient repair compiled. Original probes/failures are retained.

Closer driving framing exposed sideview clipping. Centering nonrear views fixed all four reviewed body-size cases (RAM,Midget,Roadster,CCX) with actual before/fixed/reference images retained externally and queued for this leaf. Source MCLA Roadster eight exact exterior CarPaintCustomizable part families now receive explicitly authored roughness.24/metallic.25/clearcoat.9 under exactmeshSHA71a6d4ab044ba95673582f34eb9a11621fe89aeda488bea914964a2e1e6e7bd6. Lamps, interiors, wheels and unknown hashes remain unchanged. Fresh Roadster captures show local building reflections, while missing lamp/color/normal-channel semantics remain open. Original lamp bindings recovered128² illumination and256² normal maps; MaterialID10 color meaning/UV selection is unknown and no blanketred override was made.

## Qualified source props and authored placement

Two small residential shells were selected from source2300 without changing original source positions/UVs/pixels. Native objectownership remains unknown. SourceA252840B SHA`f96356963e89cd42856354a7c67a1df8777085a7320e9d0e8d33a72ba4e45e19` has ornate entry/garage on+X,16.23×22.63×10.43m bounds. SourceB124256B SHA`df53776736b51809f4196304defef985eb295d152dfe867d584ed2140220fb06` has windowed−Z front and an explicitly authored9triangle rear/eave/gable cap; original source core is separately retained. All four native sides were inspected. Failed incomplete frame/roof pilots remain retained; array preservation did not establish visual completeness.

Qualified inputs and source manifests are retained under ignored `assets/visual-local/city-source/v1`. The repeatable baker command is:

```sh
python3 scripts/prepare_city_blocks.py --prop-a assets/visual-local/city-source/v1/a.glb --sha-a f96356963e89cd42856354a7c67a1df8777085a7320e9d0e8d33a72ba4e45e19 --prop-b assets/visual-local/city-source/v1/b.glb --sha-b df53776736b51809f4196304defef985eb295d152dfe867d584ed2140220fb06 --output assets/visual-local/city
python3 tests/prepare_city_blocks_checks.py
```

Current candidate cityGLB SHA`e4c9512c1bcd2edafaa6762234d3a61b047b7d802ec2f24923435c84bcee4269`,4,893,744B,96 houses,88,320 vertices,11 draw groups,10 original encodedPNGs/933,888 decodedRGBA bytes. Six lots perblock have localX±24/Z−27,0,+27; source entrances face the nearestXstreet. Whole transformed triangles remain within the convex7..93m interior of each100m block. Placement/rotation/Yanchor and narrow source-normal normalization are authored. UV/rawcolor/PNG data remain unchanged; raw source colors are not interpreted as native AO. This is a new residential layout, not the original MCLA city.

Independent review fixed recursive texture remapping corrupting extras, missing vertical grounding and source-index allocation before cumulativebudget checks. A temporary root repair then overwrote source-node IDs with accessorIDs; a new nested-node regression caught it. The rejected prepared output is retained under ignored `assets/visual-local/city-rejected-provenance-v1`; corrected output is byte-identical to the prior qualifiedcity. Jev escalated module uncertainty; stronger source/probe review found and repaired these concrete defects. No clean code/visual judgment is claimed.

The runtime loads local cityscenery when present, keeps the flat driving roads, replaces overlapping fallback houses, and adds lawn courts, driveways, sidewalks/fences and source alpha palms. Missing local preparation retains the proceduralbuilding fallback. Explicit source `--world-mesh`/scale inspection disables this residential scenery. Actual native driving comparisons of the assembled town are the next acceptance step; source props alone do not demonstrate console-quality art.

Retention: external propworker had five historical attempts and exceeded an internal48MiB cap with duplicate generatedPPMs. It recorded13 complete pixel-equivalence/SHA receipts, retained all failedmeshes/losslessPNG evidence, and removed only redundant generatedPPMs; current~28.4MB. Canonical raw inputs unchanged. This deviation is preserved, not represented as a continuously honoredcap. Final inputs, source/evidence and saved REA analysis are being copied into this experiment before completion.

Resume: run current assembled-town actual captures, inspect side-by-side against all retained referencegame images, record/fix visible deficiencies, qualify resource/performance/workflow checks on the current snapshot, and continue. Source windows/material richness, sparse street activity, lighting polish and overall art fidelity remain unresolved until new screenshots demonstrate otherwise.

Retention continuation: generated PPM duplicates are now losslessly retained as `.ppm.gz`; `output/ppm-retention.json` records full byte roundtrip, original/archive/PNG hashes and restoration. Corresponding PNG pixels were verified exact before archiving. Canonical inputs, failed images and analysis state remain preserved. Current continuation: `../2026-11-07-hud-surface/README.md`.

Closed-stage frozen executables now have verified full-byte gzip retention; see `output/executable-retention.json` for exact SHA/mode/mtime and restore argv before replay. PNG comparisons, input assets, failed logs and saved analysis remain retained.

Closed-stage frozen prepared GLB capture copies also have full-byte gzip retention; `output/frozen-input-retention.json` records exactSHA/mode/mtime and restore argv. Primary assets/raw inputs/analysis state remain in place. Restore referenced copiedGLBs before replay; town-v1 baseline excluded.
