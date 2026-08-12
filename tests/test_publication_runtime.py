from __future__ import annotations

from dataclasses import dataclass

from contracts import PublicationPlan
from discovery import discover_latest_issue
from publication_runtime import RefSnapshot, run_atomic_publication


@dataclass
class FakeConnector:
    snapshots: list[RefSnapshot]
    existing_at: set[str] | None = None
    verify_result: bool = True

    def __post_init__(self):
        self.existing_at = self.existing_at or set()
        self.calls = []
        self._index = 0

    def read_main(self):
        snapshot = self.snapshots[self._index]
        self._index += 1
        self.calls.append(("read_main", snapshot.commit_sha))
        return snapshot

    def identity_exists(self, snapshot, issue_key, source_url):
        self.calls.append(("identity_exists", snapshot.commit_sha))
        return snapshot.commit_sha in self.existing_at

    def create_blob(self, path, content):
        self.calls.append(("create_blob", path, content))
        return f"blob:{path}"

    def create_tree(self, base_tree_sha, blobs):
        self.calls.append(("create_tree", base_tree_sha, tuple(sorted(blobs))))
        return "tree:new"

    def create_commit(self, parent_sha, tree_sha):
        self.calls.append(("create_commit", parent_sha, tree_sha))
        return "commit:new"

    def update_main(self, commit_sha, *, force):
        self.calls.append(("update_main", commit_sha, force))

    def verify(self, commit_sha, plan):
        self.calls.append(("verify", commit_sha, plan.issue_key))
        return self.verify_result


def _plan(_base):
    return PublicationPlan(
        issue_key="wisereads-vol-156",
        source_url="https://wise.readwise.io/issues/wisereads-vol-156/",
        files={
            "README.md": "root",
            "reports/README.md": "archive",
            "reports/2026/2026-08-19-vol-156.md": "report",
        },
    )


def test_atomic_publication_updates_ref_once_without_force_and_verifies():
    connector = FakeConnector(
        snapshots=[
            RefSnapshot("main:1", "tree:1"),
            RefSnapshot("main:1", "tree:1"),
        ]
    )

    result = run_atomic_publication(connector, _plan)

    assert result.state == "PUBLISHED"
    assert result.commit_sha == "commit:new"
    assert result.rebuild_count == 0
    assert [call for call in connector.calls if call[0] == "update_main"] == [
        ("update_main", "commit:new", False)
    ]
    assert connector.calls[-1] == ("verify", "commit:new", "wisereads-vol-156")


def test_atomic_publication_returns_noop_after_another_run_publishes_identity():
    connector = FakeConnector(
        snapshots=[
            RefSnapshot("main:1", "tree:1"),
            RefSnapshot("main:2", "tree:2"),
        ],
        existing_at={"main:2"},
    )

    result = run_atomic_publication(connector, _plan)

    assert result.state == "NOOP_AFTER_RACE"
    assert not any(call[0] == "update_main" for call in connector.calls)


def test_atomic_publication_marks_failed_post_commit_read_as_unverified():
    connector = FakeConnector(
        snapshots=[
            RefSnapshot("main:1", "tree:1"),
            RefSnapshot("main:1", "tree:1"),
        ],
        verify_result=False,
    )

    result = run_atomic_publication(connector, _plan)

    assert result.state == "PUBLISHED_UNVERIFIED"
    assert result.failure_code == "FAILED_POST_COMMIT_VERIFY"


def test_discovery_returns_first_homepage_issue_and_classifies_special_edition():
    html = """
    <nav><a href="/issues/wisereads-vol-1/">Old navigation link</a></nav>
    <main>
      <h1>Weekly Wisereads</h1>
      <ul>
        <li><a href="/issues/wisereads-special-vol-2/">Wisereads Special Edition Vol. 2 — Latest</a></li>
        <li><a href="/issues/wisereads-vol-155/">Wisereads Vol. 155 — Earlier</a></li>
      </ul>
    </main>
    """
    detail = "<main><h1>Wisereads Special Edition Vol. 2 — Latest</h1></main>"

    result = discover_latest_issue(html, detail)

    assert result.state == "DISCOVERED"
    assert result.issue is not None
    assert result.issue.issue_key == "wisereads-special-vol-2"
    assert result.issue.issue_kind == "special"
    assert result.issue.issue_number == 2
    assert result.issue.source_url == "https://wise.readwise.io/issues/wisereads-special-vol-2/"


def test_discovery_requires_detail_identity_to_match_first_homepage_card():
    homepage = """
    <h1>Weekly Wisereads</h1><ul>
      <li><a href="/issues/wisereads-vol-155/">Wisereads Vol. 155 — Latest</a></li>
    </ul>
    """

    pending = discover_latest_issue(homepage)
    mismatch = discover_latest_issue(homepage, "<h1>Wisereads Vol. 154 — Wrong detail</h1>")

    assert pending.state == "DETAIL_CONFIRMATION_REQUIRED"
    assert pending.issue is not None
    assert mismatch.state == "BLOCKED_DISCOVERY_IDENTITY"
    assert mismatch.issue is None


def test_atomic_publication_maps_connector_failures_and_rechecks_uncertain_ref_update():
    class ReadFailure(FakeConnector):
        def read_main(self):
            raise RuntimeError("read failed")

    assert run_atomic_publication(ReadFailure([]), _plan).state == "FAILED_GITHUB_READ"

    class WriteFailure(FakeConnector):
        def create_blob(self, path, content):
            raise RuntimeError("write failed")

    write_result = run_atomic_publication(
        WriteFailure([RefSnapshot("main:1", "tree:1")]),
        _plan,
    )
    assert write_result.state == "FAILED_GITHUB_WRITE"

    class UncertainRefMove(FakeConnector):
        def update_main(self, commit_sha, *, force):
            assert force is False
            self.calls.append(("update_main", commit_sha, force))
            raise RuntimeError("timeout after server accepted update")

    accepted = UncertainRefMove(
        [
            RefSnapshot("main:1", "tree:1"),
            RefSnapshot("main:1", "tree:1"),
            RefSnapshot("commit:new", "tree:new"),
        ]
    )
    accepted_result = run_atomic_publication(accepted, _plan)
    assert accepted_result.state == "PUBLISHED"


def test_atomic_publication_maps_plan_errors_and_invalid_file_sets_to_blocked_state():
    connector = FakeConnector([RefSnapshot("main:1", "tree:1")])

    def broken_plan(_base):
        raise ValueError("report validation failed")

    assert run_atomic_publication(connector, broken_plan).state == "BLOCKED_PUBLICATION_PLAN"

    invalid_connector = FakeConnector([RefSnapshot("main:1", "tree:1")])

    def two_file_plan(_base):
        return PublicationPlan(
            issue_key="wisereads-vol-156",
            source_url="https://wise.readwise.io/issues/wisereads-vol-156/",
            files={"README.md": "root", "reports/README.md": "archive"},
        )

    assert run_atomic_publication(invalid_connector, two_file_plan).state == "BLOCKED_PUBLICATION_PLAN"
    assert not any(call[0] == "create_blob" for call in invalid_connector.calls)
