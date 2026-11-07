# MC3 PS2 four-car source cohort

Budget revision before glass output: root restored this leaf from 56 MiB to 64 MiB on 2026-11-06. Existing retained output is 50,691,205 bytes; the four v1 GLBs total 11,549,956 bytes. The optional glass-only v2 will remain in this leaf, with a complete payload preflight against 67,108,864 bytes and at least 20 GiB free space. All old outputs remain in place. Root separately accounts for the combined project budget. Only the four neutral opaque active `car_window` materials are authorized; existing `colored_glass`, lamps, unknown and unused materials stay unchanged.

Resume: root's v1 GPU review identified opaque neutral window materials on all four cars. Optional glass-only v2 candidates are now in `output/glass-v2/manifest.json`, ready for independent source review and root-owned GPU review. All four v1 candidates remain unchanged. None is published or eligible as a player car. Shared exhaust activation/selection for Saleen, Viper and Esprit, original runtime units, wheel sizing and suspension remain unproved. Do not confuse static assembly closure with original game execution.

## Target and bounds

The inputs come from `nicolas-found42/carmodels` commit `ce047799fc550cdf92e4f7b62d97ef5c603e53ad`. The public catalog SHA is `fcd6eb5badd4cc120da3daaae315e83b71fb2b9400062b371b73c9f42a442e6c`; the native index SHA is `4d35bc1b59b3661786d5390f1e48ba5ba9746806e052b67d85b1378e5f8d6fa7`. Its PS2 Remix ISO identity is reported by that index, not newly verified against a local whole ISO. The local Xbox game is not used.

Fleetline, Saleen SR, Viper and Esprit are combined-preview/DAT size ranks 1, 2, 6 and 8 among four-wheel public records after the already handled 350Z/Corvette. Repeated Impala police variants and the Cien concept were skipped for diversity. This is a bounded cohort, not an unbiased sample or coverage of all 94 previews. The reusable planner requires exactly four distinct native wheel bones with one rim and tire each before acquisition; traffic records, two-wheel records, duplicate requests and the two previous cars are outside its scope.

Limits: at most four requests, 16 MiB per input, 32 MiB total selected downloaded sources, 64 MiB retained leaf, 20 GiB free disk, 290-second CLI deadline, commands below 300 seconds. The completed source downloads total approximately 26.3 MB including the two shared wheel PPFs. Retained output is approximately 50.7 MB. No native window, build, runtime/catalog edit, package installation or new fetched code execution occurred. The only external decoder executed is the previously reviewed `reference-mc3_pck.py`, verified before import against SHA `68c6d61162563023560c4c71cf40bc729e2279918d8c9ef9e433df32de7bebde`.

## Results and root handoff

`output/batch-v2/manifest.json` records full source/prepared hashes and absolute descriptor paths. Each candidate is under `output/batch-v2/<code>/prepared-v1/`. It contains the prepared GLB/descriptor/receipt and a retained derived `assembled-source.glb`.

| Code | Prepared SHA prefix | External meshes appended | Native body positions | All world positions | Source wheelbase |
|---|---|---:|---:|---:|---:|
| `vp_fleetline_49` | `6daf44e2c5c5` | 0 | 5,177 | 8,789 | 3.439960 |
| `vp_saleen_sr_00` | `e1831751fd03` | 4 | 6,375 | 10,459 | 2.527641 |
| `vp_viper_03` | `e518a38dae10` | 4 | 6,586 | 10,974 | 2.603894 |
| `vp_esprit_04` | `42028aaaebbe` | 6 | 6,933 | 13,637 | 2.604686 |

Wheelbase uses uncalibrated source coordinates with the existing factor-one import assumption. It is not a manufacturer measurement or proof that native units are metres. No factory dimensions or exact retail year/trim were established in this leaf.

