"""Domain models for configurable clinical text extraction."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Confidence(str, Enum):
    """Coarse review-oriented confidence levels."""

    EMPTY = "EMPTY"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass
class FieldSchema:
    """A field the product should extract from a clinical document."""

    id: str
    name: str
    description: str = ""
    section: str = ""
    data_type: str = "text"
    required: bool = False
    source_required: bool = True
    strategies: List[str] = field(default_factory=lambda: ["regex", "rule", "llm"])
    keywords: List[str] = field(default_factory=list)
    regex_patterns: List[str] = field(default_factory=list)
    enum: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    llm_hint: str = ""
    review_policy: str = "low_or_empty"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FieldSchema":
        normalized = dict(data)
        normalized.setdefault("id", normalized.get("name", "field"))
        normalized.setdefault("name", normalized["id"])
        for key in ("strategies", "keywords", "regex_patterns", "enum", "examples"):
            value = normalized.get(key, [])
            if isinstance(value, str):
                normalized[key] = [item.strip() for item in value.split("@") if item.strip()]
        return cls(**{k: v for k, v in normalized.items() if k in cls.__dataclass_fields__})


@dataclass
class SchemaDefinition:
    """A versioned schema for one extraction task or registry."""

    id: str
    name: str
    version: str = "0.1.0"
    description: str = ""
    domain: str = "general"
    tags: List[str] = field(default_factory=list)
    fields: List[FieldSchema] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SchemaDefinition":
        normalized = dict(data)
        normalized["fields"] = [FieldSchema.from_dict(item) for item in normalized.get("fields", [])]
        return cls(**{k: v for k, v in normalized.items() if k in cls.__dataclass_fields__})


@dataclass
class LLMOptions:
    """OpenAI-compatible local or remote model settings."""

    enabled: bool = False
    api_base: str = "http://localhost:11434/v1"
    api_key: str = ""
    model: str = ""
    timeout_seconds: int = 60

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "LLMOptions":
        return cls(**{k: v for k, v in (data or {}).items() if k in cls.__dataclass_fields__})


@dataclass
class ExtractionOptions:
    """Runtime extraction options supplied by the product UI or API."""

    enable_llm: bool = False
    llm: LLMOptions = field(default_factory=LLMOptions)
    return_cleaned_text: bool = True
    confidence_threshold: Confidence = Confidence.MEDIUM

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "ExtractionOptions":
        data = data or {}
        llm = LLMOptions.from_dict(data.get("llm"))
        if data.get("enable_llm") is not None:
            llm.enabled = bool(data.get("enable_llm"))
        confidence = data.get("confidence_threshold", Confidence.MEDIUM)
        if isinstance(confidence, str):
            confidence = Confidence(confidence)
        return cls(
            enable_llm=bool(data.get("enable_llm", llm.enabled)),
            llm=llm,
            return_cleaned_text=bool(data.get("return_cleaned_text", True)),
            confidence_threshold=confidence,
        )


@dataclass
class FieldExtraction:
    """One extracted field with review evidence."""

    field_id: str
    name: str
    value: str = ""
    normalized_value: str = ""
    confidence: Confidence = Confidence.EMPTY
    strategy: str = "empty"
    section: str = ""
    source_sentence: str = ""
    source_start: int = -1
    source_end: int = -1
    needs_review: bool = True
    rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["confidence"] = self.confidence.value
        return data


@dataclass
class ExtractionResponse:
    """Full product response for one document extraction."""

    job_id: str
    schema_id: str
    schema_name: str
    schema_version: str
    results: List[FieldExtraction]
    metrics: Dict[str, Any]
    warnings: List[str] = field(default_factory=list)
    cleaned_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "schema_id": self.schema_id,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "results": [item.to_dict() for item in self.results],
            "metrics": self.metrics,
            "warnings": self.warnings,
            "cleaned_text": self.cleaned_text,
        }
