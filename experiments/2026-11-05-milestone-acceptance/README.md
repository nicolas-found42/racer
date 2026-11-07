# Original milestone acceptance audit — 2026-11-05

Objective: verify the original PLAN.md milestone requirement by requirement without substituting synthetic evidence for human acceptance. Previous goal turn: progress (offline evidence preservation implemented, failures reproduced and retained). No new milestone or scope reduction.

Target runtime SHA-25635fad0a547534630eb37e0e67d00b4031d2129b5a953777b3ecc5c212594d4d4; existing staging and evidence preserved. New output <=256MiB; each subprocess <=300s, >=20GiB free. No desktop focus/input; native process uses --background. Read-only donor findings are retained historical source/manual evidence; no donor execution is attempted.

Current evidence assessment found a concrete gap: the latest final-build moving-course no-capture performance run lasted14s and completed no gates. The plan explicitly asks for traversal through turns; the older85s sample used an earlier executable. Run a fresh85s hidden no-capture sample on the corrected final runtime with an isolated profile and recorder. Keep other requirements linked to their exact build/version evidence rather than repeatedly generating equivalent output. Outcome and remaining human requirement follow below.

## Requirement-by-requirement assessment

| PLAN requirement | Authoritative evidence checked | Status |
|---|---|---|
| Baseline, isolated profiles, preserved repository | Feedback experiment before/source manifests; observability preservation manifests; current Git status | Established; existing staged work and all historical evidence retained. |
| SLRR/GT4/MC3 bounded source research | `findings/feedback-source-evidence.md` and all three linked experiments; named Tyre/Transmission SHA-256 freshly recomputed in `output/completion-evidence.json` | Established within static/manual scope and recorded conditional runtime blockers. Edition/manual/build correspondence remains explicitly unknown; no donor execution or asset import claimed. |
| Draft/applied/save/invalid feedback | `tests/presentation_checks.cpp`, original implementation matrix and current reviewed loop error/recovery frames08–13,29–35 | Established in focused tests and retained native UI evidence; no storage serialization change. |
| Comparison identity, values, provenance, signed deltas | A8.000/B6.667/CmatchingA screenshots and actual profiles, frozen/revision matching checks, current loop manifests | Established for measured automatic tests; player differences retain driving-skill warning. |
| Test identity/phases and context controls | Both loop frames04–07,16–20,23–30 and presentation/session tests | Established in retained reviewed samples. |
| Existing measurements/handling/course invariants | Source manifests rechecked: runtime source/build hashes unchanged; prior9CTest log includes driving/setup/session/flow/presentation checks | Established for automated cases; only two offline Python files changed since final native build. |
| Native controls, held-input/focus/disconnect/rearm | Current-build `observability/output/release-native/manifest.json` and corresponding logs; fresh-process reload manifest | Established for keyboard and SDL virtual pad; hardware remains unknown. |
| Two-size full garage→tune→test→compare loop | Current build35fad0:37 captures each; all82 retained PNG hashes recomputed here; original review transcripts and pixel-comparison records retained | Established for observed sizes/states; images not reinterpreted as human acceptance. |
| Scaling/resize | Original feedback build1280x720→1512x837→1280x720 captured/reviewed, byte-identical restored image | Historical runtime evidence; resize code preserved in current source. No new focus-taking check is authorized. |
| No-capture performance, including turns | Final drive/garage/stationary14s samples plus new85s moving run in this experiment | New full-course result must be checked below;14s moving run alone was insufficient. |
| Physical controller | Native logs report none; PLAN says test when present or mark unverified | Unverified and explicitly reported; not substituted by virtual pad. |
| Human unassisted course and invalidation | Human's earlier run reported the render defect; no later human report establishes a valid lap, unaided guidance or miss/backtrack/boundary usability | **Not achieved.** Corrected build is ready but remains unopened under user's no-focus instruction. Request for actual observations is pending. |
| Review/gates, experiment records and resume state | Original implementation and observability Jev gate results plus documented root/stronger reviews; preservation gate's concrete issue repaired/reviewed; galleries and runbook retained | Established within stated local scope; no automatic gate pass claimed and no repeated gate sampling. Human acceptance cannot be closed by code review. |

Retention: preserve original inputs, all old/new captures, profiles, logs, manifests, failed probes, source snapshots and review results. `output/completion-evidence.json` verifies82 PNG hashes, both final loop manifests,37 source/build identities and two named donor-source hashes. Only the Python query tool/tests differ from that runtime manifest; the executable is unchanged. A full human lap and invalidation exercise is an observation requirement, not another instrumentation task.

## Remaining acceptance and next action

PLAN explicitly requires a human-driven valid lap without source/map assistance, plus miss/backtrack, pause/resume, reset and boundary cases. The user earlier volunteered, then reported the render defect and requested hidden execution. That defect is corrected and captured; no later observation supplies the missing human acceptance. The asynchronous request names the corrected unopened RacerDiagnostics.app and asks for lap/time, unaided guidance, cases tried and confusing behavior. Do not infer acceptance from silence or open the app while the user uses the computer.

This audit keeps the original goal and unchecked human checkbox intact. After the remaining local performance result is recorded, completion depends on that human report or an explicit user change to the acceptance requirement. Do not start a future part/import milestone to bypass it.

## Final local result

The new sample exits0 on exact build35fad0a5: Metal1920×1080,10081 measured frames/84.0084s,120FPS, longest10.8655ms, zero intervals over16.67ms. All5 gates complete with valid=1 in75.2119s under explicitly synthetic course control. `output/moving-manifest.json` retains exact argv, executable hash, PID, terminal state, exit and duration; `moving/native.log` retains measured output. `moving-query.jsonl` and `moving-verification.json` establish a complete retained history, both steering signs, valid gate5 and zero screenshot requests. This closes the no-capture traversal gap; it does not satisfy human acceptance.

Completion remains unproven solely for the required human course exercise. The same human-evidence dependency remained explicit in the preceding observability and preservation goal turns and this audit. Now that available local checks are complete, no further autonomous code/test work can establish it. Keep the goal intact and mark it blocked awaiting actual human observations; do not mark it complete, activate the app, or keep generating equivalent tests. Physical-controller/donor/OS limitations remain disclosed as conditional or out-of-scope evidence limits.
