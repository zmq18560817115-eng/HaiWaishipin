const state = {
  view: "materials",
  items: [],
  products: [],
  templates: [],
  selectedMaterialId: null,
  selectedProductId: null,
  selectedFeedbackSlug: null,
  scriptSlug: null,
  showAllMaterials: false,
  selectedAudience: [],
  selectedScenarios: [],
  lastPreview: null,
  tagPoolExtra: { audience: [], scenarios: [], selling: [], pains: [] },
  filters: { category: "", q: "", analyzedOnly: false },
  jobPoll: null,
  healthCache: null,
};

const SCENARIO_GROUPS = [
  { id: "bedroom", keys: ["卧室", "夜间", "夜奶"] },
  { id: "car", keys: ["车内", "杯架"] },
  { id: "travel", keys: ["机场", "旅途", "长途"] },
  { id: "outdoor", keys: ["公园", "遛娃"] },
  { id: "office", keys: ["办公室", "背奶"] },
  { id: "public", keys: ["餐厅", "商场", "临时冲奶"] },
];

function scenarioConflictNote(tags) {
  const groups = [];
  for (const tag of tags || []) {
    const g = SCENARIO_GROUPS.find((x) => x.keys.some((k) => tag.includes(k)));
    if (g && !groups.includes(g.id)) groups.push(g.id);
  }
  if (groups.length <= 1) return "";
  return `已选多个互斥场景，成片将统一按「${tags[0]}」生成，避免卧室/车载等画面冲突。`;
}

const esc = (t) => String(t ?? "").replace(/[&<>"']/g, (c) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
}[c]));

const ANALYSIS_LABELS = {
  hook_3s: "钩子 0-3秒",
  pain_points: "痛点",
  selling_points: "卖点",
  video_structure: "视频结构",
  reusable_template: "可复用模板",
};

const CATEGORY_ZH = {
  bottle_warmer: "便携暖奶/恒温杯",
  breast_pump: "吸奶器",
};

/** 产品资料展示：优先中文段落，口播/英文字段另列 */
function chineseText(text) {
  return parseTagList(text).join("；") || String(text || "");
}

function parseTagList(text) {
  return String(text || "")
    .split(/[；;、\n，,]/)
    .map((s) => s.trim())
    .filter((s) => s.length >= 2 && /[\u4e00-\u9fff]/.test(s));
}

const TAG_GROUPS = {
  audience: {
    field: "target_audience",
    poolKey: "audience",
    savedKey: "audience",
    label: "目标人群（可多选，本页完成）",
    placeholder: "输入人群标签，如：夜奶家庭",
  },
  scenario: {
    field: "usage_scenarios",
    poolKey: "scenarios",
    savedKey: "scenarios",
    label: "投放场景（可多选，本页完成）",
    placeholder: "输入场景标签，如：车内杯架",
  },
  selling: {
    field: "core_selling_points",
    poolKey: "selling",
    savedKey: "selling",
    label: "核心卖点（可多选，本页完成）",
    placeholder: "输入卖点，如：USB-C 充电",
  },
  pain: {
    field: "pain_points",
    poolKey: "pains",
    savedKey: "pains",
    label: "用户痛点（可多选，本页完成）",
    placeholder: "输入痛点，如：外出没热水",
  },
};

function buildTagPool(p, apiTags) {
  const pool = {
    audience: (apiTags?.audience?.length ? apiTags.audience : parseTagList(p.target_audience)),
    scenarios: (apiTags?.scenarios?.length ? apiTags.scenarios : parseTagList(p.usage_scenarios)),
    selling: (apiTags?.selling?.length ? apiTags.selling : parseTagList(p.core_selling_points)),
    pains: (apiTags?.pains?.length ? apiTags.pains : parseTagList(p.pain_points)),
  };
  for (const key of ["audience", "scenarios", "selling", "pains"]) {
    for (const t of state.tagPoolExtra[key] || []) {
      if (!pool[key].includes(t)) pool[key].push(t);
    }
  }
  return pool;
}

function defaultSelectedTags(pool, saved) {
  const pick = (poolKey, savedKey) => {
    const list = (saved?.[savedKey] || []).filter((t) => pool[poolKey].includes(t));
    return list.length ? list : (pool[poolKey][0] ? [pool[poolKey][0]] : []);
  };
  return {
    audience: pick("audience", "audience"),
    scenarios: pick("scenarios", "scenarios"),
    selling: pick("selling", "selling"),
    pains: pick("pains", "pains"),
  };
}

function readAllSelectedTags() {
  return {
    audience: readSelectedTags("audience"),
    scenarios: readSelectedTags("scenario"),
    selling: readSelectedTags("selling"),
    pains: readSelectedTags("pain"),
  };
}

function formatStoryboardHtml(storyboard) {
  const shots = storyboard || [];
  if (!shots.length) return '<p class="muted">暂无分镜</p>';
  return shots.map((s) => `
    <div class="shot-block">
      <strong>第 ${s.number} 镜 · ${esc(s.role || "")}（${esc(s.timing || "")}）</strong>
      <p><span class="pack-label">画面</span>${esc(s.visual || "")}</p>
      <p><span class="pack-label">口播（英文）</span>${esc(s.voiceover_en || "")}</p>
      <p><span class="pack-label">字幕（英文）</span>${esc(s.subtitle_en || "")}</p>
      ${s.visual_prompt ? `<p><span class="pack-label">构图提示</span>${esc(s.visual_prompt)}</p>` : ""}
      ${s.seedance_prompt ? `<p><span class="pack-label">空镜提示（英文）</span>${esc(s.seedance_prompt)}</p>` : ""}
    </div>`).join("");
}