All original source GLBs/DATs/configs remain in `output/batch-v1/<code>/`. All selected DAVE members match native-index names, ordinals, ranges, lengths and SHA values. Raw 68-byte bone records crosscheck decoded global/local positions, rotations and indices. Native skeleton values also match the original preview. These facts establish source identity and the selected static pose, not original runtime behavior.

The public Saleen/Viper/Esprit previews omitted 4/4/6 actual main-car LOD0 references. Exact case-insensitive DAVE filename joins restore their hood, bumper, light or spoiler geometry. The Fleetline already included its four external parts. Unknown or multiple filename joins fail. Native material indices are checked against the retained preview material table. Added normals are explicitly generated; original nodes, BIN prefix, materials and images remain unchanged. Seven native configuration part indices are all zero before the optional completion is allowed. This consistency supports the authored assembly; it does not recover the native index-to-activation consumer.

`assembled-body-closure.json` proves every visible main PCK LOD0 reference is included, except the original dormant ground-shadow mesh whose native draw material is `drop_shadow`. The Esprit calls that mesh `shadow_neon.mesh`; the others use `neonglow.mesh`. Dormant records are retained. These are explicit effect omissions, not missing body panels.

## Wheel and geometry evidence

`output/shared-wheel-source-proof.json` and its reproducible probe `output/verify_shared_wheels.py` join all 32 rim/tire instances to actual pinned `rim.ppf` and `tire.ppf` bytes. For each instance they verify handle/page arithmetic, page bounds, the unique containing model, collection membership, mesh offset, VIF packet SHA, local positions, triangle-strip indices and material indices. This covers 18,788 wheel positions and 14,824 triangles. The retained preview sizing/rest transforms match its pinned catalog records; runtime handle selection and sizing consumers remain unknown.

Together with 25,071 verified body positions and 17,142 body triangles, all 43,859 positions and 31,966 triangles in the candidates have native geometry lineage. `output/world-vertex-proof.json` uses a separate quaternion calculation to check every assembled-to-prepared world position, reflection/winding and body/four-wheel enclosure. Maximum position error is below `1.2e-7`. It also checks descriptor/public-source/prepared identities and original BIN prefix, node, material and image preservation.

Static frame anchors are exact native labels and positions: Fleetline `hoods`/`trunk`, Saleen `hoodbone`/`tk`, Esprit `hood`/`trunk`, plus `Arm_Front_L/R`. Viper uses the labelled front/rear suspension arms because its short `hd` kit anchor does not establish a hood position. These are narrowly described static orientation interpretations; no numeric wheel-name ordinal determines FL/FR/RL/RR. The existing exact 350Z path retains its original metadata and bytes.

## Validation and retained history

Nine cohort checks pass in `output/cohort-tests-release.txt`, including exact current-producer reproduction of all four prepared artifacts, complete world positions, source range/hash tampering, two-wheel exclusion, missing labels, duplicate/unknown external joins, unknown material indices, nondefault config and rejection before output when the budget is insufficient. Eight existing wrapper checks and seven existing wheel-contract checks pass. Existing 350Z variants and the legacy Corvette default GLB/descriptor remain byte-identical. No CMake registration or native build was performed here; root owns those steps.

REA target-free process evidence `ev_019a143dbda4320abc7e708dcfa7ed128866b707da5f99b3c4b7301953df5e73` retains the initial four anchor rejections. `rea-tests-final.json` retains eight tests passing under `ev_a555f52645ab118775c0986ac54f4ddc1aca6b2ed63b74571685d6c45a9b4abe`; the later ninth test adds byte-for-byte current-producer reproduction, with its direct command log retained. REA captures the Python preparation/test process, not the original game. Its raw terminal/process sampling limitations remain in the records.

Historical errors are preserved. The first body-closure probe used the 350Z-specific `_stk_` name rule and therefore overreported completeness for Saleen/Viper and treated the Esprit shadow spelling as missing geometry. Its `batch-v1/body-closure.json` files are superseded by the all-main-LOD0 checks in batch-v2. All four first-pass statuses were rejected for absent exact 350Z anchor names, so those erroneous intermediate closure labels did not produce candidates. An initial test used macOS's symlinked temporary directory and failed the existing symlink guard before reaching its intended assertion; `rea-tests-fixture-path-error.json` retains that fixture failure. The corrected test uses a private regular-path directory.

