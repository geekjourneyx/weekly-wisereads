# Release, Failure and Recovery

## Result states

- `PUBLISHED`: all three planned files committed, `main` moved once and post-commit reads match.
- `NOOP_ALREADY_PROCESSED`: the homepage's latest valid issue has an `issue_key` or canonical `source_url` that already exists before research/publication, so there is no new issue to publish.
- `NOOP_AFTER_RACE`: another run published the same identity after this run began.
- `BLOCKED_*`: discovery, identity, inventory, research, validation, publication-plan or concurrent-update gate stopped before a ref move.
- `FAILED_*`: a GitHub read/write or another execution dependency failed with no verified publication.
- `PUBLISHED_UNVERIFIED`: the ref moved but post-commit verification failed or could not complete; public state may exist and must be inspected before any retry.

The concrete `BLOCKED_*` and `FAILED_*` states are defined in the Skill's [atomic publication protocol](../../skills/weekly-wisereads/references/atomic-publish-protocol.md). Every run returns the issue identity, state, changed files, degraded sources and unresolved risks.

## Concurrency and writes

Publication creates exactly three blobs, one tree and one commit from the observed `main`. If `main` changes before the ref move, perform exactly one rebuild against the new base. A second change returns `BLOCKED_CONCURRENT_UPDATE` with no ref move.

Always use `force=false`; never force-push and never rewrite Git history. Never delete a historical report as rollback. Treat the report plus both indexes as one correction consistency set and submit every resulting content difference in one reviewed commit.

## Recovery matrix

| Condition | Required response |
| --- | --- |
| GitHub permission loss | Return `FAILED_GITHUB_READ` or `FAILED_GITHUB_WRITE`, make no broader access attempt, reconnect the GitHub app, repeat the harmless read check, then rerun. |
| Discovery or detail identity drift | Return the narrow `BLOCKED_*` state, preserve the observed HTML facts in the run summary, update and review the parser/Skill before retrying. |
| Inventory or evidence gate failure | Keep the issue unpublished, correct metadata or access status, and rerun validators. Do not lower the coverage gate. |
| Concurrent update | Allow exactly one rebuild. On a second change, stop; the next scheduled or supervised run starts from fresh `main`. |
| `PUBLISHED_UNVERIFIED` | Re-read `main` and all three paths first. If the commit is present, do not republish; create a reviewed forward-fix only for verified differences. |
| Public factual or evidence error | Submit a correction with primary evidence, verify the report and both derived indexes together, and merge every resulting difference in one reviewed forward-fix commit. |

## Forward-fix procedure

1. Capture the public commit SHA and the exact evidence or gate failure.
2. Reproduce in a clean checkout and add a failing deterministic test when the defect is behavioral.
3. Make the smallest correction without deleting history or weakening unrelated gates.
4. Run the complete test suite, release validator, Skill validator and diff check.
5. For every fix, fetch `origin/main`, create a unique descriptive `fix/...` branch from it, and open a reviewed PR; the new-report publication runtime is not a correction tool and must not be used against an existing path.
6. For an issue correction, edit exactly one existing report, regenerate or update `README.md` and `reports/README.md` when their derived output changes, and validate all three together. The following commands derive the report path from the actual diff, fail unless exactly one existing report changed, and stage the consistency set. Git records only files whose content changed.

   <!-- CORRECTION:STAGE:START -->
   ```bash
   set -euo pipefail
   test -z "$(git diff --cached --name-only)"
   report_path="$(git diff --name-only --diff-filter=M -- ':(glob)reports/[0-9][0-9][0-9][0-9]/*.md')"
   test -n "$report_path"
   test "$(printf '%s\n' "$report_path" | wc -l)" -eq 1
   test -f "$report_path"
   changed_paths="$(git diff --name-only)"
   while IFS= read -r changed_path; do
     case "$changed_path" in
       "$report_path"|README.md|reports/README.md) ;;
       *) exit 1 ;;
     esac
   done <<< "$changed_paths"
   git add -- "$report_path" README.md reports/README.md
   staged_paths="$(git diff --cached --name-only)"
   while IFS= read -r staged_path; do
     case "$staged_path" in
       "$report_path"|README.md|reports/README.md) ;;
       *) exit 1 ;;
     esac
   done <<< "$staged_paths"
   git diff --cached --check
   git diff --cached --name-only
   ```
   <!-- CORRECTION:STAGE:END -->

   Commit the staged consistency set, push the `fix/...` branch, and open a PR through the connected GitHub app or GitHub UI. Never write the correction directly to `main`.
7. Run `python -m pytest -q`, `python skills/weekly-wisereads/scripts/validate_repository.py --repo-root . --phase release`, and the Skill validator before opening the PR.
8. After review and merge, re-read the report and both indexes from `main`, then record the new commit SHA in the Scheduled run.

Recovery is always a forward-fix. History rewrite would destroy the repository's function as durable processing state and is prohibited.
