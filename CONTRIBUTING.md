# Contributing

Weekly Wisereads accepts evidence-first improvements that make the archive more accurate, more transparent, or easier to maintain.

## Good contributions

- fact corrections
- first-party sources
- method improvements
- Skill/template fixes
- counter-material

## Out of scope

- copied source text
- promotion
- unsourced claims
- unread batch AI reports

## Review standard

disagreement alone is not grounds to remove a source. evidence quality is reviewed independently from popularity.

## Before opening a pull request

Run:

- `python -m pytest -q`
- `python skills/weekly-wisereads/scripts/validate_repository.py --repo-root . --phase release`

## Correction requests

If a published sentence is wrong, open the correction issue form with the report path, disputed sentence, proposed correction, first-party source, and copyright confirmation.
