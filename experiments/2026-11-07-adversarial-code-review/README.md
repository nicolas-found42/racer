# Adversarial code review of the uncommitted 17-player work

Question: do the five new scripts (`car_stages.py`, `fit_juiced2_stock_tyres.py`, `juiced2_wheel_attributions.py`, `juiced2_wheel_state.py`, `verify_selection_reload.py`), the native-sizing trace scripts and the 17-player documentation deltas hold up when re-derived from a clean checkout?

Target: working tree on `main` at `71c4c9a` plus the uncommitted changes listed by `git status` at session start. Retained inputs unchanged: handling archive SHA `a2e363b0…`, inventory `dbb82032…` (as reviewed), library `catalog.racer` `72bf3e6d…` (17 entries). Excluded: `experiments/*/output` evidence trees (except the new v3/v8/v2 files), C++ sources, `assets/local`, `build/`.

Method: skill `adversarial-code-review` (persona Reyes, a maintainer re-deriving evidence; ledger outside the repository under the session scratchpad), finite-deadline checks `compile` (AST parse of scripts/tests) and `ctest --test-dir build -j4 --timeout 300`, plus probes: regenerate stage/attribution/fit outputs and compare with retained ones, tamper/perturbation tests, bad-input CLI runs against a stub binary, link/path and stale-claim scans of the modified docs. No game run, extraction or GPU replay.

Result: 19 findings (0 critical, 0 high, 10 medium, 9 low), all repaired in the working tree:
- Fit script's radius check was `... or True` (never failed): replaced by independent `verify_applied`; the four published mesh SHAs reproduce byte-for-byte, no installed asset changed.
- Reload verifier: bad/negative/duplicate indices, uncaught timeouts and end-of-run-only manifest fixed.
- Stage report: empty-string evidence counted as acceptance; stale storage blocker and hard-coded counts in generated text; bare assert.
- Wheel-state/attribution generators: prefix-only SHA pins, hard-coded archive path, duplicated parsing, MINI "exact 6/6" overclaim (4/6 identical, all within 0.003), refuted "context+684 NULL" text; `attributions-v8.json`, `per-car-wheel-state-v2.json`, `car-stages-v3.json` emitted (earlier versions retained).
- Docs: storage-blocked, 13/15 counts, held-GLB and f4=1 index lines corrected with dated superseded notes.
- `ppc_dis.py`: unbounded per-instruction subprocess fan-out replaced by one bounded call.
- Five new CTest suites (71 → 76 targets, all pass); hub `tools/check.py` PASS.

Limits: the Jev semantic checkpoints (`findings`, `completion`) could not run — the Jev provider was unconfigured (`OPENROUTER_API_KEY` not set), so no model judgment backs the repair claims; evidence is the deterministic checks above. Frozen wording "sourced stock section width" remains inside the published GLB extras and four inventory strings (editing changes the pinned mesh SHAs); it is annotated, not edited. Retained evidence outputs were not rewritten.

Next action: configure the Jev provider (`jg auth`/the pinned OpenRouter setup by the user), then import the `findings` and `completion` receipts and run `close`/`gate` on an unchanged fresh pass; separately, human lap and physical-controller acceptance remain pending.

Retrieve:
```sh
cd /Users/nicolas/Documents/github/reverse-engineering/games/racer
ctest --test-dir build -R 'car_stages|juiced2_stock|juiced2_wheel_state|juiced2_native|verify_selection_reload'
python3 -m json.tool experiments/2026-11-06-juiced2-wheel-args/output/attributions-v8.json | head -40
```

## Second pass (2026-11-07, persona Tomasz Wieczorek, CI operator)

Question: after the first pass, does the same uncommitted work still fail for an operator who clones the repository on a clean machine and feeds the tools damaged or missing inputs?

Target: working tree on `main` at `71c4c9a` plus the uncommitted changes, 29 selected files (28 at initialization plus `scripts/new_report.py` added during repair: the five scripts, five test suites, the three native-sizing trace tools, `CMakeLists.txt`, the modified and new documents and `assets/catalog/prepared-sizes.json`). Excluded: C++ sources, `experiments/*/output` evidence (except the new v4/v10/second-pass files), `assets/local`, `build/`, `scripts/juiced2_wheel_contract.py` (the audited kernel, unmodified). Retained inputs unchanged: inventory `dbb82032…`, production catalog `72bf3e6d…`, the four fit meshes `3eef358a…`, `fbbd36fe…`, `61ca0c78…`, `2a233c68…`.

