# Investigating retained Racer evidence

Use repository root `/Users/nicolas/Documents/github/reverse-engineering/games/racer`. Normal launches now record local JSONL under `~/Library/Application Support/Racer/Racer/diagnostics`; `--diagnostics-dir PATH` chooses an isolated store, `--no-diagnostics` disables it. No upload/service/credentials are involved. This cannot recover history from older builds. The [current coverage map, actual evidence and prioritized gaps](observability.md) distinguish source inspection, observed telemetry and accessible history.

## Retrieve yesterday's failure

Preserve matched runs before moving a store or changing builds. This optional local command creates a fresh bundle with whole JSONL files, hashes, build context and explicit completeness issues:

```sh
python3 scripts/diagnostics.py --root /absolute/history --run RUN_ID --bundle /absolute/new-incident
python3 scripts/diagnostics.py --root /absolute/history --since 2026-11-05T00:00:00-05:00 --until 2026-11-06T00:00:00-05:00 --operation 3 --bundle /absolute/new-incident
python3 scripts/diagnostics.py --root /absolute/new-incident --summary
```

Add `--capture-root /absolute/history/captures` to copy images matching recorded SHA-256. Only that explicitly supplied directory is searched (256 entries and a byte budget); arbitrary logged paths are never followed. Missing images are listed as unavailable; converted PNGs whose hash differs from original PPMs are not silently substituted. A bundle contains no executable, source snapshot or player profile: preserve the matching build separately when reproduction requires it.

Bundle mode prints run summaries regardless of `--limit`, preserving whole runs even when time/operation filters match a small excerpt. Payload reservation defaults to64MiB (`--bundle-max-mib 1..128`), including failed write attempts; manifest metadata is additional. Directory/files use0700/0600, existing destinations and destinations inside the source store are refused, symlink files skipped. Originals are neither moved nor pruned. Local copies can still contain sensitive information already present in input logs; review before sharing. No upload occurs.

Bundle exit0 means selected evidence copied without reported issues; exit2 means a partial bundle (inspect `manifest.json` issues); exit1 means no matched events or an export error. A wholly unreadable run can still be preserved without filters but remains unavailable evidence. Copies are not atomic across files; detected source changes are flagged, but a live snapshot can still miss later events. Querying corrupt-only files now reports the damage, and oversized histories above8MiB are explicitly unknown rather than read without a budget. A missing final newline is flagged even when its JSON parses.

```sh
python3 scripts/diagnostics.py --summary
python3 scripts/diagnostics.py --since 2026-11-05T00:00:00-05:00 --until 2026-11-06T00:00:00-05:00 --summary
python3 scripts/diagnostics.py --run RUN_ID --event app_start --event executable --event process_outcome
python3 scripts/diagnostics.py --run RUN_ID --operation 3
python3 scripts/diagnostics.py --profile PROFILE_SHA256 --summary
python3 scripts/diagnostics.py --run RUN_ID --event motion --event state --event sdl_event
```

Replace run/operation/profile placeholders with values from the first summary/event query. `--operation` includes matching `parent_operation` saves. Profile filtering selects every retained run that accessed that normalized path hash; this is correlation, not a lock or a content identity. `--root /absolute/experiment/history` queries an isolated store. Time bounds use ISO-8601 with an explicit offset; event order within a run uses monotonic time and sequence, not wall clock. Exit 1 means no matching evidence; exit 2 means output was capped (default 2000 rows), so narrow time/events or explicitly raise `--limit`. Diagnostics only read the top-level JSONL files in the chosen store.

