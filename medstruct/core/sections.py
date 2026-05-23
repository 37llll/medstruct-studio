"""Clinical section detection for Chinese EMR text."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List


SECTION_ALIASES = {
    "主诉": ["主诉"],
    "现病史": ["现病史", "病史", "发病经过"],
    "既往史": ["既往史", "既往病史"],
    "个人史": ["个人史"],
    "家族史": ["家族史"],
    "查体": ["查体", "体格检查", "专科查体", "神经系统查体"],
    "辅助检查": ["辅助检查", "检查结果", "影像学检查", "实验室检查"],
    "诊断": ["入院诊断", "出院诊断", "诊断"],
    "出院情况": ["出院情况"],
    "出院医嘱": ["出院医嘱", "出院带药"],
    "手术": ["手术名称", "手术经过", "手术记录"],
    "影像": ["影像所见", "检查所见", "印象", "影像诊断"],
    "康复": ["康复评定", "康复治疗", "康复计划"],
}

ALIAS_TO_CANONICAL = {
    alias: canonical for canonical, aliases in SECTION_ALIASES.items() for alias in aliases
}

SECTION_PATTERN = re.compile(
    r"(?m)(?P<title>"
    + "|".join(sorted(map(re.escape, ALIAS_TO_CANONICAL), key=len, reverse=True))
    + r")\s*[:：]"
)


@dataclass
class Section:
    name: str
    title: str
    content: str
    start: int
    end: int


def split_sections(text: str) -> Dict[str, Section]:
    """Split text into clinical sections and always include 全文."""

    text = text or ""
    matches = list(SECTION_PATTERN.finditer(text))
    sections: Dict[str, Section] = {
        "全文": Section(name="全文", title="全文", content=text, start=0, end=len(text))
    }
    if not matches:
        return sections

    for index, match in enumerate(matches):
        title = match.group("title")
        name = ALIAS_TO_CANONICAL.get(title, title)
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        if name in sections and sections[name].content:
            existing = sections[name]
            sections[name] = Section(
                name=name,
                title=existing.title,
                content=(existing.content + "\n" + content).strip(),
                start=existing.start,
                end=end,
            )
        else:
            sections[name] = Section(name=name, title=title, content=content, start=start, end=end)
    return sections


def resolve_section(sections: Dict[str, Section], wanted: str) -> Section:
    """Return the best matching section for a field."""

    wanted = (wanted or "").strip()
    if not wanted:
        return sections["全文"]
    if wanted in sections:
        return sections[wanted]
    canonical = ALIAS_TO_CANONICAL.get(wanted)
    if canonical and canonical in sections:
        return sections[canonical]
    for name, section in sections.items():
        if wanted in name or wanted in section.title:
            return section
    return sections["全文"]


def available_section_names() -> List[str]:
    return list(SECTION_ALIASES.keys())
