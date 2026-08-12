from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
import re
from typing import Literal, Mapping
from urllib.parse import urlparse

import yaml


AI_IDENTITY_PATTERNS = (
    r"面向中文\s*AI\s*Builder.*(?:AI\s*周报|独立开源项目)",
    r"Weekly Wisereads\s*(?:is|是).*(?:AI newsletter|AI 周报)",
)
AI_IDENTITY_NEGATION_PATTERNS = (
    r"\bnot an?\s+AI newsletter\b",
    r"不是.{0,8}AI\s*周报",
    r"并非.{0,8}AI\s*周报",
)

EBOOK_RANKING_PATTERNS = (
    r"(?:文章|articles).*(?:电子书|ebooks).*(?:独立高亮|unique highlighters).*(?:排名|ranked)",
    r"(?:电子书|ebooks).*(?:按|by).*(?:独立高亮|unique highlighters).*(?:排名|rank)",
)

INVENTORY_CONTENT_TYPES = {
    "article",
    "youtube",
    "tweet-thread",
    "pdf",
    "ebook",
    "other",
}
INVENTORY_SELECTION_BASES = {
    "highlight-ranked",
    "curated-or-partnered-ebook",
    "page-stated-other",
}
INVENTORY_ACCESS_STATUSES = {
    "FULL",
    "PARTIAL",
    "ALTERNATE",
    "SUMMARY_ONLY",
    "UNAVAILABLE",
}
REPORT_CODES = frozenset(
    {
        "REPORT_METADATA_INVALID",
        "REPORT_ITEM_COVERAGE",
        "REPORT_DUPLICATE_SOURCE",
        "REPORT_STATUS_COUNT_MISMATCH",
        "REPORT_COVERAGE_BELOW_THRESHOLD",
        "REPORT_AI_ABSENCE",
        "REPORT_BIAS_SECTION_MISSING",
        "REPORT_SUMMARY_OVERCLAIM",
        "REPORT_THEME_WITHOUT_SUPPORT",
        "REPORT_POPULARITY_EQUALS_QUALITY",
    }
)
REPORT_REQUIRED_SECTIONS = (
    "## 30 秒看懂本期",
    "## 本周集体阅读信号",
    "## 本期最值得理解的判断",
    "## 本期最值得反复思考的观点",
    "## 重点文章深拆",
    "## 专业与机会观察（如有）",
    "## 全部条目阅读笔记",
    "## 这份榜单没有告诉我们的",
    "## 本期行动建议",
    "## 来源与证据说明",
)
REPORT_REQUIRED_ENTRY_FIELDS = {
    "title",
    "creator",
    "original_url",
    "content_type",
    "selection_basis",
    "access_status",
    "conclusion",
    "key_view",
    "highlight_reason",
    "independent_quality_judgment",
    "actual_themes",
    "degradation_note",
}
REPORT_REQUIRED_BIAS_FIELDS = (
    "Readwise 用户样本",
    "排序边界",
    "观察维度",
    "supporting_item_ids",
    "观察到的偏差",
    "缺席声音",
    "可能后果",
)
REPORT_BIAS_PROSE_FIELDS = (
    "Readwise 用户样本",
    "排序边界",
    "观察到的偏差",
    "缺席声音",
    "可能后果",
)
REPORT_BIAS_MIN_SUBSTANTIVE_CHARS = 6
REPORT_BIAS_FILLER_VALUES = {
    "略",
    "未知",
    "待补充",
    "无",
    "存在偏差",
}
REPORT_BIAS_DIMENSION_TOKENS = (
    "medium",
    "媒介",
    "creator",
    "创作者",
    "作者",
    "geography",
    "地域",
    "地理",
    "language",
    "语言",
    "profession",
    "职业",
    "专业",
    "sourcesample",
    "source sample",
    "样本",
)
REPORT_AI_NONE_SENTENCE = "本期无显著 AI / Agent / 工程信号"
REPORT_AI_SIGNAL_PATTERN = re.compile(r"AI\s*/\s*Agent\s*/\s*工程信号：\s*(significant|none)")
REPORT_LEVEL2_HEADING_PATTERN = re.compile(r"(?m)^## [^\n]+$")
REPORT_LEVEL3_HEADING_PATTERN = re.compile(r"(?m)^### [^\n]+$")
REPORT_SOURCE_ANCHOR_PATTERN = re.compile(r"<!--\s*source-item:(item-\d{2})\s*-->")
REPORT_THEME_SUPPORT_LINE_PATTERN = re.compile(r"(?m)^- supporting_item_ids: \[(.*?)\]$")
REPORT_ENTRY_VALUE_PATTERN = re.compile(r"(?m)^- ([a-z_]+):\s*(.+)$")
REPORT_GENERIC_FIELD_PATTERN = re.compile(r"(?m)^- ([^:\n]+):\s*(.+)$")
REPORT_POPULARITY_TOKENS = ("排名", "高亮", "热度", "榜首", "靠前")
REPORT_IMPLICATION_TOKENS = ("说明", "意味着", "代表", "等于", "通常也", "往往", "会觉得")
REPORT_POSITIVE_QUALITY_TOKENS = ("可靠", "真实", "正确", "质量", "最好", "最值得", "最重要")
REPORT_POPULARITY_SCOPED_CAVEAT_PATTERNS = (
    r"不代表",
    r"不能说明",
    r"不意味着",
    r"不等于",
    r"不.*等于",
    r"并非.*(?:越可靠|质量更高|更真实|更值得|最值得|最真实|最好|最重要|越正确)",
    r"未必",
    r"不必然",
    r"不能据此",
)
REPORT_DEGRADED_OVERCLAIM_PATTERNS = (
    r"(?:已|已经|可视为).{0,8}完整阅读",
    r"(?:已|已经|可视为).{0,8}(?:完整读过|全文已读|完整观看)",
    r"完整论证链已验证",
    r"已直接验证完整内容",
)


