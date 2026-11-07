# Asset failure diagnostic context

Question: distinguish parser rejection of expected mesh bytes from a different/corrupt input, while retaining exact descriptor revision and fixed-stage diagnostics. Before: import-recovery run1793953542712396-67208 operation24 logs asset_parse with no actual input hash; exact intentional broken payload is retained by the original driver. Evidence output/failure-before.json, before-identities.json, before-source and catalog-before.racer.

Scope: shared mesh/vehicle loader context and focused main asset_load telemetry, meaningful existing C++ checks. No GPU or catalog mutation; original runtime behavior/rejection codes preserved. No raw paths, contents or arbitrary exception strings added to telemetry. Fixed32MiB mesh read reused; new diagnostic hashes from already read bytes, no second read. New leaf<=32MiB, commands<=300s. Root controls native failure injection/retrieval after build.

Resume: implement fixed-size input hashes/stages, add failure identity regressions, coordinate before build, then hand to root for independent review/native validation.

## Implemented context and boundaries

Shared `AssetLoadContext` is diagnostic-only, fixed-size digest arrays plus stage and byte count. `loadMeshAsset` hashes its existing complete <=32MiB input buffer before parsing. `readVehicleDefinition` retains SHA256 of the successful existing <=32768-byte descriptor read. `loadVehicleAsset` supplies expected mesh and descriptor-declared source hashes, checks them as before, and carries identity/containment stages. No second file read or new GPU dependency.

Paired `asset_load_end` retains existing success/sha256/reason fields and adds: `load_stage`, `actual_sha256`, `expected_sha256`, `descriptor_sha256`, `source_sha256`, `input_bytes`, `input_identity`. Stage codes are definition/open/read/parse/buffers/validation/geometry/images/identity/containment/upload/physics/complete. Input identity is unavailable until complete input bytes exist, unqualified for readable inspection inputs with no expected hash, otherwise match or mismatch. Existing reason order is preserved: a malformed wrong-hash file still throws asset_parse; the new identity fields explain whether those parser bytes matched the expected hash.

A partial read, extra-byte/EOF failure, missing/nonregular file, empty or overbudget file leaves actual SHA empty and bytes0. This intentionally does not claim a prefix hash is a complete file identity. Hashes reflect the bytes actually captured in memory, not an assertion that the filesystem stayed unchanged after the read. Descriptor SHA identifies the original parsed descriptor revision, not a later reread or a digest of subsequently programmatically edited definitions. Source SHA is a declared donor identity, not runtime donor verification.

Main telemetry constructs fields within catch-all fail-open boundaries, preserving original loader exceptions/recovery and preventing optional success telemetry from turning a committed load into failure. No raw paths, file contents or arbitrary exception text are introduced; existing MeshAssetError fixed internal codes remain. Digest/context helpers are allocation-free/noexcept; actual allocation-failure injection has not been performed, and unavailable diagnostics can still drop events. Generic exception reason remains upload_or_allocation with the new stage providing location.

Existing mesh/vehicle checks now exercise parse mismatch versus parse-on-expected-bytes, valid hash mismatch, containment, missing/reset context, repair recovery, exact descriptor revision distinct from equivalent physics identity, and buffer/image stages. Before source and native failure evidence are retained in output; exact new source hashes and limitations in implementation-checkpoint.json. Producer invoked no build or GPU: root took the build lease before a build command ran. Code/tests are stable and released to root/Ford independent review. Resume: root full build/CTest, then exact native corrupt/repair query on new fields; record outcomes without replacing old evidence.

## Library context follow-up

Root ran the first delta build and all58CTest checks passed in11.82s. First build/CTest logs, source snapshot and independent Ford gap report are preserved under output/before-library-context before this follow-up. The adjacent gaps were descriptor/library parse failures lacking input identity, successful library hash being reread from its path, and unguarded library telemetry Field construction.

