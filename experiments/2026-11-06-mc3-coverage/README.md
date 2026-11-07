# MC3 corpus coverage and native-pose alias contract

Preflight was recorded before outputs: fresh private leaf, free space above 20 GiB, initially 32 MiB output and subsequently parent-authorized expansion to **64 MiB**, each command at most 300 seconds, selected input at most 16 MiB per member and 32 MiB per batch. No GPU, desktop focus, original-game execution, production catalog publication or canonical input mutation. One bounded metadata index and one selected preview/native carrier were fetched; no bulk corpus download.

## Sources and platform boundary

Pinned public repository: `nicolas-found42/carmodels`, commit `ce047799fc550cdf92e4f7b62d97ef5c603e53ad`. Retained 1,435-entry catalog SHA256 `fcd6eb5badd4cc120da3daaae315e83b71fb2b9400062b371b73c9f42a442e6c`.

The MC3 native index was not already retained. One GitHub Contents metadata lookup established 4,823,675 bytes and Git blob `ced37cb948e3a942376580636a00cfa81379b510`; one bounded fetch verified that Git blob identity. [Source receipt](output/native-index-source.json), [exact index](output/native-index.json), SHA256 `4d35bc1b59b3661786d5390f1e48ba5ba9746806e052b67d85b1378e5f8d6fa7`. The index reports **PS2 MC3REMIX**, ISO 8,539,963,392 bytes, SHA256 `de199f7e7f57b7cb603a129217f7482d50644fd66558450dfeb5612857b732f9`. That ISO is not locally re-read here.

The retained local `../raw/mc3.iso` is **Xbox original DUB Edition**, historically hashed as `d58490dc8e1837e9f47716268b52ae1f1ac8578e5a5e42e061fa7f1c4b068b52`, 4,840,554,496 bytes, with corresponding Xbox XBE/manual evidence in prior experiments. This leaf does not rehash that entire ISO or infer correspondence with the PS2 Remix catalog. Names, offsets, source models and runtime conclusions must not cross that boundary without independent evidence.

## Coverage inventory

Latest machine-readable report: [coverage-audit-v2.json](output/coverage-audit-v2.json). Initial [coverage-audit.json](output/coverage-audit.json) is preserved as the earlier metadata-only stage. Each row includes `model_id`, preview `source_sha256`, `source_kind`, nullable `native_four_axles`, source package/main PCK identity, member counts, exact config paths, wheel bone/component/pose records, current assembly status and limitations. `native_four_axles` is the requested interoperability field for four wheel positions; it does not literally mean four vehicle axles.

| Area | Inspection and observed result | Remaining boundary |
| --- | --- | --- |
| Public preview catalog | All 94 entries inspected; all share PS2 static preview profile | Not 94 verified playable cars or retail identities |
| Native index | All 94 exact DAT/package identities and main PCK joins; all preview record source hashes present | Availability/provenance metadata, not all payloads decoded |
| Wheel metadata | 79 entries have four distinct native bone groups; 15 have two | Only selected actual PCK bones independently inspected |
| Joint aliases | 78 entries have four distinct joint names, 15 have two, Escalade has one name shared by four bones | Distinct names are not wheel counts; earlier name-count interpretation was corrected |
| Existing adapter | Only Corvette matches exact `whl00..whl03` whitelist | Source-compatible alias spellings previously rejected |
| Native configuration | All 94 have exact `.carcfg` basename matches in shared source index | Values, actual role, duplicate path precedence and runtime factory selection uninspected |
| Traffic | 41 separate `tune/traffic/*.vehicle` entries inventoried | Deferred; not part of the 94 `vp` preview models and no traffic feature implemented |
| Corvette native evidence | Prior exact DAT/PCK pivot proof and seven stock external-part repair retained | This leaf did not re-run original game or re-certify factory fit |
| Selected 350Z | Actual pinned DAT/main PCK decoded; all 250 bones match preview; alias contract prepared and CPU-validated | Shared PPF template geometry, full stock configuration closure and visual acceptance remain open |
| Remaining 92 entries | Metadata/source package availability inspected | Native skeletons, configurations, geometry and playability uninspected |
| Original-game runtime/hardware | Not applicable to this headless static audit; zero game launches | No runtime or physical hardware validation claimed |

