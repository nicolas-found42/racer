# Retained evidence preservation — 2026-11-05

Question: can an agent preserve and retrieve yesterday's run independently of the original store, and can damaged evidence disappear behind a no-match result?

## Previously visible

The [first-party coverage inventory](../2026-11-05-observability/coverage.md) remains the component map: application/input/simulation/garage/tests/profile, renderer callback, recorder worker, local storage, build downloads and donor research. Vendor internals remain uninspected, OS/GPU historical diagnostics and physical controllers inaccessible, server/remote deployment not applicable. Existing JSONL records provide run/sequence/UTC/monotonic time, attempts and parent saves, profile hashes, executable/config/shader identities, state, sampled motion and dependency/capture outcomes. Retention remains 10Hz motion, change-only state, 4MiB/run, 16 runs/64MiB store; no automatic deletion. Earlier source inspections and real native evidence remain retained, not described as newly executed.

Starting runtime executable SHA-256: `35fad0a547534630eb37e0e67d00b4031d2129b5a953777b3ecc5c212594d4d4`. This pass changes only the offline retrieval tool and its Python checks; no C++ or gameplay behavior changes. `output/baseline.json` captures dirty/staged status, build hash and free space; before-tool copies retained. Prior runtime manifest is compared against current source hashes in `output/source-coverage.json`, explicitly identifying the two offline changes. Runtime hash does not assert the newly edited Python was embedded in that earlier build.

Bounds: each command <=300s, output <=256MiB, free space >=20GiB. All new output lives here; no source evidence is deleted or moved. Hidden SDL run only; no focus or desktop input. Source discovery used jg with explicit src root, max-requests8000/concurrency20. Its completed excerpts identified recorder/callback/profile/flow boundaries; truncated locations remain leads, not new inspection claims.

## Blind spots identified and priorities

| Priority / diagnostic question | Basis / impact / likelihood | Acceptance |
|---|---|---|
| P1: can an entirely corrupt file be distinguished from no retained activity? | Reproduced reader result hid all corruption warnings when no rows survived. High diagnostic value; corruption is plausible after interrupted/partial storage. | Corrupt-only query emits unreadable/start/end/empty issues, retains exit1; profile-filter correlation remains explicitly unknown. |
| P1: can evidence survive relocation of the source store? | Existing runbook required manual preservation; no bounded copy/hash manifest or completeness report. High value, likely during handoff/archive. | Export whole matching run, preserve build/state context even with time/operation filters, hash files, private modes; retrieve from bundle after original path changes. Never prune originals. |
| P2: can missing screenshots, changing sources and export budget loss be mistaken for complete evidence? | Hypothetical incomplete-copy scenarios. Silent omission undermines diagnosis. | Manifest names missing capture hashes, quota/copy/changed-source issues; partial export exits2, no-match exits1; existing destination refused. |
| P2: can a final JSON row lacking its newline be treated as complete? | Safely injected malformed-tail scenario. | Reader reports unterminated tail without inventing a crash cause; large-file inspection stops explicitly at8MiB. |

Initial nested-JSON probe did **not** establish a RecursionError on this Python installation (the assertion failed); that hypothesis is rejected. `reader-red.log` actually establishes the actionable issue: only generic no-match output for a damaged-only file. `reader-green.log` exposes unreadable/start/end/empty issues for the identical retained bytes. Defensive RecursionError handling is not presented as a reproduced incident fix.

## What changed and actual evidence

`scripts/diagnostics.py` now supports `--bundle FRESH_DIR`, optional `--capture-root DIR`, and a1..128MiB payload cap (default64MiB; small manifest metadata additional). It copies **whole** selected JSONL files, preserving adjacent events and build identity rather than treating a filtered excerpt as a complete history. Bundles use0700 directories/0600 files. Logs are unchanged bytes, with SHA-256/size manifest; matching captured image bytes are found by their recorded hash within an explicitly supplied directory. No profile, executable, environment, arbitrary logged path or automatic upload is included. Copies are local evidence, not a redaction service; inspect before sharing.

