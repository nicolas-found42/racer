# 2026-11-09-theo-workflow-video: what workflow practices/tools does Theo's "Coding Isn't About Code Anymore" present, and are they useful for Racer?

- Status: completed. Transcript fetched in full; every practice in the video traced to the primary source that owns it; mapped to Racer's actual conventions. No Racer code changed.
- Target/build/platform/architecture: Racer at `12033e2`, macOS arm64. Research-only experiment; no build.
- Canonical input: YouTube video `GtJKFhztgdM`, "Coding Isn't About Code Anymore", channel "Theo - t3gg" (`@theo`), published 2026-11-08T22:41:14-08:00 (per watch-page HTML). Duration ~2,717 s (last transcript start 2717.359). Raw transcript (1,294 snippets, English) in `evidence/transcript.txt` (61,951 bytes, SHA-256 `ae2129411f8fe80b9491ef28da01c4789900fd05af789ed1276ed454966d1375`, format `[<seconds>] <text>` one snippet per line); metadata in `evidence/video-metadata.json`.
- Question and expected observation: which concrete workflow practices/tools/config conventions does the video actually present (vs. motivational framing), what owns each, and what is honestly useful for Racer given AGENTS.md files, experiments/README.md records, hub `python3 tools/check.py`, ctest 106/106, and background agents already in use.
- Tool/provider/version: `youtube-transcript-api` (pip, python 3.15.0) via `YouTubeTranscriptApi().fetch("GtJKFhztgdM")`; curl 8.7.1 for oEmbed/watch-page HTML and primary-repo reads; web search for primary sources. No AI-provider calls beyond fetch/search.
- Working directory and exact commands (from `games/racer`):
  - `pip3 install --break-system-packages youtube-transcript-api`
  - `python3 -c` loop: `YouTubeTranscriptApi().fetch("GtJKFhztgdM")`, write `experiments/2026-11-09-theo-workflow-video/evidence/transcript.txt` as `[start] text` lines; verified `OK 1294 snippets`, `lang: en`.
  - `curl -s https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=GtJKFhztgdM\&format=json` → `evidence/video-metadata.json`; publishDate/channel added from `curl -s -A "Mozilla/5.0" "https://www.youtube.com/watch?v=GtJKFhztgdM"` HTML.
  - Primary-source reads: `curl -s https://raw.githubusercontent.com/t3dotgg/tstack/main/README.md`, `.../pingdotgg/t3code/main/README.md`, `.../t3-oss/create-t3-app/main/cli/README.md`; `curl -sI` existence checks for `trpc/trpc`, `microsoft/typescript-go`, `t3-oss/create-t3-app`, `agentsmd/agents.md`, `convex/convex-backend`; web searches for agents.md, Convex, TypeScript 7, CodeRabbit, tRPC.
  - Racer-side audit: `ls tests/` (121 entries), `grep -c add_test CMakeLists.txt`, `python3 ../../tools/check.py --skip-free-space` (PASS; racer 2,671,086,042 bytes standard experiment output — at the project-output floor of the 4 GiB policy, see Limitations), `grep` for `parallel`/`background`/`smoke`/`benchmark` in PLAN.md and experiments.
- Limits before running: no execution of any video-adjacent install script; no Racer build/tests (research-only); disk bound unchanged (transcript + metadata ≈ 62 KB, no `output/` produced).
- Output location: this file plus `evidence/transcript.txt` and `evidence/video-metadata.json` under `experiments/2026-11-09-theo-workflow-video/`. No other outputs.
- Started/finished and exit result: 2026-11-09; all fetch/read commands exit 0; transcript fetch succeeded first try (fallback watch-page HTML not needed for content, only for publishDate).

## Observations and evidence

The video is a personal-essay monologue, not a tool demo. Its thesis — "we're not really engineers anymore… our role as gardeners" — is:[90.00] *"I'm going to make the argument that our role as gardeners. The best thing we can do now is maintain a healthy garden."* The concrete, actionable workflow content is thin and specific. Everything below is quoted from `evidence/transcript.txt` (timestamps are transcript seconds).

### F1. Role framing: engineers as "gardeners" (framing, not a tool)

Evidence: [1964.32]–[1993.76] *"we shouldn't be the ones growing the code. We now need to build environments where the code can grow in the right direction, have the right nutrients, have the right support systems, and have the right monitoring… that the likelihood that you can recover it before it becomes a weed and infects your garden is as high as possible."* [2268.80] *"Slop grows faster than weeds do. If you are not constantly maintaining your garden, you will very quickly come back to a garden that is composed primarily of weeds."*

