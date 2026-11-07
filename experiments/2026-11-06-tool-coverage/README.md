# Offline tool visibility and coverage delta

This pass covers 13 delegated converter/parser/fit helpers and 23 matching Python test files. It does not certify their imported dependencies, vendor code, native game behavior, GPU behavior, physical hardware, or the entire repository.

The experiment directory and private output directory were created before probes, after checking at least 20 GiB free. Commands are bounded to 300 seconds, output to 32 MiB; no build, GPU launch, download, or large extraction was performed. The shared working tree was already dirty; unrelated files were preserved.

## Previously visible

[coverage.json](output/coverage.json) binds each fully read current source to SHA256, byte count, function/class line locations, visibility and retrieval limitations. All 36 entries are inspected in this pass. Imported producer modules outside this list remain uninspected here. Old geometry reviews were not substituted for a fresh source inspection and were not promoted into runtime claims.

Successful converters usually retain source/prepared hashes, descriptor geometry and explicit authored/native limitations in GLB extras or JSON receipts. MC3 additionally verifies actual DAT/PCK bytes and a pinned reader before accepting skeleton JSON; MCLA ambient preparation explicitly remains traffic. SLRR retains scoped package/resource identities, payload hashes and unresolved material issues. `vehicle_clearance` retains descriptor/mesh hashes, bounded witnesses, discrete angles and explicit static/contact limitations. These are code capabilities. This pass did not execute the source games or re-extract their geometry.

There is no common automatically retained command/run identifier, start/end timestamp or deployment envelope for these standalone helpers. A successful artifact persists locally until manually deleted; no automatic retention period, remote telemetry store or expiry mechanism was established. Historical failures whose stdout/stderr was never retained remain unavailable. Input paths/raw donor tokens in deliberate offline reports are not privacy-filtered runtime telemetry: `slrr_assets.py:200` emits an absolute source path, and `slrr_gltf_materials.py:92` may retain an OS exception string. Keep reports private and review before sharing. No environment or credential collection was found in these inspected helpers.

## Blind spots and acceptance checks

1. High diagnostic value: `check_car_scale.py:56–63` reads one descriptor separately for geometry, source identity and hash. A deterministic read-boundary replacement produced a report with measured length 4 m but a SHA/source belonging to the replacement 6 m descriptor. This is a safe synthetic incident, not a historical production incident. Acceptance: measurement, model identity and SHA must derive from one bounded regular-file byte snapshot, with a regression replacing the file between potential reads.
2. High diagnostic value: standalone `juiced2_data.py:47–48` reads an unbounded input and opens output before strict JSON serialization completes. A 19-byte compiled float-NaN fixture exited 1 with a 338-byte invalid JSON file. Acceptance: finite typed values and bounded input/work/output; reject before opening output, preserve an existing destination, explicit nonzero failure and retained captured reason. The original failed file and stderr are preserved.
3. Medium: fresh multi-file converter publication commonly writes a successful receipt last. A crash/write failure can leave meshes or temporary decoded parts without a completion receipt. Some CLIs warn about partial output; others emit only a traceback. Acceptance: a future shared command wrapper should retain bounded stage/error/source identity and partial status, and never label receipt-less output complete. This pass does not change root-owned publishers or imply past missing receipts can be recovered.
4. Medium: `slrr_resources.py:94` limits graph depth and source bytes but not aggregate repeated reference expansion. A highly branching acyclic graph can duplicate large result trees without new input reads. Acceptance: cap visited resolution operations/output entries and explicitly report incomplete/rejected traversal. This is a source inspection finding; no expensive stress expansion was run.
5. Low/maintenance: `prepare_source_vehicle_checks.py` directly reads retained local/excluded-family fixtures rather than reporting missing dependencies as skip77. It was inspected but not run; no GT1/Redline acquisition or adaptation was performed. Other fully source-dependent MC3/MCLA/J2-fit suites have CLI77 guards. Default `mc3_repair_checks.py` and `juiced2_vehicle_checks.py` run synthetic assertions only unless an actual-artifact directory is supplied: their default exit0 is not full native fixture acceptance.

## What changed

After parent coordination released both helpers, `check_car_scale` now reads a bounded regular descriptor once and derives measurements/source identity/SHA from that same byte snapshot; the dimensions table is capped at 256 KiB. `juiced2_data` now limits input to 16 MiB, fields/lines to 100000, each string to 64 KiB, expanded strings to 8 MiB and serialized output to 32 MiB. Nonfinite floats fail explicitly. Strict serialization completes before exclusive output creation; failures return generic exit2 without printing raw paths/values. Storage failure during an actual write can still leave partial output, explicitly warned; this is not a transactional publisher.

