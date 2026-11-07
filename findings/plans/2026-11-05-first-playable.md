> Historical plan: implemented and validated. Its confirmation applies to the first playable. See [current PLAN.md](../../PLAN.md) for the next milestone.

# Racer: confirmed implementation plan

Date: 2026-11-05. All interview choices Q1–Q19 are answered. User confirmed shared understanding and authorized implementation on 2026-11-05.

## Objective and delivery boundary

Build an original offline single-player open-world racing game in C++, encompassing driving, car building, tuning, upgrades, racing and exploration. No priority order among those activities was specified.

The first implementation delivers the documented driving grid. The donor-inspired garage, customization, career and racing systems below are later work. Their exact internal behavior needs further research before implementation. Direct donor asset/data imports require individual decisions after contents and suitability are verified.

## Technical foundation

- Native macOS first, verified on the current arm64 Mac.
- C++ gameplay and simulation; CMake build; SDL3 window, events, keyboard and gamepad; bgfx rendering with the Metal backend.
- Needed tools/libraries may be downloaded. Pin the versions/revisions actually used and record reproducible build and launch commands.
- Godot is excluded. A visual world/car editor is deferred. Initial grid and tuning are C++/simple configuration.
- Begin with a bounded SDL3/bgfx build/window check. Any integration failure must be diagnosed and reported; do not silently substitute another stack.
- Keep vehicle simulation independent of rendering, using a fixed simulation step and interpolation for presentation. No donor physics formula is assumed recovered.

## First playable

### World and car

- Flat 1,000 m × 1,000 m world centered on the spawn intersection.
- Road centerlines every 100 m; roads 12 m wide; visible distance markers.
- Ground between roads is driveable with the same physics as the road for this milestone.
- Marked outer boundary stops the car without damage. The car stays inside the area.
- One clearly oriented placeholder car with approachable grip handling, inertia and speed-sensitive steering.
- Reset returns the car stationary to the central road intersection facing north, with the chase camera restored.

### Performance targets

These are authored Racer targets, not measured donor values:

| Measure | Initial target |
|---|---|
| Acceleration | 0–100 km/h (0–62.14 mph) in about 8 seconds |
| Forward speed cap | 160 km/h (99.42 mph) |
| Reverse speed cap | 30 km/h (18.64 mph) |
| Braking | 100–0 km/h in about 40 m on flat ground |
| Rendering | 60 FPS at 1920×1080 on this Mac |

Measure the actual result and report deviations. Simulation behavior must remain consistent across render frame rates.

### Inputs and direction changes

| Action | Keyboard | Gamepad logical control |
|---|---|---|
| Throttle / select forward | W or Up | Right trigger |
| Brake / select reverse | S or Down | Left trigger |
| Steering | A/D or Left/Right | Left stick horizontal |
| Reset | R | North face button (Y/Triangle position) |
| Pause | Esc | Start/Menu |

Holding brake stops forward motion and remains stopped. Release and press it again at rest to engage reverse. Throttle brakes reverse motion; release and press again at rest to select forward. Analog steering and trigger values must be preserved for gamepads.

Pause automatically on focus loss or active-gamepad disconnection. Provide Resume and Quit while paused. Avoid applying stale controls when play resumes. The first implementation supports keyboard and gamepad, with wheel support deferred.

### Presentation

Simple daylight, contrasting roads/ground, visibly oriented placeholder car, smooth chase camera, and an mph speed display with a control legend. The camera remains behind the car in reverse. No donor assets have been chosen for this milestone.

## Confirmed donor contribution plan

These are accepted design references for later milestones. Documentation and static source support the concepts; exact runtime behavior, edition correspondence and porting feasibility remain separate questions.

| Family | Contribution |
|---|---|
| Street Legal Racing: Redline | Modular car building, part compatibility, and tuning with measurable effects; compare both supplied versions. |
| Gran Turismo 4 | Per-car tuning presets and structured driving tests/feedback. |
| Midnight Club 3 | Garage/menu flow and checkpoint-based route creation. |
| Juiced 2 | Layered livery customization and performance classes for race eligibility. |
| Midnight Club Los Angeles | Map-based exploration, event discovery and street challenges. |

Source references and uncertainty are retained in [donor findings](../../findings/donor-contributions.md) and [the research experiment](../../experiments/2026-11-05-donor-inventory/README.md). The two SLRR versions count as one family; each version need not supply a separate feature. Later milestone order is not yet selected and is outside this first implementation's scope.

## Implementation and verification sequence

1. Record an implementation experiment with dependency identities, storage/time bounds and verification commands. Validate SDL3/bgfx/Metal on this machine.
2. Implement independent C++ vehicle/input state and the world bounds; check acceleration, speed caps, stopping distance, steering, reverse transitions, reset and pause.
3. Render the grid, placeholder, chase camera, markers, HUD and pause flow; integrate keyboard and gamepad events, including connection changes.
4. Build and run the native application. Inspect the visible result and exercise the driving scenarios. Measure frame pacing/performance at the target resolution and compare simulation results across frame rates.
5. Exercise controller mappings with actual hardware when available; use virtual/injected input to check mappings and disconnection paths otherwise, explicitly labeling that coverage. Initial OS inventory found no recognizable connected gamepad, so physical controller success cannot currently be promised.
6. Run relevant build/tests and the hub checker. Preserve evidence, update the README with launch commands, controls, actual dependencies, measured results and remaining limitations.

No further product requirement is silently selected by this plan. Routine code organization, rendering details and dependency pinning remain implementation decisions within these constraints. If a material requirement or scope change emerges, return to the interview for that decision.

## Confirmation

Confirmed by user: “Yes — implement this plan.”
