# Ford source cohort expansion

The strict adapter now prepares 33 research candidates from all 35 pinned Ford variants. EX and INDIGO remain held because their suspension geometry does not fit the current wheel/carrier contract. No candidates were published, and all runtime eligibility flags remain false.

## Scope and source identity

Source repository commit: `ce047799fc550cdf92e4f7b62d97ef5c603e53ad`. Catalog SHA256: `fcd6eb5badd4cc120da3daaae315e83b71fb2b9400062b371b73c9f42a442e6c`. All 35 manifests and CARDATA blocks are retained, with exact pins in `output/metadata-registry.json` and `scripts/ford_cohort_registry.py`.

There are 21 uniquely approved declarations, 13 uniquely unapproved declarations, and one conflict: 49_COUPE_MOVIE contains consecutive CAR_APPROVED 1 and 0 lines. The previous count of 14 approval-zero variants included that conflict using the last value. Native precedence is unknown. The first acquisition probe used the first value and counted 22; its result is preserved as `metadata-registry-first-approval-probe.json`. The corrected registry retains all occurrences and never resolves the conflict by guessing.

The 14 approval-zero/conflicting rows were subsequently acquired and processed through an explicit research mode. Thirteen now have prepared candidates; INDIGO is held. They remain unknown-roster entries and are not declared nonplayer cars. Source approval flags alone do not establish the original selectable roster.

Bounds were recorded before acquisition: output initially at most 128 MiB, individual members at most 16 MiB, acquisition batches at most 32 MiB, commands at most 300 seconds, and at least 20 GiB free. Root authorized a revision to 192 MiB before the additional 14 inputs (see the authorization record below). Current output is approximately 149.6 MiB, below that bound. No build, GPU, focus, CMake, shared inventory or publication actions were performed here.

The reverse-engineer-anything v49 skill applies to native artifact claims. Initial behavioral discovery used jg with the explicit Racer scripts root and 8000 requests / 20 concurrency; truncated excerpts were followed by actual source reads.

## Acquisition and adapter

Two bounded immutable payload batches retained 21 GLB inputs (three verified cache hits; 31,276,740 new bytes) and 21 native PS2 inputs (two cache hits; 29,321,168 new bytes). `glb-acquisition.json` and `native-acquisition.json` record exact URLs, bytes, hashes and reused source paths. The remaining 14 inputs were then acquired in two further bounded batches: 21,409,480 GLB bytes and 14,574,048 native PS2 bytes, recorded in the acquisition-research receipts. All 35 source inputs are retained or referenced through verified caches. No full ISO or source filesystem was acquired. All tyre blocks are verbatim and type-matched to CARDATA.

The reusable registry binds exact source, native model, configuration and canonical parsed-physics identities. This rejects altered axle metadata even when a caller retains the original file-hash annotations. Legacy Focus/F150 APIs, names and pins remain intact. `--research-any-approval` explicitly permits approval-zero/conflicting rows while preserving the exact occurrence list, unknown native roster and false runtime eligibility in candidate metadata. The default mode remains unchanged.

Normalization requires four unique named source HUBs. HUB meshes become steering-only carriers when present; an empty HUB does not cause fabricated geometry. WHEEL_STATIC descendants inherit their actual named owner. Default material variant zero must match each source default primitive. Bodies, material/image data and the entire BIN remain unchanged. Configured tyre-radius fitting is an explicit Racer adaptation with lateral scale one: no body scaling, recentering or guessed source offsets.

## Candidates

The current complete 35-row status/path inventory is `output/coverage-v2.json`. Initial directories under `prepared/` and added directories under `research-prepared-v1/` are immutable. All candidate eligibility flags remain false. Manufacturer dimensions are not inferred from model codes or source years.

