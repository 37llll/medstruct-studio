# MedStruct Studio

MedStruct Studio 是一个面向中文病历的结构化抽取工具。它把杂乱的临床文本、HTML、表格粘贴内容和 JSON-like EMR payload 转换为可复核、可导出的结构化字段。

它的第一个内置示例是脑卒中专病库模板，但产品本身不绑定任何单病种。你可以通过配置 schema，把它扩展成通用入院记录、出院记录、随访表、科研登记表、质控表或内部数据治理流程的抽取工具。

English documentation is available below.

## 为什么做它

医院和科研场景里的病历数据常常很难直接使用：格式不统一、字段散落在不同段落、表格复制后结构混乱、同一个概念有多种写法。传统方案通常需要为每一批数据写一次脚本，维护成本高，也不利于复核。

MedStruct Studio 的目标是把这类一次性的抽取脚本，升级成一个可配置、可验证、可复核的产品化工具：

- 业务人员可以通过 schema 定义需要抽取什么。
- 工程人员可以把正则、规则和本地模型组合成稳定方案。
- 复核人员可以看到每个字段来自哪一句原文，以及为什么需要人工确认。
- 数据团队可以导出 JSON 或 CSV，继续进入标注、科研、统计或数据库流程。

## 产品能力

- 可配置 schema：字段、章节、关键词、正则、枚举值、示例和 LLM hint。
- 混合抽取策略：regex、deterministic rule、关键词预筛选，以及可选的 OpenAI-compatible 本地模型。
- 脏数据清洗：HTML、JSON-like payload、病历空白符、表格粘贴内容。
- 证据优先输出：每个字段都包含原文句子、字符位置、抽取策略、置信度和复核标记。
- Schema 质量工作台：检查重复字段、错误正则、策略缺失、枚举问题，并给出 readiness score。
- 产品化 UI：schema 选择和编辑、schema 校验、示例切换、模型配置、结果表格、搜索过滤、证据复核、抽取画像和 JSON/CSV 导出。

## 快速开始

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m medstruct.server
```

打开浏览器：

```text
http://127.0.0.1:8765
```

## 本地模型支持

LLM 适配器使用 OpenAI-compatible `/chat/completions` 协议。你可以把它指向 Ollama、vLLM、Xinference、LM Studio 或内部模型网关。

默认本地 endpoint：

```text
http://localhost:11434/v1
```

不配置模型也可以正常使用。regex、规则和关键词过滤默认可用。

## API

```http
GET /api/schemas
GET /api/schemas/{schema_id}
GET /api/examples
POST /api/extract
POST /api/schemas/validate
```

示例请求：

```json
{
  "schema_id": "stroke_registry_v1",
  "document": "主诉：言语不清、右侧肢体无力 3 小时。既往史：高血压 10 年。入院 NIHSS 评分 6 分。",
  "options": {
    "enable_llm": false
  }
}
```

## 测试

```bash
python -m unittest discover medstruct\tests
```

## 发布前检查

公开仓库或发布版本前，运行：

```bash
python scripts/audit_release.py
```

这个检查用于阻止明显的本地密钥、私有地址和真实临床标识符进入公开仓库。仓库里的 demo 文档必须保持为合成样例。

## 仓库边界

这个仓库只包含干净的产品层。请不要提交任何组织私有信息、个人信息或凭据。

---

## English

MedStruct Studio is a product-oriented structuring tool for Chinese electronic medical records.

It turns messy clinical text, HTML, table paste, and JSON-like EMR payloads into structured fields with source evidence, confidence levels, extraction strategy, and review status.

The first bundled schema is a stroke registry template, but the engine is domain-neutral. New schemas can adapt it to admission notes, discharge summaries, follow-up forms, research registries, quality-control forms, and internal data governance workflows.

## Why It Exists

Clinical data is often hard to reuse directly. Formats vary across systems, important fields are scattered across sections, copied tables lose structure, and the same concept can appear in many expressions.

MedStruct Studio turns one-off extraction scripts into a configurable, verifiable, and review-friendly product:

- Domain users define what to extract through schemas.
- Engineers combine regex, deterministic rules, and local models.
- Reviewers see the source sentence and confidence for each extracted field.
- Data teams export JSON or CSV for annotation, research, statistics, or downstream databases.

## Features

- Configurable schema: fields, sections, keywords, regex patterns, enum values, examples, and LLM hints.
- Hybrid extraction: regex, deterministic rules, keyword pre-filtering, and optional OpenAI-compatible local models.
- Dirty data cleanup: HTML, JSON-like payloads, EMR whitespace, and table-like pasted content.
- Evidence-first output: source sentence, character offsets, extraction strategy, confidence, and review flag for every field.
- Schema quality workspace: duplicate ids, invalid regex, incomplete strategies, enum issues, and readiness score.
- Product UI: schema selection/editing, schema validation, demo switching, model configuration, result table, search/filter, evidence review, extraction profile, and JSON/CSV export.

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

The product works without an LLM. Regex, rules, and keyword filtering remain available by default.

## API

```http
GET /api/schemas
GET /api/schemas/{schema_id}
GET /api/examples
POST /api/extract
POST /api/schemas/validate
```

Example request:

```json
{
  "schema_id": "stroke_registry_v1",
  "document": "主诉：言语不清、右侧肢体无力 3 小时。既往史：高血压 10 年。入院 NIHSS 评分 6 分。",
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

## Repository Boundary

This repository intentionally contains only the clean product layer. Historical hospital-specific project code, real patient data, internal API addresses, and local API keys should not be committed here.
