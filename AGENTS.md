# Repository Instructions

## Required reading

Read `skills/weekly-wisereads/SKILL.md` and every reference it explicitly requires for the active phase.

## Validation

Run `python -m pytest -q` and `python skills/weekly-wisereads/scripts/validate_repository.py --repo-root . --phase release` before claiming completion.

## Publication safety

- Discover the current issue from https://wise.readwise.io/ on every run.
- Treat AI / Agent / Harness / engineering as an optional lens, never a quota.
- Do not publish unless all gates pass.
- Update a new report, `reports/README.md`, and README managed blocks in one commit.
- Never force-push, delete or rename a historical report, rewrite Git history, or create a second state store.
- Correct published content only through a reviewed forward-fix that updates the report and both indexes atomically.

## Shared-file ownership

During parallel development, only the integration owner may edit `README.md`, `reports/README.md`, or an existing report after lane commits are ready.

## Scheduled operations

- The independent Work task only schedules; this repository Skill defines behavior and GitHub stores durable state.
- Keep `skills/weekly-wisereads/references/scheduled-prompt.md` as the only prompt authority.
- Recover public mistakes with reviewed forward-fix commits; never rewrite `main` history.