function formatPackResult(pack) {
  const broll = (pack.seedance_prompts || []).filter(Boolean);
  const m = pack.inputs?.market || {};
  const tagSummary = [
    m.audience_tags?.length ? `人群：${m.audience_tags.join("、")}` : "",
    m.scenario_tags?.length ? `场景：${m.scenario_tags.join("、")}` : "",
    m.selling_tags?.length ? `卖点：${m.selling_tags.join("、")}` : "",
    m.pain_tags?.length ? `痛点：${m.pain_tags.join("、")}` : "",
  ].filter(Boolean).join(" · ");
  const sceneNote = pack.inputs?.scenario_primary
    ? `全片统一场景：${pack.inputs.scenario_primary}`
    : "";
  const sceneWarn = pack.inputs?.scenario_conflict_note;
  return `
    <h3>脚本已生成</h3>
    ${tagSummary ? `<p class="muted">本次定制下发：${esc(tagSummary)}</p>` : ""}
    ${sceneNote ? `<p class="muted">${esc(sceneNote)}</p>` : ""}
    ${sceneWarn ? `<p class="workflow-warn">${esc(sceneWarn)}</p>` : ""}
    <div class="script-pack">
      <div class="pack-row"><span>英文标题</span><p>${esc(pack.title || "")}</p></div>
      <div class="pack-row"><span>英文副标题</span><p>${esc(pack.subtitle || "")}</p></div>
      <div class="pack-row"><span>完整口播（英文）</span><p>${esc(pack.voiceover_20s || "")}</p></div>
      <div class="pack-row"><span>分镜脚本</span><div class="shot-list">${formatStoryboardHtml(pack.storyboard)}</div></div>
      ${broll.length ? `<div class="pack-row"><span>空镜提示词（英文）</span><pre>${esc(broll.join("\n\n"))}</pre></div>` : ""}
    </div>
    <p class="muted">下一步：点击「完成交付」生成英文字幕与交付包</p>`;
}

function syncFinishButton(canFinish, delivered) {
  const btn = document.getElementById("scriptFinishBtn");
  if (!btn) return;
  btn.disabled = !canFinish;
  if (!canFinish) {
    btn.textContent = "完成交付";
    btn.title = "请先生成脚本";
  } else if (delivered) {
    btn.textContent = "更新交付";
    btn.title = "脚本已更新时可重新生成交付包";
  } else {
    btn.textContent = "完成交付";
    btn.title = "生成英文字幕与交付 zip";
  }
}

function slugFor(linkId) {
  return `ref-${String(linkId).padStart(3, "0")}`;
}

function readSelectedTags(group) {
  return [...document.querySelectorAll(`.tag-chip[data-group="${group}"].active`)].map((b) => b.dataset.value);
}

function renderTagRow(containerId, options, selected, group) {
  const el = document.getElementById(containerId);
  if (!el) return;
  if (!options.length) {
    el.innerHTML = '<span class="muted">暂无标签，请在下方输入并添加</span>';
    return;
  }
  el.innerHTML = options.map((t) =>
    `<button type="button" class="tag-chip ${selected.includes(t) ? "active" : ""}" data-group="${group}" data-value="${esc(t)}">${esc(t)}</button>`
  ).join("");
}

function renderProductPanel(p, apiTags, savedTags) {
  const pool = buildTagPool(p, apiTags);
  const selected = defaultSelectedTags(pool, savedTags);
  state.selectedAudience = selected.audience;
  state.selectedScenarios = selected.scenarios;
  state.currentTagPool = pool;
  const panel = document.getElementById("scriptProduct");
  const groupsHtml = Object.entries(TAG_GROUPS).map(([group, cfg]) => `
    <div class="tag-group">
      <span class="tag-group-label">${cfg.label}</span>
      <div id="${group}TagRow" class="tag-row"></div>
      <div class="tag-add-row">
        <input type="text" class="tag-input" data-group="${group}" placeholder="${cfg.placeholder}">
        <button type="button" class="tag-add-btn" data-group="${group}">添加</button>
      </div>
    </div>`).join("");
  panel.innerHTML = `<p class="product-head">${esc(p.product_name || p.product_id || "产品")}</p>
    <p id="scenarioConflictWarn" class="workflow-warn hidden"></p>${groupsHtml}`;
  renderTagRow("audienceTagRow", pool.audience, selected.audience, "audience");
  renderTagRow("scenarioTagRow", pool.scenarios, selected.scenarios, "scenario");
  renderTagRow("sellingTagRow", pool.selling, selected.selling, "selling");
  renderTagRow("painTagRow", pool.pains, selected.pains, "pain");
  const conflict = scenarioConflictNote(selected.scenarios);
  const warn = document.getElementById("scenarioConflictWarn");
  if (warn) {
    if (conflict) {
      warn.classList.remove("hidden");
      warn.textContent = conflict;
    } else {
      warn.classList.add("hidden");
      warn.textContent = "";
    }
  }
}

