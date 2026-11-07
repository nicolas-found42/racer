# Garage setups and driving tests — 2026-11-05

Status: implemented and locally validated; presentation follow-up is planned in [PLAN.md](../../PLAN.md). Delivered scope: [archived garage plan](../../findings/plans/2026-11-05-garage-tests.md). Question: can the existing Racer grid support the persisted tune/test/compare loop while retaining baseline behavior?

Target: Racer C++20 / SDL3 3.4.18 / pinned bgfx Metal, macOS arm64. Starting executable SHA-256 a0417525e3982de46dcab2d2fa1624ef9756f1a1a057317a1216a0dbbc83cefc. Dependency pins: references/dependencies.md. Donor canonical builds/hashes: references/source-inputs.json; reuse donor-inventory output and original inputs.

Bounds: each build/check/research batch <=5 minutes, native samples <=30 seconds each, total new output <=256 MiB; no donor launch or bulk extraction. Preflight: 430 GiB free, experiments 67,468 KiB, build 10,268 KiB, dependencies 278,048 KiB. Commands run from this repository. Evidence retained in output/; source inputs and prior saved evidence retained unchanged. Independent repository and existing staging preserved.

Method: baseline build/CTest/Metal smoke; narrow source/manual comparison; independent setup/storage and test-session modules; native UI integration; deterministic checks and native flow/performance captures. REA used as evidence discipline; no new binary scan needed for available shipped source. Results below supersede the original implementation checkpoint.

## Implementation and observations

- Baseline rebuild, original CTest and 14-second 1080p Metal sample passed. Starting executable hash above matched. Baseline sample: 120 FPS, 16.565 ms longest interval, no intervals over 16.67 ms. Evidence: `baseline-build.log`, `baseline-tests.log`, `baseline-smoke.log`.
- `src/setup.*` owns validated 0.8–1.2 multipliers and applied/draft A/B/C state. `src/profile.*` owns schema v1, exact-configuration best records, strict bounded loading and temporary-file/fsync/atomic replacement. Malformed input disables writes and preserves original bytes; failed writes report unsaved changes. Real read-only-directory preservation passed on this non-root user (`setup-preservation-checks.log`).
- `src/test_session.*` owns countdowns, fixed automatic schedules, exact acceleration threshold interpolation, exact 100 km/h braking onset, within-tick stop timing, directional swept gates, frozen setup snapshots, timeout and invalidation. Default semi-implicit stopping distance remains 38.8737 m; acceleration remains 8 s. Acceleration tuning cannot change braking onset speed. A bounded synthetic driver steers the actual simulation through all five gates in 75.2119 s; this is feasibility evidence, not a human lap.
- `src/play_flow.*` owns garage/test/result navigation, comparisons and persistence decisions. `main.cpp` maps keyboard/SDL gamepad events, renders panels/gates and rearms controls after menus. Focus loss and active-controller removal stop simulation. Result transitions stop the tick accumulator before any free-driving continuation.
- No added dependencies. Original .deps pins remain in `references/dependencies.md`. No donor assets/formulas imported, no native REA session or database opened. Canonical originals and exported REA record retained.

## Donor evidence boundary

`findings/garage-evidence.md` maps rehashed SLRR-231 Tyre/Transmission source and the 221 manual to authored design. The supplied 221 tree has no matching loose source filenames. GT4 section notes were reused; a refresh returned a security page, not new support. Edition/OCR and runtime correspondence limits remain explicit. Parent reasoning independently inspected the numbered Java excerpts and earlier hash notes after Jev flagged the combined 231 claim for review (supports .72, confidence .58); versioned load/save, old/new draft inflation and cancellation/acceptance calls support the narrow source claim. Transmission temporarily mutates ratios, so Racer's isolated draft is explicitly a design choice. No donor runtime assertion is made.

## Executed checks and captures

Commands from repository root, each batch within five minutes; native app invocations below <=28 seconds:

```sh
cmake -S . -B build -G Ninja
cmake --build build -j 8
ctest --test-dir build --output-on-failure
./build/racer --verify-controls --profile /tmp/racer-final-controls.profile
./build/racer --verify-garage keyboard --benchmark --profile /tmp/racer-final-keyboard-20261105.profile --capture-loop experiments/2026-11-05-garage-tests/output/final-loop
./build/racer --verify-garage gamepad --benchmark --profile /tmp/racer-final-pad-2.profile
./build/racer --smoke 14 --benchmark --autodrive --profile /tmp/racer-benchmark-20261105.profile
./build/racer --smoke 14 --benchmark --scene garage --profile /tmp/racer-benchmark-20261105.profile
./build/racer --smoke 14 --benchmark --scene course --profile /tmp/racer-benchmark-20261105.profile
python3 ../../tools/check.py
```

