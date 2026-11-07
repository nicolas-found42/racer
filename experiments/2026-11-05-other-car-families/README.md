# Other source car families — 2026-11-05

Question: which of the pinned public six-family models retain enough explicit source wheel ownership, pivots and dimensions to become independently animated Racer vehicles without guessed body fractions?

Inputs: nicolas-found42/carmodels commit `ce047799fc550cdf92e4f7b62d97ef5c603e53ad`; catalog `../2026-11-05-car-models/output/source-catalog.json` SHA256 `fcd6eb5badd4cc120da3daaae315e83b71fb2b9400062b371b73c9f42a442e6c`. All canonical source artifacts unchanged; selected assets ignored/local only.

## Bounded acquisition / current coverage

Using `scripts/import_car_models.py acquire` with explicit five IDs and experiment-local store downloaded5 hash-verified GLBs, total5,321,460 bytes. Each<16MiB, aggregate<32MiB; commands<300s; disk424GiB available. `output/acquire.json` retains exact URLs, identities, hashes and observation. Source schema JSON copies retained for each pilot; originalGLBs in `output/assets/objects/<sha256>.glb`.

| Family | Pilot | Observed evidence / coverage |
|---|---|---|
| Ford Racing2 | MACH1_SIXTY | Raw defaultscene28record meshes; source-derived Tree0 low_speed scene6 with named hierarchy. Inspected, implementation delegated to root/ford_vehicle. Defaultscene is not an assembled driving vehicle. |
| GT1 | simulation/_a-a7r | Explicit nativeWheelIndex0..3, header/raw pivot/metre pivot, nativeWidth/nativeRadius, documented CAR/4096 Z-reflection. Adapter implemented and fixture-tested; semantic audit flagged below; original game rendering/physics inaccessible in this task. |
| MC3Remix | vp_corvettez06_03 | Named nativeWheelJoint whl00..03, separate rim/tire ownership, nativeBone source offset/global position, node quaternion/scale and source resource handles. Adapter implemented and fixture-tested; semantic audit flagged below. |
| MCLA | va_350z_04 | Ambient source embedded wheels on nativeBone4/6/8/10, matrixpivots, explicitYup/-Znose/+Xright. wheels[]empty. Inspected; implementation delegated to root/mcla_data; no nativeRSC retrieved here. |
| Redline | base/55ford_e0dfc360f3ef | Exact .car source fetched and hashmatched; source comments specify metres,+Xright/+Yup/+Zfront. WHEEL0..3 source model/pos/width/radius/suspension scale verified. Adapter implemented and fixture-tested. |
| GT4 | existing completeNSX | Not modified; root/mcla_data owns existing adapter/runtime coverage. |

No per-family roster-wide import or native runtime parity is implied by one pilot.6family totals remain catalog inventory, not playable-completeness counts.

## Retained source authority

Firecrawl retrieved pinned root/per-family READMEs and GT1/MC3/Redline exporter source. `output/reference-*` retains exact content; `output/verification.json` hashes each. Full GitHub recursive tree scrape hit host300s timeout with no tree; do not infer tree coverage. Firecrawl12req/min limit then blocked exact mc3_model fetch; bounded urllib fallback retrieved4 named source files at same pin. No global nativeREA target changed.

GT1 `gt_wheels.py`201..259 explains rawCAR coordinates before /4096,-Z and native aspect/radius scaling; `gt_model.py`635..708 exports actual wheel vertices, pivots and dimensions. MC3 `mc3_model.py`150..185 explicitly identifies nativewheelbones by source name, x-side/z-axle, globalposition;315..373 joins native wheel sourcehandles and scale, preserving nativeWheelJoint/component/bone. Native float-to-metre interpretation is the pinned export's reading; manufacturer comparison is a separate root task. Redline `redline_model.py`450..520 reads source wheel position, subtracts half maxSuspension for preview rest, applies scale[width,radius,radius] and side quaternion. `output/55ford.car`6270bytes SHA256 `25c21456e684bf4f7de5c191f24381cd81529026c64baa052ed816cbe3520e35` equals nativeConfig hash in supplied GLB. Sourcephysical values1960kg mass,150631W power,391Nm torque and inertia are retained but **not wired to Racer physics**.