All 94 package counts and SHA256 identities match the native index. The index contains 7,285 file records, including duplicate config paths by archive ordinal; no precedence is invented. Every exact model config basename has three or four copies sharing one identical SHA per model. The traffic inventory has 41 distinct filenames but only 33 distinct content hashes; it is not a proved playable traffic roster. `vp_d_chingon_04` and `vp_d_magnum_05` have multiple wheel component records per bone; the new one-rim/one-tire contract deliberately does not certify those assemblies. Small four-bone source packages such as Fleetline, Saleen SR, Viper and Esprit are identified as **next inspection candidates**, not installation recommendations.

## Selected 350Z native proof

Preview: `output/source-store/objects/8a1b7ba44d38815c6c491d3caf9e3b139dbf51c9d74d4c9546b2ee3164d48383.glb`, 3,658,156 bytes. Acquisition receipt: [350z-acquisition.json](output/350z-acquisition.json).

Actual native carrier: `output/vp_350z_04.dat`, 1,843,200 bytes, SHA256 `e4bb61d38affc565cdc22354405bd541fc45073dbbe2664f52f1c02ff846a7c6`. Main PCK occurs at DAT offset 8192, 319,840 bytes, SHA256 `7666859dd8bba326c8c75e9879b1bc4ee2b12dafc4d9d3a50f21a34be02fd346`; retained as `output/350z-main.pck`. [Native acquisition](output/350z-native-acquisition.json), [proof](output/350z-native-proof.json), proof SHA256 `b3c4a48e777a66bf81875e30b713c44e255ac650e24da49e71514b508fd9f767`. All 109 DAVE joins and raw member hashes are retained.

The existing reviewed PCK reader is verified against SHA256 `68c6d61162563023560c4c71cf40bc729e2279918d8c9ef9e433df32de7bebde` before import. No newly fetched code was executed. `output/probe_350z_native.py` compares every native index/name/parent/global/local/Euler field to the preview. Initial probe attempts exposed tuple-versus-list comparison and non-JSON VIF byte fields; corrected representation handling and bounded LOD summaries yielded the saved proof. Those were tooling errors, not source pose mismatches.

The four actual wheel bones are 8/10/12/14 named `whl_0..whl_3`: X ±.7660970092, Z ±1.3154129982, Y .3236590028. Native `hood` Z −.695306 and `trunkbone` Z +.767380 distinguish the selected front/rear convention; `Arm_Front_L` X −.062 and `Arm_Front_R` X +.061697 distinguish selected side labels. Wheel and ancestor rest rotations are zero. Canonical slots come from these source bone identities/poses and explicit body anchors, **not wheel-name numbers**. This is a selected static source-frame interpretation; original runtime coordinate consumers and physical units remain unproved.

Independent review [independent-static-frame-review.json](output/independent-static-frame-review.json) directly parsed all 109 DAT joins, 250 raw bone records, anchors and eight preview wheel node pivots. It supports this narrow static ownership/frame interpretation, not runtime steering, units, shared PPF geometry or complete stock closure. Jev [scope audit](output/jev-scope-audit.json) accepted count/platform distinctions but flagged the static-frame wording at p_wrong .79 without a specific contradictory datum. That escalation is retained without reroll; independent raw-byte review supplies the narrower adjudication, not an automatic global approval.

## Implemented integration and candidate

New `scripts/mc3_wheel_contract.py` requires actual native bones supplied by the caller, exact preview/native bone identity, explicit body/side anchors, zero wheel-ancestor rotations, four unambiguous paired poses and one rim plus one tire per slot. It rejects ambiguous aliases/frames/components instead of guessing. Numeric, underscore, uppercase and F/R aliases are labels only; poses determine order. The repeated plain `wheel` case and multi-component variants remain unsupported pending their own source contract.

