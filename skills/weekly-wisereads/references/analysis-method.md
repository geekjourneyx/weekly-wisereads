# Analysis Method

## Goal

The method is content-first and issue-bounded. It produces one terminal `SourceCard` per inventory item, then one issue-level synthesis derived only from those terminal cards. No cross-document theme, popularity claim, AI lens, or editorial recommendation may be introduced before source-card completion.

## Stage order

1. Freeze the inventory metadata.
2. Read or degrade each item to a terminal access state.
3. Produce exactly one `SourceCard` per item.
4. Only when 全部条目进入终态后, and the number of valid cards equals `detail_page_item_count`, build the issue-level synthesis.

The join barrier is strict: `IssueSynthesis` is invalid if any inventory item lacks a terminal card or still has `access_status: null`.

## SourceCard

Each source is analyzed independently before any cross-source judgment:

```yaml
item_id: item-01
core_claim: string
argument_chain: [string]
evidence:
  - statement: string
    judgment_label: confirmed|author-view|project-inference|to-verify
    source_url: https://example.com
assumptions: [string]
counter_explanations: [string]
highlight_reason:
  text: string
  judgment_label: project-inference
popularity_quality_alignment:
  verdict: aligned|mixed|diverged
  rationale: string
candidate_themes: [string]
professional_lens: [string]
long_term_lens: [string]
editorial_level: must-read|worth-reading|further-reading
report_takeaways: [string]
```

### SourceCard rules

- `item_id` must match one and only one `InventoryItem`
- `core_claim` summarizes what the source is actually arguing, not what the issue is “about”
- `argument_chain` captures the source’s own reasoning steps
- `evidence[]` records statement-level judgments using the evidence-policy labels
- `highlight_reason` explains why the source may have attracted highlights, but remains a project inference rather than a stated fact unless the source itself proves it
- `popularity_quality_alignment` must keep popularity and quality separate; a heavily highlighted source may still be weakly evidenced, and a strong source may still be niche
- `candidate_themes` are provisional tags only; they do not become issue themes until synthesis
- `professional_lens` and `long_term_lens` are optional
- `editorial_level` is per-item, not an issue-wide verdict
- `report_takeaways` are item-scoped takeaways, not cross-source synthesis

## IssueSynthesis

`IssueSynthesis` exists only after every item has a terminal card:

```yaml
themes:
  - label: string
    supporting_item_ids: [item-01]
    consensus: string
    conflicts: [string]
    uncertainty: string
attention_signal: string
quality_vs_popularity_findings: [string]
absent_perspectives:
  - dimension: string
    observed_skew: string
    missing_voice: string
    consequence: string
ai_signal: significant|none
professional_opportunities: []
long_term_views: []
focus_item_ids: [item-01]
```

### IssueSynthesis rules

- every theme must include non-empty `supporting_item_ids`
- themes without `supporting_item_ids` are invalid
- `supporting_item_ids` must reference real inventory items with terminal cards
- `attention_signal` summarizes what the issue as a set suggests about collective reading attention, not universal importance
- `quality_vs_popularity_findings` must explicitly separate highlight popularity from evidence strength and editorial quality
- `absent_perspectives` must capture issue-specific bias, missing voices, and the consequences of that skew for interpretation
- `professional_opportunities` are optional and must emerge from actual material rather than quota-filling
- `long_term_views` are optional and must emerge from actual material rather than generic reflection
- `focus_item_ids` identifies the few most consequential items for the report narrative

## AI lens and absence handling

AI / Agent / 工程 is an optional lens, never a fixed quota.

- If the issue materially supports the lens, set `ai_signal: significant`
- If the issue does not materially support the lens, set `ai_signal: none`
- When `ai_signal: none`, the report must include the exact sentence `本期无显著 AI / Agent / 工程信号`

## Degradation and evidence discipline

- Items in degraded access states still require a terminal `SourceCard`, but the card must reflect uncertainty from the evidence policy
- `IssueSynthesis` must propagate issue-level uncertainty when multiple cards are degraded
- No source text cache, full transcript mirror, or quotation archive may be stored in the repository as part of this method