async function persistProductTags(productId, field, tags) {
  const body = {};
  body[field] = tags.join("；");
  await api(`/api/products/${encodeURIComponent(productId)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const p = state.products.find((x) => x.product_id === productId);
  if (p) p[field] = body[field];
}

async function addTagInline(group, rawText) {
  const text = String(rawText || "").trim();
  if (!text || text.length < 2) return;
  const cfg = TAG_GROUPS[group];
  if (!cfg) return;
  const productId = document.getElementById("scriptProductSelect").value;
  const pool = state.currentTagPool || { audience: [], scenarios: [], selling: [], pains: [] };
  const list = [...(pool[cfg.poolKey] || [])];
  if (!list.includes(text)) list.push(text);
  if (!state.tagPoolExtra[cfg.poolKey]) state.tagPoolExtra[cfg.poolKey] = [];
  state.tagPoolExtra[cfg.poolKey] = [...new Set([...state.tagPoolExtra[cfg.poolKey], text])];
  try {
    await persistProductTags(productId, cfg.field, list);
  } catch (err) {
    console.warn("标签保存失败", err);
  }
  const p = state.products.find((x) => x.product_id === productId) || state.lastPreview?.product || {};
  const selected = readAllSelectedTags();
  const savedKey = cfg.savedKey;
  if (!selected[savedKey].includes(text)) selected[savedKey].push(text);
  renderProductPanel(p, buildTagPool(p, state.lastPreview?.delivery_tags), selected);
  updateLoopBarFromForm(state.lastPreview || {});
}

function updateLoopBarFromForm(prev = {}) {
  const bar = document.getElementById("scriptLoopBar");
  const hint = document.getElementById("loopHint");
  if (!bar) return;
  const sel = readAllSelectedTags();
  const steps = {
    material: Boolean(document.getElementById("scriptMaterialSelect")?.value),
    product: Boolean(document.getElementById("scriptProductSelect")?.value),
    tags: sel.audience.length > 0 && sel.scenarios.length > 0
      && sel.selling.length > 0 && sel.pains.length > 0,
    script: Boolean(prev.has_script),
    delivery: Boolean(prev.delivery_ready),
  };
  const order = ["material", "product", "tags", "script", "delivery"];
  let current = "delivery";
  for (const key of order) {
    if (!steps[key]) {
      current = key;
      break;
    }
  }
  bar.querySelectorAll("li").forEach((li) => {
    const key = li.dataset.step;
    li.classList.remove("done", "current");
    if (steps[key]) li.classList.add("done");
    else if (key === current) li.classList.add("current");
  });
  if (hint) {
    if (steps.delivery) {
      hint.textContent = "闭环完成：可下载 zip；重新生成脚本后可点「更新交付」刷新包。";
    } else if (steps.script) {
      hint.textContent = "脚本已生成 → 点击「完成交付」→ 成稿入库。";
    } else if (!steps.tags) {
      hint.textContent = "请在下方为人群、场景、核心卖点、用户痛点各至少点选一个标签，再生成脚本。";
    } else {
      hint.textContent = "预览确认后点击「生成脚本」。";
    }
  }
}

async function api(path, options) {
  const res = await fetch(path, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText);
  return data;
}

function debounce(fn, ms = 280) {
  let t;
  return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
}

function fmtNum(n) {
  const v = Number(n);
  if (!Number.isFinite(v) || v <= 0) return "";
  if (v >= 10000) return `${(v / 10000).toFixed(1)}万`;
  return String(v);
}

function scriptResultEl() {
  return document.getElementById("scriptResult");
}

function scriptResultBody() {
  return document.querySelector("#scriptResult .output-body");
}

// ── Navigation ─────────────────────────────────────────────────────────────

function switchView(name) {
  state.view = name;
  document.querySelectorAll(".view").forEach((el) => el.classList.remove("active"));
  document.getElementById(`view${name.charAt(0).toUpperCase()}${name.slice(1)}`)?.classList.add("active");
  document.querySelectorAll("#mainNav button").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.view === name);
  });
  if (name === "products") loadProductsView();
  if (name === "script") loadScriptView();
  if (name === "finished") loadFinishedView();
  if (name === "feedback") loadFeedbackView();
  if (name === "settings") loadSettingsView();
}

document.getElementById("mainNav").addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-view]");
  if (btn) switchView(btn.dataset.view);
});

// ── Health / stats ───────────────────────────────────────────────────────

async function refreshHealth() {
  const h = await api("/api/health");
  state.healthCache = h;
  document.getElementById("statMaterials").textContent = h.materials;
  document.getElementById("statAnalyzed").textContent = h.analyzed;
  return h;
}

function renderSeedanceSettings(health) {
  const el = document.getElementById("seedanceSettingsStatus");
  if (!el) return;
  const sd = health?.seedance || {};
  if (!sd.configured) {
    el.innerHTML = `未配置 · 双击 <strong>配置SeedDance.cmd</strong> 填写 <code>FAL_KEY</code><br><span class="muted">${esc(sd.setup || "")}</span>`;
    return;
  }
  el.innerHTML = `已配置 fal.ai · 模型 <code>${esc(sd.text_model || "")}</code>`;
}

function renderSeedance(slug, seedance, health) {
  const panel = document.getElementById("seedancePanel");
  const statusEl = document.getElementById("seedanceStatus");
  const runBtn = document.getElementById("btnSeedanceRun");
  if (!panel || !statusEl) return;

  const configured = health?.seedance?.configured;
  const pipeline = seedance?.pipeline || health?.seedance?.label || "";
  document.getElementById("seedancePipeline").textContent = pipeline;

  if (!slug || !seedance) {
    panel.classList.add("hidden");
    return;
  }

  panel.classList.remove("hidden");

  if (!configured) {
    statusEl.innerHTML = `未连接 · 请双击 <strong>配置SeedDance.cmd</strong> 填写 <code>FAL_KEY</code> 后重启工作台`;
    document.getElementById("seedanceShots").innerHTML = "";
    if (runBtn) runBtn.disabled = true;
    document.getElementById("seedanceHint").textContent = health?.seedance?.setup || "";
    return;
  }

  statusEl.innerHTML = `已连接 fal.ai · 模型 <code>${esc(health.seedance.text_model || "")}</code>`;
  if (runBtn) runBtn.disabled = false;

  if (!seedance.available) {
    document.getElementById("seedanceShots").innerHTML =
      '<p class="muted">当前项目无 AI 空镜镜头。规则模板会在痛点镜生成 AI_BROLL 空镜。</p>';
    document.getElementById("seedanceHint").textContent = "可先点「测试连接」验证密钥";
    if (runBtn) runBtn.disabled = true;
    return;
  }

  document.getElementById("seedanceHint").textContent =
    "生成后 mp4 保存在项目 broll/ 目录，并随 zip 一并下载";
  document.getElementById("seedanceShots").innerHTML = (seedance.shots || []).map((s) => {
    const status = s.ready
      ? `<a href="/api/delivery/${encodeURIComponent(slug)}/files/${encodeURI(s.file)}" target="_blank">预览 / 下载 mp4</a>`
      : '<span class="muted">待生成</span>';
    return `<div class="seedance-shot">
      <strong>镜 ${esc(s.number)} · ${esc(s.timing)}</strong>
      <p class="muted">${esc((s.prompt || "（无 Prompt）").slice(0, 200))}</p>
      ${status}
    </div>`;
  }).join("");
}

async function loadSeedanceForSlug(slug) {
  if (!slug) return;
  const health = state.healthCache || await refreshHealth();
  try {
    const seedance = await api(`/api/delivery/${encodeURIComponent(slug)}/seedance`);
    renderSeedance(slug, seedance, health);
  } catch (err) {
    renderSeedance(slug, { available: false, shots: [] }, health);
    const hint = document.getElementById("seedanceHint");
    if (hint) hint.textContent = err.message;
  }
}

// ── Materials ────────────────────────────────────────────────────────────

async function loadFilters() {
  const data = await api("/api/filters");
  state.products = data.products || [];
  const cs = document.getElementById("categorySelect");
  cs.innerHTML = '<option value="">全部</option>';
  (data.categories || []).forEach((c) => {
    const o = document.createElement("option");
    o.value = c;
    o.textContent = CATEGORY_ZH[c] || c;
    cs.appendChild(o);
  });
}

async function loadMaterials() {
  const p = new URLSearchParams();
  if (state.filters.category) p.set("category", state.filters.category);
  if (state.filters.q) p.set("q", state.filters.q);
  if (state.filters.analyzedOnly) p.set("analyzed_only", "true");
  state.items = (await api(`/api/materials?${p}`)).items || [];
  renderMaterialList();
}

function renderMaterialList() {
  const root = document.getElementById("materialList");
  if (!state.items.length) {
    root.innerHTML = '<div class="detail-empty">无匹配素材。请先在「设置」同步 TikTok。</div>';
    return;
  }
  root.innerHTML = state.items.map((item) => {
    const active = item.link_id === state.selectedMaterialId ? "active" : "";
    const thumb = item.thumbnail_url
      ? `<img class="thumb" src="${esc(item.thumbnail_url)}" alt="">`
      : '<div class="thumb placeholder">无图</div>';
    const stats = [fmtNum(item.view_count) && `${fmtNum(item.view_count)}播放`, item.duration_sec && `${item.duration_sec}s`].filter(Boolean).join(" · ");
    const badge = item.has_analysis
      ? '<span class="badge">已拆解</span>'
      : '<span class="badge missing">待拆解</span>';
    return `<button type="button" class="card ${active}" data-id="${item.link_id}">
      ${thumb}
      <div><h3>#${item.link_id} ${esc((item.title || "").slice(0, 55))}</h3>
      <div class="meta">${esc(item.author)}${stats ? ` · ${stats}` : ""}</div>${badge}</div>
    </button>`;
  }).join("");
  root.querySelectorAll(".card").forEach((c) =>
    c.addEventListener("click", () => selectMaterial(Number(c.dataset.id)))
  );
}

async function selectMaterial(linkId) {
  state.selectedMaterialId = linkId;
  renderMaterialList();
  const pane = document.getElementById("materialDetail");
  pane.innerHTML = "加载中…";
  try {
    const d = await api(`/api/materials/${linkId}`);
    const a = d.analysis || {};
    pane.className = "detail";
    pane.innerHTML = `
      <h3>#${d.link_id} ${esc((d.title || "").slice(0, 80))}</h3>
      <p class="meta">${esc(d.author)} · ${fmtNum(d.view_count) || "-"} 播放 · ${d.duration_sec || "-"}s</p>
      <a href="${esc(d.url)}" target="_blank" rel="noopener">打开 TikTok</a>
      <div class="analysis-grid">
        ${["hook_3s", "pain_points", "selling_points", "video_structure", "reusable_template"].map((k) => `
          <div class="field"><label>${ANALYSIS_LABELS[k] || k}</label><p>${esc(a[k] || "—")}</p></div>`).join("")}
      </div>
      <div class="actions row">
        <button type="button" class="primary" id="goScriptBtn">去脚本生成</button>
      </div>`;
    document.getElementById("goScriptBtn").addEventListener("click", () => {
      state.selectedMaterialId = linkId;
      const item = state.items.find((i) => i.link_id === linkId);
      if (item?.content_line) state.selectedProductId = item.content_line;
      switchView("script");
      loadScriptView();
    });
  } catch (err) {
    pane.innerHTML = `<div class="result error">${esc(err.message)}</div>`;
  }
}

// ── Products ─────────────────────────────────────────────────────────────

async function loadProductsView() {
  const data = await api("/api/products");
  state.products = data.items || [];
  const root = document.getElementById("productList");
  if (!state.products.length) {
    root.innerHTML = '<div class="detail-empty">暂无产品，请在设置同步产品资料</div>';
    return;
  }
  if (!state.selectedProductId) {
    const def = state.products.find((p) => p.product_id === "便携恒温杯") || state.products[0];
    state.selectedProductId = def.product_id;
  }
  root.innerHTML = state.products.map((p) => `
    <button type="button" class="card compact ${p.product_id === state.selectedProductId ? "active" : ""}" data-pid="${esc(p.product_id)}">
      <div><h3>${esc(p.product_name || p.product_id)}</h3>
      <div class="meta">${esc(p.product_id)}</div></div>
    </button>`).join("");
  root.querySelectorAll(".card").forEach((c) =>
    c.addEventListener("click", () => { state.selectedProductId = c.dataset.pid; loadProductsView(); })
  );
  renderProductEditor();
}

function renderProductEditor() {
  const pane = document.getElementById("productEditor");
  const p = state.products.find((x) => x.product_id === state.selectedProductId);
  if (!p) { pane.innerHTML = "选择左侧产品"; return; }
  const fields = [
    ["product_name", "产品名称"],
    ["target_audience", "目标人群"],
    ["core_selling_points", "核心卖点"],
    ["pain_points", "痛点"],
    ["usage_scenarios", "使用场景"],
    ["forbidden_terms", "禁用词"],
    ["price_range", "价格带"],
    ["competitor_ref", "竞品参考"],
  ];
  pane.className = "detail";
  pane.innerHTML = `
    <form id="productForm" class="form-grid">
      ${fields.map(([k, label]) => `
        <label>${label}<textarea name="${k}" rows="${k.includes("points") || k.includes("terms") ? 4 : 2}">${esc(p[k] || "")}</textarea></label>`).join("")}
      <button type="submit" class="primary">保存</button>
      <p id="productSaveHint" class="muted"></p>
    </form>`;
  document.getElementById("productForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const body = Object.fromEntries(fd.entries());
    const hint = document.getElementById("productSaveHint");
    try {
      await api(`/api/products/${encodeURIComponent(p.product_id)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      hint.textContent = "已保存";
      await loadProductsView();
    } catch (err) {
      hint.textContent = err.message;
    }
  });
}

