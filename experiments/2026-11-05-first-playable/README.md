# First playable — 2026-11-05

Status: completed. User confirmed PLAN.md and implementation. Question: can the agreed C++/SDL3/bgfx Metal driving grid be built and verified on this arm64 Mac?

Inputs: original Racer code and pinned upstream dependencies; no donor assets. Target hash will be recorded after build. Providers: Apple clang 21, CMake 4.4.4, SDL3 3.4.18; bgfx revision recorded by bootstrap.

Preflight: 431 GiB free, existing managed output 42.3 MB. Each fetch/build/test invocation bounded to 300 seconds; captures at most 120 frames/10 MB. Experiment output <=256 MiB. Dependencies and build at ignored .deps/ and build/, separately measured, combined ceiling 2 GiB under user's authorization to download needed tools/libraries; preserve them and supporting evidence. No original inputs altered. Working directory is Racer. Exact commands in scripts/bootstrap.sh and this record; stdout logs under output/.

Next: validate Metal integration, implement simulation and visible grid, run tests/runtime checks and update resume state.

## Implementation and exact validation

Implemented independent 120 Hz C++ vehicle simulation, SDL3 input and virtual controller verification, bgfx/Metal procedural world/car rendering, interpolated chase camera, mph HUD, pause/menu/focus/disconnection rules, reset, bounds and scale posts. Donor systems remain later work per PLAN.md.

Commands (working directory Racer):

- `./scripts/bootstrap.sh`: downloads fixed upstream revisions, configures Release with Ninja and `/opt/homebrew`, builds six jobs. Initial dependency acquisition was run separately from configuration while source was authored. Pins/licenses: `references/dependencies.md`. Sources retained in `.deps/` (278,048 KiB), build in `build/` (10,316 KiB), both under the separately declared 2 GiB ceiling.
- `cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=/opt/homebrew`; `cmake --build build -j 6`. Logs `configure*.log` and `build*.log`. Initial compile exposed the new bgfx SwapChain API; adapted to the pinned headers and rebuilt successfully. No stack substitution.
- `ctest --test-dir build --output-on-failure`: two checks pass, details in `tests-final.log`. `./build/driving_checks` measures 100 km/h after eight seconds and 38.8737 m stopping distance. Forward/reverse caps, fresh direction transitions, steering, same off-road traction, boundaries, reset and 30/60/144 Hz render schedules checked.
- `./build/racer --smoke 6 --screenshot <output>/grid.ppm`: first native Metal window run. macOS constrained initial window to 1512×837. About 119.4 FPS after warmup; first grid screenshot inspected, HUD contrast then improved.
- `./build/racer --smoke 14 --benchmark --autodrive --screenshot <output>/driving-1080.ppm`: actual 1920×1080 drawable, 1,557 measured frames / 13.0083 s = 119.692 FPS after one second warmup. Accelerated, turned off-road and braked; final speed zero at x=177.132 m, z=75.1887 m. This bounded run exceeds 60 FPS; larger-world performance not inferred.
- `./build/racer --verify-controls --screenshot <output>/pause.ppm`: virtual hardware drives real app event loop. Initial attempt failed because SDL background joystick updates were disabled. Enabled SDL background input while retaining app focus-loss pause; corrected run passed. Both failure and success logs retained (`live-checks*.log`). Virtual test checks analog driving, Y reset, restart, active-controller detach pause, focus-loss pause, Esc and menu Resume, and Quit selection. Tests do not establish physical hardware support.
- Final rebuild and `./build/racer --verify-controls`: PASS in `live-final.log`. Final executable SHA-256 in `executable.sha256`: `1ae15e12ab8491c54f1c47b762cdab2c4256e47e2eaecf98d5eb67e5aaef804f`.
- `sips -s format png <capture>.ppm --out <capture>.png`: screenshot format conversion. Grid, 1080p driving and paused images visually inspected. No source-game imagery used.
- `bash -n scripts/bootstrap.sh`, source whitespace checks and `git diff --check`: pass. Initial scaffold/source remain untracked, so source whitespace was checked separately.
- Hub checker `python3 ../../tools/check.py`: PASS, managed lab/Racer output 56,239,342 bytes before final capture, free 462,172,475,392 bytes. External dependency/build roots measured separately above.

## Result, retention and next action

First playable implemented and native launch verified. No game engine editor, donor importer, career, car-building UI, races or customization claimed implemented: those are the later systems agreed in PLAN.md. Physical gamepad verification remains outstanding. No game source inputs changed, no REA session/database opened, no commit/push/publication performed.

Keep source, pinned dependency trees/licenses, build, logs (including failed probes), screenshots, executable digest and all earlier donor evidence. No cleanup needed. Next: playtest with a physical gamepad, then agree the next donor-inspired milestone. Final capture/check results appended below.

Final executable 1920×1080 six-second capture run: Renderer: Metal | 1920x1080
Measured frames=597 seconds=5.008 FPS=119.209 final_mph=46.6028 x=11.463 z=59.8387

Final source/executable capture inspected at 1920×1080: road grid, oriented car, chase view and readable mph/controls HUD visible. Final hub check PASS: 62,504,824 managed bytes before writing the check log itself; 462,165,438,464 free bytes. `output/hub-check.log` retains the complete report. Implementation scope complete; physical controller testing remains the explicitly recorded coverage limit.
