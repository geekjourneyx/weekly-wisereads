from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
import json
import re
import secrets
import sys
from typing import Callable, TextIO
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen


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
    failure_reason: str | None = None


@dataclass(frozen=True)
class FetchedPage:
    url: str
    body: str
    http_age_seconds: int | None


class StalePageError(RuntimeError):
    pass


def _cache_busted_url(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qsl(parsed.query, keep_blank_values=True)
    query.append(("_wisereads_fresh", secrets.token_urlsafe(12)))
    return urlunparse(parsed._replace(query=urlencode(query)))


def _same_document(actual_url: str, expected_url: str) -> bool:
    actual = urlparse(actual_url)
    expected = urlparse(expected_url)
    actual_path = actual.path.rstrip("/") or "/"
    expected_path = expected.path.rstrip("/") or "/"
    return (
        actual.scheme.lower() == expected.scheme.lower()
        and actual.netloc.lower() == expected.netloc.lower()
        and actual_path == expected_path
    )


def fetch_fresh_page(
    url: str,
    *,
    max_http_age_seconds: int = 60,
    max_response_clock_skew_seconds: int = 300,
    now: datetime | None = None,
    timeout_seconds: float = 30,
) -> FetchedPage:
    request = Request(
        _cache_busted_url(url),
        headers={
            "Accept": "text/html,application/xhtml+xml",
            "Cache-Control": "no-cache, no-store, max-age=0",
            "Pragma": "no-cache",
            "User-Agent": "weekly-wisereads-discovery/1",
        },
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        body = response.read().decode(response.headers.get_content_charset() or "utf-8")
        response_date_value = response.headers.get("Date")
        if response_date_value is None:
            raise StalePageError("Missing HTTP response Date header")
        try:
            response_date = parsedate_to_datetime(response_date_value)
        except (TypeError, ValueError) as exc:
            raise StalePageError(
                f"Invalid HTTP response Date header: {response_date_value!r}"
            ) from exc
        if response_date.tzinfo is None:
            response_date = response_date.replace(tzinfo=timezone.utc)
        observed_at = now or datetime.now(timezone.utc)
        response_clock_skew = abs((observed_at - response_date).total_seconds())
        if response_clock_skew > max_response_clock_skew_seconds:
            raise StalePageError(
                "HTTP response Date differs from the run clock by "
                f"{int(response_clock_skew)}s, exceeding "
                f"{max_response_clock_skew_seconds}s"
            )
        age_value = response.headers.get("Age")
        try:
            http_age_seconds = int(age_value) if age_value is not None else None
        except ValueError as exc:
            raise StalePageError(f"Invalid HTTP Age header: {age_value!r}") from exc
        if http_age_seconds is not None and http_age_seconds < 0:
            raise StalePageError(f"Invalid HTTP Age header: {age_value!r}")
        if http_age_seconds is not None and http_age_seconds > max_http_age_seconds:
            raise StalePageError(
                f"HTTP Age {http_age_seconds}s exceeds {max_http_age_seconds}s"
            )
        return FetchedPage(
            url=response.geturl(),
            body=body,
            http_age_seconds=http_age_seconds,
        )


def discover_live_issue(
    *,
    fetch_page: Callable[[str], FetchedPage] = fetch_fresh_page,
) -> DiscoveryResult:
    try:
        homepage = fetch_page(HOMEPAGE_URL)
        if not _same_document(homepage.url, HOMEPAGE_URL):
            return DiscoveryResult(
                state="BLOCKED_DISCOVERY_IDENTITY",
                issue=None,
                failure_reason=f"Unexpected homepage final URL: {homepage.url}",
            )
        pending = discover_latest_issue(homepage.body)
        if pending.state != "DETAIL_CONFIRMATION_REQUIRED" or pending.issue is None:
            return pending
        detail = fetch_page(pending.issue.source_url)
        if not _same_document(detail.url, pending.issue.source_url):
            return DiscoveryResult(
                state="BLOCKED_DISCOVERY_IDENTITY",
                issue=None,
                failure_reason=f"Unexpected detail final URL: {detail.url}",
            )
        return discover_latest_issue(homepage.body, detail.body)
    except StalePageError as exc:
        return DiscoveryResult(
            state="BLOCKED_DISCOVERY_STALE",
            issue=None,
            failure_reason=str(exc),
        )
    except (OSError, UnicodeError) as exc:
        return DiscoveryResult(
            state="BLOCKED_DISCOVERY",
            issue=None,
            failure_reason=str(exc),
        )


def main(
    *,
    fetch_page: Callable[[str], FetchedPage] = fetch_fresh_page,
    stdout: TextIO = sys.stdout,
) -> int:
    result = discover_live_issue(fetch_page=fetch_page)
    payload = {
        "state": result.state,
        "issue": asdict(result.issue) if result.issue is not None else None,
        "failure_reason": result.failure_reason,
    }
    json.dump(payload, stdout, ensure_ascii=False, sort_keys=True)
    stdout.write("\n")
    return 0 if result.state == "DISCOVERED" else 2


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


if __name__ == "__main__":
    raise SystemExit(main())