// ── Script generation ────────────────────────────────────────────────────

function materialMatchesProduct(item, productId) {
  return !item.content_line || item.content_line === productId;
}

function materialOptionsHtml(productId) {
  const analyzed = state.items.filter((i) => i.has_analysis);
  const pool = state.showAllMaterials
    ? analyzed
    : analyzed.filter((i) => materialMatchesProduct(i, productId));
  const sorted = [...pool].sort((a, b) => a.link_id - b.link_id);
  return sorted.map((i) =>
    `<option value="${i.link_id}" ${i.link_id === state.selectedMaterialId ? "selected" : ""}>#${i.link_id} ${esc((i.title || "").slice(0, 42))}</option>`
  ).join("");
}

function pickDefaultMaterialId(pool) {
  const prefer = (pred) => pool.find(pred);
  const hit = prefer((i) => i.link_id === state.selectedMaterialId)
    || prefer((i) => i.has_script && !i.delivery_ready)
    || prefer((i) => !i.delivery_ready)
    || pool[0];
  return hit?.link_id;
}

function repopulateScriptMaterials() {
  const ms = document.getElementById("scriptMaterialSelect");
  const productId = document.getElementById("scriptProductSelect").value;
  const prev = Number(ms.value);
  const analyzed = state.items.filter((i) => i.has_analysis);
  const pool = state.showAllMaterials
    ? analyzed
    : analyzed.filter((i) => materialMatchesProduct(i, productId));
  const hint = document.getElementById("materialFilterHint");
  if (hint) {
    hint.textContent = state.showAllMaterials
      ? `共 ${analyzed.length} 条`
      : `已筛 ${pool.length} 条同品类`;
  }
  ms.innerHTML = materialOptionsHtml(productId);
  const still = [...ms.options].some((o) => Number(o.value) === prev);
  if (still) ms.value = String(prev);
  else {
    const pick = pickDefaultMaterialId(pool);
    if (pick) ms.value = String(pick);
    else if (ms.options.length) ms.selectedIndex = 0;
  }
}