1. Preserve the run file, relevant profile copy and captures before changing anything. Inspect `evidence_issues`: dropped events, absent end, partial rows or quota stops mean an incomplete history. Absence of a failure event is not evidence of success. A missing end can mean still running, crash, kill, quota or disk failure; consult the process/job handle or OS evidence before deciding which.
2. Identify executable SHA-256, source/config build ID, runtime SDL/platform, shaders, renderer/drawable and automation flags. Compare the exact build to any proposed reproduction. Build ID hashes first-party sources/tests/scripts and CMake/compiler/build type; dependency pins are in `references/dependencies.md`, not a cryptographic inventory of every vendor source.
3. Find the affected attempt using `state` test/phase/gate and operation. Follow `command` → state/focus/rearm → motion → profile save begin/end. Check stage, errno and success; correlate retry IDs and the subsequent run's load. A valid result and a successful disk save are separate facts.
4. For steering, compare selected/effective steer with physics heading, interpolated shown heading, model forward X/Z, camera position/target, pause/rearm and input source. `model_x/model_z` should match sin/cos(shown_heading). A sampled numeric match cannot prove GPU pixels; use captures and the render regression check.
5. For a stall, locate the one-second `timing` window and neighboring states/capture requests. `max_ms`, slow-frame count and clamped seconds establish timing, not the responsible thread or driver. Do not equate capture-producing runs with no-capture performance.
6. Reproduce on a fresh isolated profile/store, run the relevant regression checks, retrieve the new evidence with the same query, and compare the symptom/outcome. Keep old failed runs. Separate observed causes, plausible alternatives and facts unavailable from the retained data.

## Capture a report without recording the desktop

The first detected model/travel orientation mismatch automatically requests a bounded app capture. F8 during play emits a `user_marker`, queues an app-renderer screenshot and records request frame/ID plus completion status/hash/dimensions. PNG/PPM file hashes identify retained image bytes; path hashes bridge request/outcome without exposing paths in event payloads. Images live under `diagnostics/captures`. Inspect actual pixels; an output callback is not a visual review.

For unattended work while the computer is in use, always pass `--background`. It creates a hidden SDL/Metal window; it does not activate an app or synthesize desktop input. Live verification uses SDL's own virtual input/event queues. Do not use CUA activation or visible native windows without renewed user direction.

```sh
ctest --test-dir build --output-on-failure
./build/racer --background --smoke 14 --autodrive --profile /absolute/fresh/profile.txt --diagnostics-dir /absolute/fresh/history
python3 scripts/verify_diagnostics.py /absolute/fresh-evidence
./build/diagnostic_checks /absolute/fresh-fixture
python3 scripts/diagnostics.py --root /absolute/fresh-fixture/history --event profile_save_begin --event profile_save_end
```

The native verification script requires Pillow for lossless PPM→PNG conversion. It retains exact commands, executable hash, exits, logs and query summaries; no player profile is used. `--autodrive-left` is the mirrored synthetic turn fixture. `--shader-dir` can direct an isolated run to an empty fixture directory to exercise missing-dependency diagnostics without modifying pinned shaders.

## Schema, retention and privacy

Imported-car investigations add `vehicle_library_load` (catalog SHA/count or fixed
failure reason), paired `asset_load_begin/end` (operation, actual mesh SHA,
physics identity, section/image counts, bounds and wheelbase), four change-only
`wheel_geometry` events, and sampled `wheel_pose` for front-left axle/spin.
`motion` includes vehicle identity, wheelbase, signed travel and steering.
Library/descriptor failures, mesh decoding, GPU upload, active in-memory car,
selection persistence and reload are distinct boundaries. Retrieve them together:

```sh
python3 scripts/diagnostics.py --root /absolute/history --event vehicle_library_load --event asset_load_begin --event asset_load_end --event wheel_geometry
python3 scripts/diagnostics.py --root /absolute/history --operation 13
python3 scripts/diagnostics.py --root /absolute/history --event motion --event wheel_pose --since 2026-11-05T22:00:00Z --until 2026-11-05T22:05:00Z
./build/vehicle_validate assets/local/vehicles/catalog.racer
```