@dataclass(frozen=True)
class Finding:
    code: str
    path: str
    message: str


@dataclass(frozen=True)
class ReportMeta:
    title: str
    issue_key: str
    issue_kind: Literal["standard", "special"]
    issue_number: int
    issue_label: str
    source_url: str
    discovered_at: datetime
    generated_at: datetime
    language: Literal["zh-CN"]
    reading_time_minutes: int
    sources_total: int
    sources_full_read: int
    sources_partial: int
    sources_alternate: int
    sources_summary_only: int
    sources_unavailable: int
    sources_degraded: int


@dataclass(frozen=True)
class InventoryItem:
    item_id: str
    position: int
    title: str
    creator: str
    original_url: str
    content_type: Literal["article", "youtube", "tweet-thread", "pdf", "ebook", "other"]
    selection_basis: Literal["highlight-ranked", "curated-or-partnered-ebook", "page-stated-other"]
    access_status: Literal["FULL", "PARTIAL", "ALTERNATE", "SUMMARY_ONLY", "UNAVAILABLE"] | None
    alternate_url: str | None
    failure_reason: str | None


@dataclass(frozen=True)
class IssueInventory:
    issue_key: str
    issue_kind: Literal["standard", "special"]
    issue_number: int
    issue_label: str
    source_url: str
    discovered_at: datetime
    detail_page_item_count: int
    items: tuple[InventoryItem, ...]


@dataclass(frozen=True)
class ReportEntry:
    path: str
    meta: ReportMeta


@dataclass(frozen=True)
class PublicationPlan:
    issue_key: str
    source_url: str
    files: Mapping[str, str]


def parse_front_matter(text: str, path: str) -> tuple[ReportMeta, str]:
    if not text.startswith("---\n"):
        raise ValueError(f"{path}: missing front matter")

    try:
        _, raw_meta, body = text.split("---\n", 2)
    except ValueError as exc:
        raise ValueError(f"{path}: malformed front matter delimiters") from exc

    try:
        payload = yaml.safe_load(raw_meta)
    except yaml.YAMLError as exc:
        raise ValueError(f"{path}: malformed YAML front matter") from exc

    if not isinstance(payload, dict):
        raise ValueError(f"{path}: front matter must be a mapping")

    return _parse_report_meta(payload, path), body


def validate_positioning(text: str, path: str) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[tuple[str, str]] = set()

    for pattern in AI_IDENTITY_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match and not _is_negated_ai_identity(match.group(0)):
            _append_finding(
                findings,
                seen,
                Finding(
                    code="POSITIONING_AI_IDENTITY",
                    path=path,
                    message="Weekly Wisereads must not be described as an AI newsletter or AI-branded project.",
                ),
            )

    for pattern in EBOOK_RANKING_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            _append_finding(
                findings,
                seen,
                Finding(
                    code="POSITIONING_EBOOK_RANKING",
                    path=path,
                    message="Curated or partnered ebooks must not be described as ranked by unique highlighters.",
                ),
            )

    return findings


