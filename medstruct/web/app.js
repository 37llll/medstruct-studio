const state = {
  schemas: [],
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
  await loadSchema(state.schemas[0].id);
  await loadExample();
  if (window.lucide) window.lucide.createIcons();
}

function bindEvents() {
  $("schemaSelect").addEventListener("change", (event) => loadSchema(event.target.value));
  $("loadExampleBtn").addEventListener("click", loadExample);
  $("extractBtn").addEventListener("click", extract);
  $("exportBtn").addEventListener("click", exportJson);
  $("reviewOnlyBtn").addEventListener("click", toggleReviewOnly);
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
}

async function loadExample() {
  const data = await getJson("/api/examples");
  const dirty = data.examples.find((item) => item.id === "dirty_payload");
  const clean = data.examples.find((item) => item.id === "stroke_admission");
  $("documentInput").value = (clean || dirty || data.examples[0]).content;
}

async function extract() {
  const button = $("extractBtn");
  button.disabled = true;
  button.querySelector("span").textContent = "抽取中";
  try {
    const schema = JSON.parse($("schemaEditor").value);
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
}

function renderMetrics(metrics) {
  const items = [
    ["字段", metrics.total_fields],
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

function renderWarnings(warnings) {
  $("warnings").innerHTML = warnings.map((warning) => `<div class="warning">${escapeHtml(warning)}</div>`).join("");
}

function renderRows(results) {
  $("resultRows").innerHTML = results
    .map((item, index) => {
      const reviewClass = item.needs_review ? "needs-review" : "";
      const hidden = state.reviewOnly && !item.needs_review ? "hidden-review" : "";
      return `
        <tr class="${reviewClass} ${hidden}" data-index="${index}">
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
  if (state.lastResponse) renderRows(state.lastResponse.results);
}

function exportJson() {
  if (!state.lastResponse) return;
  const blob = new Blob([JSON.stringify(state.lastResponse, null, 2)], { type: "application/json;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `medstruct-${state.lastResponse.job_id}.json`;
  link.click();
  URL.revokeObjectURL(url);
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