Operation numbers are run-local examples: choose the actual run and operation
from the first query. `wheel_pose` samples are additional bounded events, so the
4 MiB admission cap can be reached sooner. The recorder never silently prunes
older evidence. Preserve the exact local car library and its source/prepared
receipts along with the build; the generic build snapshot excludes game assets.
Acquisition/publication receipts are separate JSON under
`assets/local/carmodels/{receipts,install-receipts,catalogs}` with UUID operations,
source commit/catalog/source/mesh/descriptor hashes, outcomes and limits. There
is no automatic receipt retention pruning; inspect disk use before bulk imports.

Screen values: 0 drive, 1 pause, 2 garage, 3 pending, 4 tests, 5 results. Phase: 0 idle, 1 countdown, 2 running, 3 valid result, 4 invalid. Action: 0 up, 1 down, 2 left, 3 right, 4 accept, 5 back, 6 pause, 7 reset. Persistence: 0 new, 1 loaded, 2 saved, 3 failed, 4 disabled. Slots are zero-based A/B/C. Operation IDs are unique only within a run. Schema is version 1; unknown schema is reported unreadable rather than silently accepted.

State transitions are change-only; pose/input/model/camera snapshots are sampled at up to 10 Hz and timing at one-second intervals. Automatic test input is labeled separately from host input; sampled host input is not a deterministic simulation replay. The recorder uses a 512-event queue, 8 KiB event limit, 4 MiB per run, at most 16 retained run files and a 64 MiB admission cap. It stops rather than deletes history. Depending on event density a run may hit its cap within minutes; `recording_stopped` marks the limit. Archive reviewed history deliberately and choose a fresh store before long investigations. There is no calendar-based guarantee, external backup or automatic rotation.

Diagnostic files are created mode 0600. Structured events omit arbitrary keys/text, raw paths, environment variables, file contents and device names/serials. Path SHA-256 is pseudonymous and may be guessable; do not publish stores without review. Native stderr and explicit experiment command manifests can contain local paths and are separate artifacts. F8 images contain only game-renderer output. Manual captures have an 8-per-run/64 MiB-directory budget; external capture runs have a 48-image/240 MiB callback budget. Concurrent manual-capture quota checks are best effort; use one capture producer per store.

Writes happen on a background thread; queue saturation counts drops, failures disable recording and warn stderr, and normal exit attempts fsync. Crashes/kills can lose queued tail; power-loss durability, filesystem hangs, OS/GPU crash dumps, remote telemetry and physical controllers are not established. The recorder reports evidence; it does not automatically diagnose a cause.

## Current workflow and model investigation

`workflow_state` is a change-only bridge for canonical parts, applied/draft livery and career save-document hashes, plus active vehicle physics identity, profile hash, revisions, screen/attempt/frame, career running/checkpoint/selection and each sidecar's status/stage/errno/write-enabled state. Hashes identify in-memory save projections; they do not establish successful disk persistence. Follow paired document save and later load events. Career's serialized hash deliberately excludes running/checkpoint; inspect their separate fields. Multiple mutations within a frame can collapse into one snapshot; command/domain events retain the finer sequence.

`livery_render` now carries frame, applied/draft revisions, vehicle and attempt. Before an automatic test the attempt can legitimately be0; use run+frame+state hash+revision to bridge that upload to the unified snapshot. Submission is not GPU completion. `asset_motion_roles` distinguishes rolling sections from steering-only caliper carriers; sampled `carrier_pose` and `wheel_pose` share frame/hub/axle context.

```sh
cd /Users/nicolas/Documents/github/reverse-engineering/games/racer
python3 scripts/diagnostics.py --root experiments/2026-11-06-observability-delta/output/workflow-evidence-v5/diagnostics --event workflow_state --event document_save_end --event document_load_end --summary
python3 scripts/diagnostics.py --root experiments/2026-11-06-fit-review/output/live-seven-v1/6/history --event asset_load_end --event workflow_state --event state
python3 scripts/diagnostics.py --root experiments/2026-11-05-city-scale/output/eligible-seven-v3/0-rear/history --event executable --event workflow_state --event livery_render
python3 scripts/diagnostics.py --root experiments/2026-11-05-car-models/output/motion-juiced2-carriers-v3/history --event asset_motion_roles --event carrier_pose --event wheel_pose --limit 500
./build/vehicle_validate assets/local/vehicles/catalog.racer
rg -l --fixed-strings e2a0ef6440d2634438446d1c2254099086852939f088abea5afc75c211597025 assets/local/carmodels/catalogs assets/local/carmodels/install-receipts
```

