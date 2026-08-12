---
name: weekly-wisereads
description: Use when asked to discover, research, draft, validate, or publish a Chinese deep-reading report for a Weekly Wisereads issue.
---

# Weekly Wisereads

## Overview

Use this skill to turn one Weekly Wisereads issue into a verified Chinese deep-reading report and, when authorized, publish the three-file repository update. The workflow is content-first: discover from the homepage, freeze a complete inventory, finish every item to a terminal access state, then synthesize and publish.

## Required references

Read only the references needed for the current phase, but route every run through these files:

- Positioning and identity: [references/positioning-contract.md](references/positioning-contract.md)
- Issue inventory schema and terminal access states: [references/inventory-contract.md](references/inventory-contract.md)
- SourceCard → IssueSynthesis sequencing: [references/analysis-method.md](references/analysis-method.md)
- Statement labels, degraded access, and quoting limits: [references/evidence-policy.md](references/evidence-policy.md)
- Fixed report structure and per-item fields: [references/report-template.md](references/report-template.md)
- Validator hard stops: [references/quality-gates.md](references/quality-gates.md)
- README / archive managed blocks: [references/readme-update-contract.md](references/readme-update-contract.md)
- Atomic GitHub publication protocol: [references/atomic-publish-protocol.md](references/atomic-publish-protocol.md)
- Scheduled task prompt source: [references/scheduled-prompt.md](references/scheduled-prompt.md)

## Workflow

### 1. Discover from the homepage first

Always open `https://wise.readwise.io/` first. Do not guess the latest issue from memory, README, prior runs, or an old volume number.

From the homepage:

1. identify the newest visible issue or special edition;
2. open its detail page;
3. classify identity (`issue_key`, `issue_kind`, `issue_number`, `issue_label`, `source_url`);
4. stop with no write if the issue page is ambiguous.

Apply the positioning contract before doing anything else:

- Weekly Wisereads is not an AI newsletter identity;
- themes emerge from the actual issue;
- AI / Agent / 工程 is optional;
- popularity never equals quality;
- curated / partnered ebooks are not in the same ranking mechanism as ranked web items.

### 2. Freeze the issue inventory before synthesis

Use [references/inventory-contract.md](references/inventory-contract.md) to build one `IssueInventory`.

Rules:

- one ordered item per visually independent recommendation on the detail page;
- `detail_page_item_count` must equal the item count;
- `item_id` / `position` stay consecutive with no gaps;
- each `original_url` must be unique;
- each item keeps metadata only, not copied source text.

If item boundaries are merged, split, duplicated, or uncertain, stop without synthesis and without repository writes.

### 3. Research every item to a terminal SourceCard

Use [references/analysis-method.md](references/analysis-method.md) and [references/evidence-policy.md](references/evidence-policy.md).

For each inventory item:

1. read the original source if possible;
2. degrade conservatively to `PARTIAL`, `ALTERNATE`, `SUMMARY_ONLY`, or `UNAVAILABLE` only when necessary;
3. produce exactly one terminal SourceCard for that `item_id`;
4. keep statement-level labels separate from access status.

Do not start issue themes early. No cross-source synthesis is allowed before every inventory item has a terminal card.

Hard rules:

- `SUMMARY_ONLY` and `ALTERNATE` never count as fully read originals;
- do not invent AI, startup, or business sections from reader persona;
- the highest-ranked item may still receive a weak quality judgment;
- a weakly evidenced source may still explain the attention signal.

### 4. Synthesize only after the join barrier is complete

Once every item has a terminal card and the card count matches `detail_page_item_count`, build `IssueSynthesis`.

Required synthesis behavior:

- themes must include `supporting_item_ids`;
- bias and absence must be issue-specific, not generic;
- popularity, evidence strength, and editorial quality stay separate;
- AI / Agent / 工程 is optional.

If the issue does not materially support the AI lens, the report must say exactly:

`本期无显著 AI / Agent / 工程信号`

If there is no validated professional opportunity signal, omit it rather than quota-fill.

### 5. Draft the report in the fixed contract

Use [references/report-template.md](references/report-template.md).

The report must:

- keep the exact front matter fields and section order;
- include the AI signal slot in `## 30 秒看懂本期`;
- anchor every item exactly once under `<!-- source-item:item-.. -->`;
- disclose degraded access conservatively;
- keep quotations short and necessary.

Do not hardcode the current volume number into the skill or prompt source.

### 6. Validate before any write

Run the repository validators before publication:

- inventory validation against the frozen issue inventory;
- report validation against the same terminal inventory;
- repository-level validation when available.

If any gate in [references/quality-gates.md](references/quality-gates.md) fails, stop without writes. Report the blocking code and the smallest factual reason; do not “mostly publish”.

### 7. Build the three-file publication plan

Use the publication script and [references/readme-update-contract.md](references/readme-update-contract.md).

Publication planning is pure and returns exactly three target files:

1. the new report under `reports/YYYY/...md`;
2. `reports/README.md`;
3. root `README.md`.

Do not write GitHub during planning. If duplicate `issue_key` or canonical `source_url` already exists, return a no-op result instead of forcing a second copy.

### 8. Publish atomically only when writes are authorized

When the task includes repository publication, follow [references/atomic-publish-protocol.md](references/atomic-publish-protocol.md) exactly.

Rules:

- publish only through the documented GitHub atomic sequence;
- re-read `main` before moving the ref;
- rebuild once if a concurrent update lands first;
- never force-push or rewrite history automatically;
- always verify the committed files after the ref move.

If publication is not requested or not authorized, stop after producing the validated bundle and run summary.

## Output contract

Every full run should return a compact structured summary with:

- `issue_key`
- `source_url`
- `state`
- `report_path` or `null`
- `coverage`
- `ai_signal`
- `degraded_items`
- `quality_gate_findings`
- `published_commit_sha` or `null`
- `notes`

Allowed high-level end states are:

- validated no-op because already processed;
- validated bundle ready for publication;
- published and verified;
- blocked or failed with the exact phase and reason.

## Common mistakes

- treating Weekly Wisereads as an AI identity project;
- deciding themes before all items have terminal cards;
- treating high rank as proof of quality;
- writing a generic “样本有偏差” paragraph without issue-specific skew;
- upgrading `SUMMARY_ONLY`, `ALTERNATE`, or `PARTIAL` into full-read certainty;
- publishing after any validator failure;
- guessing the latest issue without opening the homepage.