| Source code | Preparation | Wheelbase (interpreted m) | Prepared SHA256 |
|---|---|---:|---|
| 49_COUPE | Research candidate; roster unknown | 2.905210 | add9d60f0111f946dab3dc0376646af4d4fbdb7d5f3cd7fe59168e8ccc5be5af |
| 49_COUPE_MOVIE | Research candidate; roster unknown | 3.001518 | d275efa5c5c1ca893be27e1c0899d104ad407cc89aac826dd0c0c12543c5f5e6 |
| COBRA | Research candidate; roster unknown | 2.543601 | 700ec96d475f8b3bbc76a257efe928ae29a2c779dd129f4af128f5a032993b87 |
| CROWN_VICTORIA | Research candidate; roster unknown | 2.906912 | 62af3a9a046d29d9b1a1078cea9f061383809ff750c57d260a576d2d827d724f |
| EX | Hold: wheel_mesh_name | — | — |
| EXPLORER | Research candidate; roster unknown | 3.522181 | 08aa804241ae534c39978b3987c8a54ad45f4d1b07454f6285a361665581d3ea |
| F100_1956 | Research candidate; roster unknown | 2.877315 | 889ea2163b8a28a56ae68e9c996c88fd73ca7515eba156e57f0c8c781f38e617 |
| F100_1965 | Research candidate; roster unknown | 2.951826 | f3ab5bbcd35974325014dcf450300261b987059ed77724458ae63ddbe15e6eb3 |
| F150 | Research candidate; roster unknown | 3.567925 | dd47bde1d7ccd6af3e33d751bd33419f5a4ea400d16db5fe1a3f389c2ad27396 |
| F150_2004 | Research candidate; roster unknown | 3.401969 | 217177c8a032beef46e0f5954f99ef234f4c7a6d5b609a12691a2e17e65256fc |
| F350 | Research candidate; roster unknown | 4.014600 | a36f3af84770e55f3e2930718cac2148bb2a5d7222c526341a1db1d9012bfd9c |
| FOCUS_FR200 | Research candidate; roster unknown | 2.634847 | 236fc317c9188e8a0dcd59794e83fac27d918fc43505eec3485f8569b1a9ef76 |
| FOCUS_SVT | Research candidate; roster unknown | 2.622785 | 4cbb79372fe1934c03ce6b6cc1a4b84135c3fb1fd60f7a946a0125b425966c55 |
| FOCUS_WRC | Research candidate; roster unknown | 2.645000 | 1f9a462fa5bb0c132ef7c3d7cf4ba09d9cf8490c6ac831c2f0f88c1154ebc381 |
| FORD_GT | Research candidate; roster unknown | 2.728646 | f5b3ae2def8ca38ba794997f80f8cc1c999bf55f54d2de77dbe1ec31a672298f |
| FORTYNINE | Research candidate; roster unknown | 3.022600 | a95ba969bfd9513d222c654e919b39c936cd93049edefca4820f6dbc8cfcdf95 |
| FR500 | Research candidate; roster unknown | 2.668601 | 4bc72aa519ea4b001d26f25cd6ca9188ca41820e8df9002e1d2853e6e4f0c917 |
| GRAN_TORINO | Research candidate; roster unknown | 2.930000 | ade9a623508dfc2077d5c5f7b80051d5ba158d2ace146491d1ca9b8abe985a11 |
| GT90 | Research candidate; roster unknown | 2.864458 | cc3b6a950560546b7725506b002ea4ec7ac87dfd7dceede90ff8ab2104a07662 |
| INDIGO | Hold: wheel_mesh_name | — | — |
| LIGHTNING_SVT | Research candidate; roster unknown | 3.029854 | 0f7cdfccc56ddf6eed4d29be7ed3d6110c9ba95ef0804af49ce0638f92596ec0 |
| MACH1_AGENT | Research candidate; roster unknown | 2.769635 | f0f9cddbccc37320e078f5d0d6c3b3e494d841e707f6214ff84b27cd4eae392a |
| MACH1_SIXTY | Research candidate; roster unknown | 2.769635 | 99dec677588167c0bc3b39c4e65a4a2e462b6104955f41018dc8a5d0dee669dc |
| MACH3 | Research candidate; roster unknown | 2.613900 | c57a104db10ff4ad6c4e7a8f25ca6af9953ccb66b761a2e5fdd9404e04ee64f8 |
| MUSTANG_68 | Research candidate; roster unknown | 2.817234 | d78df11d4cc56dd1a024cb8d9c82e683a1a1e890ef029f449f50148c5c0f18ae |
| MUSTANG_68B | Research candidate; roster unknown | 2.817222 | a6267be5880fb9e60549e2f0c66046e1411595c2d9172075f288d446c1bf8b37 |
| MUSTANG_CONCEPT | Research candidate; roster unknown | 2.772537 | 0373e2f0206e5d03a3edb84193cb20ce1cc9cb3c9ae3dc62cd4101a2b99da15c |
| POWERSTROKE | Research candidate; roster unknown | 3.641030 | 976df4daf491a21a499a5034f8cbe8dd37f124399c0f1f25339a9279e3c875c6 |
| TAURUS_STOCK_A | Research candidate; roster unknown | 2.788285 | ae8daf1bf791ab4f35d10582318c0af4758ddc5a844ee0fd4699e4434ace1104 |
| TAURUS_STOCK_B | Research candidate; roster unknown | 2.788285 | 8b52e986d0e114149c2dea81428ba973ee6e3841e001838fcbe88fda222d79af |
| TAURUS_STOCK_C | Research candidate; roster unknown | 2.788285 | 9cba9b2495939e11d3cc4d21f85dd263b8da81d20134442e186222ad67e10f37 |
| TAURUS_STOCK_D | Research candidate; roster unknown | 2.788285 | d5737c81a8279dcf58bb1826b7fcdb1609d067dbd3b55260ab9f129be0fc3e31 |
| THUNDERBIRD | Research candidate; roster unknown | 2.596537 | 19d3cb449ee7a1a91c7e07c5502faaac79f02ee375a8dd14f67a7fcb7c0416cc |
| THUNDERBIRD_2002 | Research candidate; roster unknown | 2.702559 | fa1297915711ac834ed8c590bb8cb96cea3546e51e81e33fbbe1e9fc6a3ad62e |
| THUNDERBIRD_MOVIE | Research candidate; roster unknown | 2.702559 | 19ea92b7164e1fe31477abb40c4b66c72094c302e9df22fc7692b7ea8e04ae67 |

