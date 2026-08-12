# Evidence Policy

## Core rule

访问状态不等于判断类型。

Access status describes how much of the source could be reached. Judgment type describes how strong a specific statement is. A `FULL` item may still contain weak claims, and an `UNAVAILABLE` item may still support limited project-level observations such as “we could not verify this source directly.”

## Access statuses

Allowed terminal access statuses:

- `FULL`: the original source was directly read or reviewed in sufficient depth
- `PARTIAL`: only part of the original source was directly accessible
- `ALTERNATE`: a credible substitute source was used because the original was blocked, broken, or unavailable in practice
- `SUMMARY_ONLY`: only summary-layer information was available
- `UNAVAILABLE`: no usable source could be obtained

Discovery state may temporarily use `access_status: null`, but terminal research may not.

## Judgment labels

Every evidence statement uses one of four judgment labels:

- **已证实**: the statement is directly supported by accessible source evidence
- **作者观点**: the statement is the author’s stated interpretation, normative claim, or perspective
- **项目推断**: the statement is an inference made by this project from available evidence
- **待验证**: the statement is plausible or contextually important, but could not yet be confirmed

Recommended machine labels:

- `confirmed` → **已证实**
- `author-view` → **作者观点**
- `project-inference` → **项目推断**
- `to-verify` → **待验证**

## Fallback order

Use the most direct source first, then degrade conservatively:

1. Original source in full context
2. Original source with partial access
3. Credible alternate primary source
4. Summary-level source with explicit uncertainty
5. No usable source; mark unavailable

Do not skip to a lower tier when a higher tier is reasonably accessible.

## Alternate-source requirements

`ALTERNATE` is allowed only when the original item is materially inaccessible in the current run and the substitute preserves the core claims better than a summary would.

An alternate source must:

- be cited with its own URL
- preserve authorship or primary-source proximity where possible
- be clearly labeled as alternate rather than original
- not silently upgrade uncertainty

Mirror blogs, scraped reposts, and context-stripped quote dumps are weak alternates and should default to `SUMMARY_ONLY` or `UNAVAILABLE` unless there is a strong reason otherwise.

## Coverage accounting

The first-release coverage formula is:

`(FULL + ALTERNATE) / sources_total`

This ratio tracks how many items reached near-complete analytical coverage. `PARTIAL`, `SUMMARY_ONLY`, and `UNAVAILABLE` remain degraded states even if they still yield some reporting value.

## Degradation semantics

- `FULL`: normal analytical confidence, still subject to statement-level judgment labels
- `PARTIAL`: limited confidence on omitted sections; note scope gaps
- `ALTERNATE`: confidence depends on alternate fidelity; mention the substitution
- `SUMMARY_ONLY`: low confidence for nuance, argument structure, and counterarguments
- `UNAVAILABLE`: no content claims beyond the failure condition itself

Degraded access must not be hidden. Reports and downstream synthesis should reflect when a claim depends on partial, alternate, or summary-only review.

## Copyright and quotation

This project publishes original Chinese analysis, not mirrored source text.

- store metadata, links, and short necessary quotations only
- do not archive source全文、完整字幕、整段线程或整本电子书内容
- flag any single quotation over 50 Chinese characters or 25 English words for manual review
- song lyrics remain out of scope for this project

If a quotation is not necessary for analysis, paraphrase instead.