async function loadScriptView() {
  if (!state.items.length) await loadMaterials();
  const showAll = document.getElementById("showAllMaterials");
  if (showAll) showAll.checked = state.showAllMaterials;
  const ps = document.getElementById("scriptProductSelect");
  const ms = document.getElementById("scriptMaterialSelect");
  if (!state.products.length) {
    const pr = await api("/api/products");
    state.products = pr.items || [];
  }
  ps.innerHTML = state.products.map((p) =>
    `<option value="${p.product_id}">${esc(p.product_name)}</option>`
  ).join("");
  if (state.selectedProductId) {
    ps.value = state.selectedProductId;
  } else {
    const thermos = state.products.find((p) => p.product_id === "便携恒温杯");
    if (thermos) ps.value = thermos.product_id;
  }
  repopulateScriptMaterials();
  if (state.selectedMaterialId && ms.querySelector(`option[value="${state.selectedMaterialId}"]`)) {
    ms.value = String(state.selectedMaterialId);
  }
  await refreshScriptPreview();
}

async function refreshScriptPreview() {
  const linkId = Number(document.getElementById("scriptMaterialSelect").value);
  const productId = document.getElementById("scriptProductSelect").value;
  state.selectedMaterialId = linkId;
  const analysisEl = document.getElementById("scriptAnalysis");
  const productEl = document.getElementById("scriptProduct");
  const templateEl = document.getElementById("scriptTemplate");
  const resultWrap = scriptResultEl();
  try {
    const prev = await api(`/api/materials/${linkId}/preview?product_id=${encodeURIComponent(productId)}`);
    state.lastPreview = prev;
    state.scriptSlug = prev.slug;

    const warnEl = document.getElementById("scriptMismatchWarn");
    const mismatch = prev.product_match === false;
    if (mismatch) {
      warnEl.classList.remove("hidden");
      warnEl.textContent =
        `品类不一致：参考偏「${prev.content_line || "其他"}」，产品为「${productId}」。建议换同品类参考，或勾选「显示其他品类」后确认再生成。`;
    } else {
      warnEl.classList.add("hidden");
      warnEl.textContent = "";
    }
    const a = prev.material?.analysis || {};
    const brandHint = prev.brand_product && mismatch
      ? `<p class="brand-hint muted">成片品牌：${esc(prev.brand_product)}</p>`
      : "";
    analysisEl.innerHTML = `${brandHint}<div class="field-list">
      <div class="field"><label>钩子 0-3s</label><p>${esc(a.hook_3s)}</p></div>
      <div class="field"><label>痛点</label><p>${esc(a.pain_points)}</p></div>
      <div class="field"><label>卖点</label><p>${esc(a.selling_points)}</p></div>
      <div class="field"><label>结构</label><p>${esc(a.video_structure)}</p></div>
      <div class="field"><label>字幕布局</label><p>${esc(a.subtitle_layout)}</p></div>
    </div>`;
    const p = prev.product || {};
    renderProductPanel(p, prev.delivery_tags || {}, prev.selected_tags || {});
    updateLoopBarFromForm(prev);
    const t = prev.template || {};
    templateEl.innerHTML = `
      <p class="product-head">${esc(t.label || t.template_id)}</p>
      <div class="field-list">
      <div class="field"><label>结构链</label><p>${esc(t.structure_chain)}</p></div>
      <div class="field"><label>适用类型</label><p>${esc(t.suitable_for)}</p></div>
      <div class="field"><label>结构说明</label><p>${esc(prev.template_hint)}</p></div>
      </div>`;
    const dl = document.getElementById("scriptDownloadBtn");
    if (prev.delivery_ready) {
      dl.href = `/api/delivery/${prev.slug}/zip`;
      dl.classList.remove("hidden");
    } else {
      dl.classList.add("hidden");
    }
    if (prev.has_script && prev.script_pack) {
      resultWrap.classList.remove("hidden");
      scriptResultBody().innerHTML = formatPackResult(prev.script_pack);
    }
    syncFinishButton(Boolean(prev.can_finish), Boolean(prev.delivery_ready));
    if (prev.has_script || prev.project_ready) {
      await loadSeedanceForSlug(prev.slug);
    } else {
      renderSeedance(null, null, state.healthCache);
    }
  } catch (err) {
    analysisEl.innerHTML = `<div class="result error">${esc(err.message)}</div>`;
    productEl.innerHTML = "";
    templateEl.innerHTML = "";
    const lp = state.lastPreview || {};
    syncFinishButton(Boolean(lp.can_finish), Boolean(lp.delivery_ready));
  }
}

