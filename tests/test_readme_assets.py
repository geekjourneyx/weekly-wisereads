from __future__ import annotations

from pathlib import Path
import re
import xml.etree.ElementTree as ET

import pytest


ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "assets" / "readme"
SVG_PATHS = {
    "hero": ASSET_DIR / "hero.svg",
    "signal-map": ASSET_DIR / "signal-map.svg",
    "workflow": ASSET_DIR / "workflow.svg",
    "evidence-levels": ASSET_DIR / "evidence-levels.svg",
}
SVG_NS = "{http://www.w3.org/2000/svg}"
ALLOWED_COLORS = {"#080808", "#F2EFE8", "#C9A86A", "#9B968E"}
FORBIDDEN_TAG_SUFFIXES = {
    "script",
    "foreignObject",
    "animate",
    "animateMotion",
    "animateTransform",
    "set",
}
FORBIDDEN_TEXT_PATTERNS = (
    r"@font-face",
    r"font-family\s*:\s*url",
    r"xlink:href\s*=\s*['\"]https?://",
    r"href\s*=\s*['\"]https?://",
    r"<image[^>]+https?://",
)


def _parse_svg(path: Path) -> ET.Element:
    assert path.exists(), f"missing asset: {path.relative_to(ROOT)}"
    return ET.fromstring(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("name", "path"),
    [(name, path) for name, path in SVG_PATHS.items()],
    ids=SVG_PATHS.keys(),
)
def test_svg_assets_are_github_safe(name: str, path: Path):
    root = _parse_svg(path)

    assert root.tag == f"{SVG_NS}svg"
    assert root.attrib.get("viewBox")
    assert root.find(f"{SVG_NS}title") is not None
    assert root.find(f"{SVG_NS}desc") is not None

    text = path.read_text(encoding="utf-8")
    for pattern in FORBIDDEN_TEXT_PATTERNS:
        assert not re.search(pattern, text, flags=re.IGNORECASE), (
            f"{name} contains forbidden external reference pattern {pattern!r}"
        )

    font_sizes: list[float] = []

    for element in root.iter():
        tag_name = element.tag.split("}")[-1]
        assert tag_name not in FORBIDDEN_TAG_SUFFIXES, f"{name} uses forbidden tag {tag_name}"

        for attr_name, attr_value in element.attrib.items():
            if "href" in attr_name.lower():
                assert not re.search(r"^https?://", attr_value, flags=re.IGNORECASE), (
                    f"{name} links to external resource {attr_value}"
                )

            if attr_name in {"fill", "stroke", "stop-color"}:
                normalized = attr_value.strip().upper()
                if normalized != "NONE":
                    assert normalized in ALLOWED_COLORS, (
                        f"{name} uses non-editorial color {attr_value}"
                    )

            if attr_name == "style":
                for color_name in ("fill", "stroke", "stop-color"):
                    match = re.search(rf"{color_name}\s*:\s*([^;]+)", attr_value, flags=re.IGNORECASE)
                    if match:
                        normalized = match.group(1).strip().upper()
                        if normalized != "NONE":
                            assert normalized in ALLOWED_COLORS, (
                                f"{name} uses non-editorial color {match.group(1)}"
                            )

                match = re.search(r"font-size\s*:\s*([0-9]+(?:\.[0-9]+)?)", attr_value, flags=re.IGNORECASE)
                if match:
                    font_sizes.append(float(match.group(1)))

            if attr_name == "font-size":
                cleaned = attr_value.strip().removesuffix("px")
                font_sizes.append(float(cleaned))

    assert font_sizes, f"{name} must declare font sizes"
    assert min(font_sizes) >= 34, f"{name} font size drops below 34 units: {min(font_sizes)}"


def test_hero_copy_is_static_and_non_ai_branded():
    path = SVG_PATHS["hero"]
    text = path.read_text(encoding="utf-8")

    assert "READWISE'S WEEKLY READING SIGNAL" in text
    assert "DEEPLY READ IN CHINESE" in text
    assert "深读 Readwise 用户上周高亮最多的内容" in text

    forbidden = (
        "Vol.155",
        "Vol. 155",
        "2026-",
        "AI Builders",
        "Founders",
    )
    for marker in forbidden:
        assert marker not in text


def test_hero_cjk_is_vectorized_and_not_live_text():
    root = _parse_svg(SVG_PATHS["hero"])
    cjk_group = root.find(f".//{SVG_NS}g[@id='hero-cjk-outline']")
    assert cjk_group is not None
    assert cjk_group.findall(f".//{SVG_NS}path")

    text_nodes = [
        "".join(element.itertext()).strip()
        for element in root.iter(f"{SVG_NS}text")
    ]
    visible_text = " ".join(filter(None, text_nodes))
    assert not re.search(r"[\u3400-\u9fff]", visible_text)

    desc = "".join(root.find(f"{SVG_NS}desc").itertext())
    aria_label = root.attrib.get("aria-label", "")
    accessible_copy = f"{desc}\n{aria_label}"
    assert "深读 Readwise 用户上周高亮最多的内容" in accessible_copy


def test_hero_eyebrow_sits_above_headline_band():
    root = _parse_svg(SVG_PATHS["hero"])
    eyebrow = root.find(f".//{SVG_NS}g[@id='hero-eyebrow']")
    headline = root.find(f".//{SVG_NS}g[@id='hero-headline']")
    assert eyebrow is not None
    assert headline is not None

    eyebrow_y = [
        float(element.attrib["y"])
        for element in eyebrow.findall(f"{SVG_NS}text")
        if "y" in element.attrib
    ]
    headline_y = [
        float(element.attrib["y"])
        for element in headline.findall(f"{SVG_NS}text")
        if "y" in element.attrib
    ]
    assert eyebrow_y
    assert headline_y
    assert max(eyebrow_y) < min(headline_y)


def test_signal_map_separates_curated_ebook_route():
    root = _parse_svg(SVG_PATHS["signal-map"])
    text = SVG_PATHS["signal-map"].read_text(encoding="utf-8")

    assert "CURATED EBOOK" in text
    assert "HIGHLIGHT-RANKED DOCUMENTS" in text

    route_group = root.find(f".//{SVG_NS}g[@id='curated-ebook-route']")
    ranked_group = root.find(f".//{SVG_NS}g[@id='highlight-ranked-route']")
    assert route_group is not None
    assert ranked_group is not None
    assert route_group is not ranked_group


def test_evidence_levels_lists_all_access_statuses_and_four_judgment_labels():
    root = _parse_svg(SVG_PATHS["evidence-levels"])
    access_panel = root.find(f".//{SVG_NS}g[@id='access-status-panel']")
    judgment_panel = root.find(f".//{SVG_NS}g[@id='judgment-type-panel']")
    assert access_panel is not None
    assert judgment_panel is not None

    access_labels = [
        "".join(element.itertext()).strip()
        for element in access_panel.findall(f"{SVG_NS}text")
        if "".join(element.itertext()).strip()
    ]
    judgment_labels = [
        "".join(element.itertext()).strip()
        for element in judgment_panel.findall(f"{SVG_NS}text")
        if "".join(element.itertext()).strip()
    ]

    assert access_labels == [
        "FULL",
        "PARTIAL",
        "ALTERNATE",
        "SUMMARY_ONLY",
        "UNAVAILABLE",
    ]
    assert judgment_labels == [
        "FACTUAL RELIABILITY",
        "EDITORIAL SIGNIFICANCE",
        "BIAS / MISSING VIEWS",
        "SELECTION LIMITS",
    ]