## Remaining limits

- Native `ExhaustRear` is 0/26/2/13 respectively. Fleetline also has `UseSideExhaust=1` and its side exhaust is among the verified main-car parts. The other three separate shared exhaust selections are not appended or runtime-resolved here. Whole original-game stock assembly is therefore not claimed.
- Native wheel radii/widths are preview rest-sizing interpretations; no factory fit, camber/steering consumer, suspension equilibrium, damage/customization animation, mass or grip is recovered.
- Source material metadata and images are preserved. Neutral inspection paint, native GS shader behavior, lighting, transparency and effect activation remain outside these checks. Root GPU review is still required.
- Candidate names and receipts explicitly say research/player candidate and `runtime_player_eligible=false`. No publication or release eligibility is implied by static geometry checks.
- Private fresh output is bounded and never overwrites source artifacts. A storage/process interruption can leave a partial private folder; retained status/evidence must be inspected before reuse. File SHA samples are not an atomic filesystem snapshot or proof of an executing interpreter image binding.

Reproduction commands (repository root, fresh output only):

```sh
python3 scripts/mc3_cohort.py --code vp_fleetline_49 --code vp_saleen_sr_00 --code vp_viper_03 --code vp_esprit_04 --source-cache experiments/2026-11-06-mc3-cohort/output/batch-v1 --output /PRIVATE_FRESH_OUTPUT/batch
python3 tests/mc3_cohort_checks.py
python3 tests/mc3_preparation_checks.py
python3 tests/mc3_wheel_contract_checks.py
```

The batch output's parent is the 64 MiB accounting root. Do not point it at an unrelated directory or repeat a full retained generation inside this already occupied leaf; the current-producer regression safely compares one temporary candidate at a time. `output/release-integrity.json` pins current source and retained evidence for independent review. Resume with root's native/GPU/physics assessment; preserve both failed and successful source artifacts.

## Optional cohort glass v2

`scripts/mc3_cohort_glass.py` is a separate opt-in postprocessor. It does not modify the 350Z allowlist, the shared preparer, or any default output. Production requires fixed public-source, DAT, main PCK, v1 GLB, descriptor and receipt hashes. The actual DAVE member bytes must equal the pinned main PCK. Each approved material must retain its original name/category/index/profile/offset/vtable tuple, native carrier/root metadata and neutral opaque display factor, and be referenced by the active scene. Unknown metadata or an inactive approved material rejects the candidate. No color-only heuristic selects glass.

| Source code | Window material index | Native PCK byte offset | New prepared SHA prefix |
|---|---:|---:|---|
| `vp_fleetline_49` | 11 | 88144 | `3624a1699869` |
| `vp_saleen_sr_00` | 18 | 91424 | `55f268651bb9` |
| `vp_viper_03` | 2 | 17504 | `30e76a041dd6` |
| `vp_esprit_04` | 5 | 85264 | `c9ad8b932d21` |

Each tuple is `car_window`, category `car_window`, serialized vtable `8038632`, profile `original`, with the index and offset above. The pinned source graph labels class 13 and `car_window.shadert`. The helper checks the actual little-endian vtable word at that offset and retains the first 32 raw bytes. This is a bounded identity witness, not a new complete material-record decoder or proof of a native opacity consumer. Active draws identify the shell/window meshes and, for Viper and Esprit, the glass primitives within trunk meshes; exact node/mesh/primitive witnesses are in `output/glass-preservation-proof.json`.

The only display changes are `baseColorFactor=[0.08,0.12,0.16,0.45]` and `alphaMode=BLEND`. They are explicitly Racer-authored, not recovered native GS transparency. Saleen material 9 and Viper material 17 already contain dark translucent `colored_glass` and remain byte-for-byte equivalent as JSON objects. All lamps, other categories and dormant materials stay unchanged. Original material objects remain embedded in the named policy record.

