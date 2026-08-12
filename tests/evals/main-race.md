# Deterministic eval — two consecutive `main` races

This fixture drives the real pure publication state machine through a fake connector; it does not call GitHub. The first observed
change to `main` permits the protocol's single rebuild. A second observed change must
return `BLOCKED_CONCURRENT_UPDATE`; no ref move is attempted.

```json
{
  "scenario": "main-race",
  "network_calls": 0,
  "observed_main_shas": [
    "1111111111111111111111111111111111111111",
    "2222222222222222222222222222222222222222",
    "3333333333333333333333333333333333333333"
  ],
  "actions": [
    "build",
    "rebuild_once",
    "block"
  ],
  "rebuild_count": 1,
  "state": "BLOCKED_CONCURRENT_UPDATE",
  "ref_move_calls": 0,
  "tree_digest_before": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "tree_digest_after": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
}
```

Expected GREEN outcome: exactly one rebuild, then a blocked state with zero ref moves
and no repository-tree change. The fake SHAs make the two races explicit and
reproducible without live GitHub.
