# Next milestone plan — 2026-11-05

- Status: planning; documentation-only task.
- Question: what bounded playable milestone builds on the completed grid and the accepted donor directions?
- Target: Racer C++20/SDL3/bgfx Metal on macOS arm64. Current executable SHA-256 `a0417525e3982de46dcab2d2fa1624ef9756f1a1a057317a1216a0dbbc83cefc` matches the retained final validation digest (`shasum -a 256 build/racer`). Existing performance and control results are historical observations, not rerun in this task.
- Inputs: current PLAN.md, README, design interview, donor findings, source-input manifest, donor-inventory source/documentation notes, plan-validation logs and focused `src/simulation.h`/`.cpp` reads. Canonical donor identities remain in `references/source-inputs.json`; no source game is launched or imported.
- Method: apply REA evidence discipline; reuse retained evidence rather than repeat artifact scans. Source inspection suffices for Racer's known architecture. One filtered REA retained-evidence summary may check availability of the SLRR-231 identity record; it cannot establish gameplay behavior.
- Working directory: `/Users/nicolas/Documents/github/reverse-engineering/games/racer`.
- Bounds: each local command <=30 seconds, REA summary <=60 seconds, generated output <=1 MiB, initial investigation execution <=5 minutes. No downloads, extraction, native database or runtime capture.
- Preflight: 430 GiB free; experiments 67,444 KiB, `.deps/` 278,048 KiB, build 10,268 KiB. Git contains staged initial project files plus an unrelated unstaged `.gitignore` change; preserve staging and unrelated work.

## Observations and interpretation

The grid is complete. Simulation constants are currently in `src/simulation.cpp`; no setup/preset/test-session system is present in the inspected implementation. Existing SLRR shipped-source notes support studying draft/apply/cancel and persistence; GT4 documentation supports three per-car setups and driving comparison. These are source/documentation observations, not verified donor runtime behavior. Native dyno/fitment behavior and exact build correspondence remain unknown.

Proposed next milestone: one-car garage setup presets with measured driving tests, reusing the grid and authored handling. This is a planning recommendation, not a newly confirmed user priority. Preserve the old plan and its confirmation as a historical reference, then replace PLAN.md with the path from current state to this milestone.

## Retention and next action

Keep original inputs, existing evidence/state and the archived first-playable plan. Retain any new summary/check output under `output/`. Update README's resume entry to the proposed next milestone. No game implementation is part of this task. Record document/link checks and hub checker before finishing.

## Executed evidence reuse and result

- Read the current project and lab policies, project/resume entries, donor findings/interview, selected source notes, dependency/source identities and validation report. `git status --short` established the staged baseline; staging was left intact.
- `get_evidence_bundle(detail="summary", filters={evidence_id:"ev_7a1bbca51932b9245a466ee590d6b32154ed6990576a426829936a9a98f9b0d2"})`: current REA session contains zero retained records. This is a session availability observation, not lost canonical evidence or an analysis failure.
- Python `json.loads(Path(.../rea-evidence.json).read_bytes())` parsed the complete saved 17,231,730-byte bundle; selected its exact matching Evidence ID. Bundle SHA-256 `54780acc634bc632ce8cf749c9d919f13e6f2c2c9583954ece4a4e7789327429`; 13 records and 4 unknowns. Retained the selected metadata in `output/retained-evidence-summary.json`. Original provider: REA PE import parser v1; operation `inspect_pe_imports`; target SLRR-231 executable SHA-256 `f44fb88a4335c657e20701cdb84afb8d1d85f7c3aceb93d30113e6e6e44fefc2`. Import rows do not establish runtime reachability or gameplay. No fresh artifact scan or native session was opened.
- Archived the completed plan under `findings/plans/2026-11-05-first-playable.md`, retaining its confirmation and correcting relative links. Replaced PLAN.md with the current-state-to-next-milestone scope, concrete player behavior, research boundaries, implementation sequence and measurable acceptance checklist. New settings/ranges and milestone order are explicitly proposed Racer choices.
- Updated README's resume entry and experiment index; redirected the design interview's historical approval link to the archive. No game source, dependencies, donor inputs or Git staging changed.

Question answered as a planning recommendation. No new game tests or donor runtime probes were performed. Next action: execute the baseline/research step of PLAN.md when implementing the proposed milestone.

Validation: a Python scan checked all six changed/new documents for nonempty contents, local Markdown link targets and trailing whitespace; PASS. `git diff --check`: PASS. `python3 ../../tools/check.py`: PASS, 68,844,547 bytes of standard Racer/lab output, 461,652,566,016 bytes free at check time. Exact output retained in `output/checks.log`. Existing `.gitignore` edits remain untouched. The new plan, archive and planning record remain documentation changes only.

Jev completion review (`output/jev-gate.json`) verified both document claims at confidence 1.00; correctness confidence 0.91 and spec-match confidence 0.94. Its advisory gate escalated on blast-radius confidence 0.00 (`safe_to_apply=0.79`, composite 0.915). Independent reasoning review found no blocking documentary issue: new scope is proposed, historical approval preserved, baseline numbers supported, and donor evidence kept distinct from authored design. No retry was used to seek a different Jev verdict.

The archive was placed under `findings/plans/` after discovering that the existing `references/.gitignore` excludes a new archive under `references/`. No ignore rules or staging were changed. Final local-link and hub checks were repeated after the path adjustment; see `output/checks-final.log`.