## Verification and limitations

`output/verify_cohort.py` uses an independent 4×4 traversal. The first 151,300 selected world positions across 20 candidates follow only the declared wheel YZ radius fit and common ground lift. BIN, materials, images, textures, samplers, accessors and buffer views are preserved. Raw PS2 checks corroborate 305 selected node headers and the name tables/pairs. The native file hash matches each GLB originalModelSha256. The additional 13 candidates contribute 90,860 positions and 199 headers, for 242,160 positions, 504 headers and 1,061 native name strings across 33 candidates. `verify_cohort_v2.py` also checks every mesh primitive attribute/index/material reference, allowing only removal of optional material-variant mappings. Results are in `source-world-proof-v2.json` and `research-source-world-proof-v2.json`; older reports remain retained.

The independent reviewer corroborated all 151,300 positions, 264,696 indices, 305 headers and 658 native name strings, plus all body/wheel/carrier containment. Its report is `../2026-11-06-juiced2-cohort/output/independent-ford-review.json`. No actionable adapter defect was found. This is exact source-preview geometry comparison with native header/name proof, not independently rederived native VIF triangle decoding or original runtime parity.

REA controlled proof command exited zero: evidence `ev_4779388eef1e1b7d6f0fe11f99792796eb3f5ddf523391e21b65773e0938ce58`, retained as `rea-source-world-proof.json`. It observes our proof against retained artifacts. Filesystem observations are before/after snapshots, short process sampling is incomplete, and no original game ran.

Two existing cohort tests and five new registry/hub/semantic/research-mode fixtures pass. `legacy-regression.json` verifies that the current converter regenerates the exact old Focus and F150 GLB and descriptor bytes from their raw source/configurations. The independent reviewer reran those original 20 checks; review of the 13 added candidates is pending. `all-default-regression.json` additionally verifies that the research-mode extension regenerates all 20 frozen default GLBs and descriptors exactly.

## Contact-centre seam and EX hold

`output/all-wheel-lateral-summary.json` records all 132 rolling clouds: XYZ bounds, native HUB positions, geometric lateral midpoints, nominal configured tyre WIDTH and conservative symmetric descriptor WIDTH. Body and nonrolling carriers are excluded. Twelve models exceed a 1 cm midpoint/HUB offset. The original seven are F150 (maximum 0.189997 m), F150_2004 (0.023049 m), MUSTANG_CONCEPT (0.057108 m), and TAURUS_STOCK_A/B/C/D (0.018611 m each). The added five are CROWN_VICTORIA (0.023307 m), FOCUS_WRC (0.014831 m), FORTYNINE (0.010652 m), MACH3 (0.020171 m), and POWERSTROKE (0.043613 m). Two models exceed 5 cm. These are geometric midpoints, not proven native contact centres or steering axes. No geometry or pivots were adjusted to conceal the seam.

