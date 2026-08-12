# Inventory Contract

## Purpose

`IssueInventory` is the machine-routed metadata contract between issue discovery and source analysis. It records issue identity, ordered item metadata, selection basis, and access state only. It must not store source全文、长摘录、SourceCard、IssueSynthesis 或其他分析产物。

## Issue identity

An inventory payload uses `schema_version: 1` and contains one `issue` object plus one ordered `items` array.

- `issue.issue_key`: normalized primary key such as `wisereads-vol-155`
- `issue.issue_kind`: `standard` or `special`
- `issue.issue_number`: integer issue number
- `issue.issue_label`: visible label such as `Vol. 155`
- `issue.source_url`: the canonical Wise Reads detail URL
- `issue.discovered_at`: ISO 8601 timestamp with timezone offset
- `issue.detail_page_item_count`: the number of visually independent recommendations on the detail page

`detail_page_item_count` is normative. Synthesis is blocked unless it matches the number of inventory items and the number of terminal SourceCards.

## Item identity and ordering

Every `items[]` entry maps directly to one visually independent recommendation on the issue detail page.

- `item_id` uses the fixed format `item-01`, `item-02`, ...
- `position` starts at `1` and is consecutive with no gaps
- `position` and `item_id` must agree
- `title` stores the item title only
- `creator` stores the author / speaker / channel / issuing creator shown by the source or issue page
- `original_url` must be a unique absolute HTTPS URL for the original recommended item

If item boundaries are ambiguous, duplicated, or visually inconsistent with the detail page, the run fails closed before any synthesis.

## Enumerated fields

### `content_type`

Allowed values are:

- `article`
- `youtube`
- `tweet-thread`
- `pdf`
- `ebook`
- `other`

### `selection_basis`

Allowed values are:

- `highlight-ranked`
- `curated-or-partnered-ebook`
- `page-stated-other`

`ebook` items must use `curated-or-partnered-ebook`. They must never be labeled `highlight-ranked`.

## Access-state lifecycle

`access_status` expresses retrieval coverage, not editorial judgment.

During discovery:

- `access_status` may be `null`
- `alternate_url` must be `null`
- `failure_reason` must be `null`

During or after research completion, every item must be terminal:

- `access_status` must be one of `FULL`, `PARTIAL`, `ALTERNATE`, `SUMMARY_ONLY`, or `UNAVAILABLE`
- `null` is forbidden once discovery is frozen and reading begins

Terminal-state requirements:

- `FULL`: original item was read directly in sufficient detail
- `PARTIAL`: only part of the original item was available or reviewable
- `ALTERNATE`: the original item was not directly usable, but a credible alternate source was used; `alternate_url` is required
- `SUMMARY_ONLY`: only summary-level coverage was available; no alternate full-text substitution was established
- `UNAVAILABLE`: no usable source was obtained; `failure_reason` is required

State-specific invariants:

- `ALTERNATE` requires a non-null `alternate_url`
- non-`ALTERNATE` items should keep `alternate_url: null`
- `UNAVAILABLE` requires a non-null `failure_reason`
- non-`UNAVAILABLE` items should keep `failure_reason: null`

## Fail-closed rules

The inventory is invalid and cannot proceed to synthesis if any of the following occur:

- duplicate `original_url`
- missing or non-consecutive `position`
- `detail_page_item_count != len(items)`
- `ebook` paired with any selection basis other than `curated-or-partnered-ebook`
- an item remains with `access_status: null` after research completion
- ambiguous source boundaries, merged cards, or split cards that cannot be justified from the issue page

## Compact example

```json
{
  "schema_version": 1,
  "issue": {
    "issue_key": "wisereads-vol-155",
    "issue_kind": "standard",
    "issue_number": 155,
    "issue_label": "Vol. 155",
    "source_url": "https://wise.readwise.io/issues/wisereads-vol-155/",
    "discovered_at": "2026-08-12T10:00:00+08:00",
    "detail_page_item_count": 1
  },
  "items": [{
    "item_id": "item-01",
    "position": 1,
    "title": "Example",
    "creator": "Author",
    "original_url": "https://example.com/article",
    "content_type": "article",
    "selection_basis": "highlight-ranked",
    "access_status": "FULL",
    "alternate_url": null,
    "failure_reason": null
  }]
}
```