`prepare_source_vehicle.metadata` and `prepare` accept keyword-only `native_bones=None`. Existing callers and the default Corvette branch remain unchanged. When native bones are supplied for MC3, ownership/centers/evidence come from the isolated contract. No source rename or source-SHA substitution occurs. Five existing adapter tests pass; actual historical Corvette GLB and descriptor are byte-identical on the default path (validated in the new wrapper regression test).

New `scripts/prepare_mc3_vehicle.py` requires explicit source SHA and actual DAT/PCK files. It checks the pinned catalog/index, source GLB, catalog native DAT identity, exact actual DAT-to-PCK bytes, native index PCK identity, proof hash joins, pinned reader, and freshly re-decoded native bones equal to proof. **Proof JSON alone is never native authority.** No network is used by this preparation wrapper.

Candidate: [350z-prepared-v1](output/350z-prepared-v1/), SHA256 `470d50d6df2fe47d3641ebc0e73bace988146fa291283bf5a7d9484bcc013e82`, 4,118,184-byte GLB, descriptor and receipt. Original source SHA remains `8a1b7ba4…`. Selected preview geometry has 24 mesh nodes, 8,763 triangles and four embedded images. Authored import factor 1 is retained; wheelbase 2.6308259964 source import units compares to the [Nissan Z33 platform reference](https://usa.nissannews.com/en-US/releases/2006-nissan-350z-coupe-and-roadster-press-kit) 2.650 m at −0.724%. This is a platform-qualified comparison, not exact source retail year/trim or physical-unit proof. No scale correction applied. Body length 4.3352050781 includes selected preview geometry; original runtime configuration closure remains unknown.

Parent's local `build/vehicle_validate` accepted the one-entry candidate catalog: [result](output/350z-native-validation-catalog.txt). This performs CPU parser/asset/envelope validation, not GPU or original MC3 execution. Exact validator binary is retained privately as `output/vehicle_validate`; [identity](output/validator-identity.json) records its SHA256 and explicitly does not assert an independently reconstructed source-to-binary build binding. An initial descriptor-level invocation failed because this utility expects a library catalog; `--help` also treats its argument as a path. Correcting the invocation to the catalog produced success, with no model change. Initial failure output is preserved.

## Verification and reproduction

From repository root:

```sh
python3 tests/mc3_wheel_contract_checks.py
python3 tests/mc3_preparation_checks.py
python3 tests/prepare_source_vehicle_checks.py
python3 scripts/prepare_mc3_vehicle.py --source experiments/2026-11-06-mc3-coverage/output/source-store/objects/8a1b7ba44d38815c6c491d3caf9e3b139dbf51c9d74d4c9546b2ee3164d48383.glb --source-sha 8a1b7ba44d38815c6c491d3caf9e3b139dbf51c9d74d4c9546b2ee3164d48383 --native-proof experiments/2026-11-06-mc3-coverage/output/350z-native-proof.json --native-dat experiments/2026-11-06-mc3-coverage/output/vp_350z_04.dat --native-pck experiments/2026-11-06-mc3-coverage/output/350z-main.pck --output /private/tmp/mc3-350z-FRESH
experiments/2026-11-06-mc3-coverage/output/vehicle_validate experiments/2026-11-06-mc3-coverage/output/350z-prepared-v1/catalog.racer
python3 experiments/2026-11-06-mc3-coverage/output/audit_mc3.py --output /private/tmp/mc3-coverage-FRESH.json
```

Seven contract tests pass: current whitelist failure reproduced, actual native slots, deliberately reversed alias numbering and active node order, source/preview mutation, explicit frame ambiguity, rotated ancestors, duplicate/missing/orphan components, duplicate preview bones. Four wrapper tests pass: actual candidate/hash, wrong source/DAT/PCK rejection, forged proof bones rejected despite correct hash fields, and default Corvette GLB/descriptor identity. Initial wrapper fixtures used macOS symlinked temporary ancestors and were correctly rejected; using a real experiment-local private temporary directory corrected test setup without weakening path rules. Final logs are `contract-tests-final.txt`, `preparation-tests-final.txt`.

REA [controlled test replay](output/rea-preparation-tests.json), evidence `ev_6e0e81a38667827dd536be2006e752fc45795dce173aaf023b48e8cd9c8695ad`, observed four wrapper tests pass with source files' before/after hashes unchanged. Process sampling was partial at shutdown; inherited environment/network are unknown; snapshots are not syscall traces and executable hash is a prelaunch sample rather than atomic image binding. No active native target binding changed.

JG discovery used explicit scripts root, 8000 requests/20 concurrency, and capped stdout at 5000 bytes. It returned 29 leads; context truncation was explicit, followed by focused reads of the exact adapter/reader/repair sources. No whole-codebase discovery claim follows.

## Resume

Python compilation, focused whitespace checks and `python3 ../../tools/check.py` pass. [Final manifest](output/final-manifest.json) records current source hashes, retained size and free space. Retain all catalog/native/proof inputs, prior metadata report, failed/corrected command evidence and candidate. Latest coverage is v2. All 94 package records have inspected availability metadata; only two native skeleton examples have retained direct proof, and only the new 350Z candidate was prepared by this leaf. No production catalog changes or gameplay eligibility approval. Independent [wrapper/integration review](output/independent-wrapper-review.json) also completed: four wrapper and seven contract checks pass, native identity/decode chain and legacy Corvette byte equality confirmed, no actionable defect found. Parent owns the remaining GPU/steering/scale review, exact stock configuration/shared PPF closure, then another source-identified alias/assembly variant. Do not promote all four-bone metadata entries or transfer evidence across PS2/Xbox builds.

Independent wrapper closure: prepare_mc3_vehicle validates source→pinned catalog→native DAT→exact DAVE PCK bytes→pinned native index and reader, re-decodes actual PCK bones and compares supplied proof. Four wrapper and seven contract checks pass; forged bones/raw tampering rejected; retained default Corvette GLB+descriptor byte regression passes. No actionable current wrapper/integration defect found. Exact tool hashes and limits retained output/independent-wrapper-review.json. Optional native_bones handling is MC3-only; no new excluded-family dispatch. No GPU/catalog changes; source unit/runtime/stock-assembly limits remain.

Independent glass/metadata follow-up: six prep/glass and seven contract checks pass, including legacy Corvette byte equality. Separate raw GLB comparison verifies V1→V2 changes exactly factor_status, V2→V3 exactly material6/7 alpha/color plus retained policy, and all three BIN payloads identical. Descriptors differ only permitted name/id/mesh/hash fields. Exact all-source material allowlist and active-reference restriction reviewed; lamp23/unknown/unreferenced definitions unchanged. Report output/independent-glass-metadata-review.json. No GPU/catalog mutation or native opacity/full-stock claim; ExhaustRear5 remains separate.


## Latest follow-up

See [selected-body closure, metadata/glass corrections and optional static exhaust](output/350z-closure-and-exhaust-README.md). V1–V3 are retained; latest optional v4 SHA is `4e63e3d8f4daef1403293f4c613629119e1e0b92440f6d12cc3f8e05a6a9db23`. All 16 selected stock-named/embedded body nodes match actual DAT/PCK arrays; two source-informed authored exhaust attachments add the configured shared page at exact native rest frames, not guessed offsets/scales. Original runtime activation and shading remain unproved. This follow-up supersedes the earlier unresolved exhaust investigation status without promoting a runtime-complete car claim. [Current manifest](output/closure-final-manifest.json).


## Documentation checkpoint: eleven-car library

The later curated review admits exact MC3 350Z v4 (`4e63e3d8…`) as one of eleven Racer player preparations; the candidate flag in its original preparation receipt records creation-time status. Current scope, manufacturer/source-game dimension distinctions and remaining research holds are documented in [car-scale findings](../../findings/car-scale.md), sourced from `assets/catalog/dimensions.json`, `prepared-sizes.json` and the exact acceptance manifests. The latest eleven synthetic keyboard loops use retained executable `73b6409966b408902d5b8bf99432617a3f76d6538aa16cb2df38da31a9009ffa`; earlier visual/motion evidence keeps its own executable hashes. No new captures, source data, code, build or GPU work occurred in this documentation pass. Original runtime activation, physical units and native shading remain unproved.
