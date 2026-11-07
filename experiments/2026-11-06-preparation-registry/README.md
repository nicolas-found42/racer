# Retained preparation inventory integration

Question: which already-extracted/native-proven preparations are invisible to the central inventory, and can they be registered without promoting unresolved or excluded cars or changing existing player/traffic rows?

Previous goal turn: verified progress (two source-backed MC3 exhaust additions,22reviewed captures and repaired first-write attribution), not goal completion. Keep GT1/Redline excluded; MCLAambient traffic-only; native checks hidden.

Before production: this leaf<=1MiB including research/source snapshots, commands<=300s, acquisition<=128KiB/item and512KiBbatch, free>=20GiB. Prior totalstandard+newmanaged2,136,278,164B leaves11,205,484B under2GiB; reserve at most8MiB separately for later native/publication work only after an applicable candidate is found. Original inputs, previous output and staged work remain; no deletion/moves. No new game model copies here.

Inputs: existing Ford33ordinary+EX optional, J2four cohort assemblies and MC3Fleetline/Viper/attachment preparations, with actual pinned manifest/descriptor/mesh bytes. Central inventory currently15rows:12players,1traffic,2research. Unknown factory dimensions remain null and new rows must be falseeligible research-only.

Plan: audit actual candidate paths/source joins and preserve existing rows; make a reusable bounded inventory command with dry-run/checkable report and explicit source mapping, then apply only verified retained additions. Independently verify hashes/geometry and policy guards. In parallel find attributable primary Ford dimensions rather than guessed variants. No publisher or playable catalog change is authorized by a research inventory operation.

Initial resume (superseded by results below): inspect exact deduplication; per-source producer outputs are retained and reused.

Reservationv2 supersedesinitial2MiBleaf: registry1MiB, separateGTreference2MiB, conditionalnative4MiB, conditionalpublication3MiB, combined10MiB within measured11.205MBheadroom. No outputremoved. NewrawPDFbound1.6MB initsownreferenceleaf.

## Verified result

The actual selection has forty candidate identities:34 Ford preparations (33 ordinary plus optional EX), four actual-ISO Juiced2 assemblies, two MC3 preparations (Fleetline/Viper; Saleen/Esprit already registered). `output/selection-v1.json` SHA `0e39527b846a7fe28cc9d4111a3e749a67ca18e56928bf77113e1c779153984a` binds descriptor/mesh/source/evidence hashes. Independent current CPU validation passed all40 using validator SHA `61aad7de…` (full identity in `independent-CPU-validation.json`). No new game model copies were made here.

The bounded dry registrar produced52 rows:37 new research candidates, all fifteen old rows preserved, three active Ford source-ID conflicts preserved. Dry inventory SHA `0b674e10bacf02498fa58452c7e70b2d67c26177af739c19c7166cd4bc3b3c9d`; original input SHA `9a256f672229f8147d84d7a3cd640cc1b30653272119b294861f0d223611d495`. Root atomically applied those reviewed bytes after matching current input hash; `output/applied.json` records that step. No eligibility or catalog change was made by the registrar. Separate later GT review/publication is in its own experiment.

The dry run used registrar revision `289fe628d56e70715f74228842f878a7e480ca5cdf300c3a85b99e27b2a5545d`. Fresh review then found missing first/second input failures indistinguishable. Current revision `00d3c50c0d2983cfdfc0f1ab611ddb96db581d4ec5bcc07702eaede0159d418f` records fixed `active_input` before each read and retains each successful input before starting the next. Old-source reproduction fails both regression subcases; current thirteen registrar tests pass. Missing input, late report ENOSPC and unavailable sidecar fixtures are retained as detailed results in `fresh-boundary-review.json`/`fresh-boundary-repair.json`. Failed late writes can leave a partial dry inventory; original inputs stay unchanged. Diagnostic failure does not break the dry operation. No actual historical disk incident was recovered.

The native CPU tool now accepts `vehicle_validate --descriptor PATH` through the same strict loader; legacy library output is unchanged. Three actual native fixture tests cover equivalence, missing/corrupt bytes, usage exits and mesh path restriction. The initial fixture omitted library count and failed; corrected fixture and successful log remain separate (`validator-test-v1.log`/`validator-test-v2.log`). No GPU or donor-game behavior is implied.