EX remains a strict wheel_mesh_name hold. `EX-suspension-hold.json` checks its 23 native headers and source HUB/suspension structure. The four suspension meshes have rear radial extent about 0.5381 m / symmetric axial width 1.23845 m, and front radial extent 0.46674 m / axial width 1.10804 m. Ordinary wheel-cylinder containment cannot represent those arms as current carriers. INDIGO has a similar hold: source suspension axial extents about 0.962–0.999 m and an unlabeled drawable under a named wheel branch require an explicit role/motion contract (`INDIGO-suspension-hold-v2.json`). No parts were dropped, reassigned, inflated or recentered. Suspension motion and the appropriate extent/role representation need separate work.

## Reproduction and resume

Run from the repository root:

```sh
python3 tests/ford_cohort_checks.py
python3 tests/ford_registry_checks.py
python3 tests/ford_registry_checks.py experiments/2026-11-06-ford-cohort/output
python3 experiments/2026-11-06-ford-cohort/output/verify_cohort_v2.py
python3 experiments/2026-11-06-ford-cohort/output/verify_cohort_v2.py --research
python3 experiments/2026-11-06-ford-cohort/output/inspect_ex_hold.py
```

Root owns native loader, visual, physics and publication acceptance. Resume with that acceptance, the steering-axis/contact-centre representation, EX's motion/extent contract, approval precedence and the two held source-motion contracts. All 35 payloads are acquired; extraction coverage does not imply all 35 are accepted playable vehicles. Preserve all source inputs and old outputs. The all-car goal remains incomplete.

## Authorized continuation to remaining source declarations

Before further acquisition, root explicitly raised this leaf ceiling to **192 MiB**, within the lab's default256 MiB ceiling. Existing output was98,358,132bytes atrootmeasurement. Root measured overall project standard output around1.817GB and revised another leaf allocation; combined reserved worst case2,115,779,798bytes remains below2GiB. No evidence cleanup is authorized or performed. All other per-file/batch/time/free-space limits remain unchanged.

The13approval-zero andoneconflictingdeclaration are notuserexclusions. Continue their extraction/adaptation as explicit research-only inputs withoutguessingnativeapproval orplayable roster. They maypass the sameassemblycontract butcannot gainruntimeeligibility fromthis mode. Preserve the20frozenapprovedcandidate directories.

## Static suspension rest opt-in preflight

Root reduced this leaf ceiling from192MiB to160MiB after all35source acquisitions, reserving space for root-native acceptance. No output is deleted. At the next implementation preflight, retained payload was156,271,839bytes;160MiB permits11,500,321additionalbytes. Root authorized an isolated --static-suspension-rest lane for exact EX/INDIGO source pins, with eligibility false and no native animation/equilibrium claim. Only four exactly named suspension mesh nodes may be cloned into fixed source-world rest frames; original nodes retain child links/provenance, and all BIN/geometry is preserved. Source support nodes stay intact. Existing33 outputs must remain byte-identical. No GPU/build/publication from this agent. Stop if actual new output would exceed160MiB.

The added13 research candidates independently passed peer raw-accessor/world/header review:90,860positions,164,457indices,199headers and403names; all20default+13research regenerations match exact bytes. Review pointers: ../2026-11-06-juiced2-cohort/output/independent-ford-research-review.json and ford-mode-byte-regression.json. The opt-in rest lane is a new revision requiring separate checks.

## Static source-rest result and resume

The optional lane now produces **EX only**, SHA `d43e4ddcf76628f7ec83701d8db84fcea7385b96432360cfe3ea17b5018b284d`, in `output/static-rest-v1/EX/`. Four exact suspension drawable nodes are cloned at their source-world rest frames into body roles before the existing tyre radius fit. Original nodes retain their source frames, child links and metadata; their mesh references move to the clones. BIN, mesh primitives, materials, images, accessors and source support nodes remain unchanged. This is an authored static rest adaptation, with eligibility false, and does not establish native suspension animation or equilibrium.

