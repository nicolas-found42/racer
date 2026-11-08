# Visual fidelity investigation — active

Goal: actual Racer rendering visually indistinguishable in quality from a large-budget Xbox360/PS3 racer. Not achieved by tests alone.

Targets: all six canonical inputs in `/Users/nicolas/Documents/github/reverse-engineering/games/raw`; identities in hub `games/INPUTS.json`, fresh selected artifact identities in REA receipts. Worktree baseline 71664dc; canonical checkout has ongoing uncommitted source/import work preserved. Worktree is the implementation target and uses read-only existing dependency/asset directories by ignored symlinks. No changes to canonical assets.

Bounds before production: volume 385GiB available; canonical Racer experiments 2.2GiB; worktree experiments 820KiB. New leaf output <=256MiB, build <=512MiB, combined project managed new output <=4GiB; commands <=300s; no bulk source extraction/new deep databases. Keep originals and analysis. Reference screenshots reuse retained actual published gameplay captures, provenance recorded in original manifest. All native rendering hidden `--background`, isolated profile, no desktop input.

Plan: inspect every source with REA, record graphics evidence separately from runtime inference; capture baseline native Racer; compare actual screenshots side by side; implement material, environment and presentation fixes; rerender/recompare each iteration. Required final visual equivalence remains open until supported by fresh images.

Review artifacts outside target: `/tmp/racer-visual-review-20261107`. Initial Jev allocation: <=60 ordinary MCP calls/150k submitted text tokens across staged investigation; direct SDK experiments require separate permission/budget. Text tools judge audited visual observations, not pixels.

Retention: all generated evidence retained. Next: establish baseline screenshots, grounded review ledger and per-source graphics findings.

## Observed source investigations

- GT4 PS2: both current ISO identity and selected `race/reflection.img` Tex1 resource proved via REA. Actual official Japanese-UI GT4 screenshot and city replay retained in `output/reference-remaining`; local US-build correspondence unknown.
- MC3 original Xbox: ISO identity, tyre bank/BC3 resource observations retained under `output/reference-console`; archived Gamespy Xbox-attributed screenshots under `output/reference-remaining`. Exact Remix edition/native resolution uncertain.
- MCLA Xbox360: corrected PPC memory carrier `d091bab…` opened with REA/Ghidra12.2;247 defined graphics-string rows include shadow render phases, ambient occlusion shadow and bloom parameter declarations. First30 rows inspected. Xrefs led to static data, not a proven executable graphics implementation. `output/mcla-native-evidence.json` and snapshot retain exact limitations. Captures from Xbox CDN through the earlier attributed reference manifest remain published frames, not local disc execution.
- Juiced2 Xbox360: full current ISO rehashed, matching XEX and46 selected source members independently checked through REA; shader declarations and source alpha-channel ambiguity retained in `output/reference-juiced`. Actual comparison image is PC/Steam gameplay; console-specific correspondence is unknown.
- SLRR221 and231: separate fresh REA PE imports/resources and actual packaged manual/mod-showcase screenshots; no original runtime launched. See `output/reference-slrr`.

Reference code/artifact observations are separate from execution. No emulator installed, no target game activated. All six canonical raw entries inspected, but investigation is bounded and native shader formulas remain largely unresolved. Original ISOs and saved state preserved.

## Actual implementation and comparison cycles

Baseline `output/comparison-baseline.png` pairs actual native Racer with actual published MCLA screenshot. Racer was flat grid, uniform sky, unlit/baked face shading, giant event arch and debug HUD.

Added original city geometry (175740 fallback vertices), proper normals/PBR factors, authored Metal sky/directional/Fresnel shading, atmospheric depth,4xMSAA,2048 directional shadow map and car contact shadow. First native shader attempts failed (v12 reflection byte layout and Metal attribute/uniform naming); logs retained in external review artifacts. `comparison-v1.png` is a black render failure, not success. `comparison-v2.png` shows initial city/lighting.

Direct pixels found false shadow bands; Metal shadow UV orientation corrected. `shadows-v1-rear.png`, `shadows-v2-rear.png` retain failures; `shadow-y.png` shows coherent shadows. Projection snapping/filtering and derivative filtering reduce instability hypotheses; exhaustive motion stability unproven.

`output/review-v3` retains four native views and actual MCLA comparisons. Source-pinned SLRR asphalt/pavers/stone atlas, distinct world glazing factors, lowered roadside event beacons, closer chase camera and CoreText driving HUD are in `output/review-v4`. Directly inspected those rear/side/motion images. Five more side-by-side sheets `comparison-v4-{gt4,mc3,juiced2-pc,slrr221,slrr231}.png` were directly inspected; mismatched scenes/cameras/platforms remain explicit.

