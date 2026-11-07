# Human course acceptance

Status: first human session ended at its 290 s bound. The user reported a steering/rendering failure: acceleration works, but the camera turns in the expected direction and the car rotates the other way. No valid lap or human acceptance is established. See the subsequent [diagnosis and observability experiment](../2026-11-05-observability/README.md).

Target: the same native build as the accepted automated loops, SHA-256 `3b432aed7b7f15cfc2ac22c868a497fe88f3bf2372cd87326ef3ae4f921c1725`. The local app wrapper contains this unchanged executable. Session `output/human-01/manifest.json` retains its exact command, time, input method and eventual exit. `native.log`, `captures/` and `profile.txt` retain available evidence. All output is retained under the existing 256 MiB experiment budget.

The first session starts in Garage at requested 1280×720 with a fresh isolated profile, `--smoke 290`, a 295 s external watchdog and `--capture-loop`. No review script, synthetic course controls, automatic drive or injected input is enabled. The agent only raises the garage window and observes; menu and driving actions belong to the human. The capture-loop option captures the first visit to each principal screen, so it cannot by itself prove every subsequent retry/invalidation. Supplement it with direct observations and the user's account, distinguishing each source.

## Procedure

1. Use the game's menu to choose Run test / compare, then Player run: handling course. Follow only on-screen instructions and guidance; do not consult the source, route coordinates or a map.
2. Complete a valid lap through all five gates. Record the result time and any difficulty understanding the next gate, direction or off-screen cue.
3. On a retry, deliberately miss a gate and try to recover using the displayed guidance. Pause and resume during that attempt; check that progress is retained and released controls are needed to resume motion.
4. Reset during a run and inspect the invalid result. On another retry, cross the outer boundary and inspect that invalid result. Return to comparison and check that the earlier valid best remains intact.
5. Report which cases were actually performed, what worked and what was confusing. If the bounded session ends first, continue in another explicitly recorded session; do not mark unperformed steps passed.

Keyboard hints are shown in-game: arrows/Enter for menus, WASD for driving, Escape for pause and R for reset. A physical controller is optional: if one is connected, record its model/backend and repeat navigation, tuning, course and release/disconnection checks. Absence of hardware remains an explicit limitation.

## Observation record

| Item | Human report / independent evidence | Status |
|---|---|---|
| Valid five-gate lap without external navigation | Awaiting user / saved handling record and result capture | Pending |
| Left/right and off-screen guidance | Awaiting user | Pending |
| Miss and approach-side recovery | Awaiting user | Pending |
| Pause/resume and release-to-rearm | Awaiting user | Pending |
| Reset invalidation | Awaiting user / result observation | Pending |
| Boundary invalidation | Awaiting user / result observation | Pending |
| Invalid attempts preserve valid best | Awaiting user / profile comparison | Pending |
| Physical controller | No connected device established for this session | Unverified |

Do not check PLAN.md's human-course item until the required observations are recorded. Next action: finish verification of the steering transform correction and retained diagnostics, then invite a fresh human playtest when the user is available. Do not open visible test windows while the user is using the computer.
