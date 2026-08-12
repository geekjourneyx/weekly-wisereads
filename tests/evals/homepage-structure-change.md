# Deterministic eval — unrecognized homepage structure

The input below is a synthetic local snippet, not a live Weekly Wisereads page. It has
no recognized issue card, visible volume identity, or detail-page link. The truthful
outcome is to stop discovery before creating an inventory or writing a repository file.

```json
{
  "scenario": "homepage-structure-change",
  "network_calls": 0,
  "synthetic_homepage": "<main><section data-layout-v9><button>Explore</button></section></main>",
  "events": [
    "homepage_opened",
    "structure_unrecognized",
    "stop_without_write"
  ],
  "state": "BLOCKED_DISCOVERY_STRUCTURE",
  "inventory_created": false,
  "synthetic_tree": "README.md:stable\nreports/README.md:stable\n",
  "tree_digest_before": "1a2e54de691fc427f9a2e0d7199f297882691b4494f97da667eff454d8d79f99",
  "tree_digest_after": "1a2e54de691fc427f9a2e0d7199f297882691b4494f97da667eff454d8d79f99"
}
```

Expected GREEN outcome: `BLOCKED_DISCOVERY_STRUCTURE`, no inferred issue URL, no
inventory, and identical repository tree digests before and after the blocked run.
