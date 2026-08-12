from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
import re
from urllib.parse import urljoin, urlparse


HOMEPAGE_URL = "https://wise.readwise.io/"
ISSUE_SLUG_PATTERN = re.compile(r"^wisereads-(?:(special)-)?vol-(\d+)$")
ISSUE_LABEL_PATTERN = re.compile(r"^Wisereads (?:(Special Edition) )?Vol\.\s*(\d+)\b")


@dataclass(frozen=True)
class DiscoveredIssue:
    issue_key: str
    issue_kind: str
    issue_number: int
    issue_label: str
    source_url: str


@dataclass(frozen=True)
class DiscoveryResult:
    state: str
    issue: DiscoveredIssue | None


class _HomepageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._in_h1 = False
        self._h1_text: list[str] = []
        self._awaiting_list = False
        self._in_issue_list = False
        self._in_first_li = False
        self._li_seen = 0
        self._anchor_href: str | None = None
        self._anchor_text: list[str] = []
        self.latest_candidates: list[tuple[str, str]] = []
        self.issue_list_count = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "h1":
            self._in_h1 = True
            self._h1_text = []
        elif tag == "ul" and self._awaiting_list:
            self._awaiting_list = False
            self._in_issue_list = True
            self._li_seen = 0
            self.issue_list_count += 1
        elif tag == "li" and self._in_issue_list:
            self._li_seen += 1
            self._in_first_li = self._li_seen == 1
        elif tag == "a" and self._in_first_li:
            self._anchor_href = dict(attrs).get("href")
            self._anchor_text = []

    def handle_data(self, data: str) -> None:
        if self._in_h1:
            self._h1_text.append(data)
        if self._anchor_href is not None:
            self._anchor_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "h1" and self._in_h1:
            self._in_h1 = False
            heading = " ".join("".join(self._h1_text).split())
            self._awaiting_list = heading == "Weekly Wisereads"
        elif tag == "a" and self._anchor_href is not None:
            label = " ".join("".join(self._anchor_text).split())
            self.latest_candidates.append((self._anchor_href, label))
            self._anchor_href = None
            self._anchor_text = []
        elif tag == "li" and self._in_first_li:
            self._in_first_li = False
        elif tag == "ul" and self._in_issue_list:
            self._in_issue_list = False


class _HeadingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._in_h1 = False
        self._parts: list[str] = []
        self.headings: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "h1":
            self._in_h1 = True
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._in_h1:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "h1" and self._in_h1:
            self.headings.append(" ".join("".join(self._parts).split()))
            self._in_h1 = False


def discover_latest_issue(homepage_html: str, detail_html: str | None = None) -> DiscoveryResult:
    """Resolve the first official homepage issue card and confirm its detail identity."""
    parser = _HomepageParser()
    parser.feed(homepage_html)
    if parser.issue_list_count != 1 or len(parser.latest_candidates) != 1:
        return DiscoveryResult(state="BLOCKED_DISCOVERY_STRUCTURE", issue=None)

    href, link_label = parser.latest_candidates[0]
    source_url = urljoin(HOMEPAGE_URL, href)
    parsed = urlparse(source_url)
    segments = [segment for segment in parsed.path.split("/") if segment]
    if parsed.scheme != "https" or parsed.netloc != "wise.readwise.io" or len(segments) != 2 or segments[0] != "issues":
        return DiscoveryResult(state="BLOCKED_DISCOVERY_IDENTITY", issue=None)

    slug_match = ISSUE_SLUG_PATTERN.fullmatch(segments[1])
    label_match = ISSUE_LABEL_PATTERN.match(link_label)
    if slug_match is None or label_match is None:
        return DiscoveryResult(state="BLOCKED_DISCOVERY_IDENTITY", issue=None)

    slug_special = bool(slug_match.group(1))
    label_special = bool(label_match.group(1))
    slug_number = int(slug_match.group(2))
    label_number = int(label_match.group(2))
    if slug_special != label_special or slug_number != label_number:
        return DiscoveryResult(state="BLOCKED_DISCOVERY_IDENTITY", issue=None)

    issue_kind = "special" if slug_special else "standard"
    issue_label = f"Special Edition Vol. {slug_number}" if slug_special else f"Vol. {slug_number}"
    issue = DiscoveredIssue(
        issue_key=segments[1],
        issue_kind=issue_kind,
        issue_number=slug_number,
        issue_label=issue_label,
        source_url=f"{HOMEPAGE_URL}issues/{segments[1]}/",
    )
    if detail_html is None:
        return DiscoveryResult(state="DETAIL_CONFIRMATION_REQUIRED", issue=issue)

    detail_parser = _HeadingParser()
    detail_parser.feed(detail_html)
    if len(detail_parser.headings) != 1:
        return DiscoveryResult(state="BLOCKED_DISCOVERY_IDENTITY", issue=None)
    detail_match = ISSUE_LABEL_PATTERN.match(detail_parser.headings[0])
    if detail_match is None:
        return DiscoveryResult(state="BLOCKED_DISCOVERY_IDENTITY", issue=None)
    detail_special = bool(detail_match.group(1))
    detail_number = int(detail_match.group(2))
    if detail_special != slug_special or detail_number != slug_number:
        return DiscoveryResult(state="BLOCKED_DISCOVERY_IDENTITY", issue=None)

    return DiscoveryResult(state="DISCOVERED", issue=issue)
