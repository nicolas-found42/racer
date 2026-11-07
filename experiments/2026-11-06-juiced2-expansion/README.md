# Juiced 2 multi-car source expansion

Question: can the existing 350Z-only ISO converter be generalized from exact shipped car declarations and archive pairs, preserving its known output, to recover further body/wheel assemblies? Extracted configuration count is not a playable roster.

Canonical input ../raw/juiced-2/juiced-2.iso. Historical whole-image SHA e2fd26e6a56b204fdacf6f751b520bf1bcc58e54fa7fe4e7b54bdd03640176ef is not freshly recomputed. Retained typed-scripts.json contains94 BeginCar declarations, including an explicitly named online-opponent BLANK, so do not label94 player cars without evidence. Source hashes/value offsets and original scripts remain in prior juiced2-data output. Existing350Z metadata and native member lineage remain in juiced2-vehicle; original ISO unchanged.

Bounds before work: ≤300s/command; new output≤128MiB; selected source≤16MiB/member32MiB/batch; source decoded cumulative128MiB hard cap per conversion and paired ISO header checks. Free space≥20GiB, latest~420GiB. No game execution, focus, installs or bulk image duplication. New target-free REA capture may observe a bounded archive/classification/conversion command; it never establishes original game runtime. Root coordinates any active REA binding.

## Implemented and retained

`scripts/juiced2_vehicle.py` now accepts explicit `--car 350Z|MX5` profiles from `scripts/juiced2_registry.py`. Profile identity includes freshly checked ISO header bytes, archive range, exact native filename hash, hierarchy/root name, rim hash and shipped typed configuration. The old 350Z hierarchy ordinal fallback is removed: pinned external filename-list evidence supplied `models\\350z_stock.boh` and `models\\mx5_stock.boh`, both confirmed by native hash and embedded root. External filename data is a lead, not proof of runtime behavior. Retained lookup: `output/reference-filenames-firecrawl.json`.

MX5 header sector2293010,7180B SHA `cffd6fd82a5ba45cd9d2c2e06604802ba5950bf8c1aed524d7b19ac956df7d70`; archive sector2231411,size4952451. Configuration ordinal348 SHA `0700b3cfb7d312edb4688d2fa073003932316eae5efcbcf171f67dad95751360`, exact `cardefs\\cardef_mx5.txt`. Hierarchy `models\\mx5_stock.boh` key3563377616 SHA `6bb8de745892db834cdc1dc077a9e5277aa06c37d3ee838aaa4eb2605d53b709`; stock `mesh\\WHEEL_MX5.xem` SHA `25671024446ee50f4eac63d2e4dd45acba41134934f6e376161acdc6b595da5f`. All member offsets, packed/decoded hashes and sizes are retained in candidate receipt. No whole ISO duplication; whole-image historical hash above was not refreshed.

Actual candidate `output/mx5-prepared-v1/c46f0f0e2e77aebc2c4d426cb24be7a676682afadbf809e8f7a51de86568dc9a.{glb,vehicle}` contains42 mesh nodes,51,666positions,69,027triangles,15embedded native textures, full selected static body, four native rims, four adapted native Toyo tyres, four configured discs and four side-specific configured calipers. V2 binding roles retain nonrolling steering caliper carriers. Source WB2.266050033569336m uses explicit100units/metre conversion; this is not factory or original-runtime unit proof. Exact year/trim and manufacturer dimensions remain unknown; the source MX5 identifier is insufficient to infer them.

Fresh current-ISO coverage `output/configuration-archive-coverage.json` verifies all94BeginCar declarations against current script header record, packed/decoded hash and typed fields (96,375packed/277,372decoded bytes).92 have exact casefold archive/header pairs; `Noble_M12` alias and `none` have no exact pair. BLANK is explicitly “Online opponant Car”; BLANK/none are nonplayer placeholders. Only350Z andMX5 assemblies are implemented; the other archive pairs are not validated playable models. Fresh config bytes are retained in `output/source-config/`; matched headers in `output/headers/` (548,624B). A first audit comparison incorrectly included a cached `file` annotation; comparing actual decoder fields corrected that tooling error without a source mismatch.

## Verification and retrieval

Run from repository root (commands are headless, output directory must be fresh for conversion):

