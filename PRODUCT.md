# MedStruct Studio

MedStruct Studio 是从历史专病库项目中抽象出的独立产品层：中文病历结构化抽取工具。

它的产品边界是清晰的：输入脏病历文本、HTML、JSON 片段或报告内容，选择或编辑 schema，输出带来源句、置信度和复核状态的结构化结果。第一阶段用脑卒中专病库变量做示例，但引擎本身不绑定专病。

## 核心能力

- 可配置 schema：字段、章节、关键词、正则、枚举、示例、LLM 提示。
- Schema 质量检查：重复字段、坏正则、策略缺失、质量分与可发布状态。
- 混合抽取策略：正则、规则、关键词预过滤、OpenAI-compatible 本地/远程模型。
- 脏数据清洗：HTML、JSON payload、表格粘贴、EMR 空白符归一。
- 证据可追溯：每个字段返回来源句、位置、抽取策略。
- 置信度与复核：LOW/EMPTY/缺少证据自动进入复核队列。
- 产品 UI：Schema 编辑、示例载入、抽取结果、证据句、JSON 导出。
- 结果工作台：搜索、置信度过滤、复核队列、CSV 导出、抽取画像。

## 运行

```bash
pip install fastapi uvicorn beautifulsoup4 pydantic
python -m medstruct.server
```

默认地址：

```text
http://127.0.0.1:8765
```

## 本地模型

UI 中的模型配置使用 OpenAI-compatible `/chat/completions` 协议。Ollama、vLLM、Xinference、LM Studio 等只要暴露兼容接口，都可以接入。

默认本地地址：

```text
http://localhost:11434/v1
```

没有配置模型时，系统仍会使用正则和规则策略完成抽取。

## 下一步产品化

- 增加 schema 版本管理、导入导出和字段评测集。
- 增加人工复核保存、字段级修正记录和审计日志。
- 增加 Excel/FHIR/OMOP 导出。
- 把旧项目中成熟的脑卒中、脑出血、影像、手术规则迁移为插件。
- 维护公开仓库发布审计，确保 demo 数据始终为合成或脱敏样例。
