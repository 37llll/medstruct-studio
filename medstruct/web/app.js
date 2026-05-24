const state = {
  schemas: [],
  examples: [],
  currentSchema: null,
  lastResponse: null,
  reviewOnly: false,
};

const $ = (id) => document.getElementById(id);

async function getJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function postJson(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function init() {
  bindEvents();
  const schemaList = await getJson("/api/schemas");
  state.schemas = schemaList.schemas;
  $("schemaSelect").innerHTML = state.schemas
    .map((schema) => `<option value="${schema.id}">${schema.name}</option>`)
    .join("");

  const examples = await getJson("/api/examples");
  state.examples = examples.examples;
  $("exampleSelect").innerHTML = state.examples
    .map((example) => `<option value="${example.id}">${example.name}</option>`)
    .join("");

  await loadSchema(state.schemas[0].id);
  await loadExample();
  if (window.lucide) window.lucide.createIcons();
}

function bindEvents() {
  $("schemaSelect").addEventListener("change", (event) => loadSchema(event.target.value));
  $("loadExampleBtn").addEventListener("click", loadExample);
  $("validateSchemaBtn").addEventListener("click", validateCurrentSchema);
  $("extractBtn").addEventListener("click", extract);
  $("exportBtn").addEventListener("click", exportJson);
  $("exportCsvBtn").addEventListener("click", exportCsv);
  $("reviewOnlyBtn").addEventListener("click", toggleReviewOnly);
  $("resultSearch").addEventListener("input", applyResultFilters);
  $("confidenceFilter").addEventListener("change", applyResultFilters);
  document.querySelectorAll(".tab").forEach((button) => {
    button.addEventListener("click", () => activateTab(button.dataset.tab));
  });
}

async function loadSchema(schemaId) {
  const schema = await getJson(`/api/schemas/${schemaId}`);
  state.currentSchema = schema;
  $("schemaEditor").value = JSON.stringify(schema, null, 2);
  $("schemaMeta").innerHTML = `
    <div>${schema.description || ""}</div>
    <div>${schema.version} · ${schema.fields.length} 个字段</div>
  `;
  $("fieldList").innerHTML = schema.fields
    .map((field) => `<div class="field-pill"><span>${field.name}</span><span>${field.section || "全文"}</span></div>`)
    .join("");
  await validateCurrentSchema();
}

async function loadExample() {
  const selected = $("exampleSelect").value;
  const example = state.examples.find((item) => item.id === selected) || state.examples[0];
  if (example) $("documentInput").value = example.content;
}

async function extract() {
  const button = $("extractBtn");
  button.disabled = true;
  button.querySelector("span").textContent = "抽取中";
  try {
    const schema = JSON.parse($("schemaEditor").value);
    const quality = await validateCurrentSchema(false);
    if (quality?.status === "blocked") {
      alert("Schema 仍有阻断级问题，请先修正后再抽取。");
      return;
    }
    const response = await postJson("/api/extract", {
      document: $("documentInput").value,
      schema,
      options: {
        enable_llm: $("llmEnabled").checked,
        llm: {
          enabled: $("llmEnabled").checked,
          api_base: $("llmBase").value.trim(),
          model: $("llmModel").value.trim(),
          api_key: $("llmKey").value,
        },
      },
    });
    state.lastResponse = response;
    renderResponse(response);
    activateTab("cleaned");
  } catch (error) {
    alert(error.message);
  } finally {
    button.disabled = false;
    button.querySelector("span").textContent = "抽取";
  }
}

function renderResponse(response) {
  $("cleanedPreview").textContent = response.cleaned_text || "";
  $("jobInfo").textContent = `${response.schema_name} · ${response.metrics.elapsed_ms} ms`;
  renderMetrics(response.metrics);
  renderWarnings(response.warnings || []);
  renderRows(response.results || []);
  renderProfile(response.metrics);
}

function renderMetrics(metrics) {
  const completion = `${Math.round((metrics.completion_rate || 0) * 100)}%`;
  const items = [
    ["完成率", completion],
    ["已抽取", metrics.extracted_fields],
    ["高置信", metrics.high_confidence],
    ["复核", metrics.needs_review],
  ];
  $("metrics").innerHTML = items
    .map(
      ([label, value]) => `
      <div class="metric">
        <div class="metric-value">${value}</div>
        <div class="metric-label">${label}</div>
      </div>`
    )
    .join("");
}

async function validateCurrentSchema(showAlert = true) {
  try {
    const schema = JSON.parse($("schemaEditor").value);
    const report = await postJson("/api/schemas/validate", { schema });
    renderSchemaQuality(report);
    return report;
  } catch (error) {
    $("schemaQuality").innerHTML = `<div class="quality-score"><span class="quality-number">0</span><span class="quality-status">JSON 错误</span></div>`;
    $("schemaIssues").innerHTML = `<div class="issue error">${escapeHtml(error.message)}</div>`;
    if (showAlert) alert(error.message);
    return null;
  }
}

function renderSchemaQuality(report) {
  $("schemaQuality").innerHTML = `
    <div class="quality-score">
      <span class="quality-number">${report.score}</span>
      <span class="quality-status">${report.status} · ${report.field_count} fields</span>
    </div>
    <div>${report.error_count} 错误 · ${report.warning_count} 警告 · ${report.info_count} 提示</div>
  `;
  const issues = (report.issues || []).slice(0, 8);
  $("schemaIssues").innerHTML = issues.length
    ? issues
        .map(
          (issue) => `
          <div class="issue ${issue.severity}">
            <strong>${escapeHtml(issue.field_id || "schema")}</strong> · ${escapeHtml(issue.message)}
            ${issue.suggestion ? `<br><span>${escapeHtml(issue.suggestion)}</span>` : ""}
          </div>`
        )
        .join("")
    : `<div class="issue">未发现明显配置问题。</div>`;
}

function renderProfile(metrics) {
  const strategies = Object.entries(metrics.strategy_counts || {})
    .map(([key, value]) => `${key}: ${value}`)
    .join(" · ");
  const confidence = Object.entries(metrics.confidence_counts || {})
    .map(([key, value]) => `${key}: ${value}`)
    .join(" · ");
  const reviewRate = `${Math.round((metrics.review_rate || 0) * 100)}%`;
  $("profileText").innerHTML = `
    <div>复核率：${reviewRate}</div>
    <div>策略：${escapeHtml(strategies || "无")}</div>
    <div>置信度：${escapeHtml(confidence || "无")}</div>
  `;
}

function renderWarnings(warnings) {
  $("warnings").innerHTML = warnings.map((warning) => `<div class="warning">${escapeHtml(warning)}</div>`).join("");
}

function renderRows(results) {
  $("resultRows").innerHTML = results
    .map((item, index) => {
      const reviewClass = item.needs_review ? "needs-review" : "";
      return `
        <tr class="${reviewClass}" data-index="${index}">
          <td>${escapeHtml(item.name)}</td>
          <td>${escapeHtml(item.value || "")}</td>
          <td><span class="badge ${item.confidence}">${item.confidence}</span></td>
          <td>${escapeHtml(item.strategy)}</td>
        </tr>`;
    })
    .join("");
  document.querySelectorAll("#resultRows tr").forEach((row) => {
    row.addEventListener("click", () => selectEvidence(Number(row.dataset.index)));
  });
  applyResultFilters();
}

function applyResultFilters() {
  const query = $("resultSearch").value.trim().toLowerCase();
  const confidence = $("confidenceFilter").value;
  document.querySelectorAll("#resultRows tr").forEach((row) => {
    const item = state.lastResponse?.results?.[Number(row.dataset.index)];
    if (!item) return;
    const text = `${item.name} ${item.value} ${item.strategy}`.toLowerCase();
    const matchesQuery = !query || text.includes(query);
    const matchesConfidence = !confidence || item.confidence === confidence;
    const matchesReview = !state.reviewOnly || item.needs_review;
    row.classList.toggle("hidden-review", !(matchesQuery && matchesConfidence && matchesReview));
  });
}

function selectEvidence(index) {
  const item = state.lastResponse.results[index];
  const evidence = item.source_sentence || item.rationale || "无证据句";
  $("evidenceText").textContent = evidence;
  if (!item.source_sentence) return;
  const clean = state.lastResponse.cleaned_text || "";
  const escaped = escapeHtml(clean);
  const needle = escapeHtml(item.source_sentence);
  $("cleanedPreview").innerHTML = escaped.replace(needle, `<mark>${needle}</mark>`);
  activateTab("cleaned");
}

function activateTab(tab) {
  document.querySelectorAll(".tab").forEach((button) => button.classList.toggle("active", button.dataset.tab === tab));
  document.querySelectorAll(".tab-pane").forEach((pane) => pane.classList.remove("active"));
  const target = tab === "input" ? "documentInput" : tab === "cleaned" ? "cleanedPreview" : "schemaEditor";
  $(target).classList.add("active");
}

function toggleReviewOnly() {
  state.reviewOnly = !state.reviewOnly;
  $("reviewOnlyBtn").classList.toggle("active", state.reviewOnly);
  applyResultFilters();
}

function exportJson() {
  if (!state.lastResponse) return;
  const blob = new Blob([JSON.stringify(state.lastResponse, null, 2)], { type: "application/json;charset=utf-8" });
  downloadBlob(blob, `medstruct-${state.lastResponse.job_id}.json`);
}

function exportCsv() {
  if (!state.lastResponse) return;
  const rows = [
    ["field_id", "name", "value", "confidence", "strategy", "needs_review", "source_sentence"],
    ...state.lastResponse.results.map((item) => [
      item.field_id,
      item.name,
      item.value || "",
      item.confidence,
      item.strategy,
      String(item.needs_review),
      item.source_sentence || "",
    ]),
  ];
  const csv = rows.map((row) => row.map(csvCell).join(",")).join("\n");
  const blob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8" });
  downloadBlob(blob, `medstruct-${state.lastResponse.job_id}.csv`);
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function csvCell(value) {
  const text = String(value ?? "");
  return `"${text.replaceAll('"', '""')}"`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

init().catch((error) => alert(error.message));
