# Deterministic eval — paywall and dead link

This fixture models three locally supplied source outcomes; it performs no retrieval. A
paywall fragment stays `PARTIAL`, a publisher card stays `SUMMARY_ONLY`, and a dead
link stays `UNAVAILABLE`. Each outcome has a visible degradation note and supports
only the narrow claim listed below. None may be upgraded to `FULL`.

```json
{
  "scenario": "paywall-and-dead-link",
  "network_calls": 0,
  "synthetic_tree": "README.md:stable\nreports/README.md:stable\n",
  "tree_digest_before": "1a2e54de691fc427f9a2e0d7199f297882691b4494f97da667eff454d8d79f99",
  "tree_digest_after": "1a2e54de691fc427f9a2e0d7199f297882691b4494f97da667eff454d8d79f99",
  "source_cards": [
    {
      "item_id": "item-01",
      "access_status": "PARTIAL",
      "degradation_note": "Only the first two sections were present in the local paywall fixture.",
      "allowed_claim": "只能复述可见段落中的作者观点；后续论证与反例均待验证。",
      "forbidden_claim": "已完整验证全文论证链。"
    },
    {
      "item_id": "item-02",
      "access_status": "SUMMARY_ONLY",
      "degradation_note": "Only a short publisher summary was supplied; no full text or primary alternate exists.",
      "allowed_claim": "只能低置信度说明公开摘要列出的主题。",
      "forbidden_claim": "作者通过完整证据证明了摘要中的主张。"
    },
    {
      "item_id": "item-03",
      "access_status": "UNAVAILABLE",
      "degradation_note": "The synthetic original URL resolves to the fixture's dead-link outcome and no usable source is supplied.",
      "allowed_claim": "只能确认原始链接在本次评估中不可用。",
      "forbidden_claim": "该文完整论证了某个观点。"
    }
  ]
}
```

Expected GREEN outcome: three terminal SourceCards, explicit uncertainty, no source
content invented for the unavailable item, and identical before/after tree digests.
