# 2026-11-05-project-setup: establish Racer's project home

- Status: completed (documentation scaffold only).
- Target/build/platform/architecture: Racer, new original game; engine/build/platform/architecture undecided.
- Canonical input path, size, SHA-256: not applicable; no donor input selected or processed.
- Question and expected observation: can Racer be registered as an ignored, independent game repository with a resumable scope? Expect a local Git root, template files, and a passing hub check.
- Tool/provider/version: local Python 3 and Git; no REA or extraction provider used. Actual versions are recorded below after validation.
- Working directory: hub root for registration/checks; `games/racer` for project Git operations.
- Exact setup operations: register `racer` in `projects.json` and `PROJECTS.md`; confirm `git check-ignore games/racer/`; `mkdir -p games/racer`; `git init games/racer`; `git -C games/racer status --short`; copy `templates/project/`, replace README, and add this record.
- Limits before running: setup/checks only, five minutes, text files under 1 MiB, no generated extraction output; no memory-intensive tools invoked.
- Free space before running: `df -h .` reported 458 GiB available. Racer did not exist, so its generated output was zero; lab output measured by the hub checker below.
- Output location: tracked Markdown and Git metadata only; no `output/` created.
- Started/finished: 2026-11-05; setup commands exited 0.

## Observations and evidence

The hub's existing `/games/*/` ignore rule covers `games/racer/` and was verified before creation. `git init games/racer` created a separate repository; its initial status was empty. The README records the requested open world direction, grid milestone, donor research areas, provenance workflow, and resume state.

Validation commands and their results are appended below. No extraction or gameplay behavior has been tested.

## Conclusion and limits

Racer has a project home and a concrete initial milestone. Engine selection, implementation, donor selection, and asset compatibility remain open.

## Retention

Keep the scaffold and this record. No inputs, saved analysis state, captures, or disposable generated output were created.

## Next action

Choose the engine and initialize the driving-grid prototype with a placeholder car.

## Validation results

- Tools: Python 3.15.0; git version 2.56.0.
- Scaffold checks (Python): required template files present, Racer README populated, independent Git root, hub ignore rule, unique registry ID; PASS. An initial placeholder check incorrectly rejected the documented `experiments/<id>/` naming convention; corrected the check and reran successfully.
- `git -C games/racer diff --check`: exit 0; initial files are untracked.
- `python3 tools/check.py` from the hub: exit 0, PASS; Racer and total managed lab experiment output both 0 bytes; 491,520,000,000 bytes free.