def parse_inventory(text: str, path: str) -> IssueInventory:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: malformed JSON") from exc

    if not isinstance(payload, dict):
        raise ValueError(f"{path}: inventory must be a mapping")

    schema_version = payload.get("schema_version")
    if schema_version != 1 or isinstance(schema_version, bool):
        raise ValueError(f"{path}: schema_version must be exactly 1")

    issue_payload = _require_mapping(payload, "issue", path)
    items_payload = _require_list(payload, "items", path)
    source_url = _require_source_url(issue_payload, path)

    items: list[InventoryItem] = []
    for index, item_payload in enumerate(items_payload):
        item_path = f"{path}: items[{index}]"
        if not isinstance(item_payload, dict):
            raise ValueError(f"{item_path} must be a mapping")
        items.append(
            InventoryItem(
                item_id=_require_str(item_payload, "item_id", item_path),
                position=_require_int(item_payload, "position", item_path),
                title=_require_str(item_payload, "title", item_path),
                creator=_require_str(item_payload, "creator", item_path),
                original_url=_require_https_url(item_payload, "original_url", item_path),
                content_type=_require_literal(item_payload, "content_type", INVENTORY_CONTENT_TYPES, item_path),
                selection_basis=_require_literal(
                    item_payload,
                    "selection_basis",
                    INVENTORY_SELECTION_BASES,
                    item_path,
                ),
                access_status=_require_optional_literal(
                    item_payload,
                    "access_status",
                    INVENTORY_ACCESS_STATUSES,
                    item_path,
                ),
                alternate_url=_require_optional_https_url(item_payload, "alternate_url", item_path),
                failure_reason=_require_optional_str(item_payload, "failure_reason", item_path),
            )
        )

    return IssueInventory(
        issue_key=_require_str(issue_payload, "issue_key", path),
        issue_kind=_require_literal(issue_payload, "issue_kind", {"standard", "special"}, path),
        issue_number=_require_int(issue_payload, "issue_number", path),
        issue_label=_require_str(issue_payload, "issue_label", path),
        source_url=source_url,
        discovered_at=_require_datetime(issue_payload, "discovered_at", path),
        detail_page_item_count=_require_int(issue_payload, "detail_page_item_count", path),
        items=tuple(items),
    )


def validate_inventory(inventory: IssueInventory, path: str, require_terminal: bool) -> list[Finding]:
    findings: list[Finding] = []
    seen_finding_keys: set[tuple[str, str]] = set()
    seen_urls: set[str] = set()

    if len(inventory.items) != inventory.detail_page_item_count:
        _append_finding(
            findings,
            seen_finding_keys,
            Finding(
                code="INVENTORY_COUNT_MISMATCH",
                path=path,
                message=(
                    f"detail_page_item_count is {inventory.detail_page_item_count}, "
                    f"but items contains {len(inventory.items)} entries."
                ),
            ),
        )

    for expected_position, item in enumerate(inventory.items, start=1):
        expected_item_id = f"item-{expected_position:02d}"
        if item.position != expected_position or item.item_id != expected_item_id:
            _append_finding(
                findings,
                seen_finding_keys,
                Finding(
                    code="INVENTORY_POSITION_GAP",
                    path=path,
                    message=(
                        f"Expected {expected_item_id} at position {expected_position}, "
                        f"found {item.item_id} at position {item.position}."
                    ),
                ),
            )

        for url in (item.original_url, item.alternate_url):
            if url is None:
                continue
            if url in seen_urls:
                _append_finding(
                    findings,
                    seen_finding_keys,
                    Finding(
                        code="INVENTORY_DUPLICATE_URL",
                        path=path,
                        message=f"Duplicate URL detected: {url}",
                    ),
                )
            else:
                seen_urls.add(url)

        if item.content_type == "ebook" and item.selection_basis != "curated-or-partnered-ebook":
            _append_finding(
                findings,
                seen_finding_keys,
                Finding(
                    code="INVENTORY_EBOOK_SELECTION",
                    path=path,
                    message="Ebook items must use selection_basis 'curated-or-partnered-ebook'.",
                ),
            )

        if item.access_status == "ALTERNATE" and item.alternate_url is None:
            _append_finding(
                findings,
                seen_finding_keys,
                Finding(
                    code="INVENTORY_ALTERNATE_URL_REQUIRED",
                    path=path,
                    message=f"{item.item_id} requires alternate_url when access_status is ALTERNATE.",
                ),
            )

        if item.access_status == "UNAVAILABLE" and item.failure_reason is None:
            _append_finding(
                findings,
                seen_finding_keys,
                Finding(
                    code="INVENTORY_FAILURE_REASON_REQUIRED",
                    path=path,
                    message=f"{item.item_id} requires failure_reason when access_status is UNAVAILABLE.",
                ),
            )

        if require_terminal and item.access_status is None:
            _append_finding(
                findings,
                seen_finding_keys,
                Finding(
                    code="INVENTORY_NON_TERMINAL_STATUS",
                    path=path,
                    message=f"{item.item_id} must use a terminal access_status.",
                ),
            )

    return sorted(findings, key=lambda finding: (finding.path, finding.code, finding.message))