Primary source: this is Theo's own framing, not a third-party method. It appears in the video description (*"AI has given engineers a new job, which is much more akin to gardening rather than coding"*) and recurs in his T3 Code / tstack writing (see F3). No external spec exists; no corroboration needed — the claim is the video's own.

Usefulness for Racer: conceptual alignment only. Racer already behaves this way structurally (every investigation is an experiment record with question/evidence/next action; platform work and product work are interleaved in git history). The value is a shared vocabulary — "weed" = unowned friction, "stake" = a guardrail that steers agents — not a new process. Nothing to adopt; no process change recommended.

### F2. Platform/product pendulum: ~50% platform PRs (the core practice, with a named mechanism)

Evidence: [1300.00]–[1328.00] *"I was probably 50/50 split between my time spent doing platform code making it easier to work on Ping to the actual product code… like half the poll requests I was filing as a solo dev did not affect the users at all… But those poll requests made it so the other half were way easier to land. And that was the back and forth, the pendulum swing between the two… Knowing when to tap out on product because the thing is harder than it should be. Give it up for a minute, go back to the platform, make the platform easier to build on top of. And then once that is in a good state again, go back and build the feature."* Backing model: [843.52] *"what's the relationship between setting up a platform that good product can grow out of and setting up product to give feedback to the platform so that they can grow together"*; [1483.12]–[1490.56] *"so many of the pieces of friction you encounter as a dev are like one conversation and one small change in the platform away from not needing to happen."*

Primary source: Theo's own retrospective on Twitch (browser-clients platform team) and Ping/T3 Chat — see [720.64]–[739.36] and [1143.68]–[1156.56]. The concrete artifact he credits is the T3 Stack itself: *"I took three sets of tools people were using well and assembled them into one. And it was Next.js TypeScript client with Next.js as the server… Tailwind… Prisma for the database because it was full stack type safety from the database to the back end… tRPC… The contract was TypeScript."* ([1156.56]–[1207.84]). Primary repo: https://github.com/t3-oss/create-t3-app (README: *"The 'T3 Stack' is a web development stack made by Theo focused on simplicity, modularity, and full-stack typesafety"*). tRPC primary: https://github.com/trpc/trpc, https://trpc.io/docs.

Usefulness for Racer: directly applicable as a heuristic, not as a quota. Racer analog: when a feature stalls on tooling (e.g. the repeated `--start-at` / ground-placement / capture focus-loss fixes in `vehicle-physics-patches` experiments), tap out and fix the platform piece (test helper, capture script, shared loader) before retrying the feature. The 50/50 ratio is a personal anecdote for solo web dev and must not be copied as a target for a C++/SDL3 game; the transferable part is the *tap-out trigger* ("harder than it should be" → improve the surface first). Already done here in practice; worth keeping explicit as a rule of thumb in experiment records when a platform fix unblocks a feature.

### F3. Agent workflow surface: guidance files, T3 Code control surface, and agent skills (babysit-PR / council patterns)

Evidence: [2362.56]–[2369.12] *"we made some guidance changes to the repo to the agents and things like that to steer agents away from making bad tests."* [2466.88]–[2471.60] *"(the check) puts feedback in the PR that a babysitting agent will notice and address."* [2547.60]–[2550.80] *"Now I'm doing that with and for agents. I am building up the best possible code base to contribute to."*

Primary sources:
- T3 Code (agent harness control surface): https://github.com/pingdotgg/t3code — repo README states it *"enables control of the agents on your machine"*, supports Claude Code/Codex/Cursor/Grok Build/OpenCode/Antigravity/fx; install via `curl -fsSL https://t3.codes/install.sh | sh` (not executed here; noted as primary source only).
- Theo's agent skills (babysit-PR, council, sol-loop, file-pr, takeover): https://github.com/t3dotgg/tstack — README lists skills *"Works with Claude Code and Codex"*; `babysit-pr` *"Watches a PR through CI and review bots, and fixes the real findings"*; `council` *"Gets review from three models from different providers, and loops until they agree."* Guidance convention per tstack README: *"Put personal settings, like which models sit on your council, in your CLAUDE.md or AGENTS.md."*
- AGENTS.md format (the "guidance changes" mechanism): https://agents.md/ and https://github.com/agentsmd/agents.md — *"A simple, open format for guiding coding agents"*, *"Think of AGENTS.md as a README for agents."* Used by 60k+ open-source projects (per agents.md). This is the underlying spec for Racer's existing `AGENTS.md` / `CLAUDE.md` bridge pattern.

