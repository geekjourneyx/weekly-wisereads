# Weekly Wisereads Scheduled Task

## Live configuration

- Task name: `Weekly Wisereads 深度解读`
- Task identifier: private; stored only in the Scheduled task state and intentionally not committed
- Repository: `geekjourneyx/weekly-wisereads`
- Ownership: repository administrators and the private Scheduled task owner
- Execution: standalone independent Work task; no chat-history dependency
- Status: enabled
- Timezone: `Asia/Shanghai`
- DTSTART: `20260817T100000`
- RRULE: `FREQ=WEEKLY;BYDAY=MO;BYHOUR=10;BYMINUTE=0`
- Configuration audited: `2026-08-20` after the discovery-freshness incident repair
- Preflight dry run: `2026-08-12`
- Preflight result: `NOOP_ALREADY_PROCESSED` for `Vol. 155` at `https://wise.readwise.io/issues/wisereads-vol-155/`
- Changed files: none; degraded sources: none; GitHub writes: zero; `main` stayed unchanged
- Unresolved risk: the Automations interface exposes create, update and read-back but no manual run action; exact run timestamps remain in the private Scheduled UI
- First live execution: `2026-08-17T10:00:00+08:00`; it incorrectly no-op'd after reading a stale cached homepage that still exposed Vol. 155, although Vol. 156 had already been published
- Remediation: origin requests now bypass caches, reject stale `Age` / `Date` evidence as `BLOCKED_DISCOVERY_STALE`, confirm the detail identity, and perform deduplication only after `DISCOVERED`

```ical
BEGIN:VEVENT
DTSTART;TZID=Asia/Shanghai:20260817T100000
RRULE:FREQ=WEEKLY;BYDAY=MO;BYHOUR=10;BYMINUTE=0
END:VEVENT
```

## Prompt authority

- Canonical prompt: [`skills/weekly-wisereads/references/scheduled-prompt.md`](../../skills/weekly-wisereads/references/scheduled-prompt.md)
- Normalization: UTF-8 with LF line endings
- SHA-256: `bad1890f045909ffc96be7bde9d4e75b90ee9658f0fde22eae9d4a31ea289b6a`
- Skill: [`skills/weekly-wisereads/SKILL.md`](../../skills/weekly-wisereads/SKILL.md)

The live task prompt was read back after creation and matched the normalized canonical prompt. Any semantic prompt change requires tests, a new checksum, task update, read-back verification and a forward-fix documentation commit.

## Permissions

The task uses public web access plus the connected GitHub app. Scheduled publication needs repository metadata read and contents read/write for this repository only. It does not need Issues, Pull requests, Releases, Discussions, Actions or Administration.

Before activation, the connected GitHub app successfully read `main`, the Skill, Vol.155, root README and the archive. It reported admin/push access. The preflight dry run opened the live homepage first, followed its first issue link, confirmed the detail identity, found the same issue in repository front matter, and stopped without a write. This verifies the production discovery and deduplication path, but it is not represented as a run of the newly created task.

## Verification and ownership

The private task owner reviews the first three Monday runs in Scheduled and records result state, issue label and URL, changed files, degraded sources, unresolved risks, access-status distribution, coverage, reading time, commit SHA and corrections. The task prompt does not contain a fixed volume number and the repository remains the only durable processing state. Private task identifiers, conversation identifiers and exact execution timestamps must never be copied into this public repository.

Operational failures and recovery use [release-and-rollback.md](release-and-rollback.md).
