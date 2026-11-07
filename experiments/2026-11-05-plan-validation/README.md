# Plan validation — 2026-11-05

Question: does the existing first playable satisfy PLAN.md, including focus and stale-input rules on every resume path?

Target: original Racer C++ source in this independent repository, existing executable SHA-256 `1ae15e12ab8491c54f1c47b762cdab2c4256e47e2eaecf98d5eb67e5aaef804f`. Dependencies and compiler identities remain those in `references/dependencies.md`. No donor artifact analysis or import is required; source inspection is the appropriate REA route here. Control decisions are deterministic and need no TypeSafe integration in the game.

Preflight: 430 GiB available; `.deps/` 278,048 KiB, `build/` 10,200 KiB, existing experiment output 61,160 KiB. Bound each build/check to 120 seconds, native runs to 20 seconds, this output to 32 MiB and total initial investigation execution to five minutes. Retain dependencies/build and existing evidence. New logs, one screenshot, before-source copies and final executable digest go in `output/` (ignored). No cleanup or changes to canonical donor inputs.

Initial observation: pause toggles can resume without focus; menu Resume does not rearm controls after neutral input has cleared the latch while paused. Existing live verification does not cover those transitions and can exit successfully on timeout before finishing. Add regressions, demonstrate the failure, fix resume handling, and rerun native and simulation checks.

## Commands and observations

All commands run from Racer. Python `subprocess.run(..., timeout=120)` bounded the build and native invocations; `--smoke` additionally bounded native runs. Logs are retained under `output/`.

- `jg "How are vehicle physics, pause and direction transitions implemented and tested?" . --exclude '.deps/' --exclude 'build/' --max-requests 8000 --concurrency 20 --max-output-bytes 22000`: completed discovery; read source excerpts and focused files. No binary/provider session needed.
- Added live regression cases to the existing virtual SDL controller sequence. `cmake --build build -j 6` succeeded; `./build/racer --verify-controls` failed with `stale trigger applied on menu resume` (exit -6). See `build-regression.log` and `live-regression.log`.
- Routed Escape, Start, Enter and controller South through one resume function requiring focus and rearming controls. Added completion/timeout checking so partial live verification fails. Captured the original source in `main-before.cpp` and `live-before.h`; `changes.diff` records the fixes and regression cases.
- `ctest --test-dir build --output-on-failure`: 2/2 pass (`tests.log`). `./build/driving_checks`: 100 km/h after eight seconds, 38.8737 m stop; direction transitions, caps, steering, reset, boundaries and 30/60/144 Hz checks pass (`driving.log`).
- `./build/racer --verify-controls`: passes drive/reset, active-controller disconnection, focus pause, held-trigger menu resume, rejection of background Start/Escape, release/restart and Quit (`live-final.log`). These are injected/virtual inputs, not physical hardware observations.
- `./build/racer --verify-controls --smoke 0.1`: intentionally exits 1 with `FAIL: live verification ended before confirmed Quit` (`timeout.log`).
- `./build/racer --smoke 14 --benchmark --autodrive --screenshot <absolute-output>/grid.ppm`: Metal at 1920×1080, 119.617 FPS after warmup (`benchmark.log`). Converted using `sips -s format png .../grid.ppm --out .../grid.png`; visually inspected the grid, oriented car and readable HUD.
- Added frame interval reporting, rebuilt, and repeated `./build/racer --verify-controls` and `./build/racer --smoke 14 --benchmark --autodrive`. Final benchmark: 1,560 frames / 13.0003 s = 119.997 FPS, longest interval 17.3017 ms, 7/1,560 intervals above 16.67 ms. Final speed zero after off-road turning/braking. This exceeds average 60 FPS in a short local run; it does not establish a worst-frame guarantee (`build-final.log`, `live-final.log`, `benchmark-final.log`).
- Final executable SHA-256: `a0417525e3982de46dcab2d2fa1624ef9756f1a1a057317a1216a0dbbc83cefc` (`executable.sha256`).
- `bash -n scripts/bootstrap.sh`, `git diff --check` and a direct source trailing-whitespace scan passed. Source files are still untracked, as at task start, so the direct scan supplies coverage beyond Git's empty diff.
- `python3 ../../tools/check.py`: PASS (`hub-check.log`), 68,799,451 managed output bytes and 461,844,717,568 bytes free. New experiment output 6,200 KiB; `.deps/` 278,048 KiB and `build/` 10,268 KiB. Updated the stale hub project index entry; left unrelated hub changes intact.

## Result and resume

The first-playable delivery boundary in PLAN.md is implemented and revalidated. World, simulation, input, presentation, native build and bounded runtime performance checks are covered. Physical gamepad verification remains unobserved; the plan explicitly permits virtual coverage when hardware is unavailable. Donor-inspired systems remain later milestones.

Retain all original inputs, dependencies/build, historical experiments and this experiment's source snapshots, failing/passing logs, screenshot and digest. No commits or publication performed. Next action: physical gamepad playtest, then agree the next milestone. Jev completion review is recorded separately in `output/`.

## Completion review

Jev 1.14 via OpenRouter reviewed the 42,196-character source/build/documentation snapshot against PLAN.md and actual logs, with no truncation. It supported all four completion claims (no contradictions), but escalated whole-source review: `safe_to_apply=0.40`, composite `0.7075`, rubric confidences `0.20–0.78`; the combined benchmark/physical-coverage claim had confidence `0.56`. This is an advisory escalation, not an automatic pass. Retained summary: `output/jev-gate-summary.json`; reviewed source: `output/review-source.txt`.

Escalated to an independent reasoning reviewer (`review_resume`) for source-level inspection of the focused changes and evidence. No blocking findings: all four resume controls share the focus/rearm check; held controls remain suppressed until neutral; incomplete verification fails; frame reporting does not affect simulation. Reviewer directly corroborated the test and benchmark numbers in the logs and retained the virtual-only controller and short-benchmark limitations. No repeated Jev call was used to seek a favorable verdict. The review produced no further code changes.
