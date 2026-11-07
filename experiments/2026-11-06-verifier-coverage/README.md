# Verification failure lifecycle and source coverage

Target: current first-party verifier and diagnostic tooling in `/Users/nicolas/Documents/github/reverse-engineering/games/racer`. This pass closes a missing failure-record boundary; it does not certify every script branch or the whole project. Current per-file hashes and reviewed scope are in [source-coverage.json](output/source-coverage.json). The 22 listed files were actually read, including CMake/bootstrap and the requested test definitions; execution evidence is distinguished from source inspection.

Bounds: each command below completed within 300 seconds; this leaf is limited to 32 MiB and generated less than 1 MiB. Free space was approximately 440.76 GB before the fixtures. No GPU, Racer process, C++ build, network acquisition, dependency install or canonical profile/catalog change occurred. Native calls in new verifier tests were mocked. Existing source and before/after failure evidence are retained without deletion.

## Previously Visible

The diagnostic verifier already wrote a starting/running/finished native-run manifest. The feature verifier recorded start and native return. Capture, feedback, motion and selection tools retained native logs, actions, captures and successful result manifests, but some wrote their first result manifest only after all postprocessing. Existing JSONL query/bundle and build-preservation tools expose malformed/partial/unavailable evidence instead of claiming perfect history. Their fixture implementations were inspected and rerun.

Source discovery used:

```sh
jg "How do native verification scripts persist phase, process outcome and failure manifests when spawning, timing out or converting screenshots fails?" /Users/nicolas/Documents/github/reverse-engineering/games/racer/scripts --max-requests 8000 --concurrency 20 --max-output-bytes 24000
```

[Retained discovery](output/jg-verifiers.txt) ended with `End context.` and explicitly reported 791 bytes omitted by its output limit. All six changed verifier implementations were then read directly. That truncation was not treated as complete code coverage. Exact CMake, bootstrap and test paths were followed with direct reads.

## Blind Spots Identified

[Before reproduction](output/before-repro.json) ran the retained unmodified motion verifier under three headless failures: spawn `FileNotFoundError`, `TimeoutExpired`, and invalid PPM decoding. All three raised their original exception and left actions/native logs (plus the invalid image where applicable), but neither a result manifest nor a lifecycle record. Original verifier sources are retained in `output/before/` with hashes in [string-preservation.json](output/string-preservation.json).

Feature and diagnostic manifests could additionally show the native subprocess as finished even when later conversion or retrieval failed. A native exit code is not a full verifier outcome. The original historical app error is unrelated to these mocked tool failures.

The bootstrap cache branch also accepts any existing `.deps/{bgfx.cmake,bgfx,bx,bimg}` directory without checking its revision/content. [The isolated cache probe](output/bootstrap-cache-probe.json) exercised that exact embedded Python branch against four deliberately unverified private fixture directories, with network access mocked to fail if invoked. It accepted all four and made zero network calls. CMake's source-derived build ID does not hash these dependency trees. This remains a separate dependency-provenance gap; this pass did not replace or reacquire dependencies.

## What Changed

New `scripts/verification_lifecycle.py` writes a separate `lifecycle.json` beside existing manifests in six tools: diagnostics, features, vehicle motion, vehicle selection, feedback and scale capture. It starts once the fresh output directory exists. Existing manifests retain their formats and detailed evidence. Every original string constant, including the multiline feature action script, is unchanged; the preservation check is retained.

The sidecar stores fixed phase and error codes, start/finish timestamps, elapsed time, bounded process kind/exit/timeout/PID records, omitted-record count and diagnostic write-failure count. It does not store command arguments, raw paths, environment variables, arbitrary exception text or input contents. At most 64 process rows and 32 KiB are written. A phase guard avoids writes on unchanged capture-poll phases. Replacement uses a private temporary file and atomic rename; original verifier cleanup, return policy and exceptions remain authoritative. A native process that intentionally exits by kill can still be an accepted verifier case according to the original scenario policy.

Recording is best effort: failed writes preserve the previous complete JSON and cannot replace the verifier's original exception. The last phase helps diagnose where work stopped; it is not an exhaustive phase history. Disk failure or external termination can leave a stale `running` record. There is no directory fsync or power-loss durability guarantee. Process kill/wait remains the caller's existing responsibility, not the logger's.

[After reproduction](output/after-repro.json) repeats the three original motion failures. The original exception types remain; each now has a failed sidecar with the correct spawn/process/capture phase. Timeout is explicit. Conversion failure retains the native exit 0 while marking the overall verifier failed. The invalid PPM is retained. The raw sidecar examples are in `output/after-{spawn,timeout,conversion}/lifecycle.json`.

New tests also cover feature conversion and retrieval failure after its old native manifest says `finished`, selection preflight failure, successful/failed motion policy, unchanged-phase suppression, process count bounds, no secret/path text, atomic write failure isolation and Popen timeout after caller cleanup.

Executed checks (all headless):