A source model upgrade keeps old assets and catalogs; the active revision uses a new geometry identity, so old performance records are not silently mixed. Unknown saved selection IDs preserve their original sidecar and show an explicit replacement choice. The local publisher keeps Garage cycle order when upgrading an existing source. GT1/Redline listing/acquisition/publication are excluded, and MCLA ambient IDs remain traffic-only.

For geometry, retrieve the exact descriptor and mesh SHA from the retained run before using today's inventory. `scripts/vehicle_clearance.py` supports bounded triangle/cylinder diagnostics and optional actual triangle contact tests in an existing NumPy environment. Filled cylinders include interior wheel space, so intersections with suspension or wheelwell planes are not automatically source defects. See retained [contact evidence and commands](../experiments/2026-11-06-fit-review/output/clearance-v1/README.md), including corrected endpoint/timing cases. Compare actual rendered views before changing pivots or physics.

The [coverage delta](../experiments/2026-11-06-observability-delta/coverage.md) distinguishes inspected boundaries, prior retained history, current native events and remaining uninspected/inaccessible areas. Default-root inspection returned no matching history at this checkpoint; isolated experiment stores remain accessible. This is not a guarantee of yesterday's data or automatic diagnosis.

## Current loader and verifier failures

The loader now records `load_stage`, `input_identity`, `actual_sha256`, `expected_sha256`, `descriptor_sha256`, `source_sha256` and `input_bytes`. The actual input digest comes from the same complete bounded read used for parsing. `mismatch` supports a byte-identity discrepancy; `match` plus `asset_parse` supports rejection of the declared bytes, not automatically a parser defect. An empty digest/unavailable identity means no complete input identity was established. Library failures retain the exact library digest and active descriptor index/digest; successful library events do not label the last descriptor as the selected car.

Copyable actual evidence queries:

```sh
cd /Users/nicolas/Documents/github/reverse-engineering/games/racer
python3 scripts/diagnostics.py --root experiments/2026-11-06-asset-failure-context/output/native-cases/mismatched-input/history --run 1793957214987494-1825 --operation 7
python3 scripts/diagnostics.py --root experiments/2026-11-06-native-coverage/output/diagnostics-v1/interrupted/history --summary
python3 scripts/diagnostics.py --root experiments/2026-11-06-native-coverage/output/diagnostics-v1/right/history --event motion --event capture_end --limit 300
python3 -m json.tool experiments/2026-11-06-native-coverage/output/diagnostics-v1/lifecycle.json
python3 -m json.tool experiments/2026-11-06-verifier-coverage/output/after-conversion/lifecycle.json
```

The mismatch case retains actual SHA `57bc7d06…`, expected `77a9becc…`, 20 bytes, parse stage and operation 7. It was an intentional controlled fixture. The interrupted case has a missing terminal event; only its separate runner manifest establishes deliberate kill/exit -9. JSONL alone leaves the cause unknown. The default-root query remains unavailable at the [latest checkpoint](../experiments/2026-11-06-native-coverage/output/default-root-query-v1.json).

Six verification tools now write a bounded private `lifecycle.json` beside their existing detailed artifacts. Inspect status/phase/error code, individual native/reload/retrieval exits and timeouts, omitted-process count and diagnostic-write failures. A native exit 0 can coexist with overall capture or retrieval failure. A successful native process must not be relabeled by a later query timeout; the real-child before/after regression is retained in the verifier experiment. The sidecar stores no argv, environment, raw path or exception text. Limits are 64 process rows/32 KiB, atomic replacement, no directory-fsync or power-loss guarantee. A stale running record is incomplete evidence. Feedback/scale validation performed before creating output remains outside this sidecar.