Jev rerank evidence `output/adapter-priority-rerank.json` ranks GT1/Redline/MC3 highest for explicit wheel metadata. `output/wheel-metadata-audit.json` flagged GT1unit and MC3ownership claims against compact supplied summary (pwrong.82/.95), Redline claim passed. No reroll/rephrased pass attempted. Root informed and asked to stronger-review actual code snippets and actual GLB fields. **Those audit flags remain unresolved until root's independent review; test success does not dismiss them.**

## Implemented conversion

New `scripts/prepare_source_vehicle.py` supports only the3 explicit source profiles. Existing GT4 file untouched; reuses bounded GLB packing/accessor helper. It selects actual defaultscene, checks native pivot↔node/skeleton joins, requires exactly4 wheel groups, and independently copies selected per-node position/normal/tangent/index accessors before baking native world TRS. GT1/MC3 mirrorZ and winding/tangent handedness to Racer+Znose; Redline preserves native+Znose. No view-derived scale applied. Raw native custom MC3 vertex attributes remain original source arrays; they do not represent baked display positions.

Four runtime wheel bounds use actual source rim+tire vertices about exact native pivot: maximum radial distance and symmetric X extent. GT1/Redline native radius/width retained separately and crosschecked against geometry before conservative max. MC3 dimensions are geometry bounds after native source sizing, not an invented physical tire specification. Groundlift is an authored rest-placement choice. Body bounds include all selected non-wheel source geometry. Source mass/grip/performance not inferred.

Exact RACER_VEHICLE1 contract outputs: preparedSHA GLB + descriptor + receipt, node→wheel group(-1body/0..3FL..RR), fourcenters/radii/widths, bodybounds, sourcehash/preparedhash. Selectednode vertices are baked world-space so MeshAsset may subtract descriptorwheelcenter once. Existing materials/image bytes retained.

## Actual verification / retrieval

```sh
python3 tests/prepare_source_vehicle_checks.py
python3 scripts/prepare_source_vehicle.py experiments/2026-11-05-other-car-families/output/assets/objects/1132d3710c2b12310f47807298fe7cff483c32085d88c65a005d3fd3eb736c83.glb --id gran-turismo/simulation/_a-a7r --name 'GT1 pilot' --output /tmp/gt1-fresh
python3 scripts/prepare_source_vehicle.py experiments/2026-11-05-other-car-families/output/assets/objects/b0e50f8c609b770ece74ea511312a11e7b79f6e6fff6331da7ff249ba6328806.glb --id midnight-club-3-remix/vp_corvettez06_03 --name 'MC3 pilot' --output /tmp/mc3-fresh
python3 scripts/prepare_source_vehicle.py experiments/2026-11-05-other-car-families/output/assets/objects/cbcb46815ec2ecdb94f3ca86fb1e0fbf126e18adf1637b4c0fa284405e76dbc4.glb --id redline/base/55ford_e0dfc360f3ef --name 'Redline pickup' --native-config experiments/2026-11-05-other-car-families/output/55ford.car --output /tmp/redline-fresh
```

5checks pass on actual fixtures: transform handedness, all rim/tire vertices enclosed by descriptor cylinders, correct sourcehash, materials/image definitions unchanged, GT1raw↔metre pivot tamper rejected, MC3bone ownership tamper rejected, duplicate scenes and singular scale rejected, Redline missing/mutated config rejected. Old outputs preserved; current `output/{gt1,mc3,redline}-prepared-v2/` and matching `*-prepare-v2.json`; hashes/dimensions summarized `output/verification.json`.