Added one-face-per-frame double-buffered local reflection capture, corrected linear glTF material factors versus sRGB texture bytes, and styled menus/tests preserving existing text/state. `output/review-v6` retains actual native multi-angle evidence. `reflection-calibration.png` is an explicitly authored chrome sphere, not a donor car: actual reflected street facades, road and sky are visible. It validates a bounded pipeline behavior, not console car parity. `garage-loop-v7/contact.png` shows actual automatic-test/garage/compare/result panels; hidden keyboard flow passed.

Current local texture preparation uses version2 (palm crown tile replaces unused metal tile) under `assets/visual-local/v2`; version1 remains untouched. Both formats accepted with explicit foliage availability. Source materials are proprietary local data and ignored; authored mapping/scales/lighting are not donor formulas. Pixel comparisons still show repetitive architecture, simple windows, sparse street activity, incomplete foliage/lighting polish and material richness below MCLA/Juiced2. **Goal remains unmet.**

## Review, checks and retention

Run ledger `/tmp/racer-visual-review-20261107/state/review.json`, active iteration1. Selected persona Martin, vehicle look developer; seed `ce101f0ce3128a2bc059749286b3101f`, candidates digest `578a9e3d…`. Actual source-backed obsessions: environment detail, material response, preserved native flow. Targets src/tests/scripts/CMake/README/.gitignore; physics/canonical uncommitted import work preserved.

Found/fixed finite-normal overflow before normalization (independent regression), incorrect new shadow UVs, obstructive event arch/debug UI, uniform world material response, and surface preparation overwriting retained provenance. Added independent geometry/resource/reflection lifecycle tests;15 allocation-failure cases and18 capture faces cover cube isolation/cleanup in a CPU mock. Those mocks do not certify native cube seams. Shader/scene/HUD Jev reviews frequently escalated low confidence/test-gap without a concrete textual defect; stronger host inspection/native captures narrow gaps, not a clean semantic gate. Text tools only audit visual transcripts; they do not see pixels. No direct TypeSafe SDK experiment or key was used.

CTest and controls/keyboard loops have passed at intermediate snapshots; each final-source change invalidates old check freshness. Latest current check logs remain in the ledger. Hub checker PASS, canonical measured experiment output2373070133B; worktree output about107MiB before next captures, below256MiB leaf bound; build29MiB; free space385GiB+. Check actual bounds before further production.

`output/build-v4` preserves actual executable c0f099… and first-party sources, with explicit failed shader-copy issues because `.deps` is a read-only symlink. Do not call that an independently complete package. Later capture harness now retains its executable, one frozen hash-verified model/descriptor/catalog, shader pair, and surface atlas to isolate mutable canonical data. Canonical catalog was observed growing17entries; no roster/asset writes from this worktree.

Retention: all failed and successful captures, raw inputs, source snapshots, REA records and receipts retained. No Git commit/push/staging or canonical source overwrite. Remaining review findings and required semantic completion/gate remain open; no clean iteration claimed.

Next concrete actions: finish native alpha-palm validation; capture final frozen inputs through REA, rerun current tests/controls/garage/1080p timing, inspect every comparison again, resolve only substantiated fixes, then continue architecture/foliage/material detail toward the unchanged Xbox360/PS3 target.

Continuation: see `../2026-11-07-world-visual-fidelity/README.md` for textured MCLA geometry and source road-layer experiments, then `../2026-11-07-visual-calibration/README.md` for the current resume point. The earlier apparently coherent city shadows did **not** establish correct projection: a later isolated caster/receiver fixture exposed a missing Metal Y inversion. Original failing and superficially plausible images are retained; the calibration record supersedes that earlier assessment. The console-quality goal remains unmet.

Retention continuation: generated PPM duplicates are now losslessly retained as `.ppm.gz`; `output/ppm-retention.json` records full byte roundtrip, original/archive/PNG hashes and restoration. Corresponding PNG pixels were verified exact before archiving. Canonical inputs, failed images and analysis state remain preserved. Current continuation: `../2026-11-07-hud-surface/README.md`.

Closed-stage frozen Racer executables are now losslessly retained as `racer.gz` after full byte-roundtrip verification. `output/executable-retention.json` records hashes, original mode and restore commands; restore before replaying historical argv. Active builds, canonical inputs and saved analysis are unchanged.

Closed-stage frozen prepared GLB capture copies also have full-byte gzip retention; `output/frozen-input-retention.json` records exactSHA/mode/mtime and restore argv. Primary assets/raw inputs/analysis state remain in place. Restore referenced copiedGLBs before replay; town-v1 baseline excluded.