Free-drive boundary hits now emit rising-edge `boundary_contact`, avoiding loss of a one-tick contact between 10 Hz motion samples. `state.observation_failures` and `capture_end.callback_failures` are cumulative observed exception counts reported on a later successful observation/capture. They do not count recorder queue/disk losses, guarantee recovery, or prove no failure before process termination. Retrieve the focused fixtures with:

```sh
rg 'OBSERVATION_EVIDENCE|CAPTURE_EVIDENCE' experiments/2026-11-06-native-coverage/output/flow-checks-runtime-v1.log experiments/2026-11-06-native-coverage/output/render-checks-runtime-v1.log
python3 -m json.tool experiments/2026-11-06-verifier-coverage/output/aggregate-source-coverage.json
python3 -m json.tool experiments/2026-11-06-car-coverage/output/car-coverage-eleven-v6.json
```

For a source/publication investigation, join the incident's exact descriptor/source/model SHA to immutable managed catalogs and installation receipts. New publisher receipts retain actual review-inventory bytes and explicit review-evidence files by hash; older receipt-less history is not retroactively restored. Standalone converter reports can contain donor tokens/local paths and are private artifacts. Missing receipt, invalid JSON or unverified producer identity means partial/unknown evidence, even when a mesh file exists.

Preserve a matching executable/source envelope separately:

```sh
python3 scripts/preserve_build.py /absolute/fresh-build-snapshot --exe /absolute/incident/racer
```

This copies bounded first-party working-tree source and named shader/cgltf inputs; it excludes game models, profiles, most dependency trees, dylibs and OS state. Source copied today is not proof of yesterday's compiler inputs. Preserve actual historical snapshots and original failed outputs; never overwrite them to make a current replay look complete.

## Latest actual incidents

