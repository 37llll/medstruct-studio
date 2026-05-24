# MedStruct Studio

MedStruct Studio is a product-oriented Chinese EMR structuring tool.

It turns messy clinical text, HTML, table paste, and JSON-like EMR payloads into structured fields with source sentences, confidence levels, extraction strategy, and review status. The first bundled example schema is a stroke registry template, but the engine is domain-neutral and can be extended with new schemas and extraction strategies.

## Product Capabilities

- Configurable schema: fields, sections, keywords, regex patterns, enum values, examples, and LLM hints.
- Hybrid extraction: regex, deterministic rules, keyword pre-filtering, and optional OpenAI-compatible local models.
- Dirty data cleanup: HTML, JSON payloads, EMR whitespace, table-like pasted content.
- Evidence-first output: source sentence, source offsets, strategy, confidence, and review flag for every field.
- Product UI: schema selection/editing, demo switching, model configuration, extraction result table, search/filter, evidence review, and JSON/CSV export.

## Quick Start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m medstruct.server
```

Open:

```text
http://127.0.0.1:8765
```

## Local Model Support

The LLM adapter uses the OpenAI-compatible `/chat/completions` protocol. You can point it to Ollama, vLLM, Xinference, LM Studio, or an internal model gateway.

Default local endpoint:

```text
http://localhost:11434/v1
```

The product still works without an LLM. Regex, rules, and keyword filtering remain available by default.

## API

```http
GET /api/schemas
GET /api/schemas/{schema_id}
GET /api/examples
POST /api/extract
```

Example request:

```json
{
  "schema_id": "stroke_registry_v1",
  "document": "主诉：言语不清、右肢无力1天余。",
  "options": {
    "enable_llm": false
  }
}
```

## Tests

```bash
python -m unittest discover medstruct\tests
```

## Release Audit

Before making the repository public or publishing a release, run:

```bash
python scripts/audit_release.py
```

The audit blocks obvious local secrets, private IPs, and real clinical identifiers. Demo documents are synthetic and must stay synthetic.

## Repository Hygiene

This repository intentionally contains only the clean product layer. Historical hospital-specific project code, real patient data, internal API addresses, and local API keys should not be committed here.