Final `ctest --test-dir build --output-on-failure` passed68/68 targets in13.46s, no skips (`output/ctest-final-v2.log`). After GT promotion, actual40-selection re-registration against current52 rows was byte-identical:zero additions,36 already-registered, four preserved conflicts (the later name-only GT descriptor is the fourth). `post-promotion-idempotence.json` retains that query. GT1/Redline/ambient/local-family rejection, source/hash/duplicate/nonfinite/path/budget checks and fail-open behavior are covered by fixtures, not assumed from flags.

`output/aggregate-source-coverage-v4.json` enumerates169 current first-party files:164 unchanged hashes inherit the exact166-file baseline, with five selected-boundary deltas reviewed. Source inspection is distinct from runtime telemetry; vendor implementations remain uninspected, provider internals unknown, OS/driver internals inaccessible to this source audit, gameplay servers not applicable. Source evidence bodies are retained at original path/hash, not copied as portable backups. The shared inventory is245,114 bytes against a256KiB reader limit; expand capacity explicitly before additional corpus registration.

## Retrieval and next action

```sh
python3 -m json.tool experiments/2026-11-06-preparation-registry/output/dry-v1/report.json
python3 -m json.tool experiments/2026-11-06-preparation-registry/output/dry-v1/lifecycle.json
python3 -m json.tool experiments/2026-11-06-preparation-registry/output/fresh-boundary-repair.json
./build/vehicle_validate --descriptor /absolute/retained/car.vehicle
```

The [runbook](../../findings/diagnostic-runbook.md) includes bounded time/input/model retrieval. Keep input snapshots/report/lifecycle together; do not infer success from an orphan inventory. Inputs/evidence and all earlier outputs remain retained locally; no upload, expiry or cleanup was added. A full-disk sidecar failure, abrupt kill or early preflight rejection can still leave unavailable/stale evidence. Working-tree source hashes are not atomic executing-image attestations.

Resume: this bounded registry checkpoint is implemented; all-car goal remains active. Resolve inventory capacity and an attributable held assembly/unit contract before another acquisition/preparation batch; remeasure project output budget first. Do not overwrite active Ford revisions, promote MCLA traffic or touch GT1/Redline. Final gate/storage results are recorded in the sibling GT native experiment.

Final review: one Jev gate (`ford-gt-native/output/gate-input-v1.json`/`gate-result.json`) escalated at safe-to-apply0.39, composite0.68878, including a low-confidence0.24 count contradiction. No reroll or automatic-pass claim. Independent direct byte/count/order assertions (`gate-adjudication.json`) distinguish historical52=12players/1traffic/39research from current52=13/1/38; onlyGT differs, prior15 and other51 rows and old12catalog order are preserved. Fresh13registrar+3nativeCLI fixtures passed again. Broad all-car/spec completion remains unclaimed; vendor/hardware/human limits remain open.

A further actual current-CLI missing-selection run retains the real first-read245,114-byte inventory, fails exit2 with `active_input: selection`, retrieval phase/errno2, and no candidate/report. A new process retrieves the sidecar successfully; all8checks pass, original input remains unchanged and no raw missing path enters telemetry (`registrar-negative-manifest.json`, `registrar-missing-selection-v2`, `retrieved-registrar-failure.json` in GTnative/output). This is a new controlled failure, not recovered historical data. The earlier unexecuted gate input exceeded the desired aggregate cap during preflight; it remains at `gate-input.json`. Only the bounded v1 request was submitted once.

Final local checks: hub `python3 tools/check.py` PASS, both working-tree and staged `git diff --check` clean. Final direct audit verifies169 source hashes,13 capture hashes, current13-entry catalog bytes and52-row inventory; no cooperative install lock remains (`output/final-checkpoint.json` in GTnative). Storage measurement including prior/new nonstandard managed deltas and conservative curated-metadata growth is2,145,053,986 bytes, below2GiB by2,429,662 bytes before the small final report/check records. All three new experiment leaves and3MiB publication delta are within reservation (`output/storage-final-v1.json` in GTnative). This is logical accounting, not a deletion/reclaimed-space claim. Recheck before any next producer. No originals, prior evidence or unrelated staged changes were removed.