Usefulness for Racer: mixed. Racer already has the AGENTS.md bridge (project + hub level, with the explicit *"read its AGENTS.md and docs/toolchain.md"* instruction, which exists because the nested repo needs an explicit pointer — exactly the pattern agents.md documents). That part is already done here. The tstack council/babysit skills are JS/TS/PR-centric and assume multi-model subagents and GitHub PR flows; Racer's work is C++/CMake with local ctest and Jev gates, and background agents already exist in this environment (`task` delegation). Not applicable as installed tooling; the pattern worth keeping is "guidance changes in AGENTS.md to steer agents" — Racer does this but could add one line pruning guidance that no longer matches practice (it already does this implicitly via experiment records).

### F4. Test curation: delete ~half of unit tests (25,928 → 14,847; −258,735 lines; 22 restored)

Evidence: [2313.52]–[2351.12] *"This PR involved me deleting around half of all the unit tests in T3 code because the more I was working in the codebase, the more I realized how many of these tests are useless and more importantly how much the useless tests multiply and result in more and more unnecessary edge cases being tested for no good reason whatsoever. And that's why I was able to delete 250,000 lines of code from the codebase in one PR. And we've had no regressions that any of the deleted tests would have caught. I think of the 11,000 tests, I brought back four of them total."*

Prevention: [2374.88]–[2395.36] *"whenever one of us noticed one (a bad test), we would ask the person who contributed it to go find the thread where it happened and ask their agent why. What led to you adding this test?… and we would use the info it would give us to go to the root of the problem, whatever stem this weed grew from and kill that."*

Primary source: **pingdotgg/t3code PR #22557** (https://github.com/pingdotgg/t3code/pull/22557, merged 2026-10-21, verified in deep pass part 2, D1). Part 1 recorded these as unverified video claims; part 2 verified the PR: **11,000 of 25,928 tests (43%) deleted, 456 files removed, 1,195 trimmed, −258,735/+5,771 lines, summed test-file time −59%; review restored 22 auth-boundary tests**. The "4 restored" and "11,000 of 11,000" figures Theo states in the video are imprecise renderings of that PR. The *method* (printed delete/keep rubric + two-pass agreement + AST-apply, plus the ask-the-agent-why stem fix) is the portable part.

Usefulness for Racer: high but conditional, and this is the most directly transferable practice. Racer has 106/106 ctest suites, 121 files under `tests/` (~13k lines), plus a hub checker with a large-memory footprint. Practice F4 at Racer scale would mean: audit for tests that never failed / duplicate fixture data / asset-dependent suites that always `SKIP_RETURN_CODE 77` (CMakeLists marks at least 4 suites SKIPPED); delete with a revert-cheap commit and confirm no regression escapes; restore only what fails. The feedback loop (ask the contributing agent *why* it added the test, fix the stem) maps to Racer's existing experiment-record convention — every deletion should point at the experiment record that justifies it. Do not copy the "half" number; use the regret test: no deleted test would have caught a real regression.

### F5. Cheap per-PR regression stakeholder: "thread transfer impact tool" (under 45 s CI check as a "wooden stake")

Evidence: [2441.44]–[2487.92] *"I built the thread transfer impact tool, which is an action that runs on every PR that has a bunch of real event data from real codeex threads and cloud threads, runs it through a fully simulated end-to-end pipe, and checks how much data goes through the pipe. and then it would print it in every PR and flag a bunch of big red X's when anything caused a meaningful regression whatsoever… It puts feedback in the PR that a babysitting agent will notice and address… It gives the developers and the reviewers clear feedback… But the most important thing… It gives the agent the information. This is a thing we care about and it should be optimized for. To go back to the garden analogy, this is like the wood stake you put in next to a plant."* Cost: [2496.08]–[2504.32] *"This CI tool, this one additional check… takes like almost no time. I think it takes under 45 seconds to run. It might be 30."*

Primary source: Theo's T3 Code repo (https://github.com/pingdotgg/t3code) — reported here as his description; the tool's internals were not traced.