def validate_report(text: str, path: str, inventory: IssueInventory) -> list[Finding]:
    findings: list[Finding] = []
    seen_finding_keys: set[tuple[str, str]] = set()

    try:
        meta, body = parse_front_matter(text, path)
    except ValueError as exc:
        _append_finding(
            findings,
            seen_finding_keys,
            _report_finding("REPORT_METADATA_INVALID", path, str(exc)),
        )
        return findings

    for finding in validate_positioning(text, path):
        _append_finding(findings, seen_finding_keys, finding)

    sections = _parse_level2_sections(body)
    _validate_report_metadata(meta, inventory, path, findings, seen_finding_keys)
    _validate_report_sections(sections, path, findings, seen_finding_keys)
    _validate_report_ai_section(sections, path, findings, seen_finding_keys)
    _validate_report_theme_support(sections, inventory, path, findings, seen_finding_keys)
    _validate_report_bias_section(sections, inventory, path, findings, seen_finding_keys)
    _validate_report_item_entries(sections, inventory, path, findings, seen_finding_keys)
    _validate_report_quality_language(text, path, findings, seen_finding_keys)

    return sorted(findings, key=lambda finding: (finding.path, finding.code, finding.message))


def replace_managed_block(document: str, block: str, replacement: str) -> str:
    raise NotImplementedError


def discover_reports(repo_root) -> list[ReportEntry]:
    raise NotImplementedError


def build_publication_plan(repo_root, report_path: str, report_text: str) -> PublicationPlan:
    raise NotImplementedError


def validate_repository(repo_root) -> list[Finding]:
    raise NotImplementedError


def _parse_report_meta(payload: dict[str, object], path: str) -> ReportMeta:
    issue_kind = _require_literal(payload, "issue_kind", {"standard", "special"}, path)
    language = _require_literal(payload, "language", {"zh-CN"}, path)
    source_url = _require_source_url(payload, path)

    return ReportMeta(
        title=_require_str(payload, "title", path),
        issue_key=_require_str(payload, "issue_key", path),
        issue_kind=issue_kind,
        issue_number=_require_int(payload, "issue_number", path),
        issue_label=_require_str(payload, "issue_label", path),
        source_url=source_url,
        discovered_at=_require_datetime(payload, "discovered_at", path),
        generated_at=_require_datetime(payload, "generated_at", path),
        language=language,
        reading_time_minutes=_require_int(payload, "reading_time_minutes", path),
        sources_total=_require_int(payload, "sources_total", path),
        sources_full_read=_require_int(payload, "sources_full_read", path),
        sources_partial=_require_int(payload, "sources_partial", path),
        sources_alternate=_require_int(payload, "sources_alternate", path),
        sources_summary_only=_require_int(payload, "sources_summary_only", path),
        sources_unavailable=_require_int(payload, "sources_unavailable", path),
        sources_degraded=_require_int(payload, "sources_degraded", path),
    )


