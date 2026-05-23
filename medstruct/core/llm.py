"""OpenAI-compatible LLM extraction adapter.

The product treats local deployments and remote models the same way: any
endpoint that implements /chat/completions can be used.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Dict, Iterable, List

from .models import FieldSchema, LLMOptions


def extract_with_llm(text: str, fields: Iterable[FieldSchema], options: LLMOptions) -> Dict[str, Dict[str, str]]:
    """Ask an OpenAI-compatible model to fill unresolved fields."""

    fields = list(fields)
    if not fields or not options.enabled:
        return {}
    if not options.api_base or not options.model:
        raise ValueError("LLM 已启用，但 api_base 或 model 为空。")

    prompt = _build_prompt(text, fields)
    url = options.api_base.rstrip("/") + "/chat/completions"
    body = {
        "model": options.model,
        "temperature": 0.0,
        "messages": [
            {
                "role": "system",
                "content": "你是严谨的中文病历结构化抽取助手。只抽取原文明确支持的信息。",
            },
            {"role": "user", "content": prompt},
        ],
    }
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=payload, method="POST")
    request.add_header("Content-Type", "application/json")
    if options.api_key:
        request.add_header("Authorization", f"Bearer {options.api_key}")
    try:
        with urllib.request.urlopen(request, timeout=options.timeout_seconds) as response:
            response_body = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"LLM 调用失败: {exc}") from exc

    data = json.loads(response_body)
    content = data["choices"][0]["message"]["content"]
    return _parse_llm_json(content)


def _build_prompt(text: str, fields: List[FieldSchema]) -> str:
    field_lines = []
    for field in fields:
        field_lines.append(
            {
                "id": field.id,
                "name": field.name,
                "description": field.description,
                "section": field.section,
                "enum": field.enum,
                "examples": field.examples,
                "hint": field.llm_hint,
            }
        )
    return (
        "从下方病历文本中抽取字段。返回 JSON 数组，不要输出 Markdown。\n"
        "每项格式为 {\"field_id\":\"...\",\"value\":\"...\",\"source_sentence\":\"...\",\"rationale\":\"...\"}。\n"
        "source_sentence 必须是原文短句；原文没有明确依据时 value 和 source_sentence 都返回空字符串。\n\n"
        f"字段定义:\n{json.dumps(field_lines, ensure_ascii=False, indent=2)}\n\n"
        f"病历文本:\n{text}"
    )


def _parse_llm_json(content: str) -> Dict[str, Dict[str, str]]:
    content = content.strip()
    if content.startswith("```"):
        content = content.strip("`")
        content = content.replace("json\n", "", 1).strip()
    parsed = json.loads(content)
    if isinstance(parsed, dict):
        parsed = parsed.get("results", [])
    result: Dict[str, Dict[str, str]] = {}
    for item in parsed or []:
        field_id = str(item.get("field_id", "")).strip()
        if not field_id:
            continue
        result[field_id] = {
            "value": str(item.get("value", "") or "").strip(),
            "source_sentence": str(item.get("source_sentence", "") or "").strip(),
            "rationale": str(item.get("rationale", "") or "").strip(),
        }
    return result