function onScriptSelectionChange() {
  state.selectedProductId = document.getElementById("scriptProductSelect").value;
  state.tagPoolExtra = { audience: [], scenarios: [], selling: [], pains: [] };
  scriptResultEl().classList.add("hidden");
  document.getElementById("seedancePanel")?.classList.add("hidden");
}

document.getElementById("scriptMaterialSelect").addEventListener("change", async () => {
  state.selectedMaterialId = Number(document.getElementById("scriptMaterialSelect").value);
  onScriptSelectionChange();
  await refreshScriptPreview();
});
document.getElementById("scriptProductSelect").addEventListener("change", async () => {
  state.selectedProductId = document.getElementById("scriptProductSelect").value;
  onScriptSelectionChange();
  repopulateScriptMaterials();
  await refreshScriptPreview();
});
document.getElementById("showAllMaterials").addEventListener("change", async (e) => {
  state.showAllMaterials = e.target.checked;
  repopulateScriptMaterials();
  await refreshScriptPreview();
});

document.getElementById("scriptGenerateBtn").addEventListener("click", async () => {
  const linkId = Number(document.getElementById("scriptMaterialSelect").value);
  const productId = document.getElementById("scriptProductSelect").value;
  const audienceTags = readSelectedTags("audience");
  const scenarioTags = readSelectedTags("scenario");
  const sellingTags = readSelectedTags("selling");
  const painTags = readSelectedTags("pain");
  const btn = document.getElementById("scriptGenerateBtn");
  const resultWrap = scriptResultEl();
  const resultEl = scriptResultBody();
  if (!audienceTags.length || !scenarioTags.length || !sellingTags.length || !painTags.length) {
    resultWrap.classList.remove("hidden");
    resultEl.innerHTML = '<div class="result error">请为人群、场景、核心卖点、用户痛点各至少选择一个标签后再生成。</div>';
    return;
  }
  btn.disabled = true;
  resultWrap.classList.remove("hidden");
  resultEl.innerHTML = "正在生成脚本…";
  try {
    const res = await api(`/api/materials/${linkId}/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        product_id: productId,
        bridge: true,
        target_country: "US",
        language: "en",
        style: "us_tiktok_spoken",
        audience_tags: audienceTags,
        scenario_tags: scenarioTags,
        selling_tags: sellingTags,
        pain_tags: painTags,
      }),
    });
    const pack = res.script_pack || res.pack || {};
    state.scriptSlug = res.slug || slugFor(linkId);
    resultEl.innerHTML = formatPackResult(pack);
    syncFinishButton(true, Boolean(state.lastPreview?.delivery_ready));
    await refreshScriptPreview();
  } catch (err) {
    resultEl.innerHTML = `<div class="result error">${esc(err.message)}</div>`;
  } finally {
    btn.disabled = false;
  }
});

document.getElementById("scriptFinishBtn").addEventListener("click", async () => {
  const slug = state.scriptSlug;
  if (!slug) return;
  const btn = document.getElementById("scriptFinishBtn");
  const resultWrap = scriptResultEl();
  const resultEl = scriptResultBody();
  btn.disabled = true;
  resultWrap.classList.remove("hidden");
  resultEl.textContent = "正在生成交付包（英文字幕 + 脚本包）…";
  try {
    const res = await api(`/api/delivery/${slug}/finish`, { method: "POST" });
    resultEl.innerHTML = `<div class="result">交付完成：${esc(res.message || "字幕与交付包已生成")}
      <p class="muted">可在下方 SeedDance 面板生成 AI 空镜（需配置 FAL_KEY）。</p>
      <p class="loop-next">
        <button type="button" class="text-link" id="goFinishedBtn">打开成稿库</button>
        ·
        <button type="button" class="text-link" id="goFeedbackBtn">填写投放反馈</button>
      </p></div>`;
    document.getElementById("goFinishedBtn")?.addEventListener("click", () => switchView("finished"));
    document.getElementById("goFeedbackBtn")?.addEventListener("click", () => {
      state.selectedFeedbackSlug = slug;
      switchView("feedback");
    });
    const dl = document.getElementById("scriptDownloadBtn");
    dl.href = `/api/delivery/${slug}/zip`;
    dl.classList.remove("hidden");
    await refreshScriptPreview();
    await refreshHealth();
  } catch (err) {
    resultEl.innerHTML = `<div class="result error">${esc(err.message)}</div>`;
    await refreshScriptPreview();
  }
});

// ── Finished library ───────────────────────────────────────────────────────

async function loadFinishedView() {
  const data = await api("/api/library/finished");
  const items = data.items || [];
  const root = document.getElementById("finishedList");
  if (!items.length) {
    root.innerHTML = '<div class="detail-empty">暂无成稿。在脚本生成页完成交付后会自动入库。</div>';
    return;
  }
  root.innerHTML = `<table class="data-table"><thead><tr>
    <th>项目</th><th>标题</th><th>产品</th><th>保存时间</th><th>操作</th>
  </tr></thead><tbody>${items.map((r) => `
    <tr>
      <td>${esc(r.slug)}</td>
      <td>${esc((r.title || "").slice(0, 48))}</td>
      <td>${esc(r.product_name || r.product_id)}</td>
      <td>${esc((r.saved_at || "").slice(0, 19))}</td>
      <td><a href="/api/delivery/${esc(r.slug)}/zip">下载 zip</a></td>
    </tr>`).join("")}</tbody></table>`;
}

// ── Feedback ─────────────────────────────────────────────────────────────

async function loadFeedbackView() {
  const data = await api("/api/library/feedback");
  const items = data.items || [];
  const root = document.getElementById("feedbackList");
  if (!items.length) {
    root.innerHTML = '<div class="detail-empty">暂无反馈记录</div>';
    return;
  }
  if (!state.selectedFeedbackSlug) state.selectedFeedbackSlug = items[0].slug;
  root.innerHTML = items.map((r) => `
    <button type="button" class="card compact ${r.slug === state.selectedFeedbackSlug ? "active" : ""}" data-slug="${esc(r.slug)}">
      <div><h3>${esc(r.title || r.slug)}</h3>
      <div class="meta">${esc(r.adopted || "待定")} · ${esc((r.updated_at || "").slice(0, 10))}</div></div>
    </button>`).join("");
  root.querySelectorAll(".card").forEach((c) =>
    c.addEventListener("click", () => { state.selectedFeedbackSlug = c.dataset.slug; loadFeedbackView(); })
  );
  renderFeedbackEditor();
}

async function renderFeedbackEditor() {
  const pane = document.getElementById("feedbackEditor");
  const slug = state.selectedFeedbackSlug;
  if (!slug) return;
  try {
    const r = await api(`/api/library/feedback/${encodeURIComponent(slug)}`);
    const pub = r.publish || {};
    pane.className = "detail";
    pane.innerHTML = `
      <h3>${esc(r.title || slug)}</h3>
      <form id="feedbackForm" class="form-grid">
        <label>人工修改<textarea name="manual_edits" rows="4">${esc(r.manual_edits)}</textarea></label>
        <label>采纳状态
          <select name="adopted">
            ${["待定", "已采纳", "未采纳", "修改后采纳"].map((o) =>
              `<option ${r.adopted === o ? "selected" : ""}>${o}</option>`).join("")}
          </select>
        </label>
        <label>播放量<input name="publish_views" value="${esc(pub.views)}"></label>
        <label>互动率<input name="publish_engagement" value="${esc(pub.engagement)}"></label>
        <label>投放备注<textarea name="publish_notes" rows="2">${esc(pub.notes)}</textarea></label>
        <label>备注<textarea name="notes" rows="2">${esc(r.notes)}</textarea></label>
        <button type="submit" class="primary">保存反馈</button>
        <p id="fbHint" class="muted"></p>
      </form>`;
    document.getElementById("feedbackForm").addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      try {
        await api(`/api/library/feedback/${encodeURIComponent(slug)}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            manual_edits: fd.get("manual_edits"),
            adopted: fd.get("adopted"),
            notes: fd.get("notes"),
            publish_views: fd.get("publish_views"),
            publish_engagement: fd.get("publish_engagement"),
            publish_notes: fd.get("publish_notes"),
          }),
        });
        document.getElementById("fbHint").textContent = "已保存";
        await loadFeedbackView();
      } catch (err) {
        document.getElementById("fbHint").textContent = err.message;
      }
    });
  } catch (err) {
    pane.innerHTML = `<div class="result error">${esc(err.message)}</div>`;
  }
}

