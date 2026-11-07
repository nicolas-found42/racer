# Ford Racing 2 complete static car adapter

Question: convert pinned Ford preview's explicit source-named low-speed assembly into a complete Racer vehicle with separately pivoted wheels and validated geometry.

Input: carmodels commit ce047799fc550cdf92e4f7b62d97ef5c603e53ad; MACH1_SIXTY preview949636bytes SHA2560f1ae9c4ed637eac967e00377afe4989eff21c55ddfabdfc2f0804c552a9d85f, retained at ../2026-11-05-other-car-families/output/assets/objects/<sha>.glb. Original source-model hash inside preview0ccf798cb857dcfcff41ab76a23a56aad9e43119164540831b301293715a2021. No source/native files modified.

Bounds: commands<=300s, generatedoutput<=256MiB, source<=16MiB/selectedbatch<=32MiB, free>=20GiB. Hidden/source-only; no GUI/nativeREA binding. Preserve staged/dirty work/playerprofiles. Own only new prepare_ford_vehicle.py and fixture tests.

Current evidence: defaultscene0 contains28 independent records, not an assembly. Scene6 explicitly sourceTree0/visibilityPreset low_speed has source-derived state inputs and original serialized translations. Reachable11nodes contain body, four source-named wheel nodes under HUB_FRONT/BACK_LEFT/RIGHT parents, brake/reverse lights off. Front hubs positiveZ/rightpositiveX match Racer axes. Candidate interpretation, runtimeLOD/GSshading remain unverified.

External retrieval: guessed tools/export_models.py404. FullrecursiveGitHubtree Firecrawl request was terminated after slow live wait; provider completion unknown. Peer then reported sameURLtimedout300s earlier; do not repeat fullrecursive request. Use bounded tools-directory listing instead. Tool transport limitations are not evidence that no Ford exporter exists.

## Implementation and observed verification

Added `scripts/prepare_ford_vehicle.py` and `tests/ford_vehicle_checks.py`. The adapter selects only the explicit scene, validates its source-named HUB/WHEEL ownership and static state, preserves source binary geometry/materials, and emits a RACER_VEHICLE1 descriptor with four wheel pivots and body groups. It rejects malformed transforms, graphs, index budgets, ambiguous scenes, mismatched configuration joins, and output replacement. Outputs are exclusive/private and retain source identity, actual bounds, fitting parameters and limitations.

Primary pinned exporter/state sources are retained as `output/reference-export_geometry_candidates.py` and `output/reference-recover_visibility_presets.py`. The source cardata and tyre declarations are retained in `output/source-config`; their hashes and line numbers are also copied into the preparation receipt. They establish CAR_MODEL_YEAR1973 and TXT_CARS_MUSTANG_1973 despite the opaque MACH1_SIXTY identifier. This is a 1973 source-game identity; exact trim/manufacturer dimensions remain unverified here.

Per root's authorized fitting decision, front/rear wheel radii are explicitly fitted from raw approximately0.3125 to source-config0.312/0.324, using Y/Z scales0.9983998095703488/1.0367996044923384 at the original source hubs. Lateral scale stays1: actual complete-wheel widths approximately0.257518 are distinct from configured tyre widths0.235/0.243. Source positiveZ is front, negativeX is left. Source wheelbase2.7696348428726196, body width1.9013564586639404 and length4.839231014251709 are measured export-unit values, interpreted at one unit/metre for Racer. The original game's explicit unit naming is unknown. Uniform lift0.00039657855033881084 leaves rear wheels at ground and front wheels with0.0012003238201141464 clearance; no exact four-wheel ground-contact claim.

Current retained candidate: `output/mach1-prepared-v2/207871bc4b0a5ecad2b372c896eb22945ad70587d70742d31f77cbfb480d616d.glb` (945764bytes); prepared SHA256 is its basename. Descriptor SHA25670e7ee93f4e42909b17d3da78061b9fafd2723547bf074aabfbbabdf7e848a12; receipt SHA256f45216c760fef5533a5fb7b5119b14d35ad5b883e43bb0d50ae20ab80173d99f. Source is unchanged. Older `mach1-prepared` output remains retained.

`python3 tests/ford_vehicle_checks.py` passed, including fixtures, independent world-transform containment, source joins, malformed inputs and last-good preservation. `output/checks.log` retains an initial red fixture caused by macOS /var symlink ancestry; the fixture now resolves its temporary directory and green/final logs are retained. Actual candidate vertices also independently passed body AABB and all four pivot-cylinder containment. REA repeated actual conversion headlessly with exit0 and byte-identical output: evidence ev_80e50eb5be35ee0e974029809eef145fce6b12bb543568680105f1a83bdf4a23, retained `output/rea-conversion.json`; raw PTY coverage retained7227bytes, rendered frames partially truncated, process sampling incomplete, filesystem effects not observed by that capture. Direct post-run file comparison supplies the byte-equivalence check.

Reproduce into a fresh output directory (<=15seconds in observed run):

```sh
python3 scripts/prepare_ford_vehicle.py --source experiments/2026-11-05-other-car-families/output/assets/objects/0f1ae9c4ed637eac967e00377afe4989eff21c55ddfabdfc2f0804c552a9d85f.glb --id ford-racing-2/MACH1_SIXTY --name 'Ford Mustang 1973 (MACH1_SIXTY)' --source-config experiments/2026-11-05-ford-vehicle/output/source-config --output /absolute/fresh/output
python3 tests/ford_vehicle_checks.py
```

Implementation SHA2567d8dc9e3a8c15a8972b86ed6faca1133a97715afc7f7f07306f57d1cb2482c7e; test SHA25662bc1b9eb1e9db48a136f8933edc76d2b49318ad2e03f01ff99224616c08acb1. Jev gate retained `output/jev-gate.json` escalates with low aggregate confidence and no concrete defect; root was notified and will obtain a stronger independent review. No repeated gate was used to change that outcome.

## Resume / remaining limitations

Independent review follow-up fixed a runtime-cap mismatch: input node budget is now4095 so the generated lift root cannot exceed runtime4096. Regression accepts4095 source nodes/output4096 and rejects4096 source nodes. Existing traversal allows at most63 source levels plus lift root, within runtime64; cumulative expanded index budget remains1500000. Fixture suite passed again and actual pilot GLB/descriptor remained byte-identical. Revised implementation SHA256cb5167bdf046277da08cd1e128e83c59bcf8ca9de444c3ff527ec6ea5af9e4a8; revised test SHA2568601d4061940f06a6c4d9a2cf712c920ed5019c34c543c661005fdcdeab2b16a. No repeat Jev gate; stronger reviewer verifies closure.

Files released to root for independent review and native C++ descriptor/renderer/physics integration. Native visible wheel animation, ground-contact behavior and rendering are not verified by this source-conversion experiment. Source-derived assembly is not proof of original runtime LOD/state parity; candidate normals/UV/ADC/GS shading remain as documented upstream. Original binary and source exporter facts remain retained, outputs are locally retained under ignored output directories, and no native window was opened. Next: independent review, then root's hidden native acceptance and captured multiangle motion/physics checks; keep those results separate from source and fixture claims.