The source/result checker verifies all 10,176 EX and 8,056 INDIGO positions against only the declared wheel YZ radius fit, common ground lift, and body-fixed source rest frames (maximum error 2.22e-16 m). Raw PS2 node headers, named pairs and source strings are checked directly. Geometry comparison begins with exact pinned preview BIN; the raw PS2 vertex packets are not independently decoded here. All 33 existing default/research GLB and descriptor pairs regenerate byte-identically after this optional code change. Seven retained-source tests cover source/native identity, original-node preservation, root frame, exact unnamed alias, inactive reference preservation and active mesh alias rejection. Missing exact fixtures return 77.

**INDIGO remains held.** In-memory inspection establishes that the exact unnamed node 210 can inherit its unique active WHEEL_BACK_RIGHT owner while inactive mesh 31 references at nodes 31/119/270 remain unchanged. However, the retained HUB carriers exceed the existing cylinder contract: front radial distances 0.3041547/0.3041199 m exceed radius 0.286 m; rear axial distances 0.1811981 m exceed half-width 0.1634292 m. No invalid INDIGO model was written, no cylinders inflated and no source geometry removed. `output/static-rest-world-proof-v1.json` retains exact primitive/vertex/world-coordinate witnesses. These are contract limits, not a diagnosis of a source-game defect.

Retrieve/recheck, from the Racer repository root:

```sh
python3 tests/ford_static_rest_checks.py
python3 experiments/2026-11-06-ford-cohort/output/verify_static_rest_v1.py
cat experiments/2026-11-06-ford-cohort/output/static-rest-world-proof-v1.json
cat experiments/2026-11-06-ford-cohort/output/static-rest-final-manifest-v1.json
```

The verification script temporarily bypasses the final guard **only in memory** to inspect INDIGO's rejected result; it does not serialize that invalid model. The ordinary producer still rejects it. The first preparation helper run stopped on this rejection after preserving EX; the revised helper records the retained EX and explicit INDIGO hold without overwriting either source or prior output. Verification outputs are small and the current leaf remains below 160 MiB. Root owns native/GPU/physics checks; peer independent review has been requested. Resume with EX acceptance and a separately designed carrier-extent/motion contract if INDIGO is pursued. The ordinary corpus remains 33 candidates plus one new optional EX candidate, with all 35 source inputs retained; no all 35 playable claim is made.

## Independent MC3 optional glass review

A separate read-only review of `scripts/mc3_cohort_glass.py` and its four `glass-v2` candidates found no actionable defect. `output/independent_mc3_glass_review.py` uses its own GLB chunk reader and DAT name/range decoder, checks the exact source/prepared/descriptor/receipt/DAT/PCK pins, material tuples and native PCK root words, and regenerates each candidate in memory. Restoring the one authored material and removing its policy makes the entire document exactly equal to its baseline; BIN equality plus identical nodes/accessors establishes all 43,859 position instances and transforms unchanged. Only the approved neutral opaque car_window receives authored tint/BLEND; all other materials and geometry remain identical. The seven producer tests pass. Report: `output/independent-mc3-glass-review.json`; test log: `output/independent-mc3-glass-tests.log`. Retained references are used without copying any model payload. This checks an authored tint, not native GS opacity or runtime/GPU parity. Re-run with `python3 experiments/2026-11-06-ford-cohort/output/independent_mc3_glass_review.py` from the repository root.

Final root reallocation: Ford leaf152MiB (current158.7MB), remaining smallreview artifacts only. No further models/captures/acquisition in this leaf; root224MiB. All prior evidence preserved.

Latest root acceptance: Root acceptance now retains132 ordinary Ford static images plus4 optionalEX static and7 EX motion images, all reviewed. EX motion base9checks pass, but mandatory carrier3checks fail because root requested carriers for a zero-carrier descriptor; original exit1 preserved. Lightning alone is newly promoted as player12 after qualified dimensions, source review, motion/fullflow and actual process reload. INDIGO remains rejected. Latest root evidence is ../2026-11-06-cohort-acceptance/README.md.