// ── Settings / jobs ──────────────────────────────────────────────────────

async function loadSettingsView() {
  const h = await api("/api/health");
  state.healthCache = h;
  renderSeedanceSettings(h);
  document.getElementById("envInfo").innerHTML = `
    UI v${h.ui_version} · 素材 ${h.materials} · 产品 ${h.products} · 成稿 ${h.finished}<br>
    LLM: ${h.llm.available ? h.llm.model : h.llm.fallback}<br>
    SeedDance: ${h.seedance?.configured ? "已配置 FAL_KEY" : "未配置（见上方）"}`;
  await pollJobStatus();
}

async function pollJobStatus() {
  const st = await api("/api/jobs/status");
  const el = document.getElementById("jobStatus");
  const log = document.getElementById("jobLog");
  if (st.status === "running") {
    el.textContent = `运行中：${st.job}（${st.started_at || ""}）`;
    log.textContent = st.output || "";
    if (!state.jobPoll) {
      state.jobPoll = setInterval(async () => {
        const s = await api("/api/jobs/status");
        document.getElementById("jobStatus").textContent = s.status === "running"
          ? `运行中：${s.job}` : (s.exit_code === 0 ? `✅ ${s.job} 完成` : `❌ ${s.job} 失败 (code ${s.exit_code})`);
        document.getElementById("jobLog").textContent = s.output || "";
        if (s.status !== "running") {
          clearInterval(state.jobPoll);
          state.jobPoll = null;
          await refreshHealth();
          await loadMaterials();
        }
      }, 2000);
    }
  } else {
    el.textContent = st.job ? `${st.status}: ${st.job}` : "就绪";
    log.textContent = st.output || "";
  }
}