| Pilot | Body mesh W/H/L m | Source-pivot wheelbase m | Prepared SHA256 |
|---|---|---|---|
| GT1 |1.82910156/1.07910156/4.30859375|2.43896484|cdd38cfc4a2e847538b14dddfcb710f802a39826017917cae845cb8e9c82f883|
| MC3Corvette |1.99145508/1.15161133/4.36950684|2.80439997|54d94b350b706e7349e2619941d3f88c7ccd8af753bbd0c21bb3fa07d558accb|
| RedlinePickup |1.93173003/1.57844357/4.50372577|2.87|04402b77ec472fc54b95548720e29c5d2d66ac171a27875fa05150590444437b|

Headless geometric screenshots `output/*-geometry-review.png` generated from actual prepared GLB node groups by retained `output/render-review.py` and visually reviewed: each pilot has coherent body silhouette and4 wheels in its arches, no detached/wrongly scaled groups. Painter uses no depthbuffer/alpha/texture/shader; triangle overlap artifacts cannot establish GPU rendering quality. No desktop focus taken. Runtime C++ import, animated front steering/spin, vehicle edit roundtrip, native game rendering, physics and manufacturer/world scale comparison remain root-owned/not tested here.

## Resume

Root informed adapters/fixtures ready, but GT1/MC3 semantic auditflags need stronger independent review before promotion. Root should run C++ parser on these descriptors and GPU headless multi-angle driving captures. Ford and MCLA workers own their adapters. Extend each family only after actual sourceprofile/ownership variants are exercised; no exception swallowing or generic bboxwheel fallbacks. Observed available evidence cannot claim original native physics or all1435cars complete.

### Scale conflict follow-up (new user requirement)

GM primary128page2003Corvette VehicleInformationKit was retrieved through Firecrawl, retained `output/reference-GM-2003-Corvette.md`. Manufacturer PDF URL is embedded in current adapter receipt. Lines418..419 print104.5in wheelbase and179.7inlength with inconsistent mm conversion; technicaldimensionstable3960..3961 prints104.50in(2654mm)/179.70in(4564mm). Exact inch conversion2.6543m/4.56438m is used solely for comparison, not rescaling. SourceMC3 wheelbase2.804399967m andbodylength4.369506836m differ in opposite directions, so uniform scale cannot resolve both.

Independent native-byte check: catalog-pinned `vp_corvettez06_03.dat`487424bytes SHA256 `90b26498770a4f2e4bedf1480a8bcdbc6c8c8b26533088677ffbb4a8c020a26e` fetched. Exact PCK payload242528bytes SHA256 `943255c0cbb9dc285172f3b231077c274af0a5fe6d7d33f459ed943dbe1633f9` found uniquely at DAToffset6144 by bounded16byte-alignedhashscan. All8 axl00..03/whl00..03 native68byte jointrecords were directly decoded: first3float globalpositions match GLB pivots bit-exact; name pointers resolved with sourcepointer-base+128 and equal exact jointnames. Record offsets/rawhex/nameoffsets retained `output/mc3-native-pivot-check.json`; pinned `reference-mc3_pck.py`48..49/400..435 corroborates decoder fields. Initial attempt omitted +128 pointer adapter and failedASCII decoding; corrected using actual reference formula, never treated bad bytes as names.

Supported narrowing: the adapter did not introduce the MC3wheelbase, and no cross-joint label guess is required. Unknown: artist proportions vs undocumented native runtime frame/scale behavior; actual game frames were not captured. No canonical-scale fix is justified. `output/mc3-prepared-v3/` explicitly names source-reading/scaleconflict and carries canonical_scale conflict in receipt and GLBextras. Earlier v2 retained historicalonly. Root informed not to claim canonical vehicle scale.