Added optional fixed-size VehicleLibraryLoadContext: exact `librarySHA256` from the existing complete read, active/attempted `descriptorIndex` (-1 when no entry active), and exact `descriptorSHA256` from the existing complete descriptor read before parsing. Standalone readVehicleDefinition accepts an optional digest output, resetting it before reading; its successful cached descriptor digest and physics identity are unchanged. Library context resets at call entry and before each descriptor; successful entry processing clears active descriptor state, preventing stale attribution to a previous entry. Duplicate or malformed descriptor errors retain the current entry index and complete-read digest. Missing/partial descriptor reads retain index but leave digest empty; missing/partial library reads leave all hashes empty and index-1.

Main failed vehicle_library_load events add library_sha256, descriptor_index, descriptor_sha256 with existing fixed reason. Success emits exact library_sha256 and count only: no last-descriptor-as-selected implication. Both success/failure field construction are catch-all guarded; success logging is outside the loader exception block so diagnostics cannot abort a loaded library or replace its original exception. No second library read remains in this telemetry path.

Meaningful fixtures added to existing vehicle_asset_checks cover malformed standalone descriptor/read reset, equivalent successful cacheddefinition, second-descriptor schema/missing/duplicate attribution, successful wholelibrary state, truncated secondentry, trailer/schema errors and missing-library reuse reset. No compile or GPU run by producer; exact latest hashes/checklist in output/library-context-checkpoint.json. Code stable/released for root final build/CTest and native three-fault checks.

Snapshots remain per-file reads, not an atomic library+descriptor file version. The recorded hashes identify read bytes, not preserved contents or proof of no later mutation; failed/partial reads intentionally have no complete hash. Index describes active/attempted parsing, not runtime selection. Actual allocation-failure injection remains untested; fail-open source guards may drop diagnostics. Resume: root validation and independent closure, preserving first58log and oldfailure evidence.

## End-to-end retained failure evidence

All58 CTest targets passed in11.00s after the final retention/loader changes. The frozen `output/verified-build-v3` executable is `73b6409966b408902d5b8bf99432617a3f76d6538aa16cb2df38da31a9009ffa`; preservation reports no issues. It matches the prior verified build byte-for-byte; repeated source-hash samples match current reviewed source. These snapshots are working-tree copies, not atomic compiler-input or OS-image attestations.

REA6.8.0 process provider3 captured `check_native_faults.py`: evidence `ev_f7a359796ba3eb3c63cf33c298464368b0bec06718eb656002931978e892bd8c`, exit0 and verified owned-process cleanup. Process sampling is partial; unrelated platform processes were left untouched. No filesystem snapshots/network observation were requested. Full result is `output/rea-native-faults.json`. The producer itself reads the actual retained JSONL stores after each native process.

Five controlled cases pass (`output/native-cases/manifest.json`), with original fixtures preserved:

- Wrong20-byte input: `asset_parse`, stage `parse`, actual SHA differs from expected, exact descriptor/source hashes retained.
- Expected-but-malformed20-byte input: same parser failure, stage `parse`, actual SHA matches expected. This establishes rejection of the declared bytes, not a parser defect.
- Malformed descriptor: library event records the exact library and descriptor SHA and entry index0; no mesh attempt.
- Duplicate entry: exact library/descriptor hashes and index1; fixed duplicate-ID reason; no mesh attempt.
- Unchanged repaired model: exit0, complete/match context and actual1280×720 garage capture, reviewed. The conversion receipt retains original PPM SHA, PNG SHA and decoded-pixel SHA; callback hash matches.

`*-retrieved.jsonl` files are real queries through `scripts/diagnostics.py`, not synthesized expected events. These new signals cannot fill missing fields in the earlier import-recovery run, recover original user failures, or explain who changed an input. They narrow integrity, parse, geometry, upload and configuration stages; external process/filesystem history remains separate.

Next: complete the current eleven-car checks and real1080p frozen-input loop, update the coverage/runbook and retain final source/query/gallery manifests. All native windows remain hidden.