document.querySelectorAll(".job-btn").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const job = btn.dataset.job;
    try {
      await api(`/api/jobs/${job}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ engine: "auto" }),
      });
      document.getElementById("jobStatus").textContent = `已启动：${job}`;
      await pollJobStatus();
    } catch (err) {
      document.getElementById("jobStatus").textContent = err.message;
    }
  });
});

// ── Init ─────────────────────────────────────────────────────────────────

document.getElementById("openProductsBtn")?.addEventListener("click", () => switchView("products"));

document.getElementById("categorySelect").addEventListener("change", (e) => {
  state.filters.category = e.target.value;
  loadMaterials();
});
document.getElementById("keywordInput").addEventListener("input", debounce((e) => {
  state.filters.q = e.target.value.trim();
  loadMaterials();
}));
document.getElementById("analyzedOnly").addEventListener("change", (e) => {
  state.filters.analyzedOnly = e.target.checked;
  loadMaterials();
});

document.getElementById("scriptProduct").addEventListener("click", (e) => {
  const chip = e.target.closest(".tag-chip");
  if (chip) {
    chip.classList.toggle("active");
    updateLoopBarFromForm(state.lastPreview || {});
    if (chip.dataset.group === "scenario") {
      const p = state.products.find((x) => x.product_id === document.getElementById("scriptProductSelect").value)
        || state.lastPreview?.product || {};
      const selected = readAllSelectedTags();
      renderProductPanel(p, buildTagPool(p, state.lastPreview?.delivery_tags), selected);
    }
    return;
  }
  const addBtn = e.target.closest(".tag-add-btn");
  if (addBtn) {
    const group = addBtn.dataset.group;
    const input = document.querySelector(`.tag-input[data-group="${group}"]`);
    addTagInline(group, input?.value);
    if (input) input.value = "";
  }
});

document.getElementById("scriptProduct").addEventListener("keydown", (e) => {
  if (e.key !== "Enter" || !e.target.classList.contains("tag-input")) return;
  e.preventDefault();
  const group = e.target.dataset.group;
  addTagInline(group, e.target.value);
  e.target.value = "";
});

async function runSeedanceTest(hintEl) {
  const target = hintEl || document.getElementById("seedanceHint");
  if (target) target.textContent = "正在测试 fal.ai 连接（约 30–60 秒）…";
  try {
    const data = await api("/api/seedance/test");
    const msg = data.ok
      ? `✅ ${data.message || "连接成功"}`
      : `❌ ${data.message || "连接失败"}`;
    if (target) target.textContent = msg;
    await refreshHealth();
    renderSeedanceSettings(state.healthCache);
    if (state.scriptSlug) await loadSeedanceForSlug(state.scriptSlug);
    return data;
  } catch (err) {
    if (target) target.textContent = `❌ ${err.message}`;
    throw err;
  }
}

document.getElementById("btnSeedanceTest")?.addEventListener("click", () => {
  runSeedanceTest(document.getElementById("seedanceHint"));
});

document.getElementById("btnSeedanceTestSettings")?.addEventListener("click", () => {
  runSeedanceTest(document.getElementById("seedanceSettingsStatus"));
});

document.getElementById("btnSeedanceRun")?.addEventListener("click", async () => {
  const slug = state.scriptSlug;
  if (!slug) return;
  const btn = document.getElementById("btnSeedanceRun");
  const hint = document.getElementById("seedanceHint");
  btn.disabled = true;
  if (hint) hint.textContent = "正在调用 SeedDance 生成空镜，请耐心等待…";
  try {
    const data = await api(`/api/delivery/${encodeURIComponent(slug)}/seedance/run`, { method: "POST" });
    renderSeedance(slug, data.seedance, state.healthCache);
    const failed = (data.results || []).filter((r) => r.status === "error");
    const skipped = (data.results || []).filter((r) => r.status === "skipped");
    if (hint) {
      hint.textContent = failed.length
        ? `部分失败：${failed.map((r) => `镜${r.number} ${r.message}`).join("；")}`
        : skipped.length && !(data.results || []).some((r) => r.status === "ok")
          ? "未生成新视频（可能未配置 FAL_KEY 或镜头已有视频）"
          : "生成完成，可预览 mp4 或重新下载 zip";
    }
    const dl = document.getElementById("scriptDownloadBtn");
    if (dl && !dl.classList.contains("hidden")) {
      dl.href = `/api/delivery/${slug}/zip?ts=${Date.now()}`;
    }
  } catch (err) {
    if (hint) hint.textContent = err.message;
  } finally {
    btn.disabled = false;
  }
});

(async () => {
  await refreshHealth();
  await loadFilters();
  await loadMaterials();
  if (state.items.length) await selectMaterial(state.items[0].link_id);
})();