GT1 metadata identity is RX-7 A spec LM Edition, nativebase CARINFspecs4280L/1760W/1230H/2425WBmm, provenance includes nativeCARINF/SYSTEM hashes. Racebody/mirrors/spoiler need not equal nativebase specs. Bodyboxheightspan1.0791 excludes ground clearance: actual restground-to-bodytop1.227169m agrees closely with native1.23m. MC3meshwidth1.991m includesmirrors; GM1.869m excludesmirrors, so those width figures are not equivalent comparisons. Script now retains `vehicle_ground_dimensions` separately from bodybox dimensions and native canonical metadata separately from conservative mesh bounds. Root owns online manufacturer comparisons and world-size review.5fixturechecks still pass after these explicit distinctions.

Latest retained outputs are now `output/{gt1,mc3,redline}-prepared-v4/`, matching `*-prepare-v4.json`, and `output/latest-pilots.json`. GT1preparedSHA `8584f9ed8e4c18a3655e95d033e59b8f2dc791db471838f072b8d607a9fc29c9`, MC3 `42656509fd7501d7c97b02484ab6b7da3d9f191b7d486f32dfc3519d9532e259`, Redline `f858e52a5015339032c530d2404d324cc0a6eccd8935455b28438218f6dfb074`. Groundtop heights respectively1.227169/1.290704/1.883444m; totalvisible width includesmirror/wheel-envelope scope, not manufacturerwidth definition.

REA target-free artifact probe `output/rea-native-pivot-probe.json`, Evidence `ev_d31545dd8255186b7580ef570db79e7f65594e1a9221c24291f6814347824193`, ran bounded Python rawDAT/PCK hash+float probe exit0. It corroborates rawPCKfront/rearpositions and catalogsourcehashes, not originalgameexecution. No filesystemwatchpaths/networkinstrumentation selected; short processsampler was incomplete. Existing native session untouched. No later semantic audit reroll performed.

### Strong review / provenance correction

Root's independent strong review resolved the GT1/MC3 ownership and geometry audit concerns narrowly against actual source fields and code. A separate P2 claim bug remained: shared receipt wording said all exports were metres. Fixed family-specific authority: MC3 native physical units explicitly unverified, chosen importfactor1 an authored assumption with manufacturer conflict retained; GT1 pinned exporter /4096 metre convention and CARINFmm crosscheck, originalgamephysicalunitparity unproven; Redline explicit hashmatched nativeconfig metres. No repeated Jev gate used.

Current outputs `output/{gt1,mc3,redline}-prepared-v5/`, indexed `output/latest-pilots.json`; all v4 remain historical. `output/v5-geometry-regression.json` proves entire BIN payload byte-equal to v4, with matching per-family binary SHA256, and identical nodes/meshes/accessors/bufferViews/materials. Entire JSON also equal after removing only newly added racerPreparation.units. Thus no vertex/index/material or dimension rescale occurred.5 focusedfixturechecks pass including family-specific unit assertions and retained MC3conflict. Root now owns C++ import and GPU/physics checks. Remaining native-scale/manufacturer conflicts were not resolved by this provenance correction.

## Latest root checkpoint

Latest user excludes GT1/Redline completely from activework; retainhistoricalevidenceonly. MC3 exactnativeDAVEfilename joins repaired7stockexternalparts includinghood; scripts/repair_mc3_vehicle.py andactual tests pass, output/mc3-stock-repair-v1/prepared-v2 SHA f8d598fbe0291abd3c0c24c37ab4dd81c70331c030dadf024ec12c1bfaaee336. Originalsourceprefix/materials unchanged, bodylengthnow4.67956543. RootexperimentaluniformGMwheelbasecalibrationdoesnotresolve~12.5%track conflict, soMC3remainsexcludedfromplayercatalog. Freshrootreview mustnotclaimincompletesourcebonnetstillmissing ornativeunitsproven. Strongreviewsevenpartauditinterruptedbyworkspacecredits; productiontests androotdirectsource/nativechecks retained, not independentapproval.