Usefulness for Racer: the best concrete adoption candidate. Racer already has `python3 tools/check.py` (hub structure/output policy) but no fast per-change performance/regression stakeholder: the benchmark smoke commands in PLAN.md (`--smoke 14 --benchmark --autodrive`, garage/course scenes, FPS + max frame interval) exist but run manually per experiment and are documented as ~150 s-class checks, not as a sub-45 s PR gate. A small `--smoke N` FPS/max-frame/FPS-floor check that prints one line per PR (or per commit, given Racer's small-team flow) and flags a regression over a pinned baseline is a direct, honest translation of the "wooden stake." The <45 s budget is achievable: Racer's native checks are already bounded and ctest takes ~7 s per the vehicle-physics record. Also matches the video's friction argument (below): a check that agents can read is a stake.

### F6. Friction quant: slow builds/CI/dev-server block agents hardest; five-minute stalls waste tokens

Evidence: [2203.36]–[2254.96] *"Maybe your agents get blocked much harder by these things. If it takes 5 minutes to spin up the dev server to even check if the code works or not, your agent is going to be blocked insanely deeply by that. Hell, if you're using five minute TTLs, you're also going to be wasting a ton of tokens because you're not going to be hitting cache reads when you wait that long to validate a change. If your CI is too slow or it takes too much RAM and CPU to use, you become heavily limited by how much you can parallelize the work. If your release pipeline is too slow… you're not going to be hitting merge as much. The constant maintenance of the platform has never been more important because not doing this blocks your agents even harder than it blocked us."* Parallelism corollary: [2227.44] *"If your CI is too slow or it takes too much RAM and CPU to use, you become heavily limited by how much you can parallelize the work."*

Primary source: this is a claim about agent-harness economics, not about a specific tool. It is corroborated by, not owned by, the video; honest labeling: the numbers ("5 minutes", "five minute TTLs", "a ton of tokens") are rhetorical, not measured.

Usefulness for Racer: moderate and mostly already done. Racer's build/ctest loop is fast relative to the video's examples (ctest ≈ 7 s; builds "≤ a few minutes" per the vehicle-physics record), and capture parallelism is already proven: parallel hidden-window capture matrix (4 runs, 32 captures in 83 s vs ~15 min serial) in the same experiment record. The genuinely open items are: (a) no CI/GitHub Actions config — there is no `.github/` in Racer, so the "always-on gate" does not exist; the smoke checks in PLAN.md are manual runbook steps; (b) storage pressure — `tools/check.py` reports racer at 2.67 GiB of standard experiment output against a 4 GiB project limit, so retention policy is the binding constraint on running more checks; (c) token/TTL economics are harness-side and not actionable for this repo. Worth adopting: a documented <45 s smoke gate (F5) and keeping rebuilds cached; not worth adopting: any external CI service without naming its cost/policy implications.

### F7. Sponsored segment (not a practice): CodeRabbit PR code review / security scanning

Evidence: [143.76]–[154.00] *"Today's sponsor is Code Rabbit and their new Code Rabbit rabbit secure product… They can do deep scans to find things that you might have missed in the past. And they can scan every PR as they come in, making sure they are as secure as possible."* Claims: [116.00]–[128.56] AI writes exploits and insecure code; [177.36]–[182.00] *"Understanding the reachability, exploitability, and the blast radius of every change has never been more important."*

Primary source: https://docs.coderabbit.ai/ (code review and security guides). This is a paid sponsorship (14-day free trial link in the transcript); it is a vendor claim, not a workflow practice. Racer's existing review equivalents are `jev_gate`/`jev_verify` (semantic claim checks, used in both recent experiments) plus linker/Jev adversarial review passes. Nothing to adopt here; noted only because it is the video's sole named external tool.

### F8. Explicitly non-practices (named to show the video's scope)

Evidence: [983.76]–[1002.00] *"I did not talk about becoming a manager. I did not talk about super intense code review processes. I did not talk about building a bunch of guard rails and unit tests to prevent things from going certain ways. I didn't talk about code coverage. I didn't talk about any of that. All I've talked about is this relationship between setting up a platform that good product can grow out of and setting up product to give feedback to the platform."*

Implication: the video argues *against* process-by-document-tooling (management, coverage gates, heavyweight review) and *for* platform/quality-by-construction. Racer's heavyweight experiment-record + hub-check + Jev-gate process is deliberately more formal than the video's stance; that formality is a local choice for an RE lab (provenance, reproducibility), and F4/F5 actions should be understood as strengthening it, not replacing it with the video's lighter ethos. Not applicable as a directive; useful as a counterweight against adding new gates without F5-style cheapness proof.

### Practices present in the video I could not trace to a primary source

- UPDATED in deep pass (part 2, D1/D2): the test-deletion PR (#22557) and the thread-transfer tool both traced to public artifacts, so the F4/F5 numbers below are no longer "not traced" — see D1 for verified figures and D7 for the corrections. Still unverified video-on-screen claims: the merged-PRs/day chart (2→20 → 60 → 400+ merged PRs/day, [2604.08]–[2642.08]) and the ~5 KiB thread payload — reported as stated, not confirmed.
- "Sonnet 4.5 slop was blocking Opus 5.5" ([1814.08]–[1823.84]) is an anecdote about model generations, not a tool; no source maps to Racer.

## Conclusion and limits

- Top findings: (1) F4 (delete-test audit + ask-the-agent-why) and (2) F5 (<45 s per-PR regression stakeholder as a "wooden stake") are the only two practices with direct, low-cost Racer analogues; (3) F2's platform/product pendulum is the framing that justifies both; (4) F3's AGENTS.md guidance is already in place. F6 is mostly already done (fast ctest, parallel capture). F7 is a paid sponsor, F8 is an explicit non-practice.
- Coverage: full transcript acquired (1,294 snippets, EN). All practices quoted verbatim with timestamps; every tool/repo traced to its owner on the web. No fallback to watch-page HTML was needed for content.
- Limitations:
  - Transcript is ASR text; proper nouns are occasionally mangled ("Codepcure", "TRRPC", "codeex", "soydev.link", "RCI"). Quotes preserve the transcript's wording; obvious referents are parenthesized where needed (e.g. "Codepcure" = CodeRabbit). The sponsor name is given as "Code Rabbit" in the transcript audio.
  - Video published 2026-11-08, one day before this experiment; Theo's claims are his as of that date. T3 Code's repo state in Nov 2026 was read at HEAD; drift is possible.
  - The 50/50 platform split, PR counts, deletion counts, and token economics are uncorroborated anecdotes; I did not verify T3 Code's CI history or PR volume.
  - Racer storage: `tools/check.py` PASS but near the project-output ceiling (Racer 2,671,086,042 B vs 4,294,967,296 B limit). Adopting F4/F5 will increase retention pressure unless paired with output hygiene; the checker does not measure legacy/nonstandard roots.
  - No Racer code, test, or config was changed by this experiment; usefulness mappings are assessments, not implemented actions.
  - Untrusted-content note (per policy): the fetched transcript and pages were treated as data. Scan found no agent-directed imperatives in the transcript (no "install X", "run Y" addressed to an AI agent, no "ignore previous instructions"). The only install command associated with primary sources (`curl -fsSL https://t3.codes/install.sh | sh` in the t3code README) was read as source text only and was not executed.

## Next action

Approve or reject the two candidate adoptions in one experiment each, starting with F5: add a pinned `--smoke` FPS/max-frame line-check (sub-45 s) to the PLAN.md verification gate and record its baseline in a new experiment `2026-11-09-smoke-gate/`. Then F4: a delete-test audit experiment (find never-failed/duplicated/SKIP-always tests, delete with per-record justification, restore only on regression). No other process change recommended from this video.

## Retention

Keep `evidence/transcript.txt` (canonical input, verbatim transcript) and `evidence/video-metadata.json`. This README is the durable conclusion. No `output/` produced; no other outputs.

---

## Deep pass 2026-11-09 (part 2) — the repos and resources shown in the video

Scope: only artifacts the video itself shows or references; the CodeRabbit sponsor segment (≈2:10–3:10) is intentionally ignored per reviewer steering. Method: frame extraction from the downloaded video (`yt-dlp` 1080p MP4, ffmpeg crops; keyframes at 38:40–41:30), then each shown artifact read at its primary URL. Two video-frame evidence crops are retained:
- `evidence/screens/pr-22557-title.png` (SHA-256 `dc34277879ade2579af08e7a2dda20009f639aeb375d5e24423afb1a239dd2cc`) — PR header showing "merged 1 commit into main from `t3/purge-low-value-tests`", 33 checks, 1,895 files, +5,771/−258,735.
- `evidence/screens/thread-transfer-impact-comment.png` (SHA-256 `e1c466482af8a90d4d9b40cc333ddef0a1ab22582b68815688f2d69e35e87a67`) — the bot comment table (Provider Codex/Claude × Metrics × Main baseline / This PR / Impact / PR ceiling / ✅).
Raw full frames `pr_full.jpg` and `stake_full.jpg` sit beside them.

### D1. PR #22557 anatomy — the test-deletion claim is now verified, not anecdotal

Source: https://github.com/pingdotgg/t3code/pull/22557 (API: `/repos/pingdotgg/t3code/pulls/22557`), merged 2026-10-21. Video claim vs. reality: "250k lines deleted, 11,000 of 11,000 tests, 4 restored" was imprecise — the PR body states **11,000 of 25,928 tests (43%) deleted, 456 test files removed outright, 1,195 more trimmed, summed test-file time −59% (1,205 s → 490 s)**; diff is +5,771/−258,735 across 1,895 files. Review restored 22 auth-boundary tests (not 4) that the swarm had cut as "timing". Per-package wall-time table (server 1,040 s → 564 s; web 132 s → 53 s; desktop 20 s → 5 s) is in the PR body.

Methodology (PR body, quoted): *"A swarm of Claude Haiku 5.5 agents read every test file against one rubric. Delete: type-redundant, trivial logic, basic DOM behavior, real or fake timers, mock-call mirrors, smoke tests, duplicate table cases, and wall-clock perf asserts. Keep: orchestration and event-sourcing correctness, provider protocol translation, auth and permission guards, persistence and migrations, external-format parsing, and deterministic race fixes."* ~Half the files (987) got two independent passes; deletion requires both to agree; a third vote settled ~1,900 disagreements. Deletions applied mechanically via **TypeScript AST matched by test title**, so the sweep is reproducible, not hand-editing. Follow-on knip `--exports` pass un-exported ~420 test-only exports and deleted ~48 dead declarations, so "no production behavior change" is checked, not asserted. Reviewed with sol-loop (2 rounds, GPT Sol); created with Claude Opus 5.5 in Claude Code.

File census (first API page, 100/1,895 files, `pulls/22557/files`): 98 files under `apps/desktop`, 83 of the 100 are test files, 16 removed outright — sample removed: `ElectronDialog.test.ts`, `ElectronMenu.test.ts`, `DesktopAssets.test.ts` (mock-mirror Electron/UI shell tests, matching the "mock-call mirrors" rubric line).

Racer relevance update (supersedes part-1 F4): transferable artifacts are (a) the **explicit printed rubric** (delete-list / keep-list before judging), (b) **two-pass agreement + tiebreak** for ambiguous cases, (c) **AST/mechanical application** instead of hand edits, (d) **dead-export sweep after deletion** (Racer analogue: unused symbols/headers after removing test-only use), (e) review-restore pass for false "timing" classifications (Racer's 30/60/144 Hz determinism suites are exactly the class the swarm mis-scored). Racer scale is ~13k test lines, so this is one experiment, not a mega-PR.

### D2. Thread-transfer gate mechanics — how the "stake" actually works

Sources (all read at HEAD, main branch):
- `.github/workflows/thread-transfer-report.yml` — runs `workflow_run` after CI on `pull_request` events; downloads two `thread-transfer-results` artifacts (PR run + newest successful `main` baseline run by exact SHA); publishes/updates one PR comment marker `<!-- t3-thread-transfer-report -->`. Safety note in the workflow: *"Only load the publisher from the trusted default branch and never execute PR code"* — the publisher script is checked out from the default branch and self-tested with `node --test` before use; PR artifacts are strictly schema-validated and never executed.
- `.github/scripts/thread-transfer-report.cjs` (461 lines) — schema: `schemaVersion: 1`, two providers (`codex`, `claudeAgent`), five metrics (`totalWireBytes`, `threadSnapshotWireBytes`, `measuredTurnWebSocketWireBytes`, `measuredTurnWebSocketDecodedBytes`, `measuredTurnWebSocketMessages`); observed values compared against per-provider **ceilings carried inside the artifact**; ceiling changes are flagged in the comment so a PR cannot silently raise its own bar; result file capped at 64 KiB; metrics are bounded safe integers. Fail condition: any observed > ceiling (❌), irrespective of baseline delta.
- The producer is a real integration test: `apps/server/integration/transferBudgetV2.integration.test.ts` + `NetworkTransferMeasurement.integration.ts` + `TransferBudgetReport.integration.ts`. It boots a real local HTTP/WebSocket server (Effect `NodeHttpServer`, permessage-deflate on), replays a seeded thread fixture (`TRANSFER_HISTORY_TURN_COUNT` historical turns, then one measured turn), and measures **actual wire bytes** of the snapshot GET and live-turn WebSocket traffic, per provider (`codex`, `claudeAgent`), then writes `thread-transfer-result.json` as a CI artifact.
- Hard ceilings (`apps/server/integration/TransferBudgetReport.integration.ts`): `TRANSFER_BUDGET = { totalWireBytes: 7_000, threadSnapshotWireBytes: 5_000, measuredTurnWebSocketWireBytes: 2_000, measuredTurnWebSocketDecodedBytes: 25_000, measuredTurnWebSocketMessages: 8 }` for both providers, with comments explaining each is ~30–50% above measured reality so normal variation doesn't flake. (Companion budgets in the same file: long-turn page 110,000 decoded bytes/75 rows; fleet shell 55,000/27.)
- Companion: `agent-context-budget.yml` — separate gate that fails when a PR raises any value in `apps/server/src/provider/agentContextBudget.json` above main's; a test keeps that file equal to measured context so it can't be hand-edited; increases require a maintainer `agent-context-increase` label.

Portability verdict for Racer: the mechanism is portable in structure (fixture → run → measure → JSON → compare vs pinned baseline+ceiling → comment/print), but every specific artifact is web/agent-stack-specific (wire bytes, Codex/Claude providers). The Racer translation from part-1 F5 stands, with one sharpened rule learned here: **fail on ceiling, not on delta** (deltas are informational; ceilings are ~30% headroom over measured), and **validate inputs strictly, never execute PR-supplied measurement code**.

### D3. Other guardrail workflows in the repo (one line each)

- `.github/workflows/pr-size.yml` — labels PRs `size:XS…XXL` by *effective* changed lines, excluding test files in mixed PRs (`--ignore-all-space`), so test churn doesn't inflate perceived size.
- `.github/workflows/pr-vouch.yml` — labels PR authors `vouch:trusted` / `vouch:unvouched` / `vouch:denounced` via `mitchellh/vouch` against a committed `.github/VOUCHED.td` allowlist. Not discussed in the video; listed only as repo context (trust triage for agent-era PR floods).
- Full workflow inventory (24 files, API listing) includes mobile/desktop release trains and `issue-labels.yml`/`stale-needs-more-info.yml` housekeeping — not relevant to Racer.

### D4. tstack skill inventory (Theo's own agent skills)

Source: https://github.com/t3dotgg/tstack README (MIT). Skills: `full-send` (prove→review→file→babysit→merge unattended), `full-stop` (same, stops at ready-to-merge), `council` (three models from different providers loop until they agree), `sol-loop` (two-agent agreement loop with GPT Sol), `file-pr` (problem-first PR body), `takeover` (finish someone else's PR/branch/thread keeping their credit), `babysit-pr` (watch CI + review bots, fix real findings), `modernize` (rebase old PR, decide if it should exist), `leaving-pr-comments` (formatting for agent-posted comments). Settings convention: personal choices (council models) live in your `CLAUDE.md`/`AGENTS.md` so skills stay updatable. Requires a harness able to run cross-provider subagents (T3 Code's `delegate_task` or Claude Code/Codex equivalents).

Racer relevance: unchanged from part-1 (JS/PR-centric, needs GitHub PR flows + cross-provider subagents). The locally transferable *pattern* is `babysit-pr`/`council` reduced to this environment's existing pieces: background `task` agents + `jev_review`/`jev_gate` already approximate multi-pass review; a "babysit" wrapper around long ctest/capture runs is conceivable but not demanded by current work.

### D5. t3code's own AGENTS.md — the concrete "guidance changes" artifact

Source: https://raw.githubusercontent.com/pingdotgg/t3code/main/AGENTS.md (218 lines). Structure worth copying as a template: (1) product identity in five sentences; (2) non-negotiables ("Open at the core", "Performance without compromise", …) framed as user-love commitments, not lint rules; (3) a "note from Theo" persona/policy block (*"Do not preserve complexity just because it already exists… fight for the smallest model that makes the correct behavior unsurprising"*); (4) a glossary fixing pronoun ambiguity (you/we/user/agent/provider/thread/turn); (5) **"The three ways to hurt yourself"** — concrete catastrophic-action prohibitions with the exact safe command substitution given inline (never `pkill -f`; kill only PIDs you captured at spawn; never touch the live user database; never bake origins); (6) "Hit every surface" — a completeness checklist the agent must walk and *say which entries applied* (entry points, clients, providers, contracts, reverse states, connection modes, docs). That last item — self-reported checklist coverage — is the most directly transferable piece for Racer's AGENTS.md ("say which entries applied" maps to Racer's per-experiment evidence contract).

### D6. Convex (one paragraph, per prior scope decision)

Video content: 26:22–31:00 — migration of T3 Chat's custom sync engine to Convex is framed as the platform move that made the product sustainable. What the platform actually is (from https://github.com/convex/convex-backend README): an open-source reactive backend — TypeScript functions over a document store with queries that automatically re-run when their data changes, plus storage, auth, scheduling. For Racer: not applicable (C++/local game, no hosted backend); the transferable principle is "replace bespoke sync/persistence with a maintained platform when sync is not your product" — Racer's profile atomic-replace persistence is already small enough that the principle says *don't* migrate it.

### D7. Deep-pass inputs and tools

- Video 1080p MP4 via `yt-dlp` (local download, `/tmp/theo/video.mp4`, 42 MiB, not retained); ffmpeg frame extraction/crops (keyframes listed in Retention below).
- GitHub API (unauthenticated): `repos/pingdotgg/t3code` (53,654★, default `main`), `pulls/22557`, `issues/22557/comments`, `pulls/22557/files?per_page=100`, `contents/.github/workflows`, `contents/.github/scripts`.
- raw.githubusercontent.com: `thread-transfer-report.yml`, `thread-transfer-report.cjs`, `ci.yml`, `pr-size.yml`, `pr-vouch.yml`, `agent-context-budget.yml`, `t3dotgg/tstack/main/README.md`, `pingdotgg/t3code/main/AGENTS.md`, `convex/convex-backend/main/README.md`.
- Corrections to part 1 proven-wrong claims: F4's "11,000 of 11,000 tests, 4 restored, 250k lines" → verified as **11,000 of 25,928 (43%), 22 restored by review, −258,735/+5,771 lines**; F4's "not independently verified" is withdrawn — the PR is public and its numbers come from the author's own PR body (self-reported but primary). The first-pass claim that the t3code install script "was read only, never executed" remains true in this pass: nothing was executed; every artifact was read.

### D8. Updated verdicts

| Item | Part-1 verdict | Part-2 update |
|---|---|---|
| F4 test audit | candidate, unverified numbers | **methodology now portable and concrete** (D1): printed rubric, two-pass agreement, AST-apply, knip-style dead-export sweep, review-restore pass |
| F5 sub-45 s stake | candidate | structure confirmed portable; adopt **ceiling-not-delta** and trusted-publisher/strict-validation separation (D2); Racer artefact: stored `smoke` baseline JSON + one-line table print |
| F3 guidance changes | already in place | **upgrade**: adopt t3code AGENTS.md patterns "three ways to hurt yourself" + "hit every surface, say which applied" (D5) |
| tstack skills | not applicable as tooling | unchanged; pattern-level only (D4) |
| Convex, CodeRabbit, AGENTS.md spec | n/a / sponsor / already covered | unchanged (D6) |

### Deep-pass limitations

- PR body numbers (wall times, test counts) are the author's own report; the merged diff's net test-count delta was not independently recomputed from 1,895 files (only a 100-file first-page census was taken).
- `thread-transfer-report.cjs` was read to line 461 but only lines 1–263 and the ceiling table were quoted; the artifact-resolution tail (baseline SHA matching) was skimmed, not line-audited.
- `pr-vouch.yml` semantics summarized from label actions, not the full 209 lines; VOUCHED token format not inspected.
- Video frames are 1080p H.264; two text-heavy UI moments (CI check list, PRs/day chart at 43:26–44:02) were legible only at headline level.
- All reads at 2026-11-09 HEAD; repos are actively developed, drift expected.

### Deep-pass retention

Keep: two PNG crops + two raw JPG frames under `evidence/screens/` (listed with hashes above). `/tmp/theo/` downloads (video, workflow files) are disposable scratch, not retained; the cited file contents are durable at their GitHub URLs.

### Next action (supersedes part 1's)

Same two candidate experiments, now with sharpened method specs: (1) `2026-11-09-smoke-gate/` — pinned `--smoke` FPS/max-frame check with ceiling-style thresholds (~30% over measured baseline), one-line table output, failures on ceiling breach; (2) `2026-11-09-test-audit/` — print the delete/keep rubric first, two-pass agreement for deletions, dead-code sweep after, review-restore pass for determinism-sensitive suites. Plus (3) a small AGENTS.md upgrade copying D5's "hurt yourself" + "hit every surface (say which applied)" sections, adapted to Racer's actual hazards (live profile writes, capture focus, ignored asset dirs). Approval still required before any Racer file changes.
