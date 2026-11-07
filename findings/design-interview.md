# Racer design interview

Status: all rounds and shared understanding confirmed on 2026-11-05. User authorized implementation of [the archived first-playable plan](../findings/plans/2026-11-05-first-playable.md); the first playable is implemented.

The requested `grill-me` skill redirects to `grilling`: interview the current decision frontier in rounds, look up environmental facts, and wait for user decisions. Evidence is in [the donor inventory experiment](../experiments/2026-11-05-donor-inventory/README.md). Recommendations below are proposals, not accepted requirements.

## Confirmed requirements

| Decision | User answer |
|---|---|
| Q1: first implementation | Documented driving grid first; other systems are later milestones. |
| Q2: platform | Native macOS first. |
| Q3: C++ boundary | Gameplay and simulation in C++; engines, libraries and asset tools are allowed. |
| Q4: donor reuse | Recreate selected understood behavior; decide direct asset/data imports individually. |
| Tool acquisition | Download needed libraries and tools. |
| Excluded engine | **Do not use Godot.** |
| Q5: activities | Driving, car building, tuning, upgrades, racing and exploration. No ranking or mandatory loop order supplied. |
| Q6: handling | Approachable grip handling for the first playable, with inertia and speed-sensitive steering; detailed simulation deferred. |
| Q7: input devices | **Keyboard and gamepad now.** |
| Q8: stack evaluation | Evaluate a different C++ library stack; raylib was not selected. |
| Q9: donor grouping | Five game families; compare both SLRR versions, without a separate-feature quota per version. |

The first milestone includes flat ground, roads and scale markers, a placeholder car with acceleration/braking/steering/reverse, chase camera, speed display, reset, and repeatable driving checks. No donor assets have been selected for import.

## Round two: answered

| ID | Decision | Proposed answer |
|---|---|---|
| Q5 | Long-term central activity | Explore, find races, earn rewards, improve the car. Alternative priorities: car building/tuning, or driving/drifting. |
| Q6 | First-playable handling | Approachable grip handling with inertia, speed-sensitive steering and a simple flat-ground vehicle model. Alternatives: drifting or detailed simulation immediately. |
| Q7 | Input devices | Keyboard first, W/S or arrows for throttle/brake/reverse, A/D or arrows for steering, R reset. Alternatives: gamepad or wheel now. |
| Q8 | Rendering foundation | C++/CMake/raylib, Racer-owned simulation. Alternatives: evaluate a full engine (excluding Godot) or another C++ library stack. |
| Q9 | Meaning of every source game | Five donor families, comparing both SLRR variants without requiring each version to supply a distinct feature. Alternative: distinct contributions from both SLRRs. |

Answers are recorded above; the proposal table preserves what was asked, not accepted requirements. In particular, keyboard-only and raylib were not accepted.

## Round three: answered

- Q10: proposed 1 km square grid, 100 m road spacing, 12 m road width, traversable intervening ground, marked stopping boundary.
- Q11: proposed brake-to-stop; release and re-press at rest to reverse, symmetric forward selection.
- Q12: proposed keyboard bindings above; gamepad left-stick steering, triggers throttle/brake, north face reset, Start/Menu pause; auto-pause on focus loss or active-controller disconnect; Resume/Quit.
- Q13: proposed daylight, contrasting surfaces, oriented placeholder, smooth chase camera staying behind in reverse, km/h and controls HUD.
- Q14: proposed 0–100 km/h about 8 s, 160 km/h forward cap, 30 km/h reverse cap, 100–0 km/h about 40 m; 60 FPS at 1920×1080, frame-rate-independent simulation checks.
- Q15: proposed offline single-player foundation; multiplayer outside current plan.

User accepted Q10, Q11, Q12, Q14 and Q15. Q13 accepted the presentation with **mph** replacing km/h in the HUD. The acceleration/braking targets remain their accepted physical equivalents. Grid and speed targets are consistent.

## Round four: answered

- Q16: **SDL3 + bgfx**, with Metal rendering, accepted. No substitution with raylib or Godot.
- Q17: all five contribution allocations accepted; see [donor findings](donor-contributions.md).
- Q18: defer visual world/car editor; use C++/simple configuration initially.
- Q19: same road/ground physics, stationary central north-facing spawn and restored camera on reset, marked boundary stop without damage accepted.

## Design tree and remaining branches

- Platform, rendering foundation, first-playable scope, handling, controls, dimensions, boundary, presentation and player scope: settled in PLAN.md.
- Donor grouping and contribution allocation: settled; exact later systems and their order remain later work, outside this first implementation's agreed scope.
- Pin dependencies, build/launch, frame pacing and checks: implementation decisions bounded by PLAN.md.
- Shared understanding confirmed; implementation and verification completed for the first-playable scope.

Each new answer can add or remove dependent questions. User choices control scope; installed tools do not choose requirements.

## Evidence boundaries

- Inventory identifies four discs and two SLRR installation folders; Juiced 2 and MC LA also have .7z carriers. Correspondence of unpacked images to archive payloads has not been byte-verified.
- The older SLRR supplied manual documents free roaming, street races, a parts catalog, install/remove parts and tuning. This is documentation evidence, not an observed run of these supplied binaries.
- REA verifies static PE import and ELF export facts and retains a controlled `file` classification probe for Xbox executables. It does not establish donor handling, gameplay, importer compatibility or binary/source correspondence.
- The SLRR-231 REA directory scan is partial due to its metadata representation budget. A separate filesystem inventory completed; it does not fill unexamined REA content bytes.
- raylib 6.2, SDL3 3.4.18, CMake 4.4.4 and Apple clang 21.0.0 are installed. [raylib's official site](https://www.raylib.com/) documents a programming library with macOS support and no visual editor. Its suitability for this milestone is an engineering recommendation, not a benchmark result. No dependency has been installed in this interview.
- [Alternative-stack research](../experiments/2026-11-05-donor-inventory/output/stack-evaluation.md) compares SDL3 + bgfx, SDL3 + Filament and SDL3 GPU using official documentation. These remain unbuilt proposals; Godot is excluded.
- [Donor documentation](../experiments/2026-11-05-donor-inventory/output/donor-documentation.md) records publisher-manual evidence for GT4, MC3, Juiced 2 and MC LA with version/edition caveats. [SLRR source findings](../experiments/2026-11-05-donor-inventory/output/slrr-source-findings.md) records fitment and tuning examples with exact paths/lines/hashes. None is runtime verification.
- Local HID product inventory found no recognizable connected gamepad. This bounded OS inventory is not proof of absent hardware or valid SDL mappings. Physical controller verification remains outstanding.

## Next action

First playable implemented; see the README and first-playable experiment for validation and remaining physical controller coverage.
