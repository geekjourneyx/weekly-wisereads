# Report Template

## Purpose

This template defines the only allowed section order, metadata header, source anchor format, and minimum per-item fields for a Weekly Wisereads issue report.

## Front Matter

Every report begins with YAML front matter using the `ReportMeta` fields exactly:

```yaml
title: string
issue_key: string
issue_kind: standard|special
issue_number: integer
issue_label: string
source_url: https://wise.readwise.io/issues/<slug>/
discovered_at: ISO-8601 datetime with timezone
generated_at: ISO-8601 datetime with timezone
language: zh-CN
reading_time_minutes: integer
sources_total: integer
sources_full_read: integer
sources_partial: integer
sources_alternate: integer
sources_summary_only: integer
sources_unavailable: integer
sources_degraded: integer
```

Per-status counts must sum to `sources_total`, must match the terminal inventory, and must keep `(FULL + ALTERNATE) / sources_total >= 0.50`.

## Fixed section order

```markdown
## 30 秒看懂本期
## 本周集体阅读信号
## 本期最值得理解的判断
## 本期最值得反复思考的观点
## 重点文章深拆
## 专业与机会观察（如有）
## 全部条目阅读笔记
## 这份榜单没有告诉我们的
## 本期行动建议
## 来源与证据说明
```

Each required level-2 heading above must appear exactly once. Prose mentions such as `我们会在后面写 ## 本期行动建议` do not satisfy the section contract.

## Summary requirements

- `## 30 秒看懂本期` must include an explicit AI signal slot: `AI / Agent / 工程信号：significant|none`
- If the signal is `none`, the report must include the exact sentence `本期无显著 AI / Agent / 工程信号`
- The exact sentence above must not appear when the signal is `significant`

## Theme entry shape

Each issue theme is defined only inside `## 本周集体阅读信号` and uses one level-3 block per theme:

```markdown
### 主题：证据迁移成本
- supporting_item_ids: [item-01]
- consensus: ...
- conflicts: ...
- uncertainty: ...
```

Every `###` theme block in that section must contain exactly one `supporting_item_ids: [item-..]` line. Prose elsewhere does not satisfy theme support.

## Bias section shape

The section `## 这份榜单没有告诉我们的` is always required and must use the following exact structural fields:

```markdown
- Readwise 用户样本: ...
- 排序边界: ...
- 观察维度: medium, creator, geography
- supporting_item_ids: [item-02]
- 观察到的偏差: ...
- 缺席声音: ...
- 可能后果: ...
```

Bias validation rules:

- `supporting_item_ids` must be a non-empty bracketed list of real inventory item IDs
- `观察维度` must name at least one concrete dimension such as `medium/creator/geography/language/profession/source sample`
- `Readwise 用户样本`、`排序边界`、`观察到的偏差`、`缺席声音`、`可能后果` each need 至少 6 个非标点字符 after normalization
- Generic filler values such as `略/未知/待补充/无/存在偏差` are invalid
- The five prose fields above must not all reuse the same value

## Source item block

Each inventory item appears exactly once inside `## 全部条目阅读笔记`, anchored with the stable comment form:

```markdown
<!-- source-item:item-01 -->
### item-01 Example
- title: ...
- creator: ...
- original_url: ...
- content_type: article|youtube|tweet-thread|pdf|ebook|other
- selection_basis: highlight-ranked|curated-or-partnered-ebook|page-stated-other
- access_status: FULL|PARTIAL|ALTERNATE|SUMMARY_ONLY|UNAVAILABLE
- alternate_url: ...          # required for ALTERNATE; must match the terminal inventory
- conclusion: ...
- key_view: ...
- highlight_reason: ...
- independent_quality_judgment: ...
- actual_themes: ...
- professional_lens: ...      # optional
- long_term_lens: ...         # optional
- degradation_note: ...
```

Item metadata must match the terminal inventory exactly. Degraded items must disclose uncertainty and must not be written as if they were fully read.

## Positioning rules

- Ranking / popularity / unique highlighter attention must stay distinct from quality and evidence strength
- Within any one sentence, if popularity or rank (`排名/高亮/热度/榜首/靠前`) is linked by implication language (`越…越…/说明/意味着/代表/等于/通常也`) to truth, reliability, or value claims (`可靠/真实/正确/质量/最好/最值得/最重要`), the report is invalid
- Only implication-scoped caveats are safe: `不代表`、`不能说明`、`不意味着`、`不等于`、`并非…更真实/更值得`、`未必`、`不必然`、`不能据此`
- A caveat in one clause must not immunize a later positive implication in the same sentence, for example `排名越高并不总是虚假，但通常也越可靠。` is still invalid
- Themes emerge from actual issue content, not a fixed lane quota
- Curated / partnered ebooks are not part of the same unique-highlighter ranking mechanism as articles, videos, tweets / threads, and PDFs
- Degraded access may inform interpretation, but it must never be overclaimed as full verification
