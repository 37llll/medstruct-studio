"""Hybrid extraction engine: cleanup, regex/rules, optional local LLM, evidence, confidence."""

from __future__ import annotations

import re
import time
import uuid
from collections import Counter
from typing import Dict, Iterable, List, Optional, Tuple

from .cleaning import clean_document
from .llm import extract_with_llm
from .models import Confidence, ExtractionOptions, ExtractionResponse, FieldExtraction, FieldSchema, SchemaDefinition
from .sections import Section, resolve_section, split_sections


NEGATION_WORDS = ("否认", "无", "未见", "未诉", "不伴", "未发现", "排除", "没有", "未")


class ExtractionEngine:
    """Product-grade extraction engine with deterministic fallbacks."""

    def extract(
        self,
        schema: SchemaDefinition,
        document: str,
        options: Optional[ExtractionOptions] = None,
    ) -> ExtractionResponse:
        started = time.perf_counter()
        options = options or ExtractionOptions()
        cleaned = clean_document(document)
        sections = split_sections(cleaned.text)
        warnings = list(cleaned.warnings)
        results: List[FieldExtraction] = []
        unresolved_for_llm: List[Tuple[FieldSchema, Section]] = []

        for field in schema.fields:
            section = resolve_section(sections, field.section)
            item = self._extract_without_llm(field, section, cleaned.text)
            if not item.value and "llm" in field.strategies and options.enable_llm:
                unresolved_for_llm.append((field, section))
            results.append(item)

        if unresolved_for_llm and options.enable_llm:
            try:
                llm_fields = [field for field, _section in unresolved_for_llm]
                llm_result = extract_with_llm(cleaned.text, llm_fields, options.llm)
                by_id = {item.field_id: item for item in results}
                for field, _section in unresolved_for_llm:
                    candidate = llm_result.get(field.id)
                    if not candidate or not candidate.get("value"):
                        continue
                    source = candidate.get("source_sentence", "")
                    start, end = _find_span(cleaned.text, source)
                    by_id[field.id].value = candidate["value"]
                    by_id[field.id].normalized_value = _normalize_value(candidate["value"], field)
                    by_id[field.id].source_sentence = source
                    by_id[field.id].source_start = start
                    by_id[field.id].source_end = end
                    by_id[field.id].strategy = "llm"
                    by_id[field.id].confidence = Confidence.HIGH if source and start >= 0 else Confidence.MEDIUM
                    by_id[field.id].rationale = candidate.get("rationale", "LLM 抽取")
            except Exception as exc:
                warnings.append(str(exc))

        for item in results:
            field = next((candidate for candidate in schema.fields if candidate.id == item.field_id), None)
            item.needs_review = self._needs_review(item, field)

        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        metrics = self._build_metrics(results, elapsed_ms)
        return ExtractionResponse(
            job_id=str(uuid.uuid4()),
            schema_id=schema.id,
            schema_name=schema.name,
            schema_version=schema.version,
            results=results,
            metrics=metrics,
            warnings=warnings,
            cleaned_text=cleaned.text if options.return_cleaned_text else "",
        )

    def _extract_without_llm(self, field: FieldSchema, section: Section, full_text: str) -> FieldExtraction:
        text = section.content or full_text
        base = FieldExtraction(field_id=field.id, name=field.name, section=section.name)
        keywords_hit = _keywords_hit(text, field.keywords) or _keywords_hit(full_text, field.keywords)
        if field.keywords and not keywords_hit:
            base.confidence = Confidence.EMPTY
            base.rationale = "关键词预过滤未命中，跳过模型调用。"
            return base

        if "regex" in field.strategies:
            regex_result = self._extract_by_regex(field, text, section, full_text)
            if regex_result:
                return regex_result

        if "rule" in field.strategies:
            rule_result = self._extract_by_rule(field, text, section, full_text)
            if rule_result:
                return rule_result

        base.confidence = Confidence.LOW if field.required else Confidence.EMPTY
        base.rationale = "规则未能抽取。"
        return base

    def _extract_by_regex(
        self,
        field: FieldSchema,
        text: str,
        section: Section,
        full_text: str,
    ) -> Optional[FieldExtraction]:
        targets = [(text, section)]
        if section.name != "全文":
            targets.append((full_text, Section(name="全文", title="全文", content=full_text, start=0, end=len(full_text))))
        for pattern in field.regex_patterns:
            for target_text, target_section in targets:
                try:
                    match = re.search(pattern, target_text, flags=re.I | re.S)
                except re.error:
                    continue
                if not match:
                    continue
                value = _match_value(match)
                if not value:
                    continue
                local_start, local_end = match.span()
                source, sent_start, sent_end = _sentence_around(target_text, local_start, local_end)
                global_start = target_section.start + sent_start if target_section.name != "全文" else sent_start
                global_end = target_section.start + sent_end if target_section.name != "全文" else sent_end
                if source and _find_span(full_text, source)[0] >= 0:
                    global_start, global_end = _find_span(full_text, source)
                return FieldExtraction(
                    field_id=field.id,
                    name=field.name,
                    value=value,
                    normalized_value=_normalize_value(value, field),
                    confidence=Confidence.HIGH,
                    strategy="regex",
                    section=section.name,
                    source_sentence=source,
                    source_start=global_start,
                    source_end=global_end,
                    needs_review=False,
                    rationale="正则命中且证据句来自原文。",
                )
        return None

    def _extract_by_rule(
        self,
        field: FieldSchema,
        text: str,
        section: Section,
        full_text: str,
    ) -> Optional[FieldExtraction]:
        if field.enum and set(field.enum) >= {"是", "否"} and field.keywords:
            sentence = _first_sentence_with_keywords(text, field.keywords) or _first_sentence_with_keywords(full_text, field.keywords)
            if not sentence:
                return None
            value = "否" if _is_negated(sentence, field.keywords) else "是"
            start, end = _find_span(full_text, sentence)
            return FieldExtraction(
                field_id=field.id,
                name=field.name,
                value=value,
                normalized_value=value,
                confidence=Confidence.HIGH if value == "否" or start >= 0 else Confidence.MEDIUM,
                strategy="rule",
                section=section.name,
                source_sentence=sentence,
                source_start=start,
                source_end=end,
                needs_review=False,
                rationale="是否类字段由关键词和否定词窗口判断。",
            )

        if field.enum:
            sentence = _first_sentence_with_options(text, field.enum)
            if sentence:
                value = next(option for option in field.enum if option in sentence)
                start, end = _find_span(full_text, sentence)
                return FieldExtraction(
                    field_id=field.id,
                    name=field.name,
                    value=value,
                    normalized_value=value,
                    confidence=Confidence.MEDIUM,
                    strategy="rule",
                    section=section.name,
                    source_sentence=sentence,
                    source_start=start,
                    source_end=end,
                    needs_review=True,
                    rationale="枚举值在原文中出现。",
                )
        return None

    def _needs_review(self, item: FieldExtraction, field: Optional[FieldSchema]) -> bool:
        if not field:
            return True
        if field.required and not item.value:
            return True
        if field.review_policy == "never":
            return False
        if item.confidence in (Confidence.LOW, Confidence.EMPTY):
            return True
        if field.source_required and item.value and not item.source_sentence:
            return True
        return False

    def _build_metrics(self, results: Iterable[FieldExtraction], elapsed_ms: float) -> Dict[str, object]:
        results = list(results)
        strategy_counts = Counter(item.strategy for item in results)
        confidence_counts = Counter(item.confidence.value for item in results)
        total = len(results)
        extracted = sum(1 for item in results if item.value)
        needs_review = sum(1 for item in results if item.needs_review)
        return {
            "total_fields": total,
            "extracted_fields": extracted,
            "high_confidence": sum(1 for item in results if item.confidence == Confidence.HIGH),
            "needs_review": needs_review,
            "skipped_by_keyword": sum(1 for item in results if item.strategy == "empty" and item.confidence == Confidence.EMPTY),
            "elapsed_ms": elapsed_ms,
            "strategy_counts": dict(strategy_counts),
            "confidence_counts": dict(confidence_counts),
            "completion_rate": round(extracted / total, 4) if total else 0,
            "review_rate": round(needs_review / total, 4) if total else 0,
        }


