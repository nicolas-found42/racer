# Garage tune/test/compare visual review — 2026-11-05

Question: is the complete native tune/test/compare loop visually clear and usable?
Target: Racer macOS arm64 SDL3/bgfx Metal executable SHA-256 `61217ed9499e3b5294dee6dd339544b94b0d8595373c661bd32fcd7048ad44c3`.
Method: launch unchanged executable with isolated profile, navigate visible native UI, capture garage/draft/apply/test/running/result/compare/retry/return states, inspect screenshots and document findings. No donor work or gameplay changes.
Bounds: each app run <=300 seconds, each command <=5 minutes; generated output <=256 MiB. Preflight: 429 GiB free; existing experiments 128,712 KiB, build 10,964 KiB. Retain screenshots and isolated profile under output/, preserve existing source/staging and normal user profile.
Status: captured and reviewed. Next action: address the prioritized presentation findings below in a separate implementation pass.


## Capture method and evidence

[Open the complete 22-image gallery](output/gallery.html). Individual native screenshots and hashes/captions are in `output/screenshots.json`; the final isolated profile is `output/profile.txt`.

The unbundled CLI executable was not targetable by CUA's app selector. A local `.app` wrapper in `output/RacerReview.app` contains an unchanged copy of `build/racer`; SHA-256 is identical to the target above. The initial unbundled review run was terminated after it could not be targeted. The wrapper was launched with `--smoke 300 --benchmark --profile <absolute experiment output>/profile.txt`, then keyboard actions and screenshots were performed through CUA. No game code was patched or synthetic profile records inserted. Screenshots are full 3024×1738 macOS window captures of the 1920×1080 renderer, including title bar/display scaling. Native process output is retained in `output/native-review.log`. The app has a five-minute exit bound.

Sequence: Pause → Garage A → default acceleration → result → Garage B → increase acceleration to 1.20× → attempt dirty slot switch → Keep Editing → Apply → acceleration → compare A/B → braking → result → Retry → delta → populated comparison → handling countdown → drive through first gate → Reset → invalid result → Garage B. The final profile contains only the three valid records: A acceleration, B acceleration, B braking. No handling result was saved.

## Review findings

1. **P2 — Saved-state wording conflicts with current state.** [Draft](output/07-draft-B.png) says “Draft modified - Apply to use and save” while its footer says “Profile saved.” The [dirty-choice dialog](output/08-unsaved-choice.png) repeats the saved footer; the [invalid result](output/21-invalid-reset.png) also says “Profile saved.” The success message refers to an earlier write, but a player can read it as confirmation of the current edit or invalid attempt. Replace it with state-specific status: “Draft not applied,” “Applied setup saved,” or “Attempt not saved.”
2. **P2 — Comparisons lack setup context and record provenance.** [Comparison](output/18-compare-populated.png) lists A/B/C timings but omits multiplier values and the selected slot that will run next. C shows 8.000 s even though this session never ran C: its exact values match A. Focused inspection of `StoredResult::comparable` confirms matching is by car/test/revisions/values, not slot, and the profile contains the record under A. Preserve that intentional matching rule but label it “matching setup, recorded as A,” show each row's values, and mark the active slot. A clearly signed A/B delta would also make the benefit easier to scan.
3. **P2 — Active benchmark identity is hidden.** [Running acceleration](output/05-running-A.png) and [braking progress](output/16-braking-progress.png) both say only “TEST / AUTOMATIC BENCHMARK”; neither identifies the selected test or setup. They retain “Countdown 0.0” while running. Show “Setup B — 100→0 braking,” identify countdown/lead-in/measuring phases, and make the relevant metric prominent. The broad driving bindings also remain visible even when automatic inputs own the run.
4. **P2 — Course guidance needs a stronger direction cue.** [Course start](output/19-course-countdown.png) and [gate 2 progress](output/20-course-driving.png) rely on small distant yellow gates plus “follow tallest gate.” Perspective makes relative height a weak identifier, and the next turn is off to the right. Add gate numbering/color distinction, distance and a clear next-turn arrow; reduce the overlay near the horizon. This pass reached gate 2/5 and then reset; it does not evaluate a completed human lap.
5. **P3 — Visual hierarchy still reads as a debug overlay.** Most screens preserve a large blue driving-help panel above another dense, same-size monospaced panel. Controls are selected with a small `>` marker; valid and invalid states use similar white text. Result identity, primary measurement and navigation compete visually. Give the garage a dedicated panel with a stronger selected row, larger result metric, distinct success/error styling and context-specific controls. No clipping was observed at this capture size; smaller-window readability was not tested here.

## What works

- The full keyboard loop was navigable without editing game state. Explicit Apply/Discard/Keep Editing choices and the draft/applied heading make the underlying state model understandable.
- Result snapshots, units and slot attribution are visible: [A](output/06-result-A.png) is **8.000 s** at 1.00× acceleration; [B](output/11-result-B.png) is **6.667 s** at 1.20×. The braking result shows **38.874 m**, **2.807 s**, and **100.00 km/h** initial speed.
- [Retry](output/17-retry-delta.png) shows **0.000 m** against the same-setup prior best. Reset visibly marks the course invalid, and [return to garage](output/22-return-garage.png) retains applied B.

## Verification, limits and retention

Every screenshot was inspected. Jev screened the host-generated transcript (pass), audited four displayed values (all pass), and verified four factual review claims (no contradictions/unsupported claims). One active-test-label claim was flagged for review at confidence .77; direct pixel inspection of screenshots 05 and 16 confirms the narrowly stated missing labels. Jev checked the transcript rather than pixels, so its result is a text cross-check, not independent visual proof. Retained artifacts: `output/visual-transcript.txt` and `output/jev-review.json`.

This is a visual/interaction review of one Mac build at one capture size. It does not establish physical gamepad accessibility, small-window behavior, a complete handling lap, or general performance. Capture overhead makes these runs unsuitable for FPS claims. No gameplay source, normal profile, dependency or Git staging changes were made. Retain the small wrapper, captures, profile, gallery, transcript and logs; no prior evidence was removed.

Final checks: all 22 screenshot entries and local report links resolve; `git diff --check` and the lab checker pass (`output/checks.log`). Generated output is approximately 8 MiB, below the 256 MiB bound.