Seven focused checks pass in `output/glass-tests.txt`. They cover exact actual inputs, all 43,859 world positions, full BIN preservation, restoration of the entire document after reversing only the named material/policy delta, native byte tampering, each tuple component, inactive material rejection, order-independent descriptor identity rewriting and rejection before creating output when the leaf budget is insufficient. Eight existing wrapper/default regressions pass in `output/glass-default-regression.txt`, including the legacy Corvette default. The retained verification script `output/verify_glass_preservation.py` separately reopens the written v1/v2 artifacts, verifies their identities and records all geometry, material and descriptor invariants in `output/glass-preservation-proof.json`. These are producer checks; independent peer review and native rendering are still required.

After v2 generation and proof retention, output is 62,377,216 bytes, below the restored 67,108,864-byte cap; measured free disk is over 400 GiB. The helper preflights the complete four-car payload before creating output and rechecks the leaf before each file write. An I/O interruption can still leave a partial fresh private folder; this is not transactional publication. No files are moved or deleted. No new source acquisition, native game execution, GPU run, catalog modification or eligibility promotion occurred in this glass delta.

Reproduce checks without generating another retained four-car copy:

```sh
python3 tests/mc3_cohort_glass_checks.py
python3 experiments/2026-11-06-mc3-cohort/output/verify_glass_preservation.py
```

Root should re-render the four exact hashes in the new manifest and judge readability/appearance. Native shader parity, units and shared-exhaust limitations are unchanged. The earlier `release-integrity.json` remains the historical v1 snapshot and is not silently rewritten to include this delta.

## Bounded Lightning acceptance review

At root's request, `output/lightning-independent-review-v1.json` and `output/verify_lightning_acceptance.py` retain a read-only acceptance review of the separate Ford Lightning release. This uses less than 256 KiB within this leaf and changes no producer, catalog, inventory, native assets or captures. The report SHA is `4096e096541c4e83d217821b5415143ed56cac17eb74c73fbae6fdddeff061df`.

The exact mesh `0f7cdfcc…`, descriptor `b5775b49…`, source `f342376a…`, library `29379dce…` and executable `f99a38e0…` identities match the retrieved motion and full-loop histories. All 7 motion and 37 feedback capture hashes match retained files. Both processes exit zero. Sampled wheel/carrier telemetry covers wheel 0, not every wheel or every frame. The synthetic feedback loop includes time/gate overrides and is not a real performance measurement. Reviewed static, motion and save/recovery pixels show no gross assembly or wheel-arch problem in the selected views; the renderer explicitly reports partial material support.

No concrete blocker was found for a qualified authored Racer addition named `Ford SVT Lightning`. Exact year/trim and original handling remain unproved: native YEAR2002/BHP360 conflicts with the brochure's 380 hp. The 2.226 m visible mesh width is not a verified match to the 2.009 m brochure width; mirror conventions and the exact contribution of mirrors remain unknown. Wheelbase/track/length/ground-height comparisons satisfy the stated authored tolerances, not a factory-exact or native-unit claim. The historical release dimensions hash links to retained v1; corrected v2 only renames the alternate printed-mm field, and current dimensions additionally correct the coverage count. Numerical values and source identity are unchanged.

The report retains the eleven current player entries in order. These single-entry tests do not verify the later publication operation. Root owns appending the Lightning and checking that all eleven existing entries retain their positions. No publication occurred in this review. `glass-v2-integrity.json` remains its historical pre-review snapshot; this later README addition does not change the frozen glass producer or candidates.

Latest root acceptance: Root reviewed all16 original and16 optionalglass captures, with native hash/containment checks passing. No eligibility change. The parent-name research-ID collision affected old manifest labels, not established loaded-mesh identity; identity-correction.json is retained in root MC3 views. Shared exhaust/unit/activation holds remain.
