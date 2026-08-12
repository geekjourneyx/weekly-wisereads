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
- Never force-push, rewrite a historical report, or create a second state store.

## Shared-file ownership

During parallel development, only the integration owner may edit `README.md`, `reports/README.md`, or an existing report after lane commits are ready.
