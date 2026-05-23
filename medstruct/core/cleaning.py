"""Dirty clinical document cleanup utilities."""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, List, Tuple


@dataclass
class CleanedDocument:
    raw: str
    text: str
    warnings: List[str] = field(default_factory=list)


TEXT_KEYS = {
    "content",
    "html_content",
    "text",
    "plain_text",
    "inp_emr_content_plain_text",
    "wygtext",
    "image_feat",
    "image_tip",
    "imaging_findings",
    "impression",
}


def clean_document(raw: str) -> CleanedDocument:
    """Normalize HTML, JSON-ish payloads, table paste, and common EMR whitespace."""

    raw = raw or ""
    warnings: List[str] = []
    unpacked, unpack_warning = _maybe_unpack_structured_payload(raw)
    if unpack_warning:
        warnings.append(unpack_warning)
    text = _html_to_text(unpacked)
    text = _normalize_text(text)
    if len(text) < max(20, len(raw) * 0.1) and raw.strip():
        warnings.append("清洗后文本明显变短，请检查输入是否为图片、二进制或非文本数据。")
    return CleanedDocument(raw=raw, text=text, warnings=warnings)


def _maybe_unpack_structured_payload(raw: str) -> Tuple[str, str]:
    stripped = raw.strip()
    if not stripped or stripped[0] not in "[{":
        return raw, ""
    try:
        payload = json.loads(stripped)
    except Exception:
        return raw, ""
    values = list(_walk_text_values(payload))
    if not values:
        return raw, "输入像 JSON，但没有发现可抽取的文本字段，已按原文处理。"
    return "\n".join(values), "已从 JSON/列表脏数据中合并文本字段。"


def _walk_text_values(value: Any, key: str = "") -> Iterable[str]:
    if isinstance(value, str):
        if key in TEXT_KEYS or len(value) > 30:
            yield value
        return
    if isinstance(value, dict):
        for child_key, child_value in value.items():
            yield from _walk_text_values(child_value, str(child_key))
        return
    if isinstance(value, list):
        for item in value:
            yield from _walk_text_values(item, key)


def _html_to_text(raw: str) -> str:
    if not _looks_like_html(raw):
        return raw
    try:
        from bs4 import BeautifulSoup
    except Exception:
        return re.sub(r"<[^>]+>", " ", raw)

    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    for tag in soup.find_all(["br", "p", "div", "section", "article", "tr", "li", "h1", "h2", "h3"]):
        tag.insert_before("\n")
    for tag in soup.find_all(["td", "th"]):
        tag.append(" ")
    return soup.get_text("\n")


def _looks_like_html(text: str) -> bool:
    return bool(re.search(r"</?(html|body|table|tr|td|div|span|p|br)\b", text or "", flags=re.I))


def _normalize_text(text: str) -> str:
    text = html.unescape(text or "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u3000", " ")
    text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s*([:：])\s*", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [line.strip() for line in text.split("\n")]
    lines = [line for line in lines if line]
    return "\n".join(lines).strip()