```sh
python3 tests/juiced2_registry_checks.py
python3 tests/juiced2_vehicle_checks.py
python3 tests/juiced2_registry_checks.py experiments/2026-11-06-juiced2-expansion/output
python3 experiments/2026-11-06-juiced2-expansion/output/verify_mx5_source_vertices.py
python3 scripts/juiced2_vehicle.py --iso ../raw/juiced-2/juiced-2.iso --header experiments/2026-11-06-juiced2-expansion/output/headers/mx5.jfshdr --car MX5 --stock-brakes --output /tmp/racer-mx5-review-new
```

Profile tests:3pass, including exact namespace joins, rejected wrong hash/bank/config and decoded-budget rejection before first read. Existing parser known-answer tests pass. Actual candidate body/wheel/carrier vertex containment passes. `output/regression-results.txt` records byte identity of both existing350Z GLB and descriptor variants: default `9c99d140778180eb5193693a99a56570eccda74a0fe29378067b59ccc70a61e7`, brakes `6ac33b186ea3189874827d79ce844903e42838779f79c920efc83196cecfbd4c`.

Independent raw-source checker `output/verify_mx5_source_vertices.py` uses its own hierarchy4×4 traversal and XEM strip decoder: all51,666positions and69,027triangles match the emitted mesh under declared axis/unit/ground-lift transformations; native material names and strip parity match. Result `output/mx5-source-vertex-proof.json`. Its first invocation had a Python spacing syntax error, fixed before any result. This is source transformation verification, not native-game parity. Separate reviewer requested; acceptance remains pending that review and root native/GPU/motion checks.

Target-free REA conversion capture `output/rea-mx5-conversion.json`, evidence `ev_8f7f221984bfb1467eece461fbfcd0423ee7c51f2d006cad95c59a67b5ea3ed7`, produced same candidate hash with exit0. Process sampling is partial; no filesystem watch paths. This observes the converter, not Juiced2 runtime. Leaf retained size approximately34MiB. Source header and cumulative selected packed/decoded limits are checked before decoding; telemetry/trace files do not substitute for source identity checks.

## Remaining limitations and resume

Shared native Toyo geometry is an explicit adaptation: stock TYRE_PROFILE procedural construction is unresolved. Native units, side/orientation, caliper scale, original shader/material behavior and static-state selection remain bounded assumptions documented in candidate extras. No native equilibrium, original driving or exact factory dimensions claim. The attempted primary Mazda manual retrieval returned empty content and supplies no usable dimensions. Texture top-mip extraction is implemented; independent exact block-coverage verification for all15MX5 images remains pending.

Resume: await independent source review, repair any concrete findings, then root validates native loader, multiangle rendering and motion before catalog eligibility. Do not promote this candidate solely from source conversion. Preserve earlier350Z outputs and all source inputs. Generalize another profile only after exact archive/config/hierarchy/rim joins and current-header pins are established;94config declarations do not imply94player models.

Independent review now retained: `output/mcla-independent-review.json` and `.md` confirm current two profiles, three fixtures, exact both350Zvariants,48freshISOsource members and all51666MX5positions/69027triangles/42nodes,94configs/92pairedheaders. Additional15texture top-mip coverage checks find every target block written exactlyonce with no overwrites; this checks producer mapping coverage, not independentXenos ordering/pixel parity. Native hubY.284902 versus adaptedToyo radius.318525 and common33.623mm lift remain explicit adaptation/size limitations. No actionable converter defect found. Resume: root native/GPU/motion acceptance; producer/source review is not catalog approval.

Independent authored hub-rest tyre-fit review (separate producer): `output/ford-independent-tyre-review.py` and `.json` verify d7e3cd0bc91ac248bd88e584e7b059a682f72bfaed00e4a34456981878779812 against c46fsource. All51666worldpositions checked:32402body/5008rim/384disc/1420carrier onlycommon−.03362297058mYshift,12452tyrevertices onlydeclaredYZradialfit aboutoldhub thencommonshift; maximumcomparisonerror2.22e−16m. BIN/material/image/normal/index records unchanged. Actualrimradius.26481496m has20.0869mm radialclearance underauthoredtyreradius.2849019m; allgroupscontained. Descriptorwidth increases52.45nm duefloat32extremumrecalculation; geometryX/width is unchanged, descriptorwidth is notbitidentical (alreadydocumentedbyproducer). Sevenfixturechecks pass. No actionable geometry/transformdefect; originalTYRE_PROFILEconsumer/factoryspec/nativeequilibrium/GPU remain outside this review.