Fresh isolated profiles were used for native test runs; `--verify-garage` requires an explicit profile path. The live harness navigates through the same SDL event loop as normal play; virtual-pad runs use SDL virtual button/axis state. No direct flow mutation drives the native acceptance test. `flow_checks` separately tests state transitions without rendering.

- Five CTest executables pass: original driving/gamepad, setup/storage, test sessions and playable flow. `tests-final.log` contains the final run; `build-formatted.log` retains the build (only existing duplicate bx link warning). Numerical checks cover default baseline, exact multiplier effects/caps, 30/60/144 Hz schedules, swept wrong-order/reverse/fast gate crossings, reset/boundary/timeout/cancel and immutable attribution.
- Native keyboard and virtual-gamepad flows pass edit/apply → automatic result → comparison → retry → focus freeze/resume → cancellation → garage, plus profile reload. Virtual run verifies held-trigger rearm and active-controller removal. Logs: `live-keyboard-final.log`, `live-gamepad-final-build.log`, `live-controls-final.log`; earlier bounded runs also retained.
- Captures: `loop/` and `final-loop/` hold one native PPM per principal screen (garage, test choice, countdown, result). PNG derivatives `garage.png`, `results.png`, `results-final.png`, `course.png` support visual inspection. Native panels, hints, setup snapshot/measurements and visible course were inspected. Capture callbacks can stall rendering; these captures are not performance samples.
- Separate no-capture 14-second 1920×1080 samples: free driving **120.002 FPS / 9.048 ms max / 0 frames over 16.67 ms**; garage **119.999 FPS / 13.516 ms max / 0 over**; visible course **120.001 FPS / 16.637 ms max / 0 over**. Logs `perf-drive.log`, `perf-garage.log`, `perf-course.log`. Course sample renders the stationary start/countdown and gates; moving course feasibility is verified in simulation, not claimed as a native human playtest.
- Capturing live-loop sample: 119.238 FPS / 53.012 ms max; final keyboard capture 119.206 FPS / 47.187 ms max. A separate course screenshot sample also reached 53.460 ms. Investigation isolated these stalls to capture-producing runs; equivalent no-capture samples above stayed below 16.67 ms. This is bounded correlation, not a general performance guarantee.
- `git diff --check`: pass. Hub checker: pass (`hub-check.log`), roughly 125 MB total standard lab output, 461 GB free. This experiment remains below its 256 MiB limit. No original or retained evidence deleted.
- Final executable SHA-256: `61217ed9499e3b5294dee6dd339544b94b0d8595373c661bd32fcd7048ad44c3` (`final-sha256.txt`). Source manifest is retained alongside it. Final-build keyboard/gamepad/control checks are identified separately above; earlier performance runs preceded formatting/status-label-only changes.

## Retention and resume

Retain source, tests, dependency/build state, canonical donor inputs, prior REA export and all evidence under output/. Test profiles were isolated under /tmp; final fixtures are copied into output for restart reproducibility. Normal profile path observed from SDL: `/Users/nicolas/Library/Application Support/Racer/Racer/profile.txt`. No live tests write that normal profile.

Milestone implemented; no known functional blocker. Physical controller coverage remains unavailable, donor runtime behavior remains unverified, and GT4 refreshed documentation was inaccessible. Next action: address the [visual-review findings](../2026-11-05-garage-visual-review/README.md) through the feedback milestone in [PLAN.md](../../PLAN.md), including a complete human course lap and physical-controller coverage when available. Existing Git staging and unrelated edits remain intact; no commit, remote or publication was created.

## Final judgment and review

Jev's single final per-file gate (`output/jev-gate.json`, 41,055 input / 1,649 output tokens) verified all four claims, with test-pass confidence .98 and native-loop confidence .96, but advised escalation: composite .66347, safe-to-apply .35 and broad low-confidence rubric judgments. It supplied no concrete bug. The bounded performance claim had verified/contradicted/unsupported probabilities .51/.41/.08; persistence claim confidence .76. These were not treated as automatic approval, and the judgment was not repeated to seek a different verdict.

A separate reasoning-agent inspection of the final integration and actual logs found no blocking issue; its evidence and limits are retained in `output/independent-review.md`. It checked menu/rearm/focus/disconnect transitions, stopping at results, protected profile writes, immutable attribution, threshold schedules and gate ordering. Direct log comparison resolves the performance ambiguity: no-capture samples have <16.7 ms maxima, while separately identified screenshot runs reached 47–53 ms. The final-build no-capture virtual-pad run also measured 120.001 FPS / 16.493 ms maximum with no over-budget interval. Parent review concurs with those bounded conclusions. No unsupported claim was promoted to donor/runtime/hardware coverage.

An additional fresh application process opened the saved keyboard profile in the garage (`restart-native.log`, `restarted.png`); the panel shows the saved 1.05× acceleration and Profile loaded. The copied profile fixtures retain the valid result for reproducible reload checks. Final document links, whitespace and hub checks pass; the output remains within budget.
