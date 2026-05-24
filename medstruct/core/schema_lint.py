"""Schema quality checks for product readiness."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Dict, List

from .models import SchemaDefinition


VALID_STRATEGIES = {"regex", "rule", "llm"}
VALID_REVIEW_POLICIES = {"low_or_empty", "never"}


@dataclass
class SchemaIssue:
    severity: str
    field_id: str
    message: str
    suggestion: str = ""

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


def validate_schema(schema: SchemaDefinition) -> Dict[str, object]:
    """Return a product-facing schema quality report."""

    issues: List[SchemaIssue] = []
    if not schema.id.strip():
        issues.append(SchemaIssue("error", "", "Schema id 不能为空。", "设置稳定的 schema id。"))
    if not schema.name.strip():
        issues.append(SchemaIssue("warning", "", "Schema name 为空。", "设置一个面向用户的名称。"))
    if not schema.fields:
        issues.append(SchemaIssue("error", "", "Schema 没有字段。", "至少添加一个字段。"))

    ids = [field.id for field in schema.fields]
    duplicates = {field_id for field_id, count in Counter(ids).items() if count > 1}
    for duplicate in sorted(duplicates):
        issues.append(SchemaIssue("error", duplicate, "字段 id 重复。", "字段 id 必须唯一。"))

    for field in schema.fields:
        field_label = field.id or field.name
        if not field.id.strip():
            issues.append(SchemaIssue("error", field_label, "字段 id 为空。", "为字段设置稳定 id。"))
        if not field.name.strip():
            issues.append(SchemaIssue("warning", field_label, "字段名称为空。", "设置展示名称，方便复核。"))
        unknown_strategies = sorted(set(field.strategies) - VALID_STRATEGIES)
        if unknown_strategies:
            issues.append(
                SchemaIssue(
                    "error",
                    field_label,
                    f"未知抽取策略: {', '.join(unknown_strategies)}。",
                    "支持的策略是 regex、rule、llm。",
                )
            )
        if not field.strategies:
            issues.append(SchemaIssue("error", field_label, "字段没有抽取策略。", "至少配置一种策略。"))
        if "regex" in field.strategies and not field.regex_patterns:
            issues.append(SchemaIssue("warning", field_label, "启用了 regex 但没有正则。", "补充 regex_patterns 或移除 regex 策略。"))
        for pattern in field.regex_patterns:
            try:
                re.compile(pattern)
            except re.error as exc:
                issues.append(SchemaIssue("error", field_label, f"正则无法编译: {exc}。", "修正 regex_patterns。"))
        if "rule" in field.strategies and not field.keywords and not field.enum:
            issues.append(SchemaIssue("warning", field_label, "rule 策略缺少关键词或枚举。", "补充 keywords/enum。"))
        if field.data_type == "enum" and not field.enum:
            issues.append(SchemaIssue("warning", field_label, "枚举字段没有 enum 选项。", "补充 enum 选项。"))
        if field.enum and len(field.enum) != len(set(field.enum)):
            issues.append(SchemaIssue("warning", field_label, "enum 选项存在重复。", "删除重复选项。"))
        if field.review_policy not in VALID_REVIEW_POLICIES:
            issues.append(SchemaIssue("warning", field_label, f"未知复核策略: {field.review_policy}。", "使用 low_or_empty 或 never。"))
        if field.required and not (field.keywords or field.regex_patterns or "llm" in field.strategies):
            issues.append(SchemaIssue("warning", field_label, "必填字段缺少稳定抽取线索。", "补充关键词、正则或 LLM 提示。"))
        if "llm" in field.strategies and not (field.description or field.llm_hint or field.examples):
            issues.append(SchemaIssue("info", field_label, "LLM 字段缺少描述性上下文。", "补充 description、examples 或 llm_hint。"))

    error_count = sum(1 for issue in issues if issue.severity == "error")
    warning_count = sum(1 for issue in issues if issue.severity == "warning")
    info_count = sum(1 for issue in issues if issue.severity == "info")
    score = max(0, 100 - error_count * 25 - warning_count * 8 - info_count * 2)
    status = "blocked" if error_count else "ready" if score >= 85 else "review"
    return {
        "score": score,
        "status": status,
        "field_count": len(schema.fields),
        "error_count": error_count,
        "warning_count": warning_count,
        "info_count": info_count,
        "issues": [issue.to_dict() for issue in issues],
    }