The scan checks at most256 capture entries and at most the payload cap in source capture bytes. Symlink files are refused, capture hashes rechecked after copy, and source metadata changes during copying are reported. This is not an atomic cross-file snapshot, adversarial filesystem isolation, durable backup or exact replay. Exported logs remain queryable with the same CLI. Missing/corrupt inputs, absent captures, quotas and copy failures stay explicit in manifest issues; never infer success from absence.

Observed retrievals:

- `save-query.jsonl`: operation3 selects2 save events from retained run1793911592900612-99317. `save-incident` preserves the whole run, including executable identity and14 save outcomes. `reconstructed-saves.jsonl` retrieves2 actual temporary_open/errno13 failures and later atomic_replace success. The copied bytes and hashes match. All37 original PPM hashes are reported unavailable because no capture root was supplied; previously converted PNGs are separate retained evidence, not silently substituted.
- `capture-incident`: actual retained reload run yields one JSONL and one original PPM; recorded image hash matches copied bytes, manifest has no issues. No screenshot re-review is claimed in this tooling-only pass; original direct review remains linked in the previous experiment.
- A new hidden run is deliberately SIGKILLed after3s. `native-manifest.json` records exact argv/hash/exit-9. `interrupted-query.log` and copied bundle report missing end and partial export exit2. `interrupted-bundle-query.jsonl` retrieves persisted state from the copy. Stream alone cannot establish SIGKILL; the external process record supplies that cause.
- Python checks exercise moved-store retrieval, whole-run context, real hashes/capture bytes, permission modes, existing destination refusal, omitted captures, payload quota, symlink refusal, corrupt-only queries and unterminated tails. CTest9/9 passes (`output/ctest.log`), including prior renderer concurrency, profile failure/retry/redaction/quota checks. Prior native82-image and performance evidence was not rerun because runtime sources are unchanged.

### Fresh review and repaired hidden assumptions

Root review challenged partial export writes: reserving bytes only after successful close could undercount a partially written file. Reservation now precedes output, and a fixture writes5 real bytes then injects EIO; the next file is omitted under the payload cap. This is explicitly an injected output failure, not a claim of a naturally failing disk.

The single Jev gate (`output/gate.json`) escalated at composite0.711/safe_to_apply0.47, with low confidence and one low-confidence contradiction about the intentional kill. Stronger GPT-6 Astra review checked the actual process manifest, matching41-event original/copy, all37 source/build hashes, all bundle file hashes,14 save outcomes and CTest log. These direct records resolve the kill claim: the missing-end stream alone still cannot identify the cause. The gate was not resampled.

That review found a real P2: selection-stage symlink, inspection or unknown-correlation warnings could be printed but excluded from a mixed bundle's durable manifest. The repaired code carries those issues into the manifest and returns partial2. Tests cover valid+symlink, valid+injected inspection EACCES, and selected-profile+corrupt-unknown inputs. The reviewer inspected the repair and confirmed the blocker closed, with no additional actionable issue in the bounded follow-up. `output/final-patch.json`, `tool-hashes.json`, `source-coverage.json` and final9/9 CTest log describe the corrected state; `patch.json` remains the pre-review candidate. This is not an automatic gate pass.

Final `git diff --check` and hub `python3 ../../tools/check.py` pass (`output/hub-check.log`). `output/integrity.json` records about4.4MiB retained output and425GiB free, within bounds. Originals, earlier runtime captures, staged work and failed probes are retained. The executable remains the original35fad0 hash; only the offline tool/tests and audit/runbook documentation changed in this pass.

## Next iteration targets and limits

Known finite admission can disable future recording after16 runs; archive deliberately without deleting source evidence and choose a fresh diagnostic store. New preservation tooling cannot recover absent historical data or binary/source versions never archived. Queued crash tails, filesystem hangs, power loss, simultaneous profile writers, physical controls, human course acceptance and vendor/OS internals retain their previous limits. No deployment or credentials are required for these local changes.

Runbook: preserve first; inspect manifest issues and runtime identity; query time/run/operation/profile; correlate state→motion→save/dependency/capture; reproduce safely and compare retained outcomes. Exact commands and status semantics are in the [updated agent runbook](../../findings/diagnostic-runbook.md). Status: implemented and locally verified; source evidence retained. Next: use bundles during real incident handoffs; keep unverified external integrations and human acceptance explicit.