Method: skill `adversarial-code-review`; persona drawn from three grounded candidates (seed `78a1fdfc134c6db2114cf762402e3360`); finite-deadline checks `compile` (Python 3.10 grammar), `unit` (five suites), `ctest` (76 targets), `clean-checkout` (copy without `assets/local` and ignored outputs), `lint` (`ruff --select F,E9`), `devwarn` (`python -X dev`) and `docs` (stale phrases, test counts compared with real runs, v4/v10 script pins recomputed). Probes: malformed archives, receipts and library files (seeded mutation fuzz), truncated screenshots through a stub native binary, `llvm-mc` cross-checks of the scan opcode tables and `ori` operand roles, regeneration of every cited report, clean-checkout and Python 3.13/3.14 runs, concurrent report writers, link scan. No game run, extraction or GPU replay.

Result: seven iterations, 29 findings (0 critical, 0 high, 7 medium, 21 low, 1 nitpick), all repaired; iteration 7 found none and changed nothing (end fingerprint `f46820a7…` equals iteration 6). Per iteration: 15, 4, 2, 5, 1, 2, 0.
- Verifier: a truncated screenshot aborted the whole sweep and dropped the car from the manifest; library header/count/entry damage and an existing output directory were tracebacks; the manifest rewrite was not atomic.
- Wheel generators: empty, non-list or structurally damaged archives gave tracebacks or a green zero-record report (and, after the first repair, non-string `Location`/`TyreCode` values still crashed); absent attributed records, Unicode tyre digits, malformed attributed codes and an `assert` guard that vanishes under `python -O` were fixed; Charger was mislabelled `exact-4-field` (335 vs 340 bhp) and Z4 M stored a PS figure under `power_bhp`.
- Fit: a car key could be applied to another car's preparation (Z4 widths on the CCX mesh) and damaged receipts/descriptors escaped as raw exceptions.
- Trace tools: `ppc_scan.py mult` did not implement the documented lis/addi scan and later decoded `ori` operands wrongly; unclosed file handle; bad arguments and unknown patterns gave tracebacks or exit 0. The retained negative result stands: 4 loads, 0 stores, 0 address-taken uses in the decoded `.text` section.
- Tests/docs: suites failed or skipped wholesale on a clean checkout; stale counts and tallies, unretained fuzz claims, and the cited reports pinned script hashes that no longer existed (`car-stages-v4.json`, `attributions-v10.json` regenerated with identical data; v3/v9 kept as provenance).
- No installed asset, inventory row, catalog entry or game code changed. The only addition outside the selected set is `scripts/new_report.py` (shared create-new writer), now a target.

Jev (typesafe/jev-1.14-20261014 via OpenRouter; the provider that was unconfigured in the first pass worked): `jev_classify` routed all first-iteration hypotheses as observable defects; every iteration imported a `jev_verify` findings receipt (final: 6 claims, 4 auto, two restated and re-verified at ≥ 0.94) and a `jev_gate` completion receipt. **Every `jev_gate` returned `escalate`, never `auto`.** The recurring causes were (a) per-file blast-radius/correctness confidence near 0 because the scripts are untracked, so the "diffs" were condensed excerpts or prose summaries and no patch exists, and (b) bundled claims that scored low until split into atomic claims. Each escalation was settled by inspection rather than by tuning the question: importer enumeration, byte-identical regenerated outputs, `llvm-mc`, mutation-sensitivity runs and the atomic re-verifications, recorded in the `--assessment` of each receipt. In the final gate 6/6 claims were verified with none contradicted or unsupported. A model verdict does not replace the deterministic checks; receipts keep verdicts and probabilities but condense request evidence and diff texts to ids (the full texts were in the session).

Completion gate: `review.py gate` exited 0 with `"status": "complete"` on iteration 7 (unchanged target, zero findings, current coverage for 6 surfaces × 5 dimensions, required checks and both judgments current). This is within the reviewed scope and checks, not a proof of universal correctness.

Limits: the reload verifier was exercised through a stub native binary only; no hidden Metal sweep of `build/racer` was rerun and the selector wrap was modelled for library sizes 1–59, not observed in the garage. The Oversteer handling archive and ISO-derived inputs are machine-local, so the clean-checkout run skips the tests that need them. Human lap and physical-controller acceptance remain pending. No Git staging, reset or commit was performed; all of this work is still uncommitted.

Retention: the ledger, per-check logs, Jev receipts, persona/candidates and helper scripts are retained under `output/second-pass/` (808 KiB, `MANIFEST.sha256`; the original session copies lived in the agent scratchpad). The hub storage checker passes (2,373,070,133 B standard output).

Retrieve:
```sh
cd /Users/nicolas/Documents/github/reverse-engineering/games/racer
ctest --test-dir build -R 'car_stages|juiced2_stock|juiced2_wheel_state|juiced2_native|verify_selection_reload'
python3 -m json.tool experiments/2026-11-07-adversarial-code-review/output/second-pass/state/review.json | head -40
shasum -a 256 -c experiments/2026-11-07-adversarial-code-review/output/second-pass/MANIFEST.sha256   # run inside output/second-pass
sh experiments/2026-11-07-adversarial-code-review/output/second-pass/helpers/clean_check.sh        # clean-checkout suites
```

