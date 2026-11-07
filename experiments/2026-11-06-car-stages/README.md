# Car pipeline stage reconciliation

Question: what explicit per-car stage — discovered, extracted, prepared, validated, integrated, runtime-reviewed, blocked — does every in-scope source car reach today, with exact provenance and remaining acceptance checks?

Inputs (hashes pinned at generation):
- Curated preparation inventory `assets/catalog/prepared-sizes.json` SHA `3fb258cfeddaaa854e2c456176221cc2b69249caa1b0d32af40b7f2e12f23c4f` (52 rows: 13 player, 1 traffic, 38 research).
- Production catalog `assets/local/vehicles/catalog.racer` SHA `3da5f93bb8a18355877d4614c7ecb4c6fb79273d67c286aa9eee602719e7327c` (13 players).
- Pinned public catalog (965 in-scope entries) SHA `fcd6eb5badd4cc120da3daaae315e83b71fb2b9400062b371b73c9f42a442e6c`.
- Tool `scripts/car_stages.py` SHA `0c9531446bdf96c747c18184e4a86149a5eaebfff0fe730b8ab7dbed8603c290` (v2, after independent-review fixes).

Method: `car_stages.py` joins the inventory to the installed byte set and the public catalog; every stage boolean is derived from a retained field, file existence or the retained SLRR native-audit alias set, never invented: `discovered` joins the pinned public catalog, falls back to the retained SLRR native audit (chassis alias), then to existing per-row experiment evidence; the installed join matches the .vehicle filename stem (prepared_sha256 naming convention) against the inventory and additionally hashes file content against inventory descriptor SHA256s (no content-only matches; recorded in the report). Stage definitions are recorded inside the report. GT1/Redline rows are excluded by the shared catalog filter; the 41 MCLA `va_` rows remain traffic-deferred. No game run, extraction, GPU replay or promotion occurred here.

Command:
```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/car_stages.py \
  --output experiments/2026-11-06-car-stages/output/car-stages-v2.json
```

## Result

All 52 curated rows are discovered → extracted → prepared → validated (measurement basis recorded per row: publisher containment for players, reviewed-measurement or measurement-only for research). 13 rows are integrated players in the production catalog; 15 rows are runtime-reviewed (13 players via family-level retained native acceptance plus Saleen SR and Esprit via their own native-view/motion manifests). 46 rows remain blocked with explicit reasons — every research candidate's `eligibility_reason`/`limitations`, the traffic row's role, and players' retained limitations (human lap, donor dynamics/shaders, physical controller). The 3 installed-but-unregistered prepared files (`9c99d140…`, `6ac33b18…`, `46f00fd4…`) are staged historical/scenario bytes, not catalog entries (this was the 2026-11-06 state; the 2026-11-07 v3 report lists 7, see the second review correction below).

Beyond the curated rows: 919 of 965 public-catalog in-scope entries are discovered but not extracted (per-family counts in the report); SLRR contributes 70 native-audit declarations outside the public catalog. Promotion of any prepared research row was storage-blocked at this report (checker headroom ~13.1 MiB against 3.9–5.2 MB per held GLB duplicate publication); superseded 2026-11-07 when the user doubled the limits and four Juiced 2 cars were published.

## Evidence and retention

- Report: `output/car-stages-v2.json` (within the 512 KiB reservation; no-overwrite enforced). v1 is retained as the pre-review derivation with a hardcoded `discovered` flag.
- Per-row provenance: source/prepared/descriptor SHA pins, descriptor path, unit authority, wheel-contract annotation flag, blocked reasons.
- Family runtime pointers resolve to the retained acceptance experiments (expanded-acceptance, cohort-acceptance, ford-gt-native, mcla-vehicle, juiced2-vehicle/import-recovery, mc3-coverage, slrr-rest-fit).

## Limits and next action

This is a record-derived reconciliation, not new acceptance: player runtime-review uses family-level pointers, and per-car manifests stay in their own experiments. Extracted/prepared research rows are not playable. Next: resolve the per-source contract holds (Juiced 2 per-car wheel arguments; MC3/Ford canonical dimensions and attachment frames; MCLA tyre/variant; GT4 non-four-wheel layouts) in bounded batches, then re-run this reconciliation — stages advance only on retained evidence.

## Review corrections (2026-11-07)

`output/car-stages-v3.json` regenerates the report at the current 17-player library: 17 integrated, 19 runtime-reviewed, 46 blocked (the 13/15 counts above are the 2026-11-06 state). The tool now (a) accepts evidence only as a non-empty relative path to a regular file inside the project (an empty string used to count as discovered/runtime-reviewed evidence), (b) derives the SLRR audit counts and the 965 figure from the data instead of hard-coding them, (c) no longer emits a storage-headroom blocker, and (d) names offending models when the player invariant fails. Stage booleans for all 52 rows are identical to the pre-fix output. Tests: `tests/car_stages_checks.py` (CTest `car_stages_checks`).

## Second review correction (2026-11-07)

The regenerated v3 report has `installed_unregistered: 7`, not 3: the three historical stems above plus the four **pre-fit Juiced 2 preparations** `1b9a63c5…` (Z4), `b4b7b383…` (Cooper S), `ab480257…` (Charger R/T) and `3c432bbf…` (CCX) — the prepared SHAs of the `juiced2-cohort/output/*-prepared-v1` inputs. Publishing the Racer-authored stock-tyre fits replaced those four inventory rows with the fitted SHAs and left the superseded `.vehicle`/`.glb` files installed beside them. They are retained, not deleted, and are not catalog entries; the report's join (stem, then descriptor content hash) correctly classifies them as unregistered.

`output/car-stages-v4.json` regenerates the report once more after the second review's repairs. Its data equal v3 (only `inputs.tool_source_sha256` differs); v3 pins the hash of `scripts/car_stages.py` as it stood before the shared report writer and later fixes, a version that is not recoverable, so v4 is the report whose pin equals the committed tool. Command: `PYTHONDONTWRITEBYTECODE=1 python3 scripts/car_stages.py --output experiments/2026-11-06-car-stages/output/car-stages-v4.json`.