Focused tests add concurrent descriptor replacement, NaN, input/field/string/output limits, no-output-before-validation, no overwrite and symlink refusal. After-fix results and changed producer/test hashes are in [after-checks.json](output/after-checks.json); all 17 default offline commands pass again. Before-fix hashes/results and the original invalid JSON are retained unchanged. The two pre-fix producer snapshots (`output/before-check_car_scale.py`, `output/before-juiced2_data.py`) were reconstructed from the narrowly changed source and independently matched against the pre-edit SHA256 recorded in coverage-before-fixes.json; byte identity passed for both. The investigation harness is historical: rerunning it against the changed working tree is not a replay of the pre-fix producers. Five mocked missing-file CLI checks return 77 in [missing-fixture-checks.json](output/missing-fixture-checks.json); no real inputs were moved/read by those probes.

## What was actually verified

The exact executable investigation script is [audit_checks.py](output/audit_checks.py), with results in [checks.json](output/checks.json). Seventeen default offline test CLIs exited 0 in under one second total. Per-command stdout/stderr logs and test-source SHA256 are retained. Source-dependent full geometry suites were inspected but not rerun; this avoids representing old geometry acceptance as a new run. Optional NumPy surface checks ran only if the installed interpreter supplied NumPy; inspect `vehicle_clearance.log` for actual skip counts.

The safe failures reconstruct as follows:

- `mixed_generation_reproduction`: the patched read returned descriptor A while replacing the file with B. The report retained A's 4 m measurement but B's source and SHA; the independent current measurement was 6 m. This directly supports a report consistency defect. It does not establish that a real concurrent replacement happened historically.
- `partial_output_reproduction`: a typed NaN passed the decoder, strict JSON rejected it after opening the destination, exit1 and invalid338-byte output were retrieved from disk. This establishes the failure lifecycle, not any native game's use of NaN.

There is no runtime overhead/performance claim for these scripts. File and geometry limits are source-inspected limits; Python container amplification, permissions changes, interrupted publication, concurrent writers and external reader replacement remain unqualified unless a listed test explicitly exercises them.

## Investigation runbook

From the repository root:

```sh
python3 -c 'import json; d=json.load(open("experiments/2026-11-06-tool-coverage/output/coverage.json")); print([(r["path"],r["sha256"],r["observed_runtime"]) for r in d["files"]])'
python3 -m json.tool experiments/2026-11-06-tool-coverage/output/checks.json
cat experiments/2026-11-06-tool-coverage/output/nan-failure.log
```

The three synthetic J2 registry dependency checks also pass after the decoder change.

Before relying on an old artifact, hash its producer and inputs and compare them with that artifact's actual recorded pins. Identify the exact output receipt and whether its output SHA matches the file. Treat a missing receipt, incomplete JSON, omitted fixture or absent stdout as missing evidence. Do not infer completion from a directory name or a default synthetic test's exit0. For a new failure, retain the bounded command, exit status, stage and source hashes in a fresh private experiment directory before retrying; do not overwrite failed output. A new instrumented tool cannot reconstruct a failure from yesterday when nothing was retained.

Behavioral discovery used:

```sh
jg 'How do offline vehicle calibration, source parsers and static fit tools retain provenance and failure context, enforce bounds, and distinguish source-dependent skipped tests?' /Users/nicolas/Documents/github/reverse-engineering/games/racer/scripts --max-requests 8000 --concurrency 20 --max-output-bytes 6000
```

JG completed (session55180, 42 leads, `End context.`), but its output cap truncated the 292563-byte result. All delegated source/test files were therefore read directly before assigning inspected status; JG's leads alone were not accepted as coverage. An exact-symbol follow-up also exceeded stdout; no missing excerpts were treated as inspected evidence.

## Resume

The source audit and safe failure probes are complete. `coverage.json` contains current per-file hashes, not repository-wide completion. Both reproduced defects were reported before editing and then fixed after parent coordination. Current hashes are in coverage.json; original hashes are retained in coverage-before-fixes.json. Remaining priorities are aggregate SLRR reference work bounds and a shared retained failure envelope for future converter commands. Historical missing telemetry, original-game runtime, vendor/hardware and untouched dependencies remain outside this pass.
