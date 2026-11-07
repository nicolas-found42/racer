# Verification pass — current build (2026-11-06)

Question: does the current checkout satisfy the plan's verification matrix on the 13-player catalog, with performance measured separately from capture?

Build: `./build/racer` at HEAD `71664dc` working tree (clean), macOS arm64, SDL3/Metal. All runs `--background`, isolated `--profile` paths under `/tmp/racer-verify-pass`; no window activation or desktop input.

## Results (all exit 0)

| Check | Result |
|---|---|
| `ctest --test-dir build` | 71/71 passed (15.4 s; log retained at `../2026-11-06-juiced2-wheel-consumer/output/ctest-final-v2.log`, same HEAD) |
| `python3 tests/juiced2_wheel_contract_checks.py` | 9/9 OK |
| `./build/racer --verify-controls` | PASS — live SDL drive/reset/disconnect pause/focus pause/held-trigger resume/background resume rejection/Quit; 433 frames, longest 8.92 ms |
| `--verify-garage keyboard` (fresh profile) | PASS — 1500 frames, longest 17.37 ms (1/1500 over 16.67) |
| `--verify-garage gamepad` (fresh profile) | PASS — 1726 frames, longest 15.74 ms |
| `--smoke 14 --benchmark --autodrive` | 120.002 FPS, longest 12.18 ms, 0 frames over 16.67 ms |
| `--smoke 14 --benchmark --scene garage` | 120.002 FPS, longest 12.14 ms |
| `--smoke 14 --benchmark --scene course` | 119.989 FPS, longest 12.09 ms |
| `./build/vehicle_validate assets/local/vehicles/catalog.racer` | all 13 entries pass (mesh containment, physics identity, wheelbase) |
| hub `python3 tools/check.py` | PASS — 2,133,700,152 B standard output, 13,783,496 B headroom (as of the pre-artifact measurement 2026-11-06; final 2026-11-07T02:34Z re-run: 2,133,993,602 B, 13,490,046 B headroom, still PASS) |

Capture runs are excluded from the performance rows: the two `--screenshot` runs each showed one ~56-57 ms stall (capture callback), consistent with the retained capture-overhead findings.

## Fresh pixel evidence (current build)

- `output/drive-view.png` (SHA `2eb913cf…`, 1920×1080): NSX at spawn, 0.0 mph forward, correct proportions against the 12 m road, gate and 100 m posts; NSX badge legible.
- `output/garage-view.png` (SHA `b6d57242…`): full garage menu — setup rows, Apply/Cancel/Restore, Drive, Run test/compare, Retry save, Parts/inventory, Livery/layers, Events/career, car selector.
- Reviewed visually this pass. PPM intermediates (6.2 MB each) were converted to PNG and discarded as bounded-producer intermediates; PNGs are the retained evidence.

Negative observation: `--capture-loop` on a passive smoke retained no images (no principal-screen navigation occurs without scripted input); the empty directory was removed. Scripted multi-screen capture remains available through the retained review drivers.

## Retained-evidence retrieval (runbook spot checks)

- Lightning save failure/retry: runs `lightning-save-op63`, `lightning-save-op67` (fail), `lightning-save-op70` (retry) retrieve with expected events; missing start/end issues are the retained deliberate-excerpt flags, not new damage.
- Ford GT production reload: run `1793968848330269-59259` retrieves `vehicle_library_load` (catalog `3da5f93b…`, 13 entries), GT `asset_load_end` (mesh `f5b3ae2d…`, identity match) and atomic document saves.
- Default-root query remains empty at this checkout (historical default store has no events); isolated experiment stores are the accessible history.

## Limits

Human unaided lap and physical-controller acceptance remain pending (no human/controller available AFK). Donor-game runtime behavior unverified. The capture-loop negative and the escalated historical Jev gates are retained as-is; nothing was rerolled.

## Capture set 2 — multi-angle course views (2026-11-07)

Five fresh captures from the current build (`--background`, isolated `--profile` under `/tmp/racer-shots`, PPM→PNG conversion, intermediates discarded). All reviewed visually this pass:

| File | Vehicle (catalog index) | View | Review |
|---|---|---|---|
| `output/drive-nsx-index0-rear-v2.png` | Acura NSX '04 (0) | rear | proportions vs 12 m road/gates correct; NSX badge legible |
| `output/drive-fordgt-index12-elevated-v2.png` | Ford GT (12) | elevated | longtail proportions, wheels seated, sane vs lane width |
| `output/drive-juiced350z-index4-right-v2.png` | Juiced 2 Nissan 350Z (4) | right | correct car and stance |
| `output/drive-midget-index8-left-v2.png` | Daihatsu Midget II '98 (8) | left | kei-truck scale correctly tiny vs road; shadow side renders very dark (flat single-light shading, retained observation) |
| `output/garage-view-v2.png` | default NSX | garage | full menu matches capture set 1 |

Index mapping verified: `--vehicle N` follows `catalog.racer` line order (index 0 = first catalog line). Selector contract is exact match — display names need the full suffix (`Acura NSX '04`, not `Acura NSX`) and ids are the full `vehicle-<64-hex sha>`; partial values fail with `vehicle_selection_unavailable` (verified: truncated id and prefix name both fail, exact values both pass). Not a defect; recorded as a usage pitfall.
