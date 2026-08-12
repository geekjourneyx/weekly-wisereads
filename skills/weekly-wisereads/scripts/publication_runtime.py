from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

from contracts import PublicationPlan


@dataclass(frozen=True)
class RefSnapshot:
    commit_sha: str
    tree_sha: str


@dataclass(frozen=True)
class AtomicPublishResult:
    state: str
    rebuild_count: int
    commit_sha: str | None = None
    failure_code: str | None = None


class AtomicConnector(Protocol):
    def read_main(self) -> RefSnapshot: ...
    def identity_exists(self, snapshot: RefSnapshot, issue_key: str, source_url: str) -> bool: ...
    def create_blob(self, path: str, content: str) -> str: ...
    def create_tree(self, base_tree_sha: str, blobs: dict[str, str]) -> str: ...
    def create_commit(self, parent_sha: str, tree_sha: str) -> str: ...
    def update_main(self, commit_sha: str, *, force: bool) -> None: ...
    def verify(self, commit_sha: str, plan: PublicationPlan) -> bool: ...


def run_atomic_publication(
    connector: AtomicConnector,
    build_plan: Callable[[RefSnapshot], PublicationPlan],
) -> AtomicPublishResult:
    """Execute the one-retry, never-force publication state machine."""
    try:
        base = connector.read_main()
    except Exception:
        return AtomicPublishResult(state="FAILED_GITHUB_READ", rebuild_count=0)

    for attempt in range(2):
        try:
            plan = build_plan(base)
        except Exception:
            return AtomicPublishResult(state="BLOCKED_PUBLICATION_PLAN", rebuild_count=attempt)
        if not plan.files:
            state = "NOOP_ALREADY_PROCESSED" if attempt == 0 else "NOOP_AFTER_RACE"
            return AtomicPublishResult(state=state, rebuild_count=attempt)
        try:
            identity_exists = connector.identity_exists(base, plan.issue_key, plan.source_url)
        except Exception:
            return AtomicPublishResult(state="FAILED_GITHUB_READ", rebuild_count=attempt)
        if identity_exists:
            state = "NOOP_ALREADY_PROCESSED" if attempt == 0 else "NOOP_AFTER_RACE"
            return AtomicPublishResult(state=state, rebuild_count=attempt)
        if len(plan.files) != 3:
            return AtomicPublishResult(state="BLOCKED_PUBLICATION_PLAN", rebuild_count=attempt)

        try:
            blobs = {
                path: connector.create_blob(path, content)
                for path, content in sorted(plan.files.items())
            }
            tree_sha = connector.create_tree(base.tree_sha, blobs)
            commit_sha = connector.create_commit(base.commit_sha, tree_sha)
        except Exception:
            return AtomicPublishResult(state="FAILED_GITHUB_WRITE", rebuild_count=attempt)
        try:
            observed = connector.read_main()
        except Exception:
            return AtomicPublishResult(state="FAILED_GITHUB_READ", rebuild_count=attempt)

        if observed.commit_sha == base.commit_sha:
            try:
                connector.update_main(commit_sha, force=False)
            except Exception:
                try:
                    after_uncertain_write = connector.read_main()
                except Exception:
                    return AtomicPublishResult(state="FAILED_GITHUB_WRITE", rebuild_count=attempt)
                if after_uncertain_write.commit_sha != commit_sha:
                    return AtomicPublishResult(state="FAILED_GITHUB_WRITE", rebuild_count=attempt)
            try:
                verified = connector.verify(commit_sha, plan)
            except Exception:
                verified = False
            if not verified:
                return AtomicPublishResult(
                    state="PUBLISHED_UNVERIFIED",
                    rebuild_count=attempt,
                    commit_sha=commit_sha,
                    failure_code="FAILED_POST_COMMIT_VERIFY",
                )
            return AtomicPublishResult(state="PUBLISHED", rebuild_count=attempt, commit_sha=commit_sha)

        if attempt == 0:
            try:
                already_published = connector.identity_exists(observed, plan.issue_key, plan.source_url)
            except Exception:
                return AtomicPublishResult(state="FAILED_GITHUB_READ", rebuild_count=0)
            if already_published:
                return AtomicPublishResult(state="NOOP_AFTER_RACE", rebuild_count=0)
            base = observed
            continue

        return AtomicPublishResult(state="BLOCKED_CONCURRENT_UPDATE", rebuild_count=1)

    raise AssertionError("unreachable")