def _require_str(payload: dict[str, object], key: str, path: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{path}: {key} must be a non-empty string")
    return value


def _require_int(payload: dict[str, object], key: str, path: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{path}: {key} must be an integer")
    return value


def _require_literal(
    payload: dict[str, object],
    key: str,
    allowed: set[str],
    path: str,
):
    value = _require_str(payload, key, path)
    if value not in allowed:
        allowed_values = ", ".join(sorted(allowed))
        raise ValueError(f"{path}: {key} must be one of {allowed_values}")
    return value


def _require_datetime(payload: dict[str, object], key: str, path: str) -> datetime:
    value = _require_str(payload, key, path)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{path}: {key} must be an ISO 8601 timestamp") from exc

    if parsed.tzinfo is None:
        raise ValueError(f"{path}: {key} must include a timezone offset")
    return parsed


def _require_mapping(payload: dict[str, object], key: str, path: str) -> dict[str, object]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: {key} must be a mapping")
    return value


def _require_list(payload: dict[str, object], key: str, path: str) -> list[object]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ValueError(f"{path}: {key} must be a list")
    return value


def _require_optional_literal(
    payload: dict[str, object],
    key: str,
    allowed: set[str],
    path: str,
):
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or value not in allowed:
        allowed_values = ", ".join(sorted(allowed))
        raise ValueError(f"{path}: {key} must be one of {allowed_values} or null")
    return value


def _require_optional_str(payload: dict[str, object], key: str, path: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(f"{path}: {key} must be a non-empty string or null")
    return value


def _require_https_url(payload: dict[str, object], key: str, path: str) -> str:
    value = _require_str(payload, key, path)
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"{path}: {key} must be an absolute HTTPS URL")
    return value


def _require_optional_https_url(payload: dict[str, object], key: str, path: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(f"{path}: {key} must be an absolute HTTPS URL or null")
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"{path}: {key} must be an absolute HTTPS URL or null")
    return value


def _require_source_url(payload: dict[str, object], path: str) -> str:
    value = _require_str(payload, "source_url", path)
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.netloc != "wise.readwise.io":
        raise ValueError(f"{path}: source_url must use https://wise.readwise.io/")
    issue_path = parsed.path.removeprefix("/issues/")
    issue_segments = issue_path.split("/")
    if (
        not parsed.path.startswith("/issues/")
        or not issue_segments[0]
        or len(issue_segments) not in {1, 2}
        or any(segment for segment in issue_segments[1:] if segment)
    ):
        raise ValueError(f"{path}: source_url must be a Wisereads issue detail URL under /issues/")
    return value


def _append_finding(findings: list[Finding], seen: set[tuple[str, str]], finding: Finding) -> None:
    key = (finding.code, finding.path)
    if key in seen:
        return
    seen.add(key)
    findings.append(finding)


def _is_negated_ai_identity(matched_text: str) -> bool:
    return any(re.search(pattern, matched_text, flags=re.IGNORECASE) for pattern in AI_IDENTITY_NEGATION_PATTERNS)


def _report_finding(code: str, path: str, message: str) -> Finding:
    if code not in REPORT_CODES:
        raise ValueError(f"Unknown report finding code: {code}")
    return Finding(code=code, path=path, message=message)


def _validate_report_metadata(
    meta: ReportMeta,
    inventory: IssueInventory,
    path: str,
    findings: list[Finding],
    seen: set[tuple[str, str]],
) -> None:
    mismatches: list[str] = []
    if meta.issue_key != inventory.issue_key:
        mismatches.append("issue_key")
    if meta.issue_kind != inventory.issue_kind:
        mismatches.append("issue_kind")
    if meta.issue_number != inventory.issue_number:
        mismatches.append("issue_number")
    if meta.issue_label != inventory.issue_label:
        mismatches.append("issue_label")
    if meta.source_url != inventory.source_url:
        mismatches.append("source_url")
    if meta.discovered_at != inventory.discovered_at:
        mismatches.append("discovered_at")

    if mismatches:
        _append_finding(
            findings,
            seen,
            _report_finding(
                "REPORT_METADATA_INVALID",
                path,
                f"Report metadata does not match inventory for: {', '.join(mismatches)}.",
            ),
        )

    if not 15 <= meta.reading_time_minutes <= 20:
        _append_finding(
            findings,
            seen,
            _report_finding(
                "REPORT_METADATA_INVALID",
                path,
                "reading_time_minutes must be between 15 and 20 inclusive.",
            ),
        )

    inventory_counts = _inventory_status_counts(inventory)
    report_counts = {
        "sources_total": meta.sources_total,
        "sources_full_read": meta.sources_full_read,
        "sources_partial": meta.sources_partial,
        "sources_alternate": meta.sources_alternate,
        "sources_summary_only": meta.sources_summary_only,
        "sources_unavailable": meta.sources_unavailable,
        "sources_degraded": meta.sources_degraded,
    }
    expected_counts = {
        "sources_total": len(inventory.items),
        "sources_full_read": inventory_counts["FULL"],
        "sources_partial": inventory_counts["PARTIAL"],
        "sources_alternate": inventory_counts["ALTERNATE"],
        "sources_summary_only": inventory_counts["SUMMARY_ONLY"],
        "sources_unavailable": inventory_counts["UNAVAILABLE"],
        "sources_degraded": (
            inventory_counts["PARTIAL"]
            + inventory_counts["ALTERNATE"]
            + inventory_counts["SUMMARY_ONLY"]
            + inventory_counts["UNAVAILABLE"]
        ),
    }
    if (
        meta.sources_full_read
        + meta.sources_partial
        + meta.sources_alternate
        + meta.sources_summary_only
        + meta.sources_unavailable
        != meta.sources_total
        or report_counts != expected_counts
    ):
        _append_finding(
            findings,
            seen,
            _report_finding(
                "REPORT_STATUS_COUNT_MISMATCH",
                path,
                (
                    "Report status counts must sum to sources_total and match the terminal inventory. "
                    f"Expected {expected_counts}, found {report_counts}."
                ),
            ),
        )

    if meta.sources_total == 0 or (meta.sources_full_read + meta.sources_alternate) / meta.sources_total < 0.5:
        _append_finding(
            findings,
            seen,
            _report_finding(
                "REPORT_COVERAGE_BELOW_THRESHOLD",
                path,
                "(FULL + ALTERNATE) / sources_total must be at least 0.50.",
            ),
        )


def _inventory_status_counts(inventory: IssueInventory) -> dict[str, int]:
    counts = {status: 0 for status in INVENTORY_ACCESS_STATUSES}
    for item in inventory.items:
        if item.access_status is not None:
            counts[item.access_status] += 1
    return counts


def _validate_report_sections(
    sections: list[tuple[str, str]],
    path: str,
    findings: list[Finding],
    seen: set[tuple[str, str]],
) -> None:
    headings = [heading for heading, _ in sections]
    for section in REPORT_REQUIRED_SECTIONS:
        if headings.count(section) != 1:
            _append_finding(
                findings,
                seen,
                _report_finding(
                    "REPORT_METADATA_INVALID",
                    path,
                    f"Required section must appear exactly once as a level-2 heading: {section}",
                ),
            )
            return
    required_headings = [heading for heading in headings if heading in REPORT_REQUIRED_SECTIONS]
    if required_headings != list(REPORT_REQUIRED_SECTIONS):
        _append_finding(
            findings,
            seen,
            _report_finding(
                "REPORT_METADATA_INVALID",
                path,
                "Report sections must appear exactly once and in the fixed order defined by the template.",
            ),
        )


def _validate_report_ai_section(
    sections: list[tuple[str, str]],
    path: str,
    findings: list[Finding],
    seen: set[tuple[str, str]],
) -> None:
    summary = _section_content(sections, "## 30 秒看懂本期")
    match = REPORT_AI_SIGNAL_PATTERN.search(summary)
    if not match:
        _append_finding(
            findings,
            seen,
            _report_finding(
                "REPORT_AI_ABSENCE",
                path,
                "30 秒看懂本期 must declare AI / Agent / 工程 signal as significant or none.",
            ),
        )
        return
    signal = match.group(1)
    has_sentence = REPORT_AI_NONE_SENTENCE in summary
    if signal == "none" and not has_sentence:
        _append_finding(
            findings,
            seen,
            _report_finding(
                "REPORT_AI_ABSENCE",
                path,
                f"When AI signal is none, include the exact sentence: {REPORT_AI_NONE_SENTENCE}",
            ),
        )
    if signal != "none" and has_sentence:
        _append_finding(
            findings,
            seen,
            _report_finding(
                "REPORT_AI_ABSENCE",
                path,
                "The exact no-AI sentence may only appear when the AI signal is none.",
            ),
        )


def _validate_report_theme_support(
    sections: list[tuple[str, str]],
    inventory: IssueInventory,
    path: str,
    findings: list[Finding],
    seen: set[tuple[str, str]],
) -> None:
    item_ids = {item.item_id for item in inventory.items}
    signal_section = _section_content(sections, "## 本周集体阅读信号")
    themes = _parse_level3_blocks(signal_section)
    if not themes:
        _append_finding(
            findings,
            seen,
            _report_finding(
                "REPORT_THEME_WITHOUT_SUPPORT",
                path,
                "本周集体阅读信号 must contain one or more level-3 theme entries.",
            ),
        )
        return

    for theme_heading, theme_body in themes:
        support_matches = REPORT_THEME_SUPPORT_LINE_PATTERN.findall(theme_body)
        if len(support_matches) != 1:
            _append_finding(
                findings,
                seen,
                _report_finding(
                    "REPORT_THEME_WITHOUT_SUPPORT",
                    path,
                    f"{theme_heading} must contain exactly one supporting_item_ids field.",
                ),
            )
            return
        raw_ids = support_matches[0]
        supporting_ids = [part.strip() for part in raw_ids.split(",") if part.strip()]
        if not supporting_ids or any(item_id not in item_ids for item_id in supporting_ids):
            _append_finding(
                findings,
                seen,
                _report_finding(
                    "REPORT_THEME_WITHOUT_SUPPORT",
                    path,
                    f"{theme_heading} must reference one or more real inventory item IDs.",
                ),
            )
            return


def _validate_report_bias_section(
    sections: list[tuple[str, str]],
    inventory: IssueInventory,
    path: str,
    findings: list[Finding],
    seen: set[tuple[str, str]],
) -> None:
    bias = _section_content(sections, "## 这份榜单没有告诉我们的")
    if not bias.strip():
        _append_finding(
            findings,
            seen,
            _report_finding(
                "REPORT_BIAS_SECTION_MISSING",
                path,
                "The report must include a non-empty issue-specific bias section.",
            ),
        )
        return

    field_pairs = REPORT_GENERIC_FIELD_PATTERN.findall(bias)
    fields = {key: value.strip() for key, value in field_pairs}
    if (
        len(field_pairs) != len(REPORT_REQUIRED_BIAS_FIELDS)
        or set(fields) != set(REPORT_REQUIRED_BIAS_FIELDS)
        or any(not fields[key].strip() for key in REPORT_REQUIRED_BIAS_FIELDS)
    ):
        _append_finding(
            findings,
            seen,
            _report_finding(
                "REPORT_BIAS_SECTION_MISSING",
                path,
                "The bias section must define the exact structured fields for Readwise 用户样本, 排序边界, 观察维度, supporting_item_ids, 观察到的偏差, 缺席声音, and 可能后果.",
            ),
        )
        return

    supporting_item_ids = _parse_supporting_item_ids(fields["supporting_item_ids"])
    known_item_ids = {item.item_id for item in inventory.items}
    if not supporting_item_ids or any(item_id not in known_item_ids for item_id in supporting_item_ids):
        _append_finding(
            findings,
            seen,
            _report_finding(
                "REPORT_BIAS_SECTION_MISSING",
                path,
                "The bias section must include non-empty supporting_item_ids that reference real inventory items.",
            ),
        )
        return

    if not _bias_dimension_is_concrete(fields["观察维度"]):
        _append_finding(
            findings,
            seen,
            _report_finding(
                "REPORT_BIAS_SECTION_MISSING",
                path,
                "观察维度 must name at least one concrete dimension such as medium, creator, geography, language, profession, or source sample.",
            ),
        )
        return

    normalized_prose_values = [_normalize_report_text(fields[field]) for field in REPORT_BIAS_PROSE_FIELDS]
    if len(set(normalized_prose_values)) == 1:
        _append_finding(
            findings,
            seen,
            _report_finding(
                "REPORT_BIAS_SECTION_MISSING",
                path,
                "The five prose bias fields must not all reuse the same value.",
            ),
        )
        return

    for field in REPORT_BIAS_PROSE_FIELDS:
        normalized = _normalize_report_text(fields[field])
        if len(normalized) < REPORT_BIAS_MIN_SUBSTANTIVE_CHARS or normalized in REPORT_BIAS_FILLER_VALUES:
            _append_finding(
                findings,
                seen,
                _report_finding(
                    "REPORT_BIAS_SECTION_MISSING",
                    path,
                    f"{field} must contain meaningful content of at least {REPORT_BIAS_MIN_SUBSTANTIVE_CHARS} non-punctuation characters and must not use generic filler.",
                ),
            )
            return


def _validate_report_item_entries(
    sections: list[tuple[str, str]],
    inventory: IssueInventory,
    path: str,
    findings: list[Finding],
    seen: set[tuple[str, str]],
) -> None:
    notes = _section_content(sections, "## 全部条目阅读笔记")
    anchors = REPORT_SOURCE_ANCHOR_PATTERN.findall(notes)
    expected_item_ids = [item.item_id for item in inventory.items]
    if len(anchors) != len(set(anchors)):
        _append_finding(
            findings,
            seen,
            _report_finding("REPORT_DUPLICATE_SOURCE", path, "Each source-item anchor may appear only once."),
        )
    if set(anchors) != set(expected_item_ids):
        _append_finding(
            findings,
            seen,
            _report_finding(
                "REPORT_ITEM_COVERAGE",
                path,
                "Source-item anchors must cover every terminal inventory item exactly once.",
            ),
        )
        return

    blocks = _report_entry_blocks(notes)
    seen_urls: set[str] = set()
    inventory_by_id = {item.item_id: item for item in inventory.items}
    for item_id in expected_item_ids:
        block = blocks.get(item_id)
        if block is None:
            _append_finding(
                findings,
                seen,
                _report_finding("REPORT_ITEM_COVERAGE", path, f"Missing notes block for {item_id}."),
            )
            continue
        values = dict(REPORT_ENTRY_VALUE_PATTERN.findall(block))
        missing_fields = sorted(field for field in REPORT_REQUIRED_ENTRY_FIELDS if not values.get(field))
        if missing_fields:
            _append_finding(
                findings,
                seen,
                _report_finding(
                    "REPORT_ITEM_COVERAGE",
                    path,
                    f"{item_id} is missing required report fields: {', '.join(missing_fields)}.",
                ),
            )
            continue

        item = inventory_by_id[item_id]
        expected_pairs = {
            "title": item.title,
            "creator": item.creator,
            "original_url": item.original_url,
            "content_type": item.content_type,
            "selection_basis": item.selection_basis,
            "access_status": item.access_status,
        }
        if item.access_status == "ALTERNATE":
            expected_pairs["alternate_url"] = item.alternate_url
        mismatched = [
            key
            for key, expected in expected_pairs.items()
            if values.get(key) != expected
        ]
        if mismatched:
            _append_finding(
                findings,
                seen,
                _report_finding(
                    "REPORT_ITEM_COVERAGE",
                    path,
                    f"{item_id} does not match inventory fields: {', '.join(mismatched)}.",
                ),
            )

        original_url = values["original_url"]
        if original_url in seen_urls:
            _append_finding(
                findings,
                seen,
                _report_finding(
                    "REPORT_DUPLICATE_SOURCE",
                    path,
                    f"Duplicate source URL in report entries: {original_url}",
                ),
            )
        else:
            seen_urls.add(original_url)

        if item.access_status != "FULL" and values["degradation_note"].startswith("无"):
            _append_finding(
                findings,
                seen,
                _report_finding(
                    "REPORT_SUMMARY_OVERCLAIM",
                    path,
                    f"{item_id} must disclose its degraded access state in degradation_note.",
                ),
            )

        if item.access_status in {"PARTIAL", "ALTERNATE", "SUMMARY_ONLY", "UNAVAILABLE"}:
            for pattern in REPORT_DEGRADED_OVERCLAIM_PATTERNS:
                if re.search(pattern, block):
                    _append_finding(
                        findings,
                        seen,
                        _report_finding(
                            "REPORT_SUMMARY_OVERCLAIM",
                            path,
                            f"{item_id} overclaims confidence for a degraded access state.",
                        ),
                    )
                    break


def _validate_report_quality_language(
    text: str,
    path: str,
    findings: list[Finding],
    seen: set[tuple[str, str]],
) -> None:
    for sentence in _split_report_sentences(text):
        if _sentence_implies_popularity_equals_quality(sentence):
            _append_finding(
                findings,
                seen,
                _report_finding(
                    "REPORT_POPULARITY_EQUALS_QUALITY",
                    path,
                    "The report must not imply that ranking or highlight popularity equals truth, reliability, importance, or quality.",
                ),
            )
            break


def _parse_level2_sections(body: str) -> list[tuple[str, str]]:
    matches = list(REPORT_LEVEL2_HEADING_PATTERN.finditer(body))
    sections: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        sections.append((match.group(0), body[start:end].strip()))
    return sections


def _section_content(sections: list[tuple[str, str]], heading: str) -> str:
    for current_heading, content in sections:
        if current_heading == heading:
            return content
    return ""


def _parse_level3_blocks(section_text: str) -> list[tuple[str, str]]:
    matches = list(REPORT_LEVEL3_HEADING_PATTERN.finditer(section_text))
    blocks: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(section_text)
        blocks.append((match.group(0), section_text[start:end].strip()))
    return blocks


def _parse_supporting_item_ids(raw_value: str) -> list[str]:
    match = re.fullmatch(r"\[(.*?)\]", raw_value.strip())
    if not match:
        return []
    return [part.strip() for part in match.group(1).split(",") if part.strip()]


def _normalize_report_text(value: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", value).lower()


def _bias_dimension_is_concrete(value: str) -> bool:
    normalized = _normalize_report_text(value)
    return any(_normalize_report_text(token) in normalized for token in REPORT_BIAS_DIMENSION_TOKENS)


def _split_report_sentences(text: str) -> list[str]:
    sentences: list[str] = []
    for part in re.split(r"(?<=[。！？!?；;])\s+|\n+", text):
        stripped = part.strip()
        if stripped:
            sentences.append(stripped)
    return sentences


def _sentence_implies_popularity_equals_quality(sentence: str) -> bool:
    compact = re.sub(r"\s+", "", sentence)
    if not any(token in compact for token in REPORT_POPULARITY_TOKENS):
        return False

    popularity_context = False
    for clause in _split_popularity_clauses(sentence):
        clause_compact = re.sub(r"\s+", "", clause)
        if not clause_compact:
            continue
        if any(token in clause_compact for token in REPORT_POPULARITY_TOKENS):
            popularity_context = True

        if not popularity_context:
            continue
        if not any(token in clause_compact for token in REPORT_POSITIVE_QUALITY_TOKENS):
            continue
        if _clause_has_scoped_popularity_caveat(clause_compact):
            continue
        if _clause_has_positive_popularity_implication(clause_compact, popularity_context):
            return True
    return False


def _report_entry_blocks(notes: str) -> dict[str, str]:
    matches = list(REPORT_SOURCE_ANCHOR_PATTERN.finditer(notes))
    blocks: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(notes)
        blocks[match.group(1)] = notes[start:end].strip()
    return blocks


def _split_popularity_clauses(sentence: str) -> list[str]:
    clauses = [part.strip() for part in re.split(r"[，,；;]", sentence) if part.strip()]
    return [re.sub(r"^(但|然而|不过)", "", clause).strip() for clause in clauses if clause.strip()]


def _clause_has_scoped_popularity_caveat(clause: str) -> bool:
    return any(re.search(pattern, clause) for pattern in REPORT_POPULARITY_SCOPED_CAVEAT_PATTERNS)


def _clause_has_positive_popularity_implication(clause: str, popularity_context: bool) -> bool:
    if not popularity_context:
        return False

    if "越" in clause and any(token in clause for token in REPORT_IMPLICATION_TOKENS):
        return True

    implication_group = "(?:说明|意味着|代表|等于|通常也|往往|会觉得)"
    positive_group = "(?:可靠|真实|正确|质量|最好|最值得|最重要)"
    return bool(re.search(fr"{implication_group}.{{0,20}}{positive_group}", clause))
