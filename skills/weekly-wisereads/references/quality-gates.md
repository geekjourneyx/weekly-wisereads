# Report Quality Gates

## Hard gates

The report validator fails closed. Any finding below means `STOP_WITHOUT_WRITE`.

- `REPORT_METADATA_INVALID`: front matter is malformed, issue identity mismatches inventory, or the fixed report structure is broken
- `REPORT_METADATA_INVALID`: required level-2 section headings are missing, duplicated, out of order, or only mentioned in prose instead of appearing as real `##` headings
- `REPORT_ITEM_COVERAGE`: source anchors or per-item metadata do not cover the exact terminal inventory
- `REPORT_DUPLICATE_SOURCE`: a source anchor or source URL appears more than once
- `REPORT_STATUS_COUNT_MISMATCH`: per-status counts do not sum correctly or do not match the terminal inventory
- `REPORT_COVERAGE_BELOW_THRESHOLD`: `(FULL + ALTERNATE) / sources_total` is below `0.50`
- `REPORT_AI_ABSENCE`: the AI signal slot is missing, the exact no-AI sentence is missing when required, or it appears when not allowed
- `REPORT_BIAS_SECTION_MISSING`: the issue-specific bias / missing-perspectives section is absent or generic
- `REPORT_SUMMARY_OVERCLAIM`: degraded access is written with more certainty than the evidence policy allows
- `REPORT_THEME_WITHOUT_SUPPORT`: a theme block under `## 本周集体阅读信号` lacks exactly one valid `supporting_item_ids: [item-..]` line
- `REPORT_POPULARITY_EQUALS_QUALITY`: the report implies that highlighter attention or ranking automatically means quality
- `POSITIONING_AI_IDENTITY`: the report describes Weekly Wisereads as an AI identity project
- `POSITIONING_EBOOK_RANKING`: the report claims curated / partnered ebooks were ranked by unique highlighters

## Validation intent

- All report metadata must match the same terminal inventory used for synthesis
- Required level-2 sections count only as exact Markdown headings, exactly once each, in fixed order
- Bias must be structured with explicit sample, medium, geography, missing-voice, and consequence fields
- Every inventory item must appear exactly once under `<!-- source-item:item-.. -->`
- Ranking language must never overclaim quality, truth, or representativeness
- Ebook mechanism language must remain distinct from the ranked issue feed
- Degraded access must stay visible and conservative