def _keywords_hit(text: str, keywords: List[str]) -> bool:
    if not keywords:
        return True
    return any(keyword and keyword in text for keyword in keywords)


def _match_value(match: re.Match) -> str:
    if "value" in match.groupdict():
        return (match.group("value") or "").strip()
    for group in match.groups():
        if group:
            return str(group).strip()
    return match.group(0).strip()


def _normalize_value(value: str, field: FieldSchema) -> str:
    value = (value or "").strip()
    value = re.sub(r"\s+", "", value) if field.data_type in {"number", "duration", "measurement"} else value
    if field.enum and value not in field.enum:
        for option in field.enum:
            if option in value:
                return option
    return value


def _sentence_around(text: str, start: int, end: int) -> Tuple[str, int, int]:
    left = max(text.rfind(mark, 0, start) for mark in ["。", "；", ";", "\n", "！", "？"])
    sent_start = 0 if left < 0 else left + 1
    right_candidates = [text.find(mark, end) for mark in ["。", "；", ";", "\n", "！", "？"]]
    right_candidates = [item for item in right_candidates if item >= 0]
    sent_end = min(right_candidates) + 1 if right_candidates else len(text)
    return text[sent_start:sent_end].strip(), sent_start, sent_end


def _first_sentence_with_keywords(text: str, keywords: List[str]) -> str:
    for sentence in _split_sentences(text):
        if any(keyword in sentence for keyword in keywords):
            return sentence
    return ""


def _first_sentence_with_options(text: str, options: List[str]) -> str:
    for sentence in _split_sentences(text):
        if any(option in sentence for option in options):
            return sentence
    return ""


def _split_sentences(text: str) -> List[str]:
    pieces = re.split(r"(?<=[。；;！？\n])", text or "")
    return [piece.strip() for piece in pieces if piece.strip()]


def _is_negated(sentence: str, keywords: List[str]) -> bool:
    clauses = [clause for clause in re.split(r"[，,、；;。]", sentence) if clause.strip()]
    for keyword in keywords:
        for clause in clauses:
            clause = clause.replace("无明显诱因", "").replace("无明确诱因", "").replace("无特殊诱因", "")
            pos = clause.find(keyword)
            if pos < 0:
                continue
            before = clause[max(0, pos - 8):pos]
            keyword_window = clause[max(0, pos - 2): min(len(clause), pos + len(keyword) + 4)]
            if any(word in before for word in NEGATION_WORDS):
                return True
            if any(keyword_window.startswith(word + keyword) for word in NEGATION_WORDS):
                return True
    return False


def _find_span(text: str, needle: str) -> Tuple[int, int]:
    if not needle:
        return -1, -1
    start = text.find(needle)
    if start < 0:
        compact_text = re.sub(r"\s+", "", text)
        compact_needle = re.sub(r"\s+", "", needle)
        compact_start = compact_text.find(compact_needle)
        return (-1, -1) if compact_start < 0 else (compact_start, compact_start + len(compact_needle))
    return start, start + len(needle)
