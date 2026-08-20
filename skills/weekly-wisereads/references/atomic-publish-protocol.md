# Atomic publish protocol

## Scope

This protocol is the only allowed write path for scheduled or direct publication into `geekjourneyx/weekly-wisereads`.

Terminal result states:

- `PUBLISHED`
- `NOOP_ALREADY_PROCESSED`
- `NOOP_AFTER_RACE`
- `BLOCKED_CONCURRENT_UPDATE`
- `PUBLISHED_UNVERIFIED`

Phase-specific blocked / failed states:

- `BLOCKED_DISCOVERY`
- `BLOCKED_DISCOVERY_STALE`
- `BLOCKED_IDENTITY`
- `BLOCKED_INVENTORY`
- `BLOCKED_RESEARCH`
- `BLOCKED_VALIDATION`
- `BLOCKED_PUBLICATION_PLAN`
- `FAILED_GITHUB_READ`
- `FAILED_GITHUB_WRITE`
- `FAILED_POST_COMMIT_VERIFY`

## Required permissions

The connector needs only:

- Metadata read
- Contents read/write

Issues, Pull requests, Actions, and Administration are unnecessary for scheduled publication.

## Exact sequence

`scripts/publication_runtime.py` is the executable pure state-machine model for this
sequence. Connector-backed runs must preserve its call order and result semantics;
the fake-connector tests exercise both race branches without live GitHub writes.

1. Read the current `main` ref and capture both the commit SHA and tree SHA.
2. Re-run issue identity classification against that snapshot and the latest homepage-derived issue.
3. If the same `issue_key` or canonical `source_url` is already present, return `NOOP_ALREADY_PROCESSED`.
4. Create exactly three blobs from `PublicationPlan.files`.
5. Create one tree using the current `base_tree_sha`.
6. Create one commit with only the current `main` commit as parent.
7. Re-read `main`.
8. If `main` is unchanged, update `refs/heads/main` with `force=false`.
9. If `main` changed, re-read, reclassify, and rebuild once.
10. If that other run already published the same issue, return `NOOP_AFTER_RACE`.
11. If the branch changes twice, return `BLOCKED_CONCURRENT_UPDATE` without moving the ref.
12. Re-read all three published files and verify `issue_key`, canonical URLs, and the resulting commit SHA.
13. If post-commit verification fails, return `PUBLISHED_UNVERIFIED` and never rewrite history automatically.

## Failure table

| Phase | Condition | Result |
| --- | --- | --- |
| discovery | homepage or detail page cannot establish one issue identity | `BLOCKED_DISCOVERY` |
| discovery freshness | cache age or response date cannot prove a fresh origin read | `BLOCKED_DISCOVERY_STALE` |
| identity | issue slug / number / kind stays ambiguous after re-check | `BLOCKED_IDENTITY` |
| inventory | item boundaries, counts, or URLs violate the inventory contract | `BLOCKED_INVENTORY` |
| research | one or more items never reach terminal status | `BLOCKED_RESEARCH` |
| validation | any hard gate fails | `BLOCKED_VALIDATION` |
| publication planning | three-file plan cannot be built deterministically | `BLOCKED_PUBLICATION_PLAN` |
| GitHub read | current ref, tree, or existing files cannot be read | `FAILED_GITHUB_READ` |
| GitHub write | blob/tree/commit/ref update call fails | `FAILED_GITHUB_WRITE` |
| post-commit verify | committed files do not match the publication plan | `FAILED_POST_COMMIT_VERIFY` |

## Verification checklist

After a successful ref update, confirm:

- the report path exists once;
- root `README.md` latest block points to the new report;
- `reports/README.md` lists the new report in descending order;
- file contents preserve the expected `issue_key` and canonical `source_url`;
- the observed `main` SHA equals the published commit SHA.