The [cohort experiment](../experiments/2026-11-06-cohort-acceptance/README.md#investigation-runbook) gives copyable time/run/operation queries for Lightning save failures (63/67), successful retry (70), later process reload and a rejected review key. Preserve its script and native log alongside JSONL: `key confirm` previously meant Down, so process exit 0 alone could not prove intended screen coverage. The strict driver now retains `review_script_error` with fixed reason `unknown_key` and numeric command index, without raw script text. Use the script at that index to investigate; do not infer that later commands ran. The new-process comparison has a native PPM hash and pixel-equivalent PNG; older failed captures remain separate.

The current [164-file source inventory](../experiments/2026-11-06-cohort-acceptance/output/aggregate-source-coverage-v2.json) records exact inspection hashes. Converter receipts may still be absent after partial output or interruption; inspect each producer's retained status/log/source pins and report missing evidence explicitly. A successful current preparation cannot reconstruct an earlier unretained failure.

Source preparation attempts now also have direct retrieval examples in [MC3 attachment acceptance](../experiments/2026-11-06-mc3-attachment-acceptance/README.md#historical-investigation-commands). Read `lifecycle.json` using `python3 -m json.tool`; correlate the fresh attempt folder, `started_unix_ms`, requested source/config hashes, phase, active model, final status and errno. Before/after retained first-Saleen write probes demonstrate why the actual write owner matters. The shared `checkpoint()` persists changed context within the same phase, but failed diagnostic writes can leave older state. No sidecar status alone establishes a process is still live.

## Register and investigate retained preparations

The registrar is a dry operation. Use a fresh, explicitly budgeted output directory; it never edits the curated inventory or publishes a player. Existing model-ID conflicts are reported and preserved. New rows are always ineligible research candidates. The actual current inventory is near its256 KiB limit; do not treat the commands as an all-car import.

```sh
python3 scripts/register_research_preparations.py --help
./build/vehicle_validate --descriptor /absolute/retained/car.vehicle
python3 -m json.tool experiments/2026-11-06-preparation-registry/output/dry-v1/report.json
python3 -m json.tool experiments/2026-11-06-preparation-registry/output/dry-v1/lifecycle.json
python3 -m json.tool experiments/2026-11-06-preparation-registry/output/fresh-boundary-repair.json
```

Inspect `inventory_input_sha256`, `selection_sha256`, `inventory_output_sha256`, `source_tool_sha256`, each outcome and evidence-file hash. Frozen input JSON is the actual read used by that attempt. Source/evidence bodies are retained in place, not transitively copied. `active_input` distinguishes inventory/selection failures in the repaired version; earlier attempts lack it. `active_model` identifies validation ownership; null at batch writes. An absent sidecar is unknown evidence, not success. A late write may leave `inventory.json` without `report.json`; never apply that orphan result.

This bounded time query inspects at most64 immediate attempt sidecars in the known registry leaf (not arbitrary paths), excludes symlinks, limits each read to32 KiB and prints fixed diagnostic fields. Set `wanted_model` to an exact model ID if investigating validation ownership. The fresh directory path plus input hashes/timestamps identifies an attempt; registrar operations have no global UUID or JSONL phase history.

```sh
python3 - <<'PYQUERY'
from pathlib import Path
from datetime import datetime
import json
root = Path('experiments/2026-11-06-preparation-registry/output')
since = int(datetime.fromisoformat('2026-11-06T00:00:00+00:00').timestamp()*1000)
until = int(datetime.fromisoformat('2026-11-07T00:00:00+00:00').timestamp()*1000)
wanted_model = None
paths = sorted(root.glob('*/lifecycle.json'))
print({'candidates': len(paths), 'capped': len(paths) > 64})
for p in paths[:64]:
    if p.is_symlink() or p.parent.is_symlink():
        print({'attempt': p.parent.name, 'evidence': 'symlink_skipped'}); continue
    try:
        with p.open('rb') as stream:
            raw = stream.read(32769)
        if len(raw) > 32768:
            print({'attempt': p.parent.name, 'evidence': 'oversize'}); continue
        row = json.loads(raw)
    except (OSError, ValueError):
        print({'attempt': p.parent.name, 'evidence': 'unreadable_or_invalid'}); continue
    if since <= row.get('started_unix_ms', -1) < until and (wanted_model is None or row.get('active_model') == wanted_model):
        print({'attempt': p.parent.name, **{k: row.get(k) for k in ('status', 'phase', 'started_unix_ms', 'finished_unix_ms', 'active_input', 'active_model', 'inventory_sha256', 'selection_sha256', 'error_code', 'errno', 'diagnostic_write_failures')}})
PYQUERY
```

For the actual Ford GT production save/reload, these commands retrieve the loaded catalog/asset and saved-document outcome; the example reload run is `1793968852277313-59277`, asset operation6. The first process history contains the preceding selection save. Each process has its own operation namespace.

```sh
python3 scripts/diagnostics.py --root experiments/2026-11-06-ford-gt-native/output/production-reload-v1/history --event vehicle_library_load --event asset_load_end --event document_save_end
python3 scripts/diagnostics.py --root experiments/2026-11-06-ford-gt-native/output/production-reload-v1/reload/history --run 1793968852277313-59277 --operation 6
python3 scripts/diagnostics.py --root experiments/2026-11-06-ford-gt-native/output/production-reload-v1/reload/history --since 2026-11-06T00:00:00Z --until 2026-11-07T00:00:00Z --event document_load_end --event asset_load_end
```

Reconstruct order from run/sequence/monotonic timestamps, verify actual catalog/descriptor/source/mesh hashes and compare the retained `.vehicle` selection sidecar. This supports the observed selected-car save/restart diagnosis. It cannot establish human usability, original-game handling, unavailable older runs or why a driver stalled without additional evidence.

The retained actual negative attempt can be retrieved directly without creating more output:

```sh
python3 -m json.tool experiments/2026-11-06-ford-gt-native/output/registrar-missing-selection-v2/lifecycle.json
python3 -m json.tool experiments/2026-11-06-ford-gt-native/output/registrar-negative-manifest.json
shasum -a 256 experiments/2026-11-06-ford-gt-native/output/registrar-missing-selection-v2/input-inventory.json
```

Observed reconstruction: current input SHA `a75b0ce56e2b1f0d5d02619e8b86ed65d2520f2b5eeb09aedc1c44fc930dd659` was read and frozen, the next selection read failed with errno2, no dry candidate/report was published, and the real input still has that SHA. The fixed input kind narrows the failing operation. Exact missing path cannot be determined from the redacted sidecar alone; the private retained command manifest supplies the deliberate fixture path. No automatic causal diagnosis is promised for arbitrary I/O failures.

## Large inventories and bounded selection evidence

Current preparation format limits are16MiB/3000records, shared by registration, publication, coverage and scale capture. Registration still takes at most64 selections/256KiB and128MiB total actual reads; publisher still selects at most16 and scale capture at most7. An admitted metadata file is not proof of source validity or player eligibility. Legacy missing-schema read inputs remain accepted where previously supported; registration requires schema1. Unknown explicit schemas, duplicate keys/IDs, nonfinite values and over-budget input/result are rejected.

Registrar output must reserve both immutable inventory copies plus selection/report and the largest publication temporary; its hard cap is50.25MiB including allowance. Do not infer that much project allowance is available: the project is close to its retained-output ceiling. Recheck the storage ledger/experiment reservation before running a producer. Encoding stops at the result byte cap, but serialized size does not guarantee peak Python memory. Source/input/evidence bodies are still separate retained paths.

The selection verifier stages only NSX/Nissan/Ford/target-Juiced2 scenario inputs. The original source indices and source catalog SHA remain in `selection-inputs.json`; target becomes subset index3. Selected payload64MiB and aggregate reads128MiB (including every scanned descriptor) are separate caps. An active catalog may contain many more models without copying its historical files. A rejected plan never starts the native process; a late staging failure can leave a plan and partial files. Do not call those a completed GPU test.

```sh
python3 -m json.tool experiments/2026-11-06-inventory-capacity/output/actual-selection-plan.json
./build/vehicle_validate assets/local/vehicles/research-selection-capacity-v1.racer
python3 -m json.tool experiments/2026-11-06-inventory-capacity/output/late-staging-failure-v1/lifecycle.json
python3 -m json.tool experiments/2026-11-06-inventory-capacity/output/actual-validation-and-failure.json
python3 -m json.tool experiments/2026-11-06-inventory-capacity/output/capacity-proof.json
```

Observed controlled failure: phasecapture, `publication_kind: mesh`, `active_input: mesh`, original descriptor index0 and expected mesh SHA `4c157f280bd085aa43bca9d9f82d380b84e7ebad2cac269fdf7dac3188475e8e`, errno28, no spawned processes. The plan pins source catalog `3da5f93b…` and four input identities; only the first descriptor was staged before injected mesh failure. A separate process retrieved this sidecar. The injection/test context establishes why errno28 occurred here; an arbitrary real errno28 event alone would not prove a physical-volume diagnosis. The sidecar remains best effort and excludes raw paths/exception text.

Check its `started_unix_ms`/`finished_unix_ms` for a time-range match and use expected mesh SHA/original index plus source catalog SHA to identify the operation. These are per-attempt records, not a global phase journal. The invoking experiment must retain the Python tool version; this phase freezes twelve changed/new files in `inventory-capacity/output/after` and links160 unchanged hashes to the prior source inventory. This is not an automatic source backup for future standalone invocations or an atomic executing-code attestation. Current player inventory/catalog were unchanged by the capacity/verification work.

Read-counter precision: admitted successful bytes are capped; the existing regular-file reader may consume one additional byte when probing an oversized rejected file. Failed read attempts increment the attempt count but do not add unadmitted bytes to the retained successful-byte total. This is not an OS-level I/O counter.