| Command | Result and retained evidence |
|---|---|
| `python3 tests/verification_lifecycle_checks.py` | Nine tests passed after timeout attribution closure; [final log](output/lifecycle-tests-attribution-final.txt). The earlier eight-test log is retained. |
| `python3 tests/feedback_capture_checks.py` | Six tests passed; [final log](output/feedback-tests-final.txt). Initial integration exposed a mock without PID; the helper now records unavailable PID without breaking that existing process interface. The initial failing log remains retained. |
| `python3 tests/vehicle_capture_checks.py` | Six tests passed; [log](output/capture-tests.txt). |
| `python3 tests/build_preservation_checks.py` | Passed existing private/hash/budget/partial-write/traversal fixtures; [log](output/build-preservation-tests.txt). |
| `python3 tests/diagnostic_query_checks.py` | Passed actual fixture JSONL query/bundle, moved-store and failure retention checks; [log](output/diagnostic-query-tests.txt). |
| `python3 tests/car_import_checks.py` | 15 offline fixture tests passed; [log](output/car-import-tests.txt). |
| `python3 tests/car_install_checks.py` | 14 offline fixture tests passed; [log](output/car-install-tests.txt). |
| `python3 ../../tools/check.py` | Hub checker passed; [log](output/hub-check.txt). |

No C++ tests were rerun here. Career, career integration, diagnostics, document store, garage features, livery, raster and parts test sources were read for their actual assertions and limitations. Their previous 58-suite result is not used as a substitute for this inspection. Root owns CMake test registration and any later full-suite/native acceptance.

Actual existing history was queried, without launching the app:

```sh
python3 scripts/diagnostics.py --root experiments/2026-11-06-asset-failure-context/output/native-cases/mismatched-input/history --event asset_load_end --limit 10
```

[Retrieved event](output/current-native-query.jsonl): run `1793957214987494-1825`, operation 7, `asset_parse`, stage `parse`, actual input SHA `57bc7d06ba31c708672bc5ca79b9dd513c1603699dff337354df6b675ba734ee`, expected mesh SHA `77a9becc6d20882a97417610a5a6a22120c33076c92d54ae7b84bec70eef81fb`, identity `mismatch`, input bytes 20. This is retrieval of the earlier controlled native case on the retained 73b640… executable, not a new native run or recovery of the original human incident. New lifecycle JSON is independently inspectable with ordinary JSON tooling; no new telemetry service was added.

## Next Iteration Targets

- Validate or explicitly qualify existing bootstrap dependency caches and retain acquisition identity. The current accepted-directory probe is a concrete gap, not a demonstrated malicious dependency.
- Motion/selection still accept external executable/library paths and sample some identities after execution. Their new lifecycle record does not provide the feedback tool's stronger input freezer guarantee.
- The feature verifier's existing acceptance does not require exactly eleven captures at each size. Lifecycle `completed` means the existing verifier returned successfully, not that every intended screenshot was independently checked.
- Failures before fresh-directory creation cannot write into that directory. Permanent disk failure, abrupt kill, hostile concurrent mutation and allocation exhaustion remain limits; missing terminal status must be treated as incomplete evidence.
- Root should independently review the helper/integrations, register the new headless test, and choose any fresh native run. Historical captures and their driver hashes remain immutable; this code change does not retroactively upgrade them.

Resume: implementation and headless checks are complete for this bounded lifecycle delta. Root review/registration and separate cache/provenance work remain. Do not infer broad project completion from this leaf.

## Final combined inspection checkpoint

The [aggregate inventory](output/aggregate-source-coverage.json) combines the asset-context, native, tool and verifier inventories plus the new [independent observer/capture review](../2026-11-06-native-coverage/output/independent-observer-capture-review.json). The measured universe is now **152 files**, because this pass added one helper and one test. All 152 have exact-current-hash selected-boundary inspection credit; there are **zero uninspected or hash-stale paths at this checkpoint**. Every current source hash and inventory input hash was rechecked after final tool changes and root CMake registration. This is file-level boundary inspection coverage, not every branch, all runtime configurations, vendor code or a broad project completion claim.

The independent observer/capture review found no actionable defect in the changed PlayFlow observer, per-tick boundary edge, screenshot callback and main requestCapture diagnostic guards. Root's retained direct flow/render logs were read: they contain the recovered `observation_failures=1` state, transient `boundary_contact`, and successful `capture_end` with `callback_failures=1`. Both report PASS. The render fixture validates a one-pixel PPM and concurrent trace ordinals; it is not a GPU window test. No new C++ execution was performed by this reviewer. The precise source hashes, limits and root log hashes are retained in the review JSON.

## Independent timeout attribution correction

Ford's independent review found that the original helper could relabel the last native Popen row as timed out when a later retrieval subprocess timed out. The exact real-Python reproduction is retained in `output/timeout-attribution-before/` and `output/timeout-attribution-before.txt`: native exit 0 was incorrectly tagged timeout. After the correction, `output/timeout-attribution-after/` and its text record preserve native exit 0 with `timeout=false`; only the retrieval row is timed out. The original timeout still propagates.

The helper now tracks the current process record and only attributes an escaping timeout to an unfinished current Popen record. New headless regression cases cover both explicit `process_done` and native exit before retrieval without that explicit call. All nine lifecycle tests pass. Source and aggregate inventories have been rehashed after this fix; the earlier 59-test/root native completion records remain evidence for their earlier helper revision. Their successful runs had no retrieval timeout, so they are not relabeled or claimed to exercise the fixed branch. [Ford independent closure](../2026-11-06-native-coverage/output/independent-lifecycle-review-closure.json) confirms the same real Python-child reproduction and all nine tests pass. Root final rebuild remains separately owned.
