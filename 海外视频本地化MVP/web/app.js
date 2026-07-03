const state = {
  view: "generate",
  draftFeedbackSub: "finished",
  feedbackEditorTab: "review",
  items: [],
  products: [],
  templates: [],
  selectedMaterialId: null,
  selectedProductId: null,
  selectedFeedbackSlug: null,
  feedbackHideReviewed: false,
  feedbackTagDefs: null,
  scriptSlug: null,
  showAllMaterials: false,
  selectedAudience: [],
  selectedScenarios: [],
  lastPreview: null,
  tagPoolExtra: { audience: [], scenarios: [], selling: [], pains: [] },
  tagSelection: { audience: [], scenarios: [], selling: [], pains: [] },
  filters: { category: "", q: "", analyzedOnly: true },
  jobPoll: null,
  healthCache: null,
  scriptStep: "product",
  generateStudioTab: "featured",
  imitateStudioTab: "featured",
  selectedScenarioFeature: null,
  generateWorkspaceOpen: false,
  generateDockMode: "imitate",
  pendingScenarioTag: null,
  createPipelineActive: false,
  seedanceProgressPersist: false,
  scriptTagSnapshot: null,
  lastScriptProductId: null,
  scriptEditBaseline: null,
  videoSettings: {
    resolution: "720P",
    aspectRatio: "9:16",
    durationSec: 5,
    generateCount: 1,
    editMode: "multi_shot",
  },
  promptEnhanceOn: false,
  promptEnhanceUsed: false,
  viralPipelineBusy: false,
  pendingViralLinkId: null,
  generatePromptSelection: null,
  reverseType: "video",
  reverseMaterialId: null,
  reverseLastResult: null,
};

const VIDEO_RESOLUTIONS = ["720P", "1080P"];
const VIDEO_ASPECT_RATIOS = ["9:16", "16:9", "1:1", "3:4", "4:3"];
const VIDEO_DURATIONS = [5, 10, 20];
const GENERATE_COUNTS = [1, 2, 3, 4];

const SCOPED_MATERIAL_JOBS = new Set(["discover", "promote", "fetch"]);

function productIdForScopedCapture() {
  const productId = currentProductId();
  if (!productId) {
    window.alert("请先在底部配置「产品」与场景标签。抓取将只保留当前产品品类（如便携恒温杯）。");
    return "";
  }
  return productId;
}

const JOB_LABELS = {
  discover: "发现候选",
  promote: "筛选入库",
  fetch: "同步 TikTok",
  decompose: "结构拆解",
  templates: "更新模板",
  products: "同步产品资料",
  links: "生成链接表",
  "cache-thumbnails": "缓存封面图",
  prune: "整理素材库",
};

function jobLabel(name) {
  return JOB_LABELS[name] || name || "";
}

const SCENARIO_GROUPS = [
  { id: "bedroom", keys: ["卧室", "夜间", "夜奶"] },
  { id: "car", keys: ["车内", "杯架"] },
  { id: "travel", keys: ["机场", "旅途", "长途"] },
  { id: "outdoor", keys: ["公园", "遛娃"] },
  { id: "office", keys: ["办公室", "背奶"] },
  { id: "public", keys: ["餐厅", "商场", "临时冲奶"] },
];

/** 与后端 product_tags.PRODUCT_TAG_PRESETS 保持一致，供前端离线兜底 */
const PRODUCT_TAG_PRESETS = {
  "便携恒温杯": {
    audience: ["0-12月新手爸妈", "夜奶/外出行程家庭", "混合喂养与瓶喂妈妈", "经常带娃出门、坐飞机、车内喂奶人群"],
    scenarios: ["夜间卧室喂奶", "车内杯架加热", "机场/旅途出行", "公园遛娃", "办公室背奶妈妈", "餐厅/商场临时冲奶"],
    selling: ["便携可充电设计，外出随时加热", "多档温控，奶液加热更均匀", "USB-C 充电，妈咪包/杯架都能放", "保温锁温，减少反复加热", "清洗简单，配件少"],
    pains: ["外出没热水、找微波炉麻烦", "加热太慢宝宝哭闹", "温度忽高忽低", "传统暖奶器太大不便携", "夜喂等待久、手忙脚乱", "飞机上/车内难加热"],
  },
  "吸奶器": {
    audience: ["0-6月新手妈妈", "背奶职场妈妈", "夜间吸奶人群", "混合喂养家庭"],
    scenarios: ["夜间吸奶", "背奶通勤", "居家哺乳角", "办公室隐蔽吸奶", "乳头皲裂恢复期"],
    selling: ["活塞泵技术，吸放节奏更接近婴儿吮吸", "可调吸力档位", "多种护罩尺寸", "可充电电池", "易拆洗结构", "夜奶场景下电机相对安静", "便携设计适合背奶"],
    pains: ["吸不出来/吸不干净", "疼痛导致放弃母乳", "吸力不适", "护罩尺寸不合", "清洗繁琐", "夜间噪音打扰", "外出不便"],
  },
};

const GENERATE_FEATURES = [
  { id: "bedroom", label: "夜间场景", sub: "卧室 · 夜奶", grad: "g-bedroom", scenarioTag: "卧室" },
  { id: "car", label: "车载场景", sub: "杯架 · 通勤", grad: "g-car", scenarioTag: "车内" },
  { id: "travel", label: "旅途场景", sub: "机场 · 长途", grad: "g-travel", scenarioTag: "机场" },
  { id: "office", label: "办公场景", sub: "背奶 · 工位", grad: "g-office", scenarioTag: "办公室" },
  { id: "outdoor", label: "户外遛娃", sub: "公园 · 出行", grad: "g-outdoor", scenarioTag: "公园" },
  { id: "public", label: "商场餐厅", sub: "临时冲奶", grad: "g-public", scenarioTag: "商场" },
];

const IMITATE_FEATURES = [
  { id: "extract", label: "原视频提取", sub: "拉取对标结构", grad: "g-extract", planned: true },
  { id: "template", label: "套结构模板", sub: "镜头语言复用", grad: "g-template", planned: true },
  { id: "brand", label: "品牌脚本套用", sub: "一键出模仿稿", grad: "g-brand", planned: true },
];

const REVERSE_FEATURES = [
  { id: "video-rev", label: "视频反推", sub: "拆镜头 → Prompt", grad: "g-video-rev", reverseType: "video" },
  { id: "script-rev", label: "脚本反推", sub: "拆解脚本结构", grad: "g-script-rev", reverseType: "script" },
];

const DRAFT_FEEDBACK_FEATURES = [
  { id: "finished", label: "成稿库", sub: "已交付成片", grad: "g-finished", action: "finished" },
  { id: "feedback", label: "反馈库", sub: "投放数据记录", grad: "g-feedback", action: "feedback" },
  { id: "iterate", label: "迭代优化", sub: "反哺下一轮", grad: "g-iterate", action: "audit", planned: true },
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
    label: "目标人群",
    placeholder: "输入人群标签，如：夜奶家庭",
    single: true,
  },
  scenario: {
    field: "usage_scenarios",
    poolKey: "scenarios",
    savedKey: "scenarios",
    label: "投放场景",
    placeholder: "输入场景标签，如：车内杯架",
    single: true,
  },
  selling: {
    field: "core_selling_points",
    poolKey: "selling",
    savedKey: "selling",
    label: "核心卖点",
    placeholder: "输入卖点，如：USB-C 充电",
  },
  pain: {
    field: "pain_points",
    poolKey: "pains",
    savedKey: "pains",
    label: "用户痛点",
    placeholder: "输入痛点，如：外出没热水",
  },
};

function buildTagPool(p, apiTags) {
  const pid = p?.product_id || "";
  const presets = PRODUCT_TAG_PRESETS[pid] || {};
  const pool = {
    audience: (apiTags?.audience?.length ? apiTags.audience : parseTagList(p.target_audience)),
    scenarios: (apiTags?.scenarios?.length ? apiTags.scenarios : parseTagList(p.usage_scenarios)),
    selling: (apiTags?.selling?.length ? apiTags.selling : parseTagList(p.core_selling_points)),
    pains: (apiTags?.pains?.length ? apiTags.pains : parseTagList(p.pain_points)),
  };
  for (const key of ["audience", "scenarios", "selling", "pains"]) {
    for (const t of presets[key] || []) {
      if (!pool[key].includes(t)) pool[key].push(t);
    }
    for (const t of state.tagPoolExtra[key] || []) {
      if (!pool[key].includes(t)) pool[key].push(t);
    }
  }
  return pool;
}

function tagSelectModeHint(cfg) {
  return cfg.single
    ? '<span class="tag-panel-hint muted">单选</span>'
    : '<span class="tag-panel-hint muted">可多选</span>';
}

function defaultSelectedTags(pool, saved) {
  const pick = (poolKey, savedKey, single = false) => {
    if (saved && Object.prototype.hasOwnProperty.call(saved, savedKey)) {
      const list = (saved[savedKey] || []).filter((t) => pool[poolKey].includes(t));
      return single ? list.slice(0, 1) : list;
    }
    const list = (saved?.[savedKey] || []).filter((t) => pool[poolKey].includes(t));
    if (list.length) return single ? list.slice(0, 1) : list;
    return pool[poolKey][0] ? [pool[poolKey][0]] : [];
  };
  return {
    audience: pick("audience", "audience", true),
    scenarios: pick("scenarios", "scenarios", true),
    selling: pick("selling", "selling"),
    pains: pick("pains", "pains"),
  };
}

function readAllSelectedTags() {
  return {
    audience: [...(state.tagSelection?.audience || [])],
    scenarios: [...(state.tagSelection?.scenarios || [])],
    selling: [...(state.tagSelection?.selling || [])],
    pains: [...(state.tagSelection?.pains || [])],
  };
}

const TAG_GROUP_DOM = {
  audience: { row: "audienceTagRow", library: "audienceLibraryRow", poolKey: "audience", savedKey: "audience" },
  scenario: { row: "scenarioTagRow", library: "scenarioLibraryRow", poolKey: "scenarios", savedKey: "scenarios" },
  selling: { row: "sellingTagRow", library: "sellingLibraryRow", poolKey: "selling", savedKey: "selling" },
  pain: { row: "painTagRow", library: "painLibraryRow", poolKey: "pains", savedKey: "pains" },
};

function readSelectedTags(group) {
  const key = TAG_GROUP_DOM[group]?.savedKey;
  return key ? [...(state.tagSelection?.[key] || [])] : [];
}

function syncDockPromptFromScenarioTags() {
  const scenarios = readSelectedTags("scenario");
  const text = scenarios.length
    ? `${scenarios[0]}场景：展示产品在真实使用环境中的卖点与痛点，口播自然、镜头节奏对标爆款结构。`
    : "";
  setImitationPrompt(text);
}

function toggleTagChip(group, value) {
  const cfg = TAG_GROUPS[group];
  const dom = TAG_GROUP_DOM[group];
  if (!cfg || !dom || !value) return;
  const key = dom.savedKey;
  let sel = [...(state.tagSelection[key] || [])];
  if (cfg.single) {
    state.tagSelection[key] = sel.includes(value) ? [] : [value];
    if (group === "scenario") syncDockPromptFromScenarioTags();
    return;
  }
  state.tagSelection[key] = sel.includes(value) ? sel.filter((t) => t !== value) : [...sel, value];
}

function refreshTagGroupsUI() {
  const pool = state.currentTagPool || { audience: [], scenarios: [], selling: [], pains: [] };
  const sel = state.tagSelection || readAllSelectedTags();
  for (const [group, dom] of Object.entries(TAG_GROUP_DOM)) {
    const picked = sel[dom.savedKey] || [];
    renderTagRow(dom.row, pool[dom.poolKey] || [], picked, group);
    renderLibraryTagRow(dom.library, pool[dom.poolKey] || [], picked, group);
  }
  const warn = document.getElementById("scenarioConflictWarn");
  if (warn) {
    const conflict = scenarioConflictNote(sel.scenarios);
    if (conflict) {
      warn.classList.remove("hidden");
      warn.textContent = conflict;
    } else {
      warn.classList.add("hidden");
      warn.textContent = "";
    }
  }
}

function hasActiveTagSelection() {
  return ["audience", "scenarios", "selling", "pains"].some(
    (k) => (state.tagSelection?.[k] || []).length > 0,
  );
}

function syncProductTagPanelFromPreview(p, deliveryTags, savedTags) {
  const pool = buildTagPool(p, deliveryTags || {});
  state.currentTagPool = pool;
  if (!hasActiveTagSelection()) {
    renderProductPanel(p, deliveryTags || {}, savedTags || {});
  } else {
    refreshTagGroupsUI();
  }
}

function packMatchesCurrentTags(pack) {
  const m = pack?.inputs?.market || pack?.inputs?.personalization || {};
  const cur = readAllSelectedTags();
  const same = (a, b) => JSON.stringify([...(a || [])].sort()) === JSON.stringify([...(b || [])].sort());
  return same(m.audience_tags || m.audience, cur.audience)
    && same(m.scenario_tags || m.scenarios, cur.scenarios)
    && same(m.selling_tags || m.selling, cur.selling)
    && same(m.pain_tags || m.pains, cur.pains);
}

function formatPersonalizationBanner(pack) {
  const p = pack?.inputs?.personalization;
  const m = pack?.inputs?.market || {};
  const summary = pack?.personalization_summary || "";
  const lines = [];
  const audience = p?.audience_tags || m.audience_tags || [];
  const scenarios = p?.scenario_tags || m.scenario_tags || [];
  const selling = p?.selling_tags || m.selling_tags || [];
  const pains = p?.pain_tags || m.pain_tags || [];
  const primaryScene = p?.primary_scene || pack?.inputs?.scenario_primary || scenarios[0] || "";
  if (audience.length) lines.push(`<span class="pack-pers-chip">人群 ${esc(audience.join("、"))}</span>`);
  if (scenarios.length) lines.push(`<span class="pack-pers-chip pack-pers-chip-scene">场景 ${esc(primaryScene || scenarios.join("、"))}</span>`);
  if (selling.length) lines.push(`<span class="pack-pers-chip">卖点 ${esc(selling.join("、"))}</span>`);
  if (pains.length) lines.push(`<span class="pack-pers-chip">痛点 ${esc(pains.join("、"))}</span>`);
  if (!lines.length && summary) {
    lines.push(`<span class="pack-pers-chip">${esc(summary)}</span>`);
  }
  if (!lines.length) return "";
  const stale = !packMatchesCurrentTags(pack);
  return `<div class="pack-personalization${stale ? " pack-personalization-stale" : ""}">
    <div class="pack-personalization-head">个性化定制${stale ? " · 与当前产品定义不一致" : ""}</div>
    <div class="pack-personalization-chips">${lines.join("")}</div>
    ${stale ? '<p class="workflow-warn pack-personalization-warn">产品标签已变更，请点击「重新生成脚本」同步场景/卖点/痛点。</p>' : ""}
  </div>`;
}

function formatStoryboardHtml(storyboard) {
  return formatStoryboardEditableHtml(storyboard);
}

function formatStoryboardEditableHtml(storyboard) {
  const shots = storyboard || [];
  if (!shots.length) return '<p class="muted">暂无分镜</p>';
  return `<div class="shot-list-compact shot-list-editable">${shots.map((s, idx) => {
    const vo = String(s.voiceover_en || "").trim();
    const voPreview = vo.length > 72 ? `${vo.slice(0, 72)}…` : vo;
    return `
    <details class="shot-compact shot-edit-row"${idx === 0 ? " open" : ""}
      data-shot-idx="${idx}"
      data-shot-role="${esc(s.role || "")}"
      data-shot-timing="${esc(s.timing || "")}"
      data-shot-footage="${esc(s.footage_type || "")}"
      data-shot-number="${esc(String(s.number || idx + 1))}">
      <summary>第 ${s.number} 镜 · ${esc(s.role || "")}（${esc(s.timing || "")}）${voPreview ? ` — ${esc(voPreview)}` : ""}</summary>
      <div class="shot-compact-body script-edit-fields">
        <label class="script-edit-field"><span class="pack-label">画面</span><textarea rows="2" data-shot-field="visual">${esc(s.visual || "")}</textarea></label>
        <label class="script-edit-field"><span class="pack-label">口播</span><textarea rows="2" data-shot-field="voiceover_en">${esc(s.voiceover_en || "")}</textarea></label>
        <label class="script-edit-field"><span class="pack-label">字幕</span><textarea rows="2" data-shot-field="subtitle_en">${esc(s.subtitle_en || "")}</textarea></label>
        <label class="script-edit-field"><span class="pack-label">构图</span><textarea rows="4" data-shot-field="visual_prompt">${esc(s.visual_prompt || "")}</textarea></label>
        <label class="script-edit-field"><span class="pack-label">空镜</span><textarea rows="4" data-shot-field="seedance_prompt">${esc(s.seedance_prompt || "")}</textarea></label>
      </div>
    </details>`;
  }).join("")}</div>`;
}

function packEditsSnapshot(pack) {
  if (!pack) return "";
  return JSON.stringify({
    title: String(pack.title || "").trim(),
    subtitle: String(pack.subtitle || "").trim(),
    voiceover_20s: String(pack.voiceover_20s || "").trim(),
    storyboard: (pack.storyboard || []).map((s) => ({
      number: s.number,
      role: s.role || "",
      timing: s.timing || "",
      footage_type: s.footage_type || "",
      visual: String(s.visual || "").trim(),
      voiceover_en: String(s.voiceover_en || "").trim(),
      subtitle_en: String(s.subtitle_en || "").trim(),
      visual_prompt: String(s.visual_prompt || "").trim(),
      seedance_prompt: String(s.seedance_prompt || "").trim(),
    })),
  });
}

function setScriptEditBaseline(pack) {
  state.scriptEditBaseline = packEditsSnapshot(pack);
}

function collectScriptPackEdits() {
  const form = document.getElementById("scriptEditForm");
  if (!form) return null;
  const pack = {
    title: form.querySelector('[data-pack-field="title"]')?.value?.trim() || "",
    subtitle: form.querySelector('[data-pack-field="subtitle"]')?.value?.trim() || "",
    voiceover_20s: form.querySelector('[data-pack-field="voiceover_20s"]')?.value?.trim() || "",
    storyboard: [],
  };
  form.querySelectorAll(".shot-edit-row").forEach((row) => {
    const shot = {
      number: Number(row.dataset.shotNumber) || pack.storyboard.length + 1,
      role: row.dataset.shotRole || "",
      timing: row.dataset.shotTiming || "",
      footage_type: row.dataset.shotFootage || "",
    };
    row.querySelectorAll("[data-shot-field]").forEach((el) => {
      shot[el.dataset.shotField] = el.value.trim();
    });
    pack.storyboard.push(shot);
  });
  return pack;
}

function scriptEditsDirty() {
  const form = document.getElementById("scriptEditForm");
  if (!form || !state.scriptEditBaseline) return false;
  return JSON.stringify(collectScriptPackEdits()) !== state.scriptEditBaseline;
}

async function saveScriptEditsIfDirty({ silent = false } = {}) {
  if (!scriptEditsDirty()) return true;
  const linkId = Number(document.getElementById("scriptMaterialSelect")?.value || state.selectedMaterialId);
  if (!linkId) {
    if (!silent) setScriptActionStatus("请先选择对标素材");
    return false;
  }
  const edits = collectScriptPackEdits();
  if (!edits) return false;
  if (!silent) setScriptActionStatus("正在保存脚本修改…");
  try {
    const res = await api(`/api/materials/${linkId}/script`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(edits),
    });
    const pack = res.script_pack || res.pack;
    if (pack) {
      state.lastPreview = { ...(state.lastPreview || {}), script_pack: pack, has_script: true };
      if (res.slug) state.scriptSlug = res.slug;
      setScriptEditBaseline(pack);
    }
    if (!silent) setScriptActionStatus(res.message || "脚本修改已保存");
    return true;
  } catch (err) {
    if (!silent) setScriptActionStatus(`保存脚本失败：${err.message}`);
    return false;
  }
}

function appendScriptEditTextarea(parent, label, fieldAttr, fieldName, value, rows = 3) {
  const labelEl = document.createElement("label");
  labelEl.className = "script-edit-field";
  const span = document.createElement("span");
  span.className = "pack-label";
  span.textContent = label;
  const ta = document.createElement("textarea");
  ta.rows = rows;
  ta.dataset[fieldAttr] = fieldName;
  ta.value = String(value ?? "");
  ta.spellcheck = false;
  labelEl.append(span, ta);
  parent.appendChild(labelEl);
  return ta;
}

function mountScriptPackEditor(container, pack, meta) {
  if (!container || !pack) return;
  container.replaceChildren();

  const h3 = document.createElement("h3");
  h3.textContent = "脚本已生成";
  container.appendChild(h3);

  const bannerHtml = formatPersonalizationBanner(pack);
  if (bannerHtml) {
    const bannerWrap = document.createElement("div");
    bannerWrap.innerHTML = bannerHtml;
    container.appendChild(bannerWrap);
  }

  const m = pack.inputs?.market || {};
  const provider = meta?.provider || pack.provider || "";
  const model = meta?.model || pack.model || "";
  const providerLine = provider === "doubao"
    ? `脚本引擎：豆包（${model || "ark"}）`
    : provider === "anthropic"
      ? `脚本引擎：Claude（${model || "claude"}）`
      : provider === "rule_template"
        ? "脚本引擎：规则模板（LLM 未配置或 API 失败时自动使用）"
        : "";
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

  for (const [text, cls] of [
    [providerLine, "pack-summary-line"],
    [tagSummary, "pack-summary-line"],
    [sceneNote, "pack-summary-line"],
  ]) {
    if (!text) continue;
    const p = document.createElement("p");
    p.className = cls;
    p.textContent = text;
    container.appendChild(p);
  }
  if (sceneWarn) {
    const p = document.createElement("p");
    p.className = "workflow-warn";
    p.textContent = sceneWarn;
    container.appendChild(p);
  }

  const hint = document.createElement("p");
  hint.className = "script-edit-hint muted";
  hint.textContent = "可直接修改下方字段；点击「保存修改」或「确认生成视频」时将按当前内容出片。";
  container.appendChild(hint);

  const form = document.createElement("form");
  form.id = "scriptEditForm";
  form.className = "script-pack script-edit-form";
  form.autocomplete = "off";
  form.addEventListener("submit", (e) => e.preventDefault());

  const metaDetails = document.createElement("details");
  metaDetails.className = "pack-meta-details";
  metaDetails.open = true;
  const metaSummary = document.createElement("summary");
  metaSummary.textContent = "标题与口播全文";
  metaDetails.appendChild(metaSummary);
  appendScriptEditTextarea(metaDetails, "英文标题", "packField", "title", pack.title, 2);
  appendScriptEditTextarea(metaDetails, "英文副标题", "packField", "subtitle", pack.subtitle, 2);
  appendScriptEditTextarea(metaDetails, "完整口播", "packField", "voiceover_20s", pack.voiceover_20s, 3);
  form.appendChild(metaDetails);

  const shotsLabel = document.createElement("div");
  shotsLabel.className = "pack-row script-shot-list-head";
  const shotsTitle = document.createElement("span");
  shotsTitle.textContent = `分镜脚本（${(pack.storyboard || []).length} 镜，可直接编辑）`;
  shotsLabel.appendChild(shotsTitle);
  form.appendChild(shotsLabel);

  const shotsWrap = document.createElement("div");
  shotsWrap.className = "shot-list-compact shot-list-editable";
  (pack.storyboard || []).forEach((s, idx) => {
    const row = document.createElement("section");
    row.className = "shot-edit-row script-shot-editor";
    row.dataset.shotIdx = String(idx);
    row.dataset.shotRole = s.role || "";
    row.dataset.shotTiming = s.timing || "";
    row.dataset.shotFootage = s.footage_type || "";
    row.dataset.shotNumber = String(s.number || idx + 1);

    const head = document.createElement("div");
    head.className = "script-shot-head";
    head.textContent = `第 ${s.number || idx + 1} 镜 · ${s.role || ""}（${s.timing || ""}）`;
    row.appendChild(head);

    appendScriptEditTextarea(row, "画面", "shotField", "visual", s.visual, 2);
    appendScriptEditTextarea(row, "口播", "shotField", "voiceover_en", s.voiceover_en, 2);
    appendScriptEditTextarea(row, "字幕", "shotField", "subtitle_en", s.subtitle_en, 2);
    appendScriptEditTextarea(row, "构图", "shotField", "visual_prompt", s.visual_prompt, 5);
    appendScriptEditTextarea(row, "空镜", "shotField", "seedance_prompt", s.seedance_prompt, 5);
    shotsWrap.appendChild(row);
  });
  form.appendChild(shotsWrap);
  container.appendChild(form);
  setScriptEditBaseline(pack);
}

function formatPackResult(pack, meta) {
  const wrap = document.createElement("div");
  mountScriptPackEditor(wrap, pack, meta);
  return wrap.innerHTML;
}

function currentScriptSlug() {
  return state.scriptSlug || state.lastPreview?.slug || "";
}

function captureTagSnapshot() {
  return JSON.stringify(readAllSelectedTags());
}

function scriptTagSnapshotFromPack(pack, savedTags) {
  const m = pack?.inputs?.market || pack?.inputs?.personalization || {};
  return JSON.stringify({
    audience: m.audience_tags || savedTags?.audience || [],
    scenarios: m.scenario_tags || savedTags?.scenarios || [],
    selling: m.selling_tags || savedTags?.selling || [],
    pains: m.pain_tags || savedTags?.pains || [],
  });
}

function tagsChangedSinceScript() {
  const cur = captureTagSnapshot();
  if (state.scriptTagSnapshot) {
    return cur !== state.scriptTagSnapshot;
  }
  const pack = state.lastPreview?.script_pack;
  if (pack && state.lastPreview?.has_script) {
    return !packMatchesCurrentTags(pack);
  }
  return false;
}

function scriptNeedsRegenerate(prev = {}) {
  if (!prev.has_script) return true;
  if (tagsChangedSinceScript()) return true;
  if (prev.script_pack && !packMatchesCurrentTags(prev.script_pack)) return true;
  return false;
}

function resolveScenarioTagFromFeature(scenarioTag) {
  const pool = [
    ...(state.currentTagPool?.scenarios || []),
    ...(state.tagPoolExtra?.scenarios || []),
  ];
  const hit = pool.find((t) => t.includes(scenarioTag) || scenarioTag.includes(t));
  return hit || scenarioTag;
}

function openFloatPanel(panelId, backdropId) {
  const panel = document.getElementById(panelId);
  const backdrop = document.getElementById(backdropId);
  if (!panel || !backdrop) return;
  panel.hidden = false;
  panel.style.display = "";
  backdrop.hidden = false;
  panel.setAttribute("aria-hidden", "false");
  requestAnimationFrame(() => {
    panel.classList.add("open");
    backdrop.classList.add("open");
  });
}

function closeFloatPanel(panelId, backdropId, afterClose) {
  const panel = document.getElementById(panelId);
  const backdrop = document.getElementById(backdropId);
  if (!panel || !backdrop) return;
  panel.classList.remove("open");
  backdrop.classList.remove("open");
  panel.setAttribute("aria-hidden", "true");
  const delay = panelId === "refFloatPanel" ? 250 : 200;
  window.setTimeout(() => {
    if (!panel.classList.contains("open")) {
      panel.hidden = true;
      panel.style.display = "none";
      backdrop.hidden = true;
      afterClose?.();
    }
  }, delay);
}

function ensureScriptResultVisible() {
  openScriptFloatPanel();
}

function syncScriptOutputSection() {
  syncDockScrollPadding();
}

function scrollScriptOutputIntoView() {
  openScriptFloatPanel();
}

let dockPadRaf = 0;
function syncDockScrollPadding() {
  if (dockPadRaf) cancelAnimationFrame(dockPadRaf);
  dockPadRaf = requestAnimationFrame(() => {
    dockPadRaf = 0;
    const configs = [
      { view: "generate", dockId: "generateDock", module: "generate" },
      { view: "imitate", dockId: "imitateDock", module: "imitate" },
    ];
    for (const { view, dockId, module } of configs) {
      if (state.view !== view) continue;
      const dock = document.getElementById(dockId);
      const scroll = document.querySelector(`.module-studio[data-module="${module}"] .module-studio-scroll`);
      const studio = document.querySelector(`.module-studio[data-module="${module}"]`);
      if (!dock || !scroll) continue;
      const h = Math.ceil(dock.getBoundingClientRect().height) + 24;
      scroll.style.paddingBottom = `${h}px`;
      studio?.style.setProperty("--dock-pad", `${h}px`);
    }
  });
}

function dockRunDefaultHtml(view = state.view) {
  return view === "imitate"
    ? '<span class="dock-run-icon">✦</span> 开始复刻'
    : '<span class="dock-run-icon">✦</span> 开始创作';
}

function forEachDockRunBtn(fn) {
  ["generateDockRun", "imitateDockRun"].forEach((id) => {
    const btn = document.getElementById(id);
    if (btn) fn(btn, id);
  });
}

function activeStudioDock() {
  return state.view === "imitate"
    ? document.getElementById("imitateDock")
    : document.getElementById("generateDock");
}

function getImitationPromptEls() {
  return [
    document.getElementById("generateDockPrompt"),
    document.getElementById("imitateDockPrompt"),
  ].filter(Boolean);
}

function getImitationPrompt() {
  const primary = state.generateDockMode === "generate" || state.view !== "imitate"
    ? document.getElementById("generateDockPrompt")
    : document.getElementById("imitateDockPrompt");
  return primary?.value?.trim()
    || document.getElementById("generateDockPrompt")?.value?.trim()
    || document.getElementById("imitateDockPrompt")?.value?.trim()
    || "";
}

function setImitationPrompt(value) {
  getImitationPromptEls().forEach((ta) => { ta.value = value; });
}

function syncImitationPromptFields() {
  const gen = document.getElementById("generateDockPrompt");
  const im = document.getElementById("imitateDockPrompt");
  if (!gen || !im) return;
  const src = gen.value || im.value;
  if (gen.value !== src) gen.value = src;
  if (im.value !== src) im.value = src;
}

function syncFinishButton(canFinish, delivered) {
  const canProduce = Boolean(canFinish && currentScriptSlug());
  forEachDockRunBtn((runBtn) => {
    if (runBtn.dataset.busy) return;
    const imitate = runBtn.id === "imitateDockRun";
    runBtn.disabled = !canProduce && Boolean(state.lastPreview?.has_script) === false
      ? !tagsSelectionOk() || !state.selectedMaterialId
      : false;
    runBtn.title = canProduce || tagsSelectionOk()
      ? imitate ? "按爆款结构生成脚本并出片" : "生成脚本并产出 AI 分镜视频"
      : "请先配置产品与对标";
  });
}

const SEEDANCE_PROGRESS_TARGETS = [
  { bar: "seedanceProgress", status: "seedanceProgressStatus", fill: "seedanceProgressFill", meta: "seedancePipelineCompact", countdown: "seedanceProgressCountdown" },
  { bar: "imitateSeedanceProgress", status: "imitateSeedanceProgressStatus", fill: "imitateSeedanceProgressFill", meta: "imitateSeedancePipelineCompact", countdown: "imitateSeedanceProgressCountdown" },
];

const SEEDANCE_COUNTDOWN_PHASE_SEC = {
  analysis: 45,
  script: 120,
  delivery: 60,
};

let scriptGenCountdownTimer = null;
let scriptGenCountdownRemaining = 0;
let scriptGenCountdownTotal = 0;

function stopScriptGenCountdown() {
  if (scriptGenCountdownTimer) {
    clearInterval(scriptGenCountdownTimer);
    scriptGenCountdownTimer = null;
  }
  scriptGenCountdownRemaining = 0;
  scriptGenCountdownTotal = 0;
  const countdown = document.getElementById("scriptGenProgressCountdown");
  if (countdown) {
    countdown.textContent = "";
    countdown.classList.add("hidden");
  }
}

function syncScriptGenCountdownProgressFill() {
  if (!scriptGenCountdownTotal) return;
  const fill = document.getElementById("scriptGenProgressFill");
  const bar = document.getElementById("scriptGenProgress");
  if (!fill || !bar || bar.classList.contains("hidden")) return;
  const pct = scriptGenCountdownRemaining > 0
    ? Math.min(92, Math.round((1 - scriptGenCountdownRemaining / scriptGenCountdownTotal) * 100))
    : 95;
  fill.classList.remove("indeterminate");
  fill.style.width = `${pct}%`;
  bar.querySelector(".seedance-progress-track")?.setAttribute("aria-valuenow", String(pct));
}

function syncScriptGenCountdownUi() {
  const label = scriptGenCountdownRemaining > 0
    ? `预计剩余 ${formatCountdownMmSs(scriptGenCountdownRemaining)}`
    : "比预计稍久，继续生成中…";
  const countdown = document.getElementById("scriptGenProgressCountdown");
  const bar = document.getElementById("scriptGenProgress");
  if (countdown && bar && !bar.classList.contains("hidden")) {
    countdown.textContent = label;
    countdown.classList.remove("hidden");
  }
  enforceStaticBusyButtonLabels();
  syncScriptGenCountdownProgressFill();
}

function startScriptGenCountdown(seconds) {
  stopScriptGenCountdown();
  scriptGenCountdownTotal = Math.max(30, Math.round(seconds));
  scriptGenCountdownRemaining = scriptGenCountdownTotal;
  syncScriptGenCountdownUi();
  scriptGenCountdownTimer = setInterval(() => {
    scriptGenCountdownRemaining = Math.max(0, scriptGenCountdownRemaining - 1);
    syncScriptGenCountdownUi();
  }, 1000);
}

function showScriptProgress(show, { status, percent, indeterminate, pipeline, countdownSec } = {}) {
  const bar = document.getElementById("scriptGenProgress");
  const statusEl = document.getElementById("scriptGenProgressStatus");
  const fill = document.getElementById("scriptGenProgressFill");
  const meta = document.getElementById("scriptGenProgressMeta");
  const track = bar?.querySelector(".seedance-progress-track");
  if (!bar) return;

  if (show && countdownSec != null && countdownSec > 0) startScriptGenCountdown(countdownSec);
  if (!show) stopScriptGenCountdown();

  bar.classList.toggle("hidden", !show);
  if (!show) {
    fill?.classList.remove("indeterminate");
    if (fill) fill.style.width = "";
    if (statusEl) statusEl.textContent = "准备中…";
    if (meta) meta.textContent = "";
    return;
  }

  if (status && statusEl) statusEl.textContent = status;
  if (pipeline != null && meta) meta.textContent = pipeline;
  if (fill) {
    fill.classList.toggle("indeterminate", Boolean(indeterminate));
    if (percent != null) fill.style.width = `${Math.min(100, Math.max(0, percent))}%`;
  }
  if (track && percent != null) track.setAttribute("aria-valuenow", String(Math.round(percent)));
}

function resetScriptProgress() {
  stopScriptGenCountdown();
  const fill = document.getElementById("scriptGenProgressFill");
  if (fill) {
    fill.classList.remove("indeterminate");
    fill.style.width = "";
  }
  const meta = document.getElementById("scriptGenProgressMeta");
  if (meta) meta.textContent = "";
  const statusEl = document.getElementById("scriptGenProgressStatus");
  if (statusEl) statusEl.textContent = "准备中…";
  showScriptProgress(false);
}

let seedanceCountdownTimer = null;
let seedanceCountdownRemaining = 0;
let seedanceCountdownTotal = 0;

function formatCountdownMmSs(sec) {
  const s = Math.max(0, Math.ceil(sec));
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${String(r).padStart(2, "0")}`;
}

const BUSY_BTN_TIME_RE = /\d+:\d{2}/;

/** 倒计时只显示在进度条，强制去掉按钮上的 mm:ss（含旧版缓存脚本误写） */
function enforceStaticBusyButtonLabels() {
  const regenBtn = document.getElementById("scriptFloatRegenBtn");
  if (regenBtn?.dataset.busy === "1" && BUSY_BTN_TIME_RE.test(regenBtn.textContent)) {
    regenBtn.textContent = "生成中…";
  }
  const produceBtn = document.getElementById("scriptFloatProduceBtn");
  if (produceBtn?.dataset.busy === "1" && BUSY_BTN_TIME_RE.test(produceBtn.textContent)) {
    produceBtn.textContent = "生成中…";
  }
  forEachDockRunBtn((runBtn) => {
    if (runBtn.dataset.busy !== "1") return;
    const text = runBtn.textContent || "";
    if (!BUSY_BTN_TIME_RE.test(text)) return;
    if (text.includes("流水线")) {
      runBtn.innerHTML = '<span class="dock-run-icon">✦</span> 流水线运行中…';
    } else if (text.includes("创作")) {
      runBtn.innerHTML = '<span class="dock-run-icon">✦</span> 创作中…';
    } else {
      runBtn.innerHTML = '<span class="dock-run-icon">✦</span> 生成中…';
    }
  });
}

function estimateSeedanceVideoSeconds({ force } = {}) {
  const maxShots = parseInt(state.healthCache?.production?.ai_video_max_shots || "5", 10) || 5;
  const perShot = force ? 270 : 210;
  return maxShots * perShot + 90;
}

function stopSeedanceCountdown() {
  if (seedanceCountdownTimer) {
    clearInterval(seedanceCountdownTimer);
    seedanceCountdownTimer = null;
  }
  seedanceCountdownRemaining = 0;
  seedanceCountdownTotal = 0;
  for (const ids of SEEDANCE_PROGRESS_TARGETS) {
    const el = document.getElementById(ids.countdown);
    if (el) {
      el.textContent = "";
      el.classList.add("hidden");
    }
  }
}

function syncSeedanceCountdownProgressFill() {
  if (!seedanceCountdownTotal) return;
  const pct = seedanceCountdownRemaining > 0
    ? Math.min(92, Math.round((1 - seedanceCountdownRemaining / seedanceCountdownTotal) * 100))
    : 95;
  for (const ids of SEEDANCE_PROGRESS_TARGETS) {
    const bar = document.getElementById(ids.bar);
    const fill = document.getElementById(ids.fill);
    if (!bar || bar.classList.contains("hidden") || !fill) continue;
    fill.classList.remove("indeterminate");
    fill.style.width = `${pct}%`;
    const track = bar.querySelector(".seedance-progress-track");
    track?.setAttribute("aria-valuenow", String(pct));
  }
}

function syncSeedanceCountdownUi() {
  const label = seedanceCountdownRemaining > 0
    ? `预计剩余 ${formatCountdownMmSs(seedanceCountdownRemaining)}`
    : "比预计稍久，继续生成中…";
  for (const ids of SEEDANCE_PROGRESS_TARGETS) {
    const el = document.getElementById(ids.countdown);
    const bar = document.getElementById(ids.bar);
    if (!el || !bar || bar.classList.contains("hidden")) continue;
    el.textContent = label;
    el.classList.remove("hidden");
  }
  enforceStaticBusyButtonLabels();
  syncSeedanceCountdownProgressFill();
}

function startSeedanceCountdown(seconds) {
  stopSeedanceCountdown();
  seedanceCountdownTotal = Math.max(30, Math.round(seconds));
  seedanceCountdownRemaining = seedanceCountdownTotal;
  syncSeedanceCountdownUi();
  seedanceCountdownTimer = setInterval(() => {
    seedanceCountdownRemaining = Math.max(0, seedanceCountdownRemaining - 1);
    syncSeedanceCountdownUi();
  }, 1000);
}

function showSeedanceProgress(show, { status, percent, indeterminate, pipeline, persist, countdownSec } = {}) {
  if (persist != null) state.seedanceProgressPersist = Boolean(persist);
  if (!show && persist !== true) state.seedanceProgressPersist = false;

  const visible = Boolean(show && (state.createPipelineActive || state.seedanceProgressPersist));
  let wasVisible = false;

  if (visible && countdownSec != null && countdownSec > 0) startSeedanceCountdown(countdownSec);

  for (const ids of SEEDANCE_PROGRESS_TARGETS) {
    const bar = document.getElementById(ids.bar);
    const statusEl = document.getElementById(ids.status);
    const fill = document.getElementById(ids.fill);
    const meta = document.getElementById(ids.meta);
    const track = bar?.querySelector(".seedance-progress-track");
    if (!bar) continue;

    if (!bar.classList.contains("hidden")) wasVisible = true;
    bar.classList.toggle("hidden", !visible);

    if (!visible) {
      fill?.classList.remove("indeterminate");
      continue;
    }

    if (status && statusEl) statusEl.textContent = status;
    if (pipeline != null && meta) meta.textContent = pipeline;
    if (fill) {
      fill.classList.toggle("indeterminate", Boolean(indeterminate));
      if (percent != null) fill.style.width = `${Math.min(100, Math.max(0, percent))}%`;
    }
    if (track && percent != null) track.setAttribute("aria-valuenow", String(Math.round(percent)));
  }

  if (!visible) stopSeedanceCountdown();
  if (!visible && wasVisible) syncDockScrollPadding();
  else if (visible && !wasVisible) syncDockScrollPadding();
}

function resetSeedanceProgressDock() {
  stopSeedanceCountdown();
  state.seedanceProgressPersist = false;
  for (const ids of SEEDANCE_PROGRESS_TARGETS) {
    const fill = document.getElementById(ids.fill);
    if (fill) {
      fill.classList.remove("indeterminate");
      fill.style.width = "";
    }
    const meta = document.getElementById(ids.meta);
    if (meta) {
      meta.textContent = "";
      meta.innerHTML = "";
    }
    const statusEl = document.getElementById(ids.status);
    if (statusEl) statusEl.textContent = "准备中…";
    const countdown = document.getElementById(ids.countdown);
    if (countdown) {
      countdown.textContent = "";
      countdown.classList.add("hidden");
    }
  }
  showSeedanceProgress(false);
}

function renderSeedanceFinalPreview(slug, seedance) {
  const box = document.getElementById("seedanceFinalPreview");
  if (!box) return;
  const final = seedance?.final_video || {};
  if (final.ready && final.file && slug) {
    box.classList.remove("hidden");
    box.innerHTML = `<a class="seedance-final-link" href="${withApiToken(`/api/delivery/${encodeURIComponent(slug)}/files/${encodeURI(final.file)}`)}" target="_blank">预览成片 final-video.mp4</a>`;
  } else {
    box.classList.add("hidden");
    box.innerHTML = "";
  }
}

async function runStartCreate() {
  const ps = document.getElementById("scriptProductSelect");
  if (ps?.value) {
    state.selectedProductId = ps.value;
    await refreshScriptPreview();
  }
  if (!tagsSelectionOk()) {
    await openProductFloatPanel();
    return;
  }
  const linkId = Number(document.getElementById("scriptMaterialSelect")?.value || state.selectedMaterialId);
  if (!linkId) {
    openRefFloatPanel();
    return;
  }

  forEachDockRunBtn((runBtn) => {
    runBtn.disabled = true;
    runBtn.dataset.busy = "1";
    runBtn.innerHTML = '<span class="dock-run-icon">✦</span> 创作中…';
  });

  try {
    const prev = state.lastPreview || {};
    if (scriptNeedsRegenerate(prev)) {
      await runScriptGenerate();
      if (!currentScriptSlug() && !state.lastPreview?.has_script) return;
      openScriptFloatPanel();
      return;
    }
    refreshScriptFloatFromPreview(prev);
    openScriptFloatPanel();
  } finally {
    forEachDockRunBtn((runBtn) => {
      delete runBtn.dataset.busy;
      runBtn.disabled = false;
      runBtn.innerHTML = dockRunDefaultHtml(runBtn.id === "imitateDockRun" ? "imitate" : "generate");
    });
    syncFinishButton(Boolean(state.lastPreview?.can_finish), Boolean(state.lastPreview?.delivery_ready));
  }
}

function renderDockProduceComplete(slug, message) {
  const msg = message || "视频生成完成，可下载 zip 或预览成片";
  if (slug) syncDownloadLinks(`/api/delivery/${encodeURIComponent(slug)}/zip`, true);
  setScriptActionStatus(msg);
  resetSeedanceProgressDock();
}

async function runConfirmProduceVideo() {
  const slug = currentScriptSlug();
  if (!slug) {
    setScriptActionStatus("请先生成并确认脚本");
    openScriptFloatPanel();
    return;
  }
  if (scriptEditsDirty()) {
    const saved = await saveScriptEditsIfDirty();
    if (!saved) {
      openScriptFloatPanel();
      return;
    }
  }
  const produceBtn = document.getElementById("scriptFloatProduceBtn");
  closeScriptFloatPanel();
  state.seedanceProgressPersist = false;
  syncDownloadLinks("", false);
  if (produceBtn) {
    produceBtn.disabled = true;
    produceBtn.dataset.busy = "1";
    produceBtn.textContent = "生成中…";
  }
  forEachDockRunBtn((runBtn) => {
    runBtn.disabled = true;
    runBtn.dataset.busy = "1";
    runBtn.innerHTML = '<span class="dock-run-icon">✦</span> 生成中…';
  });
  state.createPipelineActive = true;
  activeStudioDock()?.scrollIntoView({ behavior: "smooth", block: "end" });
  try {
    const ok = await runProduceVideo({ background: true });
    await refreshScriptPreview();
    updateLoopBarFromForm(state.lastPreview || {});
    const finalSlug = currentScriptSlug();
    const finalReady = Boolean(state.lastPreview?.seedance?.final_video?.ready);
    if (ok && finalSlug && finalReady) {
      syncDownloadLinks(`/api/delivery/${finalSlug}/zip`, true);
      renderDockProduceComplete(finalSlug, "视频生成完成，可下载 zip 或预览成片");
    } else if (finalSlug && !finalReady) {
      setScriptActionStatus("分镜已生成，成片拼接未完成，请检查 ffmpeg 后重试");
    }
  } finally {
    state.createPipelineActive = false;
    resetSeedanceProgressDock();
    if (produceBtn) {
      delete produceBtn.dataset.busy;
      produceBtn.disabled = false;
      produceBtn.textContent = "确认生成视频";
    }
    forEachDockRunBtn((runBtn) => {
      delete runBtn.dataset.busy;
      runBtn.disabled = false;
      runBtn.innerHTML = dockRunDefaultHtml(runBtn.id === "imitateDockRun" ? "imitate" : "generate");
    });
    syncFinishButton(Boolean(state.lastPreview?.can_finish), Boolean(state.lastPreview?.delivery_ready));
  }
}

function refreshScriptFloatFromPreview(prev = {}) {
  const body = scriptResultBody();
  if (!body) return;
  if (prev.has_script && prev.script_pack) {
    mountScriptPackEditor(body, prev.script_pack, prev.script_meta);
  } else {
    body.replaceChildren();
    state.scriptEditBaseline = null;
  }
  updateLoopBarFromForm(prev);
}

function setScriptActionStatus(msg) {
  const el = document.getElementById("scriptActionStatus");
  if (el) el.textContent = msg || "";
  if ((state.createPipelineActive || state.seedanceProgressPersist) && msg) {
    const dockSt = document.getElementById("seedanceProgressStatus");
    if (dockSt) dockSt.textContent = msg;
  }
}

function syncDownloadLinks(href, visible) {
  const url = href ? withApiToken(href) : "";
  document.querySelectorAll("#scriptDownloadBtnBottom, .js-script-download").forEach((dl) => {
    if (url) dl.href = url;
    dl.classList.toggle("hidden", !visible);
  });
}

function videoZipDownloadReady(prev = state.lastPreview || {}) {
  return Boolean(prev?.seedance?.final_video?.ready);
}

function syncScriptDownloadZip(prev = state.lastPreview || {}) {
  if (videoZipDownloadReady(prev) && prev?.slug) {
    syncDownloadLinks(`/api/delivery/${encodeURIComponent(prev.slug)}/zip`, true);
  } else {
    syncDownloadLinks("", false);
  }
}

function slugFor(linkId) {
  return `ref-${String(linkId).padStart(3, "0")}`;
}

function renderTagRow(containerId, options, selected, group) {
  const el = document.getElementById(containerId);
  if (!el) return;
  const picked = [...new Set(selected)];
  if (!picked.length) {
    el.innerHTML = '<span class="muted tag-selected-empty">暂未选用</span>';
  } else {
    el.innerHTML = picked.map((t) =>
      `<button type="button" class="tag-chip active" data-group="${group}" data-value="${esc(t)}">${esc(t)}</button>`
    ).join("");
  }
}

function renderLibraryTagRow(containerId, options, selected, group) {
  const el = document.getElementById(containerId);
  if (!el) return;
  const picked = [...new Set(selected)];
  if (!options.length) {
    el.innerHTML = '<span class="muted tag-preset-empty">暂无产品预设，请手动添加或到「设置」同步产品资料</span>';
    return;
  }
  el.innerHTML = options.map((t) =>
    `<button type="button" class="tag-chip ${picked.includes(t) ? "active" : ""}" data-group="${group}" data-value="${esc(t)}">${esc(t)}</button>`
  ).join("");
}

function renderProductPanel(p, apiTags, savedTags) {
  const pool = buildTagPool(p, apiTags);
  const selected = defaultSelectedTags(pool, savedTags);
  state.tagSelection = {
    audience: [...selected.audience].slice(0, 1),
    scenarios: [...selected.scenarios].slice(0, 1),
    selling: [...selected.selling],
    pains: [...selected.pains],
  };
  state.selectedAudience = state.tagSelection.audience;
  state.selectedScenarios = state.tagSelection.scenarios;
  state.currentTagPool = pool;
  const panel = document.getElementById("scriptProduct");
  panel.className = "script-tag-grid script-tag-grid-float";
  const groupsHtml = Object.entries(TAG_GROUPS).map(([group, cfg]) => `
    <div class="tag-panel tag-panel-compact">
      <div class="tag-panel-head">
        <span class="tag-group-label">${cfg.label}</span>
        ${tagSelectModeHint(cfg)}
      </div>
      <div class="tag-section tag-section-selected">
        <span class="tag-section-label">已选</span>
        <div id="${group}TagRow" class="tag-row tag-row-selected"></div>
      </div>
      <div class="tag-preset-block">
        <span class="tag-section-label">产品预设（点击选用）</span>
        <div id="${group}LibraryRow" class="tag-row tag-library-row tag-preset-row"></div>
      </div>
      <div class="tag-add-row">
        <input type="text" class="tag-input" data-group="${group}" placeholder="${cfg.placeholder}">
        <button type="button" class="tag-add-btn" data-group="${group}">添加</button>
      </div>
    </div>`).join("");
  panel.innerHTML = groupsHtml;
  refreshTagGroupsUI();
}

async function loadProductTagPanel(productId) {
  const productEl = document.getElementById("scriptProduct");
  if (!productId || !productEl) return;
  try {
    const p = await api(`/api/products/${encodeURIComponent(productId)}`);
    const idx = state.products.findIndex((x) => x.product_id === productId);
    if (idx >= 0) state.products[idx] = { ...state.products[idx], ...p };
    else state.products.push(p);
    const hasSaved = ["audience", "scenarios", "selling", "pains"].some(
      (key) => (state.tagSelection?.[key] || []).length > 0,
    );
    const saved = hasSaved ? readAllSelectedTags() : {};
    renderProductPanel(p, p.delivery_tags || {}, saved);
    syncProductFloatStatus();
    syncDockProductSlot();
    syncDockRefSlot();
  } catch (err) {
    productEl.className = "script-tag-grid script-tag-grid-float detail-empty";
    productEl.innerHTML = `<div class="result error">${esc(err.message)}</div>`;
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
  const key = cfg.savedKey;
  if (cfg.single) {
    state.tagSelection[key] = [text];
  } else if (!(state.tagSelection[key] || []).includes(text)) {
    state.tagSelection[key] = [...(state.tagSelection[key] || []), text];
  }
  renderProductPanel(p, buildTagPool(p, state.lastPreview?.delivery_tags), readAllSelectedTags());
  updateLoopBarFromForm(state.lastPreview || {});
  if (group === "scenario") syncDockPromptFromScenarioTags();
}

function tagsSelectionOk() {
  const sel = readAllSelectedTags();
  return sel.audience.length > 0 && sel.scenarios.length > 0
    && sel.selling.length > 0 && sel.pains.length > 0;
}

function selectGenerateScenario(featureId) {
  state.selectedScenarioFeature = featureId;
  document.querySelectorAll("#generateFeatureGrid .feature-card").forEach((c) => {
    c.classList.toggle("selected", c.dataset.featureId === featureId);
  });
  const feat = GENERATE_FEATURES.find((f) => f.id === featureId);
  if (feat?.scenarioTag) {
    state.tagSelection.scenarios = [resolveScenarioTagFromFeature(feat.scenarioTag)];
    syncDockPromptFromScenarioTags();
    refreshTagGroupsUI();
    const warn = document.getElementById("scenarioConflictWarn");
    if (warn) {
      const conflict = scenarioConflictNote(state.tagSelection.scenarios);
      if (conflict) {
        warn.classList.remove("hidden");
        warn.textContent = conflict;
      } else {
        warn.classList.add("hidden");
        warn.textContent = "";
      }
    }
  }
}

function viralVideoCardHtml(item) {
  const active = item.link_id === state.selectedMaterialId ? " selected" : "";
  const thumb = item.thumbnail_url
    ? `<img class="viral-video-thumb" src="${esc(item.thumbnail_url)}" alt="">`
    : `<span class="feature-card-bg g-video-rev"></span>`;
  const title = (item.title || "").trim().slice(0, 32) || `爆款 #${item.link_id}`;
  const stats = [item.author, fmtNum(item.view_count) && `${fmtNum(item.view_count)}播放`, item.duration_sec && `${item.duration_sec}s`].filter(Boolean).join(" · ");
  return `<button type="button" class="feature-card viral-video-card${active}" data-link-id="${item.link_id}">
    ${thumb}
    <span class="viral-video-badge">${materialBadgeHtml(item)}</span>
    <span class="feature-card-label"><strong>${esc(title)}</strong><span>${esc(stats || `#${item.link_id}`)}</span></span>
  </button>`;
}

function syncImitationViralGridDesc(descId, count, variant = "generate") {
  const el = document.getElementById(descId);
  if (!el) return;
  const productId = currentProductId();
  if (!productId) {
    el.textContent = variant === "imitate"
      ? "请先在底部配置「产品」与场景标签，此处展示同品类爆款供结构复刻"
      : "请先在底部配置「产品」与场景标签，此处将展示同品类已抓取爆款";
    return;
  }
  if (!count) {
    el.textContent = variant === "imitate"
      ? `当前产品「${currentProductLabel()}」暂无已抓取对标，可在设置同步 TikTok 或打开「对标」浏览`
      : `当前产品「${currentProductLabel()}」暂无已拆解对标，占位预留 · 可在设置中同步 TikTok 或打开「对标」浏览`;
    return;
  }
  el.textContent = variant === "imitate"
    ? `已抓取 ${count} 条同品类爆款，点击卡片自动拆解结构 → 套用品牌脚本 → 出片`
    : `已抓取 ${count} 条同品类爆款（按播放量排序），点击卡片自动拆解 → 生成脚本 → 出片`;
}

function bindViralVideoCards(root) {
  if (!root) return;
  root.querySelectorAll(".viral-video-card[data-link-id]").forEach((card) => {
    card.addEventListener("click", async () => {
      const linkId = Number(card.dataset.linkId);
      if (!productWorkflowReady()) {
        state.pendingViralLinkId = linkId;
        await openProductFloatPanel();
        return;
      }
      await runViralBenchmarkPipeline(linkId);
    });
  });
}

function renderImitationViralGrid(gridId, descId, variant = "generate") {
  const root = document.getElementById(gridId);
  if (!root) return;
  const pool = getMaterialPreviewPool();
  const sorted = [...pool].sort((a, b) => (Number(b.view_count) || 0) - (Number(a.view_count) || 0));
  const display = sorted.slice(0, 12);
  syncImitationViralGridDesc(descId, display.length, variant);

  if (display.length) {
    root.classList.add("has-viral-videos");
    root.innerHTML = display.map((item) => viralVideoCardHtml(item)).join("");
    bindViralVideoCards(root);
    return;
  }

  root.classList.remove("has-viral-videos");
  if (variant === "generate") {
    renderFeatureGrid(gridId, GENERATE_FEATURES);
  } else {
    root.innerHTML = `<p class="muted module-feature-empty">配置产品标签后，同品类爆款将显示在此；也可在「结构模板」页选用镜头节奏。</p>`;
  }
}

function renderAllImitationViralGrids() {
  renderImitationViralGrid("generateFeatureGrid", "generateViralGridDesc", "generate");
  renderImitationViralGrid("imitateFeatureGrid", "imitateViralGridDesc", "imitate");
}

function renderGenerateViralGrid() {
  renderAllImitationViralGrids();
}

async function selectGenerateViralVideo(linkId) {
  if (state.selectedMaterialId !== linkId) resetPromptEnhanceUsed();
  state.selectedMaterialId = linkId;
  repopulateScriptMaterials();
  syncMaterialSelectFromState();
  syncWorkspaceRefChip();
  renderGenerateViralGrid();
  renderRefFloatMaterialList();
  if (currentProductId()) await refreshScriptPreview();
}

async function ensureMaterialAnalysis(linkId) {
  const item = state.items.find((i) => i.link_id === linkId);
  if (item?.has_analysis) return item;
  showSeedanceProgress(true, {
    status: "正在拆解对标视频结构（规则，省 token）…",
    indeterminate: true,
    pipeline: "",
    countdownSec: SEEDANCE_COUNTDOWN_PHASE_SEC.analysis,
  });
  setScriptActionStatus("正在拆解对标结构…");
  const res = await api(`/api/materials/${linkId}/ensure-analysis`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider: "rule" }),
  });
  const detail = await api(`/api/materials/${linkId}`);
  if (item) {
    item.has_analysis = Boolean(detail.analysis);
    item.analysis = detail.analysis;
    item.analyze_provider = detail.analysis?.analyze_provider || res.provider || "rule";
  }
  renderAllImitationViralGrids();
  renderMaterialList();
  renderRefFloatMaterialList();
  return item;
}

async function runViralBenchmarkPipeline(linkId) {
  if (state.viralPipelineBusy) return;
  if (!productWorkflowReady()) {
    state.pendingViralLinkId = linkId;
    await openProductFloatPanel();
    return;
  }
  if (!materialInProductPool(linkId) && !state.showAllMaterials) {
    setScriptActionStatus("该爆款与当前产品品类不一致，请更换产品或勾选「显示其他品类」。");
    return;
  }

  state.viralPipelineBusy = true;
  forEachDockRunBtn((runBtn) => {
    runBtn.disabled = true;
    runBtn.dataset.busy = "1";
    runBtn.innerHTML = '<span class="dock-run-icon">✦</span> 流水线运行中…';
  });

  try {
    if (state.selectedMaterialId !== linkId) resetPromptEnhanceUsed();
    state.selectedMaterialId = linkId;
    repopulateScriptMaterials();
    syncMaterialSelectFromState();
    syncWorkspaceRefChip();
    syncDockRefSlot();
    renderAllImitationViralGrids();
    renderRefFloatMaterialList();
    closeScriptFloatPanel();
    state.createPipelineActive = true;
    state.seedanceProgressPersist = false;
    activeStudioDock()?.scrollIntoView({ behavior: "smooth", block: "end" });

    await ensureMaterialAnalysis(linkId);
    await refreshScriptPreview();

    if (state.lastPreview?.product_match === false) {
      const msg = document.getElementById("scriptMismatchWarn")?.textContent
        || "对标与产品品类不一致，请更换对标或产品。";
      setScriptActionStatus(msg);
      showSeedanceProgress(true, { status: msg, persist: true });
      return;
    }

    showSeedanceProgress(true, {
      status: "正在根据对标结构生成品牌脚本…",
      indeterminate: true,
      pipeline: state.healthCache?.llm?.label || "",
      countdownSec: SEEDANCE_COUNTDOWN_PHASE_SEC.script,
    });
    await runScriptGenerate();
    await refreshScriptPreview();

    if (!state.lastPreview?.has_script && !currentScriptSlug()) {
      setScriptActionStatus("脚本生成失败，请检查产品标签与 API 配置");
      showSeedanceProgress(true, { status: "脚本生成失败", persist: true });
      return;
    }

    const ok = await runProduceVideo({ background: true });
    await refreshScriptPreview();
    const slug = currentScriptSlug();
    const finalReady = Boolean(state.lastPreview?.seedance?.final_video?.ready);
    if (ok && slug && finalReady) {
      syncDownloadLinks(`/api/delivery/${slug}/zip`, true);
      renderDockProduceComplete(slug, "对标流水线完成：可下载 zip 或预览成片");
      setScriptActionStatus("视频生成完成，可下载 zip 或预览成片");
    } else if (slug && !finalReady) {
      setScriptActionStatus("分镜已生成，成片拼接未完成；请检查 ffmpeg 或重新生成");
    }
  } catch (err) {
    stopSeedanceCountdown();
    setScriptActionStatus(err.message);
    showSeedanceProgress(true, { status: `失败：${err.message}`, persist: true });
  } finally {
    state.viralPipelineBusy = false;
    state.createPipelineActive = false;
    resetSeedanceProgressDock();
    forEachDockRunBtn((runBtn) => {
      delete runBtn.dataset.busy;
      runBtn.disabled = false;
      runBtn.innerHTML = dockRunDefaultHtml(runBtn.id === "imitateDockRun" ? "imitate" : "generate");
    });
    syncFinishButton(Boolean(state.lastPreview?.can_finish), Boolean(state.lastPreview?.delivery_ready));
  }
}

function handleDraftFeedbackFeature(action) {
  if (action === "audit") {
    switchDraftFeedbackStudioTab("audit");
    return;
  }
  switchDraftFeedbackSub(action);
  document.getElementById("draftFeedbackBody")?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderFeatureGrid(containerId, items, { onClick } = {}) {
  const root = document.getElementById(containerId);
  if (!root) return;
  root.innerHTML = items.map((item) => `
    <button type="button" class="feature-card${item.planned ? " planned" : ""}${state.selectedScenarioFeature === item.id ? " selected" : ""}"
      data-feature-id="${esc(item.id)}" data-scenario-tag="${esc(item.scenarioTag || "")}"
      data-action="${esc(item.action || "")}" ${item.planned ? "disabled" : ""}>
      <span class="feature-card-bg ${esc(item.grad || "")}"></span>
      ${item.planned ? '<span class="feature-card-badge">规划中</span>' : ""}
      <span class="feature-card-label"><strong>${esc(item.label)}</strong><span>${esc(item.sub || "")}</span></span>
    </button>`).join("");
  root.querySelectorAll(".feature-card:not(.planned)").forEach((card) => {
    card.addEventListener("click", () => {
      if (onClick) onClick(card.dataset.featureId, card);
      else if (card.dataset.scenarioTag) selectGenerateScenario(card.dataset.featureId);
      else if (card.dataset.action) handleDraftFeedbackFeature(card.dataset.action);
    });
  });
}

function switchModuleStudioTab(moduleRoot, tab) {
  if (!moduleRoot) return;
  moduleRoot.querySelectorAll(".module-studio-tabs button").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.studioTab === tab);
  });
  moduleRoot.querySelectorAll("[data-studio-panel]").forEach((panel) => {
    panel.classList.toggle("hidden", panel.dataset.studioPanel !== tab);
  });
  const featureSection = moduleRoot.querySelector(".module-feature-section");
  if (featureSection) featureSection.classList.toggle("hidden", tab !== "featured");
}

function switchGenerateStudioTab(tab) {
  state.generateStudioTab = tab;
  const root = document.querySelector('.module-studio[data-module="generate"]');
  switchModuleStudioTab(root, tab);
  if (tab === "featured") renderAllImitationViralGrids();
  if (tab === "examples") renderGenerateExamples();
}

function switchImitateStudioTab(tab) {
  state.imitateStudioTab = tab;
  const root = document.querySelector('.module-studio[data-module="imitate"]');
  switchModuleStudioTab(root, tab);
  if (tab === "featured") renderAllImitationViralGrids();
  if (tab === "templates") renderImitateTemplates();
}

async function renderImitateTemplates() {
  const root = document.getElementById("imitateTemplatesList");
  if (!root) return;
  root.innerHTML = '<p class="muted">加载结构模板…</p>';
  try {
    const data = await api("/api/templates");
    const items = data.items || [];
    if (!items.length) {
      root.innerHTML = '<p class="muted">暂无结构模板，请先同步对标并完成拆解。</p>';
      return;
    }
    root.innerHTML = items.map((t) => `
      <button type="button" class="feature-card imitate-template-card" data-template-id="${esc(t.template_id)}">
        <span class="feature-card-bg g-template"></span>
        <span class="feature-card-label">
          <strong>${esc(t.label || t.template_id)}</strong>
          <span>${esc(t.structure_chain || "")}</span>
        </span>
      </button>`).join("");
    root.querySelectorAll(".imitate-template-card").forEach((card) => {
      card.addEventListener("click", () => {
        const item = items.find((x) => x.template_id === card.dataset.templateId);
        if (!item) return;
        setImitationPrompt(`按「${item.label}」结构拍摄：${item.structure_chain}`);
        activeStudioDock()?.scrollIntoView({ behavior: "smooth", block: "end" });
      });
    });
  } catch (err) {
    root.innerHTML = `<p class="muted">加载失败：${esc(err.message)}</p>`;
  }
}

function switchDraftFeedbackStudioTab(tab) {
  const root = document.querySelector('.module-studio[data-module="draft-feedback"]');
  switchModuleStudioTab(root, tab);
}

function expandGenerateWorkspace() {
  state.generateWorkspaceOpen = true;
}

function collapseGenerateWorkspace() {
  state.generateWorkspaceOpen = false;
  document.getElementById("generateBackHomeBtn")?.classList.add("hidden");
  switchGenerateStudioTab(state.generateStudioTab || "featured");
}

function syncGenerateDockMode(mode = state.generateDockMode) {
  state.generateDockMode = mode || "imitate";
  const dock = document.getElementById("generateDock");
  document.querySelectorAll('#generateDock .studio-dock-modes [data-gen-mode]').forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.genMode === state.generateDockMode);
  });
  const isGenerate = state.generateDockMode === "generate";
  dock?.classList.toggle("dock-gen-mode-generate", isGenerate);
  dock?.classList.toggle("dock-gen-mode-imitate", !isGenerate);
  const promptTa = document.getElementById("generateDockPrompt");
  if (promptTa) {
    promptTa.placeholder = isGenerate
      ? "点击「提示词选择」选用品类提示词，完整文案将显示在此，可直接修改后「开始创作」"
      : "① 点击「产品」配置场景标签 → ② 点击上方爆款卡片（自动拆解+出片）或底部「开始创作」";
  }
  syncDockPromptSelectSlot();
  syncDockScrollPadding();
}

function syncDockPromptSelectSlot() {
  const btn = document.getElementById("dockOpenPromptSelectBtn");
  if (!btn) return;
  const sel = state.generatePromptSelection;
  const promptText = document.getElementById("generateDockPrompt")?.value?.trim() || "";
  const hasText = Boolean(sel?.text || promptText);
  btn.classList.toggle("has-value", hasText);
  btn.title = sel?.label ? `已选：${sel.label}` : (hasText ? "已填写创作提示词，点击更换" : "选择创作提示词模板");
}

async function renderPromptSelectList() {
  const root = document.getElementById("promptSelectList");
  if (!root) return;
  root.innerHTML = '<p class="muted">加载提示词…</p>';
  const items = [];
  try {
    const productId = currentProductId() || "";
    const libPath = productId
      ? `/api/prompt-library?product_id=${encodeURIComponent(productId)}`
      : "/api/prompt-library";
    const lib = await api(libPath);
    for (const row of lib.presets || lib.items?.filter((r) => r.source === "preset") || []) {
      const text = row.prompt_text || row.prompt_text_en || "";
      if (!text) continue;
      items.push({
        id: row.prompt_id,
        promptId: row.prompt_id,
        label: row.label || row.prompt_type,
        sub: row.sub || text.slice(0, 48),
        text,
        kind: "preset",
        sortOrder: Number(row.sort_order) || 99,
      });
    }
    for (const row of lib.reverse || lib.items?.filter((r) => String(r.source || "").startsWith("reverse")) || []) {
      const text = row.prompt_text_en || row.prompt_text || "";
      if (!text) continue;
      const usage = Number(row.usage_count) || 0;
      items.push({
        id: `lib-${row.prompt_id}`,
        promptId: row.prompt_id,
        label: row.label || "反推提示词",
        sub: `${row.reverse_type === "script" ? "脚本" : "视频"}反推 · 使用 ${usage} 次`,
        text,
        kind: "library",
        usageCount: usage,
      });
    }
  } catch {
    /* fall through */
  }
  try {
    const data = await api("/api/templates");
    for (const t of data.items || []) {
      items.push({
        id: `tpl-${t.template_id}`,
        label: t.label || t.template_id,
        sub: (t.structure_chain || "").slice(0, 48),
        text: `按「${t.label}」结构拍摄：${t.structure_chain || ""}`,
        kind: "template",
        sortOrder: 50,
      });
    }
  } catch {
    /* optional */
  }
  items.sort((a, b) => {
    const order = { preset: 0, template: 1, library: 2 };
    const ao = order[a.kind] ?? 9;
    const bo = order[b.kind] ?? 9;
    if (ao !== bo) return ao - bo;
    if (a.kind === "preset") return (a.sortOrder || 99) - (b.sortOrder || 99);
    if (a.kind === "library") return (b.usageCount || 0) - (a.usageCount || 0);
    return 0;
  });
  if (!items.length) {
    root.innerHTML = '<p class="muted">暂无提示词，请检查数据表 prompt_library.json</p>';
    return;
  }
  const activeId = state.generatePromptSelection?.id || "";
  const cardGrad = (kind) => {
    if (kind === "library") return "g-video-rev";
    if (kind === "preset") return "g-template";
    return "g-brand";
  };
  root.innerHTML = items.map((item, idx) => `
    <button type="button" class="feature-card prompt-select-card${activeId === item.id ? " selected" : ""}${item.kind === "library" ? " prompt-library-card" : ""}"
      data-prompt-idx="${idx}">
      <span class="feature-card-bg ${cardGrad(item.kind)}"></span>
      <span class="feature-card-label">
        <strong>${esc(item.label)}</strong>
        <span>${esc(item.sub || item.text)}</span>
      </span>
    </button>`).join("");
  root.querySelectorAll(".prompt-select-card").forEach((card) => {
    card.addEventListener("click", () => {
      const item = items[Number(card.dataset.promptIdx)];
      if (!item) return;
      root.querySelectorAll(".prompt-select-card").forEach((c) => c.classList.remove("selected"));
      card.classList.add("selected");
      state.generatePromptSelection = {
        id: item.id,
        label: item.label,
        text: item.text,
        kind: item.kind,
        promptId: item.promptId || "",
      };
      setImitationPrompt(item.text);
      resetPromptEnhanceUsed();
      syncDockPromptSelectSlot();
      const status = document.getElementById("promptSelectFloatStatus");
      if (status) status.textContent = `已选：${item.label}（已写入编辑区，可修改）`;
    });
  });
}

async function openPromptSelectFloatPanel() {
  const panel = document.getElementById("promptSelectFloatPanel");
  const backdrop = document.getElementById("promptSelectFloatBackdrop");
  if (!panel || !backdrop) return;
  await renderPromptSelectList();
  const status = document.getElementById("promptSelectFloatStatus");
  if (status) {
    status.textContent = state.generatePromptSelection?.label
      ? `已选：${state.generatePromptSelection.label}`
      : "请选择一条提示词";
  }
  openFloatPanel("promptSelectFloatPanel", "promptSelectFloatBackdrop");
}

function closePromptSelectFloatPanel() {
  closeFloatPanel("promptSelectFloatPanel", "promptSelectFloatBackdrop", () => {
    syncDockPromptSelectSlot();
  });
}

function confirmPromptSelectFloatPanel() {
  const sel = state.generatePromptSelection;
  const ta = document.getElementById("generateDockPrompt");
  const text = ta?.value?.trim() || sel?.text || "";
  if (!text) {
    const status = document.getElementById("promptSelectFloatStatus");
    if (status) status.textContent = "请先选择一条提示词";
    return;
  }
  setImitationPrompt(text);
  if (sel) state.generatePromptSelection = { ...sel, text };
  resetPromptEnhanceUsed();
  syncDockPromptSelectSlot();
  if (sel?.promptId) {
    api(`/api/prompt-library/${encodeURIComponent(sel.promptId)}/use`, { method: "POST" }).catch(() => {});
  }
  closePromptSelectFloatPanel();
  ta?.focus();
  if (ta) ta.setSelectionRange(ta.value.length, ta.value.length);
}

function syncReverseDockType() {
  const reverseType = state.reverseType || "video";
  document.querySelectorAll("#reverseDock .studio-dock-modes button").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.reverseType === reverseType);
  });
}

function syncReverseDockMaterial() {
  const label = document.getElementById("reverseDockMaterialLabel");
  const chip = document.getElementById("reverseDockStatusChip");
  const linkId = state.reverseMaterialId;
  const item = linkId ? state.items.find((i) => i.link_id === linkId) : null;
  if (label) {
    label.textContent = item
      ? (item.title || `#${linkId}`).slice(0, 14)
      : "素材库";
  }
  if (chip) {
    const reverseType = state.reverseType || "video";
    chip.textContent = item
      ? `已选 #${linkId} · ${reverseType === "script" ? "脚本" : "视频"}反推`
      : "拆解 · 反推入库";
  }
}

async function renderReversePromptLibrary() {
  const root = document.getElementById("reversePromptLibraryList");
  if (!root) return;
  root.innerHTML = '<p class="muted">加载中…</p>';
  try {
    const productId = currentProductId() || "";
    const path = productId
      ? `/api/prompt-library?product_id=${encodeURIComponent(productId)}`
      : "/api/prompt-library";
    const data = await api(path);
    const rows = (data.reverse || data.items || []).filter(
      (r) => String(r.source || "").startsWith("reverse"),
    );
    if (!rows.length) {
      root.innerHTML = '<p class="muted">暂无反推提示词。选择素材并点击「开始反推」后自动入库。</p>';
      return;
    }
    root.innerHTML = rows.map((row, idx) => {
      const text = row.prompt_text_en || row.prompt_text || "";
      const usage = Number(row.usage_count) || 0;
      const typeZh = row.reverse_type === "script" ? "脚本" : "视频";
      return `
        <button type="button" class="feature-card prompt-select-card prompt-library-card" data-lib-idx="${idx}">
          <span class="feature-card-bg g-video-rev"></span>
          <span class="feature-card-label">
            <strong>${esc(row.label || "反推提示词")}</strong>
            <span>${esc(typeZh)} · 使用 ${usage} 次 · #${esc(row.link_id || "")}</span>
          </span>
        </button>`;
    }).join("");
    root.querySelectorAll(".prompt-library-card").forEach((card) => {
      card.addEventListener("click", () => {
        const row = rows[Number(card.dataset.libIdx)];
        const ta = document.getElementById("reverseDockPrompt");
        if (ta && row) ta.value = row.prompt_text_en || row.prompt_text || "";
      });
    });
  } catch (err) {
    root.innerHTML = `<p class="muted">加载失败：${esc(err.message)}</p>`;
  }
}

function loadReverseView() {
  syncReverseDockType();
  syncReverseDockMaterial();
  renderReversePromptLibrary();
}

async function runReversePrompt() {
  const linkId = state.reverseMaterialId;
  if (!linkId) {
    window.alert("请先从素材库选择对标视频");
    openMaterialLibraryDrawer();
    return;
  }
  const btn = document.getElementById("reverseDockRun");
  const ta = document.getElementById("reverseDockPrompt");
  const chip = document.getElementById("reverseDockStatusChip");
  const reverseType = state.reverseType || "video";
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="dock-run-icon">✦</span> 反推中…';
  }
  if (chip) chip.textContent = "正在反推并写入提示词库…";
  try {
    const data = await api(`/api/materials/${linkId}/reverse-prompt`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        reverse_type: reverseType,
        product_id: currentProductId() || "",
        save: true,
      }),
    });
    state.reverseLastResult = data;
    if (ta) ta.value = data.primary_prompt || "";
    if (chip) {
      chip.textContent = `已入库 ${data.saved_count || 0} 条 · ${data.composite_label || ""}`.slice(0, 48);
    }
    await renderReversePromptLibrary();
  } catch (err) {
    window.alert(err.message || "反推失败");
    if (chip) chip.textContent = "拆解 · 反推入库";
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<span class="dock-run-icon">✦</span> 开始反推';
    }
  }
}

function openGenerateModule() {
  switchView("generate");
  expandGenerateWorkspace();
  syncGenerateDockMode("generate");
  document.getElementById("generateDock")?.scrollIntoView({ behavior: "smooth", block: "end" });
}

async function renderDraftFeedbackHistory() {
  const root = document.getElementById("draftFeedbackHistoryList");
  if (!root) return;
  try {
    const data = await api("/api/library/finished");
    const items = (data.items || []).slice(0, 12);
    root.classList.remove("detail-empty");
    if (!items.length) {
      root.classList.add("detail-empty");
      root.innerHTML = "暂无成稿。完成交付后在此查看历史。";
      return;
    }
    root.innerHTML = items.map((r) => `
      <div class="feature-history-item">
        <span><strong>${esc(r.slug)}</strong> · ${esc(r.title || r.product_id || "")}</span>
        <span class="feature-history-actions">
          <span class="muted">${esc(r.saved_at || "")}</span>
          <button type="button" class="secondary pill-btn pill-btn-sm js-history-open-workspace" data-slug="${esc(r.slug)}">进入工作台</button>
        </span>
      </div>`).join("");
    root.querySelectorAll(".js-history-open-workspace").forEach((btn) => {
      btn.addEventListener("click", () => openHistoryInWorkspace(btn.dataset.slug));
    });
  } catch (err) {
    root.classList.add("detail-empty");
    root.innerHTML = `加载失败：${esc(err.message)}`;
  }
}

async function openHistoryInWorkspace(slug) {
  if (!slug) return;
  const item = state.items.find((m) => m.slug === slug || `ref-${String(m.link_id).padStart(3, "0")}` === slug);
  if (item) await selectMaterial(item.link_id);
  switchView("generate");
  refreshScriptFloatFromPreview(state.lastPreview || {});
  openScriptFloatPanel();
}

function renderGenerateExamples() {
  const root = document.getElementById("generateExamplesGrid");
  if (!root) return;
  const items = (state.items || []).filter((m) => m.analyzed).slice(0, 6);
  if (!items.length) {
    root.innerHTML = '<div class="detail-empty">暂无已拆解对标，请先在设置中同步并拆解素材。</div>';
    return;
  }
  root.innerHTML = items.map((m) => `
    <button type="button" class="feature-card" data-link-id="${m.link_id}">
      <span class="feature-card-bg g-video-rev"></span>
      <span class="feature-card-label"><strong>${esc((m.title || "").slice(0, 18) || `素材 #${m.link_id}`)}</strong><span>${esc(m.author || "")}</span></span>
    </button>`).join("");
  root.querySelectorAll("[data-link-id]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await selectMaterial(Number(btn.dataset.linkId));
      openRefFloatPanel();
      updateLoopBarFromForm(state.lastPreview || {});
    });
  });
}

async function renderDraftFeedbackStats() {
  const root = document.getElementById("draftFeedbackFeatureGrid");
  if (!root) return;
  try {
    const [fin, fb] = await Promise.all([
      api("/api/library/finished"),
      api("/api/library/feedback"),
    ]);
    const finN = (fin.items || []).length;
    const fbN = (fb.items || []).length;
    root.innerHTML = `
      <button type="button" class="feature-stat-card" data-action="finished">
        <strong>${finN}</strong><span>成稿库 · 已交付</span>
      </button>
      <button type="button" class="feature-stat-card" data-action="feedback">
        <strong>${fbN}</strong><span>反馈库 · 投放记录</span>
      </button>
      <button type="button" class="feature-stat-card" data-action="audit">
        <strong>—</strong><span>迭代优化 · 规划中</span>
      </button>`;
    root.querySelectorAll("[data-action]").forEach((btn) => {
      btn.addEventListener("click", () => handleDraftFeedbackFeature(btn.dataset.action));
    });
  } catch {
    renderFeatureGrid("draftFeedbackFeatureGrid", DRAFT_FEEDBACK_FEATURES);
  }
}

function initModuleStudios() {
  initDockGenSettings();
  renderAllImitationViralGrids();
  renderFeatureGrid("reverseFeatureGrid", REVERSE_FEATURES, {
    onClick: (id) => {
      const feat = REVERSE_FEATURES.find((f) => f.id === id);
      if (feat?.reverseType) {
        state.reverseType = feat.reverseType;
        syncReverseDockType();
        syncReverseDockMaterial();
      }
    },
  });
  renderDraftFeedbackStats();

  document.querySelectorAll('.module-studio[data-module="generate"] .module-studio-tabs button').forEach((btn) => {
    btn.addEventListener("click", () => switchGenerateStudioTab(btn.dataset.studioTab));
  });
  document.querySelectorAll('.module-studio[data-module="imitate"] .module-studio-tabs button').forEach((btn) => {
    btn.addEventListener("click", () => switchImitateStudioTab(btn.dataset.studioTab));
  });
  document.querySelectorAll('.module-studio[data-module="reverse"] .module-studio-tabs button').forEach((btn) => {
    btn.addEventListener("click", () => {
      const root = document.querySelector('.module-studio[data-module="reverse"]');
      switchModuleStudioTab(root, btn.dataset.studioTab);
      if (btn.dataset.studioTab === "exports") renderReversePromptLibrary();
    });
  });
  document.querySelectorAll('.module-studio[data-module="draft-feedback"] .module-studio-tabs button').forEach((btn) => {
    btn.addEventListener("click", () => switchDraftFeedbackStudioTab(btn.dataset.studioTab));
  });

  document.getElementById("generateBackHomeBtn")?.addEventListener("click", collapseGenerateWorkspace);
  document.getElementById("generateDockModeBtn")?.addEventListener("click", () => openGenerateModule());
  document.querySelector('#generateDock .studio-dock-modes [data-gen-mode="imitate"]')
    ?.addEventListener("click", () => {
      switchView("generate");
      syncGenerateDockMode("imitate");
    });
  document.querySelector('#generateDock .studio-dock-modes [data-gen-mode="generate"]')
    ?.addEventListener("click", () => openGenerateModule());
  document.getElementById("generateDockRun")?.addEventListener("click", () => runStartCreate());
  document.getElementById("imitateDockRun")?.addEventListener("click", () => runStartCreate());
  document.getElementById("dockOpenMaterialsBtn")?.addEventListener("click", () => openRefFloatPanel());
  document.getElementById("imitateOpenMaterialsBtn")?.addEventListener("click", () => openRefFloatPanel());
  document.getElementById("dockOpenProductBtn")?.addEventListener("click", () => openProductFloatPanel());
  document.getElementById("dockOpenPromptSelectBtn")?.addEventListener("click", () => openPromptSelectFloatPanel());
  document.getElementById("promptSelectFloatCloseBtn")?.addEventListener("click", closePromptSelectFloatPanel);
  document.getElementById("promptSelectFloatBackdrop")?.addEventListener("click", closePromptSelectFloatPanel);
  document.getElementById("promptSelectFloatConfirmBtn")?.addEventListener("click", confirmPromptSelectFloatPanel);
  document.getElementById("imitateOpenProductBtn")?.addEventListener("click", () => openProductFloatPanel());
  getImitationPromptEls().forEach((ta) => {
    ta.addEventListener("input", () => {
      syncImitationPromptFields();
      if (ta.id === "generateDockPrompt") syncDockPromptSelectSlot();
    });
  });
  document.getElementById("productFloatCloseBtn")?.addEventListener("click", closeProductFloatPanel);
  document.getElementById("productFloatBackdrop")?.addEventListener("click", closeProductFloatPanel);
  document.getElementById("productFloatConfirmBtn")?.addEventListener("click", async () => {
    syncProductFloatStatus();
    if (!document.getElementById("scriptProductSelect")?.value) {
      setScriptActionStatus("请先选择产品");
      return;
    }
    if (!tagsSelectionOk()) {
      setScriptActionStatus("请为人群、场景、卖点、痛点各至少选择一项");
      return;
    }
    const hadScript = Boolean(state.lastPreview?.has_script);
    const tagsChanged = tagsChangedSinceScript();
    const productId = document.getElementById("scriptProductSelect")?.value;
    const productChanged = Boolean(state.lastScriptProductId && productId !== state.lastScriptProductId);
    if (productChanged || tagsChanged) resetPromptEnhanceUsed();
    closeProductFloatPanel();
    const pendingViral = state.pendingViralLinkId;
    state.pendingViralLinkId = null;
    if (pendingViral) {
      await runViralBenchmarkPipeline(pendingViral);
      return;
    }
    if (hadScript && (tagsChanged || productChanged)) {
      await runScriptGenerate();
      await refreshScriptPreview();
      openScriptFloatPanel();
    } else {
      await refreshScriptPreview();
      updateLoopBarFromForm(state.lastPreview || {});
      syncDockProductSlot();
      syncDockRefSlot();
      repopulateScriptMaterials();
      renderAllImitationViralGrids();
      if (!state.selectedMaterialId) openRefFloatPanel();
    }
  });
  document.getElementById("refFloatCloseBtn")?.addEventListener("click", closeRefFloatPanel);
  document.getElementById("refFloatBackdrop")?.addEventListener("click", closeRefFloatPanel);
  document.getElementById("refFloatConfirmBtn")?.addEventListener("click", async () => {
    if (!state.selectedMaterialId) return;
    closeRefFloatPanel();
    syncDockRefSlot();
    if (document.getElementById("scriptProductSelect")?.value) {
      await refreshScriptPreview();
    }
    updateLoopBarFromForm(state.lastPreview || {});
  });
  document.getElementById("scriptFloatCloseBtn")?.addEventListener("click", closeScriptFloatPanel);
  document.getElementById("scriptFloatBackdrop")?.addEventListener("click", closeScriptFloatPanel);
  document.getElementById("scriptFloatProduceBtn")?.addEventListener("click", () => runConfirmProduceVideo());
  document.getElementById("scriptFloatSaveBtn")?.addEventListener("click", async () => {
    if (!scriptEditsDirty()) {
      setScriptActionStatus("脚本未修改，无需保存");
      return;
    }
    await saveScriptEditsIfDirty();
  });
  document.getElementById("scriptFloatRegenBtn")?.addEventListener("click", async () => {
    if (!tagsSelectionOk()) {
      await openProductFloatPanel();
      return;
    }
    await runScriptGenerate();
    openScriptFloatPanel();
  });
  document.getElementById("reverseDockMaterialBtn")?.addEventListener("click", () => openMaterialLibraryDrawer());
  document.getElementById("reverseDockRun")?.addEventListener("click", () => runReversePrompt());
  document.querySelectorAll("#reverseDock .studio-dock-modes button").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.reverseType = btn.dataset.reverseType || "video";
      syncReverseDockType();
      syncReverseDockMaterial();
    });
  });
  syncGenerateDockMode(state.generateDockMode || "imitate");
}

function syncDockChipsFromHealth() {
  const h = state.healthCache;
  const prov = h?.seedance?.provider === "volcengine-ark" ? "SeedDance" : "AI 视频";
  const mode = h?.seedance?.mode === "script" ? "脚本分镜" : "空镜";
  const modelText = h?.seedance ? `${prov} · ${mode}` : null;
  const model = document.getElementById("dockModelChip");
  if (model && modelText) model.textContent = modelText;
  const imitateChip = document.getElementById("imitateDockModelChip");
  if (imitateChip) imitateChip.textContent = modelText ? `爆款模仿 · ${mode}` : "爆款模仿 · 结构复刻";
  syncDailyScriptQuota();
  syncDailyVideoQuota();
  syncDockVideoSettingsLabel();
  syncDockProductSlot();
}

function syncDailyScriptQuota(quotaOverride) {
  const q = quotaOverride || state.healthCache?.production?.daily_script_quota;
  const chips = [
    document.getElementById("dailyScriptQuotaChip"),
    document.getElementById("imitateDailyQuotaChip"),
  ].filter(Boolean);
  if (!q?.enabled || !q.limit) {
    chips.forEach((chip) => chip.classList.add("hidden"));
  } else {
    const blocked = q.remaining <= 0;
    const label = `脚本 ${q.used}/${q.limit}`;
    chips.forEach((chip) => {
      chip.classList.remove("hidden", "quota-warn", "quota-full");
      chip.textContent = label;
      if (blocked) chip.classList.add("quota-full");
      else if (q.remaining <= 2) chip.classList.add("quota-warn");
    });
  }
  syncDockRunButtonsDisabled();
}

function syncDailyVideoQuota(quotaOverride) {
  const q = quotaOverride || state.healthCache?.production?.daily_video_quota;
  const chips = [
    document.getElementById("dailyVideoQuotaChip"),
    document.getElementById("imitateDailyVideoQuotaChip"),
  ].filter(Boolean);
  if (!q?.enabled || !q.limit) {
    chips.forEach((chip) => chip.classList.add("hidden"));
  } else {
    const blocked = q.remaining <= 0;
    const label = `成片 ${q.used}/${q.limit}`;
    chips.forEach((chip) => {
      chip.classList.remove("hidden", "quota-warn", "quota-full");
      chip.textContent = label;
      if (blocked) chip.classList.add("quota-full");
      else if (q.remaining <= 2) chip.classList.add("quota-warn");
    });
  }
  syncDockRunButtonsDisabled();
}

function syncDockRunButtonsDisabled() {
  const scriptQ = state.healthCache?.production?.daily_script_quota;
  const videoQ = state.healthCache?.production?.daily_video_quota;
  const scriptBlocked = scriptQ?.enabled && scriptQ.remaining <= 0;
  const videoBlocked = videoQ?.enabled && videoQ.remaining <= 0;
  document.querySelectorAll(".js-script-generate").forEach((btn) => {
    btn.disabled = scriptBlocked;
    btn.title = scriptBlocked ? "今日 LLM 脚本配额已满，明日再试或调高 DAILY_SCRIPT_QUOTA" : "";
  });
  document.querySelectorAll("#generateDockRun, #imitateDockRun, #scriptFloatProduceBtn").forEach((btn) => {
    btn.disabled = scriptBlocked || videoBlocked;
    btn.title = videoBlocked
      ? "今日成片产出配额已满，明日再试或调高 DAILY_VIDEO_QUOTA"
      : (scriptBlocked ? "今日 LLM 脚本配额已满" : "");
  });
}

function currentVideoSettings() {
  return state.videoSettings;
}

function persistVideoSettings() {
  try {
    localStorage.setItem("vl_video_settings", JSON.stringify(state.videoSettings));
  } catch { /* ignore */ }
}

function loadVideoSettings() {
  try {
    const raw = localStorage.getItem("vl_video_settings");
    if (!raw) return;
    const saved = JSON.parse(raw);
    if (VIDEO_RESOLUTIONS.includes(saved.resolution)) state.videoSettings.resolution = saved.resolution;
    if (VIDEO_ASPECT_RATIOS.includes(saved.aspectRatio)) state.videoSettings.aspectRatio = saved.aspectRatio;
    if (VIDEO_DURATIONS.includes(Number(saved.durationSec))) state.videoSettings.durationSec = Number(saved.durationSec);
    if (GENERATE_COUNTS.includes(Number(saved.generateCount))) state.videoSettings.generateCount = Number(saved.generateCount);
  } catch { /* ignore */ }
}

function syncDockVideoSettingsLabel() {
  const vs = currentVideoSettings();
  const text = `${vs.resolution} · ${vs.aspectRatio}`;
  const countText = `生成 ${vs.generateCount} 条`;
  for (const id of ["dockVideoSettingsLabel", "imitateDockVideoSettingsLabel"]) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  }
  for (const id of ["dockGenerateCountLabel", "imitateDockGenerateCountLabel"]) {
    const el = document.getElementById(id);
    if (el) el.textContent = countText;
  }
}

function renderDockVideoSettingsPanel() {
  const vs = currentVideoSettings();
  const resHtml = VIDEO_RESOLUTIONS.map((r) =>
    `<button type="button" class="dock-settings-pill${r === vs.resolution ? " active" : ""}" data-resolution="${r}">${r}</button>`
  ).join("");
  const ratioHtml = VIDEO_ASPECT_RATIOS.map((ratio) => {
    const cls = ratio.replace(":", "x");
    return `<button type="button" class="dock-ratio-btn${ratio === vs.aspectRatio ? " active" : ""}" data-aspect-ratio="${ratio}" title="${ratio}">
      <span class="dock-ratio-icon ratio-${cls}" aria-hidden="true"></span>
      <span>${ratio}</span>
    </button>`;
  }).join("");

  for (const id of ["dockResolutionRow", "imitateDockResolutionRow"]) {
    const row = document.getElementById(id);
    if (!row) continue;
    row.innerHTML = resHtml;
    row.querySelectorAll("[data-resolution]").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.videoSettings.resolution = btn.dataset.resolution;
        persistVideoSettings();
        renderDockVideoSettingsPanel();
        syncDockVideoSettingsLabel();
      });
    });
  }
  for (const id of ["dockAspectRatioRow", "imitateDockAspectRatioRow"]) {
    const row = document.getElementById(id);
    if (!row) continue;
    row.innerHTML = ratioHtml;
    row.querySelectorAll("[data-aspect-ratio]").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.videoSettings.aspectRatio = btn.dataset.aspectRatio;
        persistVideoSettings();
        renderDockVideoSettingsPanel();
        syncDockVideoSettingsLabel();
      });
    });
  }
}

function renderDockGenerateCountMenu() {
  const vs = currentVideoSettings();
  const html = GENERATE_COUNTS.map((n) =>
    `<button type="button" class="dock-gen-count-option${n === vs.generateCount ? " active" : ""}" role="menuitem" data-count="${n}">生成 ${n} 条</button>`
  ).join("");
  for (const id of ["dockGenerateCountMenu", "imitateDockGenerateCountMenu"]) {
    const menu = document.getElementById(id);
    if (!menu) continue;
    menu.innerHTML = html;
    menu.querySelectorAll("[data-count]").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.videoSettings.generateCount = Number(btn.dataset.count);
        persistVideoSettings();
        syncDockVideoSettingsLabel();
        renderDockGenerateCountMenu();
        closeDockGenerateCountMenu();
        closeImitateDockGenerateCountMenu();
      });
    });
  }
}

function closeImitateDockVideoSettingsPanel() {
  const wrap = document.getElementById("imitateVideoSettingsWrap");
  const btn = document.getElementById("imitateVideoSettingsBtn");
  const panel = document.getElementById("imitateDockVideoSettingsPanel");
  wrap?.classList.remove("open");
  btn?.setAttribute("aria-expanded", "false");
  panel?.classList.add("hidden");
  if (panel) panel.hidden = true;
}

function openImitateDockVideoSettingsPanel() {
  const wrap = document.getElementById("imitateVideoSettingsWrap");
  const btn = document.getElementById("imitateVideoSettingsBtn");
  const panel = document.getElementById("imitateDockVideoSettingsPanel");
  if (!wrap || !btn || !panel) return;
  closeImitateDockGenerateCountMenu();
  closeDockVideoSettingsPanel();
  closeDockGenerateCountMenu();
  renderDockVideoSettingsPanel();
  panel.classList.remove("hidden");
  panel.hidden = false;
  wrap.classList.add("open");
  btn.setAttribute("aria-expanded", "true");
}

function closeImitateDockGenerateCountMenu() {
  const wrap = document.getElementById("imitateGenerateCountWrap");
  const btn = document.getElementById("imitateGenerateCountBtn");
  const menu = document.getElementById("imitateDockGenerateCountMenu");
  wrap?.classList.remove("open");
  btn?.setAttribute("aria-expanded", "false");
  menu?.classList.add("hidden");
  if (menu) menu.hidden = true;
}

function openImitateDockGenerateCountMenu() {
  const wrap = document.getElementById("imitateGenerateCountWrap");
  const btn = document.getElementById("imitateGenerateCountBtn");
  const menu = document.getElementById("imitateDockGenerateCountMenu");
  if (!wrap || !btn || !menu) return;
  closeImitateDockVideoSettingsPanel();
  closeDockVideoSettingsPanel();
  closeDockGenerateCountMenu();
  renderDockGenerateCountMenu();
  menu.classList.remove("hidden");
  menu.hidden = false;
  wrap.classList.add("open");
  btn.setAttribute("aria-expanded", "true");
}

function closeDockVideoSettingsPanel() {
  const wrap = document.getElementById("dockVideoSettingsWrap");
  const btn = document.getElementById("dockVideoSettingsBtn");
  const panel = document.getElementById("dockVideoSettingsPanel");
  wrap?.classList.remove("open");
  btn?.setAttribute("aria-expanded", "false");
  panel?.classList.add("hidden");
  if (panel) panel.hidden = true;
}

function openDockVideoSettingsPanel() {
  const wrap = document.getElementById("dockVideoSettingsWrap");
  const btn = document.getElementById("dockVideoSettingsBtn");
  const panel = document.getElementById("dockVideoSettingsPanel");
  if (!wrap || !btn || !panel) return;
  closeImitateDockGenerateCountMenu();
  closeDockGenerateCountMenu();
  renderDockVideoSettingsPanel();
  panel.classList.remove("hidden");
  panel.hidden = false;
  wrap.classList.add("open");
  btn.setAttribute("aria-expanded", "true");
}

function closeDockGenerateCountMenu() {
  const wrap = document.getElementById("dockGenerateCountWrap");
  const btn = document.getElementById("dockGenerateCountBtn");
  const menu = document.getElementById("dockGenerateCountMenu");
  wrap?.classList.remove("open");
  btn?.setAttribute("aria-expanded", "false");
  menu?.classList.add("hidden");
  if (menu) menu.hidden = true;
}

function openDockGenerateCountMenu() {
  const wrap = document.getElementById("dockGenerateCountWrap");
  const btn = document.getElementById("dockGenerateCountBtn");
  const menu = document.getElementById("dockGenerateCountMenu");
  if (!wrap || !btn || !menu) return;
  closeDockVideoSettingsPanel();
  closeImitateDockVideoSettingsPanel();
  renderDockGenerateCountMenu();
  menu.classList.remove("hidden");
  menu.hidden = false;
  wrap.classList.add("open");
  btn.setAttribute("aria-expanded", "true");
}

function syncPromptEnhanceButton() {
  const used = state.promptEnhanceUsed;
  const title = used
    ? "本轮已使用提示词增强（切换产品/对标或完成生成后可再次使用）"
    : "结合标签与对标结构强化创作指令（每轮仅可点击一次）";
  for (const id of ["dockPromptEnhanceBtn", "imitatePromptEnhanceBtn"]) {
    const btn = document.getElementById(id);
    if (!btn) continue;
    btn.disabled = used;
    btn.classList.toggle("active", Boolean(state.promptEnhanceOn) && !used);
    btn.title = title;
  }
}

function resetPromptEnhanceUsed() {
  state.promptEnhanceUsed = false;
  state.promptEnhanceOn = false;
  syncPromptEnhanceButton();
}

function enhanceDockPrompt() {
  if (state.promptEnhanceUsed) return;
  const tags = readAllSelectedTags();
  const vs = currentVideoSettings();
  const material = state.items.find((i) => i.link_id === state.selectedMaterialId);
  const analysis = material?.analysis || state.lastPreview?.material?.analysis || {};
  const base = getImitationPrompt();
  const sceneLine = tags.scenarios[0]
    ? `${tags.scenarios[0]}场景：展示产品在真实使用环境中的卖点与痛点，口播自然、镜头节奏对标爆款结构。`
    : "";
  const lead = base || sceneLine;
  const boosts = [
    "【增强】结构：钩子3秒痛点 → 产品入画 → 使用演示 → 效果验证 → 软性CTA",
    tags.audience.length ? `人群：${tags.audience.join("、")}` : "",
    tags.scenarios.length ? `场景：${tags.scenarios.join("、")}` : "",
    tags.selling.length ? `卖点：${tags.selling.join("、")}` : "",
    tags.pains.length ? `痛点：${tags.pains.join("、")}` : "",
    `画幅 ${vs.aspectRatio} · ${vs.resolution} · 生成 ${vs.generateCount} 条`,
    analysis.video_structure ? `对标结构：${String(analysis.video_structure).slice(0, 100)}` : "",
    analysis.hook_3s ? `钩子参考：${String(analysis.hook_3s).slice(0, 80)}` : "",
    "口播口语化、镜头节奏紧凑；禁止医疗承诺、竞品品牌与夸大表述",
  ].filter(Boolean);
  setImitationPrompt(lead ? `${lead}\n\n${boosts.join("；")}` : boosts.join("；"));
  state.promptEnhanceOn = true;
  state.promptEnhanceUsed = true;
  syncPromptEnhanceButton();
}

function initDockGenSettings() {
  loadVideoSettings();
  syncDockVideoSettingsLabel();
  renderDockVideoSettingsPanel();
  renderDockGenerateCountMenu();

  syncPromptEnhanceButton();

  document.getElementById("dockVideoSettingsBtn")?.addEventListener("click", (e) => {
    e.stopPropagation();
    const wrap = document.getElementById("dockVideoSettingsWrap");
    if (wrap?.classList.contains("open")) closeDockVideoSettingsPanel();
    else openDockVideoSettingsPanel();
  });
  document.getElementById("dockGenerateCountBtn")?.addEventListener("click", (e) => {
    e.stopPropagation();
    const wrap = document.getElementById("dockGenerateCountWrap");
    if (wrap?.classList.contains("open")) closeDockGenerateCountMenu();
    else openDockGenerateCountMenu();
  });
  document.getElementById("dockPromptEnhanceBtn")?.addEventListener("click", () => {
    enhanceDockPrompt();
  });
  document.getElementById("imitateVideoSettingsBtn")?.addEventListener("click", (e) => {
    e.stopPropagation();
    const wrap = document.getElementById("imitateVideoSettingsWrap");
    if (wrap?.classList.contains("open")) closeImitateDockVideoSettingsPanel();
    else openImitateDockVideoSettingsPanel();
  });
  document.getElementById("imitateGenerateCountBtn")?.addEventListener("click", (e) => {
    e.stopPropagation();
    const wrap = document.getElementById("imitateGenerateCountWrap");
    if (wrap?.classList.contains("open")) closeImitateDockGenerateCountMenu();
    else openImitateDockGenerateCountMenu();
  });
  document.getElementById("imitatePromptEnhanceBtn")?.addEventListener("click", () => {
    enhanceDockPrompt();
  });

  document.addEventListener("click", (e) => {
    if (!e.target.closest("#dockVideoSettingsWrap")) closeDockVideoSettingsPanel();
    if (!e.target.closest("#dockGenerateCountWrap")) closeDockGenerateCountMenu();
    if (!e.target.closest("#imitateVideoSettingsWrap")) closeImitateDockVideoSettingsPanel();
    if (!e.target.closest("#imitateGenerateCountWrap")) closeImitateDockGenerateCountMenu();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closeDockVideoSettingsPanel();
      closeDockGenerateCountMenu();
      closeImitateDockVideoSettingsPanel();
      closeImitateDockGenerateCountMenu();
    }
  });
}

function normalizeView(name) {
  if (name === "home") return "generate";
  if (name === "materials" || name === "script" || name === "workspace") return "generate";
  if (name === "finished" || name === "feedback") return "draft-feedback";
  return name;
}

function viewElementId(name) {
  const n = normalizeView(name);
  const map = {
    generate: "viewWorkspace",
    imitate: "viewImitate",
    reverse: "viewReverse",
    "draft-feedback": "viewDraftFeedback",
    products: "viewProducts",
  };
  if (map[n]) return map[n];
  const camel = n.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
  return `view${camel.charAt(0).toUpperCase()}${camel.slice(1)}`;
}

function activateView(name, options = {}) {
  name = normalizeView(name);
  const viewId = viewElementId(name);
  const el = document.getElementById(viewId);
  if (!el) {
    console.warn(`Unknown view: ${name} (${viewId})`);
    document.getElementById("viewWorkspace")?.classList.add("active");
    state.view = "generate";
    loadWorkspaceView();
    return "generate";
  }
  state.view = name;
  document.querySelectorAll(".view").forEach((node) => node.classList.remove("active"));
  el.classList.add("active");
  document.querySelectorAll("#mainNav button").forEach((btn) => {
    btn.classList.toggle("active", normalizeView(btn.dataset.view) === name);
  });
  if (name === "generate") {
    loadWorkspaceView();
    if (!state.generateWorkspaceOpen) collapseGenerateWorkspace();
  }
  if (name === "imitate") loadImitateView();
  if (name === "reverse") loadReverseView();
  if (name === "products") loadProductsView();
  if (name === "draft-feedback") {
    const sub = options.sub || state.draftFeedbackSub || "finished";
    switchDraftFeedbackSub(sub);
    renderDraftFeedbackStats();
    renderDraftFeedbackHistory();
  }
  syncDockScrollPadding();
  return name;
}

function syncDraftFeedbackSubNav(sub) {
  state.draftFeedbackSub = sub;
  document.querySelectorAll("#draftFeedbackSubNav button").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.sub === sub);
  });
  document.getElementById("draftFeedbackPanelFinished")?.classList.toggle("hidden", sub !== "finished");
  document.getElementById("draftFeedbackPanelFeedback")?.classList.toggle("hidden", sub !== "feedback");
  const finishedPanel = document.getElementById("draftFeedbackPanelFinished");
  finishedPanel?.classList.toggle("active", sub === "finished");
  const feedbackPanel = document.getElementById("draftFeedbackPanelFeedback");
  feedbackPanel?.classList.toggle("active", sub === "feedback");
  document.querySelector('.module-studio[data-module="draft-feedback"]')
    ?.classList.toggle("draft-feedback-mode-feedback", sub === "feedback");
}

function switchDraftFeedbackSub(sub) {
  if (!["finished", "feedback"].includes(sub)) return;
  syncDraftFeedbackSubNav(sub);
  if (sub === "finished") loadFinishedView();
  if (sub === "feedback") loadFeedbackView();
  renderDraftFeedbackHistory();
}

function syncWorkspaceActionBar(step) {
  document.querySelectorAll(".workspace-action-step").forEach((el) => {
    el.classList.toggle("hidden", el.dataset.forStep !== step);
  });
}

function syncMaterialSelectFromState() {
  const ms = document.getElementById("scriptMaterialSelect");
  if (!ms || !state.selectedMaterialId) return;
  const val = String(state.selectedMaterialId);
  if (ms.querySelector(`option[value="${val}"]`)) ms.value = val;
}

function syncScriptProduceEmpty() {
  syncDockScrollPadding();
}

function setScriptStep(step, { scroll = true } = {}) {
  const order = ["product", "ref", "produce"];
  if (!order.includes(step)) return;
  state.scriptStep = step;
  syncWorkspaceActionBar(step);
  if (!scroll) return;
  if (step === "product") openProductFloatPanel();
  else if (step === "ref") openRefFloatPanel();
  else if (step === "produce") openScriptFloatPanel();
}

function updateLoopBarFromForm(prev = {}) {
  const hint = document.getElementById("loopHint");
  const hasMaterial = Boolean(document.getElementById("scriptMaterialSelect")?.value);
  const tagsOk = tagsSelectionOk();
  const hasScript = Boolean(prev.has_script) || Boolean(prev.delivery_ready);
  syncScriptProduceEmpty(hasScript);
  if (hint) {
    if (tagsChangedSinceScript() && hasScript) {
      hint.textContent = "产品定义已更新（场景/卖点/痛点），点击「开始创作」或「重新生成脚本」同步。";
    } else if (state.scriptStep === "produce" && prev.delivery_ready) {
      hint.textContent = "成片已完成：可下载 zip 或预览视频。";
    } else if (state.scriptStep === "produce" && hasScript) {
      hint.textContent = "请检查脚本与分镜，确认无误后点击「确认生成视频」。";
    } else if (state.scriptStep === "product") {
      hint.textContent = tagsOk
        ? "标签已齐 → 点击底部「对标」选择爆款。"
        : "点击底部「产品」配置人群、场景、卖点与痛点。";
    } else if (state.scriptStep === "ref" && !hasMaterial) {
      hint.textContent = "点击底部「对标」选择爆款视频。";
    } else if (state.scriptStep === "ref" && hasMaterial) {
      hint.textContent = "对标已选 → 点击「开始创作」生成脚本。";
    } else if (!tagsOk) {
      hint.textContent = "请先点击底部「产品」完成场景标签配置。";
    } else if (!hasMaterial) {
      hint.textContent = "产品已就绪 → 点击「对标」选择同品类爆款。";
    } else {
      hint.textContent = "产品与对标已就绪 → 点击「开始创作」生成脚本预览。";
    }
  }
  syncDockProductSlot();
  syncDockRefSlot();
}

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (window.__WB_TOKEN__) headers["X-Workbench-Token"] = window.__WB_TOKEN__;
  const res = await fetch(path, { ...options, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText);
  return data;
}

function withApiToken(path) {
  if (!window.__WB_TOKEN__) return path;
  const sep = path.includes("?") ? "&" : "?";
  return `${path}${sep}token=${encodeURIComponent(window.__WB_TOKEN__)}`;
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
  return document.getElementById("scriptFloatPanel");
}

function scriptResultBody() {
  return document.getElementById("scriptFloatBody");
}

// ── Navigation ─────────────────────────────────────────────────────────────

function switchView(name, options = {}) {
  activateView(name, options);
}

async function loadWorkspaceView() {
  if (!state.items.length) await loadMaterials();
  await loadScriptView();
  syncWorkspaceActionBar(state.scriptStep);
  renderAllImitationViralGrids();
  syncDockChipsFromHealth();
  syncDockProductSlot();
  syncDockRefSlot();
  syncImitationPromptFields();
  syncDockScrollPadding();
}

async function loadImitateView() {
  if (!state.items.length) await loadMaterials();
  if (!state.products.length) await loadScriptView();
  renderAllImitationViralGrids();
  syncDockChipsFromHealth();
  syncDockProductSlot();
  syncDockRefSlot();
  syncImitationPromptFields();
  syncFinishButton(Boolean(state.lastPreview?.can_finish), Boolean(state.lastPreview?.delivery_ready));
  const tab = state.imitateStudioTab || "featured";
  const root = document.querySelector('.module-studio[data-module="imitate"]');
  switchModuleStudioTab(root, tab);
  if (tab === "templates") renderImitateTemplates();
  syncDockScrollPadding();
}

function openSettingsDrawer() {
  const drawer = document.getElementById("settingsDrawer");
  const backdrop = document.getElementById("settingsBackdrop");
  const trigger = document.getElementById("settingsOpenBtn");
  if (!drawer || !backdrop) return;
  drawer.hidden = false;
  backdrop.hidden = false;
  requestAnimationFrame(() => {
    drawer.classList.add("open");
    backdrop.classList.add("open");
  });
  drawer.setAttribute("aria-hidden", "false");
  trigger?.setAttribute("aria-expanded", "true");
  loadSettingsView();
}

function closeSettingsDrawer() {
  const drawer = document.getElementById("settingsDrawer");
  const backdrop = document.getElementById("settingsBackdrop");
  const trigger = document.getElementById("settingsOpenBtn");
  if (!drawer || !backdrop) return;
  drawer.classList.remove("open");
  backdrop.classList.remove("open");
  drawer.setAttribute("aria-hidden", "true");
  trigger?.setAttribute("aria-expanded", "false");
  window.setTimeout(() => {
    if (!drawer.classList.contains("open")) {
      drawer.hidden = true;
      backdrop.hidden = true;
    }
  }, 220);
}

function openCollectorEntry() {
  openSettingsDrawer();
  ensureCollectorPanel();
  window.setTimeout(() => {
    const block = document.getElementById("collectorSettingsBlock");
    if (block) block.open = true;
    document.getElementById("collectorKeywords")?.focus();
  }, 180);
}

function openTikTokLibraryEntry() {
  openMaterialLibraryDrawer();
  window.setTimeout(() => {
    const fold = document.querySelector(".material-library-tiktok-db");
    if (fold) fold.open = true;
    document.getElementById("materialLibraryTikTokQuery")?.focus();
  }, 180);
}

const STARTER_GUIDE_DISMISSED_KEY = "vl_starter_guide_dismissed";

function isStarterGuideDismissed() {
  return (
    localStorage.getItem(STARTER_GUIDE_DISMISSED_KEY) === "1"
    || localStorage.getItem("vl_starter_guide_closed") === "1"
  );
}

function dismissStarterGuide() {
  localStorage.setItem(STARTER_GUIDE_DISMISSED_KEY, "1");
  localStorage.removeItem("vl_starter_guide_closed");
  closeStarterGuidePanel();
}

function openStarterGuidePanel() {
  if (isStarterGuideDismissed()) return;
  openFloatPanel("starterGuidePanel", "starterGuideBackdrop");
}

function closeStarterGuidePanel() {
  closeFloatPanel("starterGuidePanel", "starterGuideBackdrop");
}

function ensureCollectorPanel() {
  if (document.getElementById("btnCollectorRun")) return;
  const body = document.querySelector(".settings-drawer-body");
  const productsBlock = document.getElementById("openProductsBtn")?.closest(".settings-block");
  if (!body || !productsBlock) return;
  const wrap = document.createElement("details");
  wrap.id = "collectorSettingsBlock";
  wrap.className = "settings-block";
  wrap.open = true;
  wrap.innerHTML = `
    <summary>TikTok 采集</summary>
    <p class="hint">按关键词抓取 TikTok 公开视频元数据，并自动同步入当前素材库。</p>
    <p id="collectorRuntimeHint" class="workflow-warn hidden"></p>
    <div class="collector-form">
      <label>关键词
        <textarea id="collectorKeywords" rows="3" placeholder="每行一个关键词，例如：&#10;breast pump&#10;baby bottle&#10;baby products"></textarea>
      </label>
      <label>每词条数
        <input id="collectorLimit" type="number" min="1" max="200" value="50">
      </label>
      <p class="hint muted">默认每词 50 条；可在 <code>tiktok_collector/.env</code> 调整滚动次数与清洗阈值。</p>
      <div class="collector-actions">
        <button type="button" class="primary pill-btn" id="btnCollectorRun">开始采集</button>
      </div>
      <div id="collectorStatus" class="seedance-status">待执行</div>
      <div id="collectorResult" class="collector-result muted"></div>
      <div class="collector-actions">
        <button type="button" class="pill-btn" id="btnCollectorQuery">MySQL</button>
      </div>
      <label>TikTok 库内查询
        <input id="collectorQueryText" type="text" placeholder="关键词 / 作者 / video_id / hashtag">
      </label>
      <div id="collectorQueryStatus" class="seedance-status muted">待查询</div>
      <div id="collectorQueryResult" class="collector-query-result muted tiktok-db-preview-list"></div>
    </div>`;
  body.insertBefore(wrap, productsBlock);
  document.getElementById("btnCollectorRun")?.addEventListener("click", runCollectorImport);
  document.getElementById("btnCollectorQuery")?.addEventListener("click", runCollectorQuery);
  void refreshCollectorRuntimeHint();
}

async function refreshCollectorRuntimeHint() {
  const hint = document.getElementById("collectorRuntimeHint");
  if (!hint) return;
  try {
    const health = await api("/api/health");
    const runtime = health.tiktok_collector?.runtime || {};
    if (runtime.launch_blocked) {
      hint.classList.remove("hidden");
      hint.textContent = runtime.launch_blocked;
      return;
    }
    if (runtime.cursor_sandbox || (runtime.playwright_sandbox_path && !runtime.collector_ready)) {
      hint.classList.remove("hidden");
      hint.textContent =
        "当前服务在 Cursor 沙箱中运行，TikTok 采集不可用。请关闭 Cursor 内的 python 服务，在资源管理器中双击「启动页面.cmd」重新打开工作台。";
      return;
    }
    if (!runtime.system_browsers?.length) {
      hint.classList.remove("hidden");
      hint.textContent = "未检测到本机 Chrome/Edge，请先安装浏览器后再采集。";
      return;
    }
    hint.classList.add("hidden");
    hint.textContent = "";
  } catch {
    hint.classList.add("hidden");
  }
}

const TIKTOK_DB_PREVIEW_LIMIT = 20;
const TIKTOK_DB_CAPTION_LEN = 48;

function renderTikTokDbPreviewCards(items, total = items.length) {
  if (!items.length) return '<div class="muted">暂无匹配记录。</div>';
  const shown = items.slice(0, TIKTOK_DB_PREVIEW_LIMIT);
  const rest = Math.max(0, (total || items.length) - shown.length);
  const cards = shown.map((item) => {
    const caption = String(item.caption || "").trim();
    const short = caption.slice(0, TIKTOK_DB_CAPTION_LEN);
    return `<article class="tiktok-db-preview-card">
      <a href="${esc(item.video_url)}" target="_blank" rel="noreferrer">${esc(item.author_name || item.video_id || "视频")}</a>
      <span class="tiktok-db-preview-meta">${esc(item.source_keyword || "-")} · ${esc(item.like_count || 0)} 赞 · ${esc(item.comment_count || 0)} 评</span>
      ${caption ? `<p class="tiktok-db-preview-caption">${esc(short)}${caption.length > TIKTOK_DB_CAPTION_LEN ? "…" : ""}</p>` : ""}
    </article>`;
  }).join("");
  const more = rest > 0
    ? `<p class="tiktok-db-preview-more muted">还有 ${rest} 条未展示，请缩小关键词或在下方素材库查看</p>`
    : "";
  return cards + more;
}

function normalizeCollectorError(message) {
  return String(message || "")
    .replace(/^采集失败：/g, "")
    .replace(/^TikTok 采集失败:\s*/gi, "")
    .trim();
}

function collectorErrorHint(message) {
  const raw = normalizeCollectorError(message);
  if (/cursor-sandbox|cursor 沙箱|不要用 cursor|cursor-sandbox-cache/i.test(raw)) {
    return [
      "服务正在 Cursor 内置终端/沙箱中运行，无法调用本机 Chrome。",
      "1. 关掉 Cursor 里运行 app.main 的终端窗口",
      "2. 打开文件夹：海外视频本地化工作流\\海外视频本地化MVP",
      "3. 双击「启动页面.cmd」",
      "4. 浏览器打开 http://127.0.0.1:8788 后再采集",
    ].join("\n");
  }
  if (/不是通过「启动页面\.cmd」启动|WORKBENCH_LAUNCHER|常见于 Cursor/i.test(raw)) {
    return [
      "工作台必须从 cmd 窗口启动，不能从 Cursor 终端启动：",
      "1. 关掉 Cursor 里运行 python 的终端（以及占用 8788 的旧服务）",
      "2. 双击根目录「启动工作台.cmd」或 海外视频本地化MVP\\启动页面.cmd",
      "3. 等黑窗口出现「启动本地化工作台」后再采集",
    ].join("\n");
  }
  if (/has been closed|target page, context or browser|profile appears to be in use|singletonlock/i.test(raw)) {
    return [
      "浏览器配置目录可能被占用或上次异常退出：",
      "1. 关闭所有 Chrome / Edge 窗口（含后台）",
      "2. 关闭工作台黑窗口，双击「启动页面.cmd」重新打开",
      "3. 再试采集；仍失败可删除文件夹：tiktok_collector\\data\\browser_profile",
      "4. 不要用 Cursor 终端启动服务",
    ].join("\n");
  }
  if (/playwright|chromium|chrome\.exe|launch_persistent|无法启动/i.test(raw)) {
    return [
      "无需 playwright install。请确认：",
      "1. 本机已安装 Google Chrome 或 Edge",
      "2. 不要用 Cursor 终端启动服务",
      "3. 双击「启动页面.cmd」打开工作台",
      "4. 采集时会弹出浏览器窗口",
    ].join("\n");
  }
  return "";
}

function renderCollectorError(resultEl, message) {
  if (!resultEl) return;
  const raw = normalizeCollectorError(message);
  const hint = collectorErrorHint(message);
  resultEl.className = "collector-result collector-error-detail";
  resultEl.innerHTML = `
    <p class="collector-error-msg">${esc(raw)}</p>
    ${hint ? `<p class="collector-error-hint">${esc(hint)}</p>` : ""}`;
}

async function runCollectorImport() {
  const keywordsRaw = document.getElementById("collectorKeywords")?.value || "";
  const keywords = keywordsRaw.split(/\r?\n/).map((s) => s.trim()).filter(Boolean);
  const limit = Number(document.getElementById("collectorLimit")?.value || 50);
  const productId = productIdForScopedCapture();
  const statusEl = document.getElementById("collectorStatus");
  const resultEl = document.getElementById("collectorResult");
  if (!keywords.length) {
    if (statusEl) statusEl.textContent = "请至少输入一个关键词";
    return;
  }
  if (!productId) return;
  if (statusEl) {
    statusEl.className = "seedance-status collector-status";
    statusEl.textContent = `正在采集「${currentProductLabel()}」同品类 TikTok 数据…`;
  }
  if (resultEl) {
    resultEl.className = "collector-result muted";
    resultEl.textContent = "";
  }
  try {
    const data = await api("/api/tiktok-collector/collect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        keywords,
        limit_per_keyword: Number.isFinite(limit) ? limit : 50,
        product_id: productId,
      }),
    });
    if (statusEl) {
      statusEl.className = "seedance-status collector-status";
      statusEl.textContent = `采集完成：抓取 ${data.total_collected} 条，入库 ${data.imported_total ?? (data.imported_new_links + data.updated_existing_links)} 条（新增 ${data.imported_new_links}，更新 ${data.updated_existing_links}，清洗丢弃 ${data.total_dropped || 0}）`;
    }
    if (resultEl) {
      resultEl.className = "collector-result muted";
      const parts = [
        data.json_path ? `JSON: ${data.json_path}` : "",
        data.csv_path ? `CSV: ${data.csv_path}` : "",
        data.output_dir ? `输出目录: ${data.output_dir}` : "",
      ].filter(Boolean);
      resultEl.textContent = parts.join(" | ");
    }
    await refreshHealth();
    await loadMaterials();
  } catch (err) {
    if (statusEl) {
      statusEl.className = "seedance-status collector-status collector-status-error";
      statusEl.textContent = "采集失败";
    }
    renderCollectorError(resultEl, err.message);
  }
}

function renderCollectorQueryItems(items, total) {
  return renderTikTokDbPreviewCards(items, total);
}

async function runCollectorQuery() {
  const q = document.getElementById("collectorQueryText")?.value?.trim() || "";
  const statusEl = document.getElementById("collectorQueryStatus");
  const resultEl = document.getElementById("collectorQueryResult");
  if (statusEl) statusEl.textContent = "正在查询 MySQL…";
  if (resultEl) resultEl.innerHTML = "";
  try {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    params.set("limit", String(TIKTOK_DB_PREVIEW_LIMIT));
    const data = await api(`/api/tiktok-collector/db/videos?${params.toString()}`);
    if (statusEl) {
      statusEl.textContent = data.db_enabled
        ? `MySQL 查询完成，命中 ${data.total} 条，预览 ${Math.min(data.items.length, TIKTOK_DB_PREVIEW_LIMIT)} 条`
        : "未配置 MySQL，无法查询。";
    }
    if (resultEl) resultEl.innerHTML = renderCollectorQueryItems(data.items || [], data.total);
  } catch (err) {
    if (statusEl) statusEl.textContent = `MySQL 查询失败：${err.message}`;
  }
}

function openMaterialLibraryDrawer() {
  const drawer = document.getElementById("materialLibraryDrawer");
  const backdrop = document.getElementById("materialLibraryBackdrop");
  if (!drawer || !backdrop) return;
  syncDrawerFiltersFromState();
  drawer.hidden = false;
  backdrop.hidden = false;
  requestAnimationFrame(() => {
    drawer.classList.add("open");
    backdrop.classList.add("open");
  });
  drawer.setAttribute("aria-hidden", "false");
  void loadMaterials();
}

function closeMaterialLibraryDrawer() {
  const drawer = document.getElementById("materialLibraryDrawer");
  const backdrop = document.getElementById("materialLibraryBackdrop");
  if (!drawer || !backdrop) return;
  drawer.classList.remove("open");
  backdrop.classList.remove("open");
  drawer.setAttribute("aria-hidden", "true");
  window.setTimeout(() => {
    if (!drawer.classList.contains("open")) {
      drawer.hidden = true;
      backdrop.hidden = true;
    }
  }, 220);
}

function syncProductFloatStatus() {
  const el = document.getElementById("productFloatStatus");
  if (!el) return;
  const ps = document.getElementById("scriptProductSelect");
  const productName = ps?.selectedOptions?.[0]?.textContent?.trim() || "";
  if (!ps?.value) {
    el.textContent = "请先选择产品";
    return;
  }
  if (!tagsSelectionOk()) {
    el.textContent = "请为人群、场景、卖点、痛点各至少选择一项";
    return;
  }
  el.textContent = productName ? `已配置：${productName}` : "标签已就绪";
}

function syncDockProductSlot() {
  const ready = Boolean(document.getElementById("scriptProductSelect")?.value) && tagsSelectionOk();
  for (const id of ["dockOpenProductBtn", "imitateOpenProductBtn"]) {
    const btn = document.getElementById(id);
    if (btn) btn.classList.toggle("has-value", ready);
  }
}

function syncDockRefSlot() {
  const ready = productWorkflowReady();
  for (const id of ["dockOpenMaterialsBtn", "imitateOpenMaterialsBtn"]) {
    const btn = document.getElementById(id);
    if (!btn) continue;
    btn.disabled = !ready;
    btn.classList.toggle("dock-upload-slot-locked", !ready);
    btn.classList.toggle("has-value", ready && Boolean(state.selectedMaterialId));
    btn.title = ready ? "选择同品类对标视频" : "请先点击「产品」完成配置";
  }
}

function syncRefFloatStatus() {
  const el = document.getElementById("refFloatStatus");
  if (!el) return;
  const item = state.items.find((i) => i.link_id === state.selectedMaterialId);
  if (item) {
    const title = (item.title || "").slice(0, 24);
    el.textContent = `已选 #${item.link_id}${title ? ` · ${title}` : ""}`;
  } else {
    el.textContent = "未选择对标";
  }
}

function syncRefFloatFiltersFromState() {
  const cat = document.getElementById("refFloatCategorySelect");
  const kw = document.getElementById("refFloatKeywordInput");
  const analyzed = document.getElementById("refFloatAnalyzedOnly");
  const showAll = document.getElementById("refFloatShowAllMaterials");
  if (cat) cat.value = state.filters.category || "";
  if (kw) kw.value = state.filters.q || "";
  if (analyzed) analyzed.checked = Boolean(state.filters.analyzedOnly);
  if (showAll) showAll.checked = Boolean(state.showAllMaterials);
}

function syncDrawerFiltersFromState() {
  const cat = document.getElementById("categorySelect");
  const kw = document.getElementById("keywordInput");
  const analyzed = document.getElementById("analyzedOnly");
  const showAll = document.getElementById("showAllMaterials");
  if (cat) cat.value = state.filters.category || "";
  if (kw) kw.value = state.filters.q || "";
  if (analyzed) analyzed.checked = Boolean(state.filters.analyzedOnly);
  if (showAll) showAll.checked = Boolean(state.showAllMaterials);
}

async function openRefFloatPanel() {
  if (!productWorkflowReady()) {
    await openProductFloatPanel();
    return;
  }
  if (!state.items.length) await loadMaterials();
  syncRefFloatFiltersFromState();
  if (!state.showAllMaterials) {
    const pool = getMaterialPreviewPool();
    if (state.selectedMaterialId && !pool.some((i) => i.link_id === state.selectedMaterialId)) {
      state.selectedMaterialId = null;
      syncMaterialSelectFromState();
      const pane = document.getElementById("materialDetail");
      if (pane) {
        pane.className = "detail-empty ref-float-detail";
        pane.innerHTML = "选择左侧对标视频查看拆解";
      }
    }
  }
  renderRefFloatMaterialList();
  syncRefFloatProductLine();
  renderGenerateViralGrid();
  openFloatPanel("refFloatPanel", "refFloatBackdrop");
  syncRefFloatStatus();
  if (state.selectedMaterialId) {
    const pane = document.getElementById("materialDetail");
    if (pane && pane.classList.contains("detail-empty")) {
      await selectMaterial(state.selectedMaterialId, { keepDetail: true });
    }
  }
}

function closeRefFloatPanel() {
  closeFloatPanel("refFloatPanel", "refFloatBackdrop", () => {
    syncDockRefSlot();
    updateLoopBarFromForm(state.lastPreview || {});
  });
}

function openScriptFloatPanel() {
  refreshScriptFloatFromPreview(state.lastPreview || {});
  openFloatPanel("scriptFloatPanel", "scriptFloatBackdrop");
}

function closeScriptFloatPanel() {
  closeFloatPanel("scriptFloatPanel", "scriptFloatBackdrop");
}

async function openProductFloatPanel() {
  const panel = document.getElementById("productFloatPanel");
  const backdrop = document.getElementById("productFloatBackdrop");
  if (!panel || !backdrop) return;
  await populateScriptProductSelect();
  const productId = document.getElementById("scriptProductSelect")?.value;
  if (productId) {
    await loadProductTagPanel(productId);
    if (state.selectedMaterialId) await refreshScriptPreview();
  }
  openFloatPanel("productFloatPanel", "productFloatBackdrop");
  syncProductFloatStatus();
}

function closeProductFloatPanel() {
  closeFloatPanel("productFloatPanel", "productFloatBackdrop", () => {
    syncDockProductSlot();
    updateLoopBarFromForm(state.lastPreview || {});
  });
}

document.getElementById("decomposeCollectorBtn")?.addEventListener("click", () => openCollectorEntry());
document.getElementById("decomposeLibraryBtn")?.addEventListener("click", () => openMaterialLibraryDrawer());
["openMaterialLibraryBtn"].forEach((id) => {
  document.getElementById(id)?.addEventListener("click", () => openMaterialLibraryDrawer());
});
document.getElementById("openMaterialLibraryAnalyzedBtn")?.addEventListener("click", () => {
  state.filters.analyzedOnly = true;
  const analyzed = document.getElementById("analyzedOnly");
  if (analyzed) analyzed.checked = true;
  const ref = document.getElementById("refFloatAnalyzedOnly");
  if (ref) ref.checked = true;
  openMaterialLibraryDrawer();
});
document.getElementById("materialLibraryCloseBtn")?.addEventListener("click", closeMaterialLibraryDrawer);
document.getElementById("materialLibraryBackdrop")?.addEventListener("click", closeMaterialLibraryDrawer);
document.getElementById("materialLibraryTikTokSearchBtn")?.addEventListener("click", () => loadMaterialLibraryTikTokDb());
document.getElementById("materialLibraryTikTokQuery")?.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    loadMaterialLibraryTikTokDb();
  }
});

document.getElementById("mainNav")?.addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-view]");
  if (btn) switchView(btn.dataset.view);
});

document.getElementById("draftFeedbackSubNav")?.addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-sub]");
  if (btn) switchDraftFeedbackSub(btn.dataset.sub);
});

// ── Health / stats ───────────────────────────────────────────────────────

async function refreshHealth() {
  try {
    const h = await api("/api/health");
    state.healthCache = h;
    const matEl = document.getElementById("statMaterials");
    const anaEl = document.getElementById("statAnalyzed");
    if (matEl) matEl.textContent = h.materials ?? 0;
    if (anaEl) anaEl.textContent = h.analyzed ?? 0;
    syncDockChipsFromHealth();
    return h;
  } catch (err) {
    console.warn("refreshHealth failed", err);
    const matEl = document.getElementById("statMaterials");
    const anaEl = document.getElementById("statAnalyzed");
    if (matEl && matEl.textContent === "-") matEl.textContent = "?";
    if (anaEl && anaEl.textContent === "-") anaEl.textContent = "?";
    throw err;
  }
}

function renderSeedanceSettings(health) {
  const el = document.getElementById("seedanceSettingsStatus");
  if (!el) return;
  const sd = health?.seedance || {};
  const mode = sd.mode === "script" ? "脚本分镜模式（各镜生成短视频）" : "空镜模式（仅痛点镜）";
  if (!sd.configured) {
    el.innerHTML = `未配置 · 在 <code>overseas-loc-mvp/.env</code> 填写 <code>ARK_API_KEY</code><br><span class="muted">${esc(sd.setup || "")}</span>`;
    return;
  }
  const prov = sd.provider === "volcengine-ark" ? "火山方舟 Ark" : (sd.provider || "fal.ai");
  el.innerHTML = `已配置 ${esc(prov)} · ${esc(mode)}<br>模型 <code>${esc(sd.text_model || "")}</code>`;
}

function feishuResultText(data) {
  if (!data) return "";
  const payload = data.json && typeof data.json === "object" ? data.json : null;
  const parts = [];
  const url = payload?.verification_uri_complete || payload?.verification_url || payload?.url;
  const userCode = payload?.user_code || payload?.code;
  const deviceCode = payload?.device_code;
  if (url) parts.push(`授权链接：${url}`);
  if (userCode) parts.push(`用户码：${userCode}`);
  if (deviceCode) parts.push(`device_code：${deviceCode}`);
  const out = String(data.stdout || "").trim();
  const err = String(data.stderr || "").trim();
  if (out && !parts.includes(out)) parts.push(out);
  if (err) parts.push(err);
  return parts.join("\n\n") || (data.ok ? "完成" : "无输出");
}

function renderFeishuSettings(status) {
  const el = document.getElementById("feishuSettingsStatus");
  if (!el) return;
  const fs = status?.feishu || status || {};
  if (!fs.installed) {
    el.innerHTML = `未安装 · 本地工具目录 <code>tools/feishu-cli</code><br><span class="muted">请重新执行 Feishu CLI 集成。</span>`;
    return;
  }
  const version = fs.version || fs.package_version || "@larksuite/cli";
  if (fs.authenticated) {
    el.innerHTML = `已安装并授权 · <code>${esc(version)}</code>`;
    return;
  }
  if (fs.configured === false) {
    el.innerHTML = `已安装 · <code>${esc(version)}</code><br><span class="warn-inline">尚未配置/授权</span>：先运行根目录 <code>配置飞书CLI.cmd</code>，再回到这里检测。`;
    return;
  }
  el.innerHTML = `已安装 · <code>${esc(version)}</code><br><span class="muted">点击「检测状态」查看配置和授权。</span>`;
}

function showFeishuOutput(data) {
  const out = document.getElementById("feishuAuthOutput");
  if (!out) return;
  out.classList.remove("hidden");
  out.textContent = feishuResultText(data);
}

async function refreshFeishuSettings() {
  const el = document.getElementById("feishuSettingsStatus");
  if (el) el.textContent = "正在检测飞书 CLI…";
  try {
    const status = await api("/api/feishu/status");
    renderFeishuSettings(status);
    return status;
  } catch (err) {
    if (el) el.textContent = err.message || "飞书 CLI 检测失败";
    throw err;
  }
}

function renderSeedance(slug, seedance, health) {
  const statusEl = document.getElementById("seedanceStatus");
  const pipelineEl = document.getElementById("seedancePipeline");
  const hintEl = document.getElementById("seedanceHint");
  if (!statusEl) return;

  const pipeline = seedance?.pipeline || health?.seedance?.label || "";
  if (pipelineEl) pipelineEl.textContent = pipeline;

  if (!slug || !seedance) {
    showSeedanceProgress(false);
    renderSeedanceFinalPreview(null, null);
    return;
  }

  const finalReady = Boolean(seedance.final_video?.ready);
  renderSeedanceFinalPreview(slug, seedance);

  if (!state.createPipelineActive) {
    showSeedanceProgress(false);
    return;
  }

  const configured = health?.seedance?.configured;
  if (!configured) {
    statusEl.textContent = "未连接 SeedDance";
    showSeedanceProgress(true, {
      status: "未配置 ARK_API_KEY",
      pipeline: health?.seedance?.setup || "",
      percent: 0,
    });
    if (hintEl) hintEl.textContent = health?.seedance?.setup || "";
    return;
  }

  const prov = health.seedance.provider === "volcengine-ark" ? "火山方舟 Ark" : (health.seedance.provider || "fal.ai");
  const modeHint = health.seedance.mode === "script" ? "脚本分镜模式" : "空镜模式";
  const statusText = `已连接 ${prov} · ${modeHint} · ${health.seedance.text_model || ""}`;
  statusEl.textContent = statusText;

  const shots = seedance.shots || [];
  const readyCount = shots.filter((s) => s.ready).length;
  const total = shots.length || 5;
  const pct = finalReady ? 100 : (total ? Math.round((readyCount / total) * 90) : 10);

  showSeedanceProgress(true, {
    status: finalReady ? "成片已就绪" : (readyCount ? `已生成 ${readyCount}/${total} 镜` : statusText),
    pipeline,
    percent: pct,
    indeterminate: !finalReady && readyCount === 0,
  });

  if (hintEl) {
    hintEl.textContent = finalReady
      ? "视频生成完成"
      : "每镜约 5 秒；全部生成后自动拼接为 final-video.mp4";
  }

  document.getElementById("seedanceShots").innerHTML = shots.map((s) => `<span data-n="${s.number}"></span>`).join("");
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
  for (const id of ["categorySelect", "refFloatCategorySelect"]) {
    const cs = document.getElementById(id);
    if (!cs) continue;
    cs.innerHTML = '<option value="">全部</option>';
    (data.categories || []).forEach((c) => {
      const o = document.createElement("option");
      o.value = c;
      o.textContent = CATEGORY_ZH[c] || c;
      cs.appendChild(o);
    });
  }
}

async function loadMaterials() {
  const p = new URLSearchParams();
  if (state.filters.category) p.set("category", state.filters.category);
  if (state.filters.q) p.set("q", state.filters.q);
  if (state.filters.analyzedOnly) p.set("analyzed_only", "true");
  state.items = (await api(`/api/materials?${p}`)).items || [];
  renderMaterialList();
  renderRefFloatMaterialList();
  renderGenerateViralGrid();
}

function renderMaterialLibraryTikTokCards(items, total) {
  return renderTikTokDbPreviewCards(items, total);
}

async function loadMaterialLibraryTikTokDb() {
  const q = document.getElementById("materialLibraryTikTokQuery")?.value?.trim() || state.filters.q || "";
  const statusEl = document.getElementById("materialLibraryTikTokStatus");
  const listEl = document.getElementById("materialLibraryTikTokList");
  const summaryEl = document.getElementById("materialLibraryTikTokSummary");
  if (statusEl) statusEl.textContent = "正在查询…";
  if (listEl) listEl.innerHTML = "";
  try {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    params.set("limit", String(TIKTOK_DB_PREVIEW_LIMIT));
    const data = await api(`/api/tiktok-collector/db/videos?${params.toString()}`);
    if (statusEl) {
      statusEl.textContent = data.db_enabled
        ? `命中 ${data.total} 条，预览 ${Math.min((data.items || []).length, TIKTOK_DB_PREVIEW_LIMIT)} 条`
        : "未启用 TikTok 数据库";
    }
    if (summaryEl && data.db_enabled) {
      summaryEl.textContent = data.total ? `（${data.total} 条）` : "（无结果）";
    }
    if (listEl) listEl.innerHTML = renderMaterialLibraryTikTokCards(data.items || [], data.total);
  } catch (err) {
    if (statusEl) statusEl.textContent = `查询失败：${err.message}`;
  }
}

function materialBadgeHtml(item) {
  if (!item.has_analysis) {
    return '<span class="badge badge-pending">待拆解</span>';
  }
  return '<span class="badge badge-done">已拆解</span>';
}

function materialCardHtml(item, { compact = false } = {}) {
  const active = item.link_id === state.selectedMaterialId ? "active" : "";
  const thumb = item.thumbnail_url
    ? `<img class="thumb" src="${esc(item.thumbnail_url)}" alt="">`
    : '<div class="thumb placeholder">无图</div>';
  const stats = [fmtNum(item.view_count) && `${fmtNum(item.view_count)}播放`, item.duration_sec && `${item.duration_sec}s`].filter(Boolean).join(" · ");
  const badge = materialBadgeHtml(item);
  const title = item.title || "";
  const titleText = `#${item.link_id} ${title}`;
  const titleSlice = compact ? 56 : 80;
  return `<button type="button" class="card ${active}" data-id="${item.link_id}">
    ${thumb}
    <div><h3 title="${esc(titleText)}">${esc(`#${item.link_id} ${title.slice(0, titleSlice)}`)}</h3>
    <div class="meta">${esc(item.author)}${stats ? ` · ${stats}` : ""}</div>${badge}</div>
  </button>`;
}

function productWorkflowReady() {
  return Boolean(document.getElementById("scriptProductSelect")?.value) && tagsSelectionOk();
}

function currentProductId() {
  return document.getElementById("scriptProductSelect")?.value || state.selectedProductId || "";
}

function currentProductLabel() {
  const productId = currentProductId();
  const p = state.products.find((x) => x.product_id === productId);
  return p?.product_name || productId;
}

function getMaterialPreviewPool() {
  const productId = currentProductId();
  let pool = state.items.filter((i) => i.fetch_status === "ok" || i.has_analysis || i.url);
  if (productId && !state.showAllMaterials) {
    pool = pool.filter((i) => materialMatchesProduct(i, productId));
  }
  return pool;
}

function materialInProductPool(linkId, productId = currentProductId()) {
  if (!linkId || !productId) return false;
  return getMaterialPreviewPool().some((i) => i.link_id === Number(linkId));
}

function syncRefFloatProductLine() {
  const line = document.getElementById("refFloatProductLine");
  const hint = document.getElementById("refFloatPoolHint");
  const productId = currentProductId();
  const pool = getMaterialPreviewPool();
  if (line) {
    line.textContent = productId
      ? `当前产品：${currentProductLabel()} · 脚本将严格按此产品标签 + 所选对标结构生成`
      : "";
  }
  if (hint) {
    hint.textContent = productId
      ? (state.showAllMaterials ? `共 ${pool.length} 条（含其他品类）` : `同品类 ${pool.length} 条`)
      : "";
  }
}

function syncWorkspaceRefChip() {
  syncRefFloatStatus();
  syncDockRefSlot();
}

function renderMaterialListPreview() {
  const root = document.getElementById("materialListPreview");
  if (!root) return;
  const pool = getMaterialPreviewPool();
  if (!pool.length) {
    root.innerHTML = '<div class="detail-empty">暂无素材。点击「浏览全部素材」打开素材库。</div>';
    return;
  }
  const sorted = [...pool].sort((a, b) => a.link_id - b.link_id);
  const selected = sorted.find((i) => i.link_id === state.selectedMaterialId) || sorted[0];
  const others = sorted.filter((i) => i.link_id !== selected.link_id).slice(0, 3);
  const previewItems = [selected, ...others];
  root.innerHTML = previewItems.map((item) => materialCardHtml(item, { compact: true })).join("");
  root.querySelectorAll(".card").forEach((c) =>
    c.addEventListener("click", () => selectMaterial(Number(c.dataset.id), { fromDrawer: false }))
  );
}

function renderRefFloatMaterialList() {
  const root = document.getElementById("refFloatMaterialList");
  if (!root) return;
  const productId = currentProductId();
  if (!productId) {
    root.innerHTML = '<div class="detail-empty">请先在底部点击「产品」并完成场景标签配置。</div>';
    syncRefFloatProductLine();
    return;
  }
  const pool = getMaterialPreviewPool();
  syncRefFloatProductLine();
  if (!pool.length) {
    root.innerHTML = state.showAllMaterials
      ? '<div class="detail-empty">暂无已拆解素材。请在设置中同步并拆解，或调整筛选条件。</div>'
      : `<div class="detail-empty">暂无与「${esc(currentProductLabel())}」同品类的已拆解对标。可勾选「显示其他品类」浏览全部，或更换产品。</div>`;
    return;
  }
  const sorted = [...pool].sort((a, b) => a.link_id - b.link_id);
  root.innerHTML = sorted.map((item) => materialCardHtml(item)).join("");
  root.querySelectorAll(".card").forEach((c) =>
    c.addEventListener("click", () => selectMaterial(Number(c.dataset.id), { fromRefFloat: true }))
  );
}

function renderMaterialList() {
  const root = document.getElementById("materialList");
  if (!root) return;
  if (!state.items.length) {
    root.innerHTML = '<div class="detail-empty">无匹配素材。请先在「设置」同步 TikTok。</div>';
    renderMaterialListPreview();
    return;
  }
  root.innerHTML = state.items.map((item) => materialCardHtml(item)).join("");
  root.querySelectorAll(".card").forEach((c) =>
    c.addEventListener("click", () => selectMaterial(Number(c.dataset.id), { fromDrawer: true }))
  );
  renderMaterialListPreview();
}

function fmtShotRange(start, end) {
  const pad = (v) => {
    const n = parseInt(String(v).replace(/\D/g, ""), 10);
    if (Number.isNaN(n)) return String(v || "0");
    const m = Math.floor(n / 60);
    const s = n % 60;
    return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  };
  return `${pad(start)} - ${pad(end)}`;
}

function copyText(text, btn) {
  if (!text) return;
  navigator.clipboard.writeText(text).then(() => {
    if (btn) {
      const orig = btn.textContent;
      btn.textContent = "已复制";
      setTimeout(() => { btn.textContent = orig; }, 1500);
    }
  }).catch(() => alert("复制失败"));
}

function renderDissectorMedia(d) {
  const thumb = d.thumbnail_url
    ? `<img class="dissector-poster-img" src="${esc(d.thumbnail_url)}" alt="">`
    : `<div class="dissector-poster-placeholder">无封面</div>`;
  const stats = [
    fmtNum(d.view_count) && `${fmtNum(d.view_count)} 播放`,
    d.duration_sec && `${d.duration_sec}s`,
    fmtNum(d.like_count) && `${fmtNum(d.like_count)} 赞`,
  ].filter(Boolean).join(" · ");
  return `
    <div class="dissector-media">
      <div class="dissector-poster">${thumb}</div>
      <div class="dissector-meta">
        <div class="dissector-author">@${esc(d.author || "unknown")}</div>
        <h2 class="dissector-title">#${d.link_id} ${esc(d.title || "")}</h2>
        <div class="dissector-stats">${esc(stats || "—")}</div>
        <a class="dissector-link" href="${esc(d.url)}" target="_blank" rel="noopener">打开 TikTok ↗</a>
      </div>
    </div>`;
}

function renderDissectorShots(shots) {
  if (!shots.length) {
    return `<p class="dissector-empty">暂无分镜，豆包拆解完成后将显示在此</p>`;
  }
  return `<table class="dissector-table">
    <thead><tr>
      <th class="col-idx">#</th>
      <th class="col-time">时间</th>
      <th class="col-visual">画面描述</th>
      <th class="col-dialogue">台词</th>
      <th class="col-sub">字幕/标签</th>
    </tr></thead>
    <tbody>${shots.map((s) => `<tr>
      <td class="col-idx">${esc(s.index)}</td>
      <td class="col-time">${esc(fmtShotRange(s.start, s.end))}</td>
      <td class="col-visual">${esc(s.visual_description || "")}</td>
      <td class="col-dialogue">${esc(s.dialogue || "")}</td>
      <td class="col-sub">${esc(s.subtitle_or_title || "")}</td>
    </tr>`).join("")}</tbody>
  </table>`;
}

function friendlyAnalyzeError(msg, detail) {
  const text = String(msg || "").trim();
  if (text.includes("video_analysis.csv") || text.includes("豆包失败，已回退规则") || text.includes("rule shots=")) {
    return "豆包拆解超时或失败。若下方已有分镜表可继续使用，也可点击「重试拆解」。";
  }
  return text || "豆包拆解失败";
}

function renderMaterialDetail(d, detail) {
  const a = (detail?.analysis || d.analysis || {});
  let shots = detail?.shots || [];
  let status = detail?.status || (shots.length ? "ready" : "unknown");
  const summary = detail?.summary || a.summary || "";
  const transcript = detail?.full_transcript || a.full_transcript || "";
  let warning = detail?.warning || "";

  if (status === "error" && shots.length) {
    status = "ready";
    warning = warning || friendlyAnalyzeError(detail?.message, detail);
  }

  if (status === "running") {
    return `
      <div class="dissector">
        <div class="dissector-top">
          ${renderDissectorMedia(d)}
          <div class="dissector-script-panel dissector-loading-panel">
            <div class="dissector-panel-head"><span>完整文案（逐字稿）</span></div>
            <div class="analyze-loading">
              <p><strong>豆包视频拆解中…</strong></p>
              <p class="muted">正在生成逐字稿与分镜表（约 1–3 分钟），完成后自动刷新</p>
            </div>
          </div>
        </div>
        <div class="dissector-bottom">
          <div class="dissector-panel-head"><span>分镜脚本</span></div>
          <p class="dissector-empty muted">等待拆解结果…</p>
        </div>
      </div>`;
  }

  if (status === "error") {
    return `
      <div class="dissector">
        <div class="dissector-top">${renderDissectorMedia(d)}</div>
        <div class="result error">${esc(friendlyAnalyzeError(detail?.message, detail))}</div>
        <div class="dissector-foot dissector-foot-row">
          ${detail?.retryable ? '<button type="button" class="secondary" id="retryAnalyzeBtn">重试拆解</button>' : ""}
          <button type="button" class="primary primary-dark" id="goScriptBtn">生成脚本</button>
        </div>
      </div>`;
  }

  return `
    <div class="dissector">
      ${warning ? `<div class="dissector-warn">${esc(warning)}</div>` : ""}
      <div class="dissector-top">
        ${renderDissectorMedia(d)}
        <div class="dissector-script-panel">
          <div class="dissector-panel-head">
            <span>完整文案（逐字稿）</span>
            <button type="button" class="btn-text" id="copyTranscriptBtn" ${transcript ? "" : "disabled"}>复制</button>
          </div>
          <div class="dissector-transcript" id="transcriptBody">${transcript ? esc(transcript) : '<span class="muted">（无逐字稿）</span>'}</div>
          ${summary ? `<div class="dissector-summary"><strong>概要：</strong>${esc(summary)}</div>` : ""}
        </div>
      </div>
      <div class="dissector-bottom">
        <div class="dissector-panel-head">
          <span>分镜脚本（共 ${shots.length} 镜）</span>
          <span class="dissector-tag">已拆解</span>
        </div>
        ${renderDissectorShots(shots)}
      </div>
      <details class="dissector-fold">
        <summary>结构参考（供脚本生成）</summary>
        <div class="dissector-fold-grid">
          ${["hook_3s", "pain_points", "selling_points", "video_structure", "reusable_template"].map((k) => `
            <div><dt>${ANALYSIS_LABELS[k] || k}</dt><dd>${esc(a[k] || "—")}</dd></div>`).join("")}
        </div>
      </details>
      <div class="dissector-foot">
        <button type="button" class="primary primary-dark" id="goScriptBtn">生成脚本</button>
      </div>
    </div>`;
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function fetchMaterialAnalysis(linkId, pane) {
  for (let i = 0; i < 80; i++) {
    const detail = await api(`/api/materials/${linkId}/analysis/detail`);
    if (detail.status === "running") {
      if (pane) {
        const d = state.items.find((x) => x.link_id === linkId) || { link_id: linkId, title: "", author: "", url: "#" };
        pane.innerHTML = renderMaterialDetail(d, detail);
      }
      await sleep(3000);
      continue;
    }
    return detail;
  }
  throw new Error("豆包拆解超时，请稍后重试");
}

async function selectMaterial(linkId, { fromDrawer = false, fromRefFloat = false, keepDetail = false } = {}) {
  if (state.selectedMaterialId !== linkId) resetPromptEnhanceUsed();
  state.selectedMaterialId = linkId;
  renderMaterialList();
  renderRefFloatMaterialList();
  renderGenerateViralGrid();
  if (fromDrawer) closeMaterialLibraryDrawer();
  if (state.view === "reverse") {
    state.reverseMaterialId = linkId;
    syncReverseDockMaterial();
  }
  repopulateScriptMaterials();
  syncMaterialSelectFromState();
  syncWorkspaceRefChip();
  const pane = document.getElementById("materialDetail");
  if (!pane) return;
  if (!keepDetail) {
    pane.className = "detail dissector-detail ref-float-detail";
    pane.innerHTML = "加载中…";
  }
  try {
    const d = await api(`/api/materials/${linkId}`);
    let detail = await fetchMaterialAnalysis(linkId, pane);
    const item = state.items.find((i) => i.link_id === linkId);
    if (item) {
      item.analyze_provider = detail.analyze_provider || "doubao_video";
      item.has_analysis = true;
    }
    pane.className = "detail dissector-detail";
    pane.innerHTML = renderMaterialDetail(d, detail);
    if (document.getElementById("scriptProductSelect")?.value) {
      await refreshScriptPreview();
    } else {
      updateLoopBarFromForm(state.lastPreview || {});
    }
    document.getElementById("retryAnalyzeBtn")?.addEventListener("click", async () => {
      const btn = document.getElementById("retryAnalyzeBtn");
      if (btn) { btn.disabled = true; btn.textContent = "拆解中…"; }
      try {
        await api(`/api/materials/${linkId}/analyze`, { method: "POST" });
        await selectMaterial(linkId);
      } catch (err) {
        alert(err.message);
        if (btn) { btn.disabled = false; btn.textContent = "重试拆解"; }
      }
    });
    if (state.view === "reverse") syncReverseDockMaterial();
    document.getElementById("copyTranscriptBtn")?.addEventListener("click", (e) => {
      const text = detail?.full_transcript || d.analysis?.full_transcript || "";
      copyText(text, e.currentTarget);
    });
    document.getElementById("goScriptBtn")?.addEventListener("click", async () => {
      state.selectedMaterialId = linkId;
      const row = state.items.find((i) => i.link_id === linkId);
      if (row?.content_line) state.selectedProductId = row.content_line;
      syncMaterialSelectFromState();
      repopulateScriptMaterials();
      if (document.getElementById("scriptProductSelect")?.value) {
        await refreshScriptPreview();
      }
      setScriptStep("ref");
      if (tagsSelectionOk()) {
      await runStartCreate();
    } else {
        setScriptStep("product");
        const hint = document.getElementById("loopHint");
        if (hint) hint.textContent = "请先点击底部「产品」完成场景标签。";
      }
      updateLoopBarFromForm(state.lastPreview || {});
    });
    setScriptStep("ref", { scroll: false });
    await refreshHealth();
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
  const productId = currentProductId();
  const prev = Number(ms.value);
  const pool = getMaterialPreviewPool();
  const hint = document.getElementById("materialFilterHint");
  if (hint) {
    hint.textContent = productId
      ? (state.showAllMaterials ? `共 ${pool.length} 条可选` : `同品类 ${pool.length} 条`)
      : "";
  }
  if (!productId) {
    ms.innerHTML = "";
    return;
  }
  ms.innerHTML = pool.map((i) =>
    `<option value="${i.link_id}" ${i.link_id === state.selectedMaterialId ? "selected" : ""}>#${i.link_id} ${esc((i.title || "").slice(0, 42))}</option>`
  ).join("");
  const still = [...ms.options].some((o) => Number(o.value) === prev);
  if (still) ms.value = String(prev);
  else {
    const next = pickDefaultMaterialId(pool);
    if (next) {
      ms.value = String(next);
      state.selectedMaterialId = next;
    } else {
      ms.value = "";
      state.selectedMaterialId = null;
    }
  }
  syncDockRefSlot();
  renderMaterialListPreview();
}

async function populateScriptProductSelect() {
  const ps = document.getElementById("scriptProductSelect");
  if (!ps) return;
  try {
    const pr = await api("/api/products");
    state.products = pr.items || [];
  } catch {
    if (!state.products.length) {
      const filters = await api("/api/filters").catch(() => ({}));
      state.products = filters.products || [];
    }
  }
  if (!state.products.length) {
    ps.innerHTML = '<option value="">请先在「设置」同步产品资料</option>';
    return;
  }
  ps.innerHTML = state.products.map((p) =>
    `<option value="${esc(p.product_id)}">${esc(p.product_name || p.product_id)}</option>`
  ).join("");
  if (state.selectedProductId && [...ps.options].some((o) => o.value === state.selectedProductId)) {
    ps.value = state.selectedProductId;
  } else {
    const thermos = state.products.find((p) => p.product_id === "便携恒温杯");
    ps.value = thermos ? thermos.product_id : state.products[0].product_id;
    state.selectedProductId = ps.value;
  }
  syncDockProductSlot();
  syncDockRefSlot();
}

async function loadScriptView() {
  if (!state.items.length) await loadMaterials();
  const showAll = document.getElementById("showAllMaterials");
  const refShowAll = document.getElementById("refFloatShowAllMaterials");
  if (showAll) showAll.checked = state.showAllMaterials;
  if (refShowAll) refShowAll.checked = state.showAllMaterials;
  const analyzed = document.getElementById("analyzedOnly");
  const refAnalyzed = document.getElementById("refFloatAnalyzedOnly");
  if (analyzed) analyzed.checked = state.filters.analyzedOnly;
  if (refAnalyzed) refAnalyzed.checked = state.filters.analyzedOnly;
  const ms = document.getElementById("scriptMaterialSelect");
  await populateScriptProductSelect();
  repopulateScriptMaterials();
  if (state.selectedProductId) {
    await loadProductTagPanel(state.selectedProductId);
  }
  if (state.selectedMaterialId && ms?.querySelector(`option[value="${state.selectedMaterialId}"]`)) {
    ms.value = String(state.selectedMaterialId);
  }
  if (state.selectedMaterialId && state.selectedProductId) {
    await refreshScriptPreview();
  }
  syncWorkspaceRefChip();
  syncDockProductSlot();
  syncDockRefSlot();
  renderGenerateViralGrid();
}

async function refreshScriptPreview() {
  const linkId = Number(document.getElementById("scriptMaterialSelect").value);
  const productId = document.getElementById("scriptProductSelect").value;
  state.selectedMaterialId = linkId;
  const analysisEl = document.getElementById("scriptAnalysis");
  const productEl = document.getElementById("scriptProduct");
  if (!productId) {
    if (productEl) {
      productEl.className = "script-tag-grid script-tag-grid-float detail-empty";
      productEl.innerHTML = "选择产品后配置场景标签";
    }
    if (analysisEl) {
      analysisEl.innerHTML = linkId
        ? '<div class="detail-empty">选择产品后显示结构迁移摘要</div>'
        : '<div class="detail-empty">选择对标后显示</div>';
    }
    return;
  }
  if (!linkId) {
    await loadProductTagPanel(productId);
    if (analysisEl) {
      analysisEl.innerHTML = '<div class="detail-empty">选择对标后显示结构迁移摘要</div>';
    }
    return;
  }
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
    analysisEl.innerHTML = `${brandHint}<div class="field-grid-compact">
      <div class="field-compact"><label>钩子 0-3s</label><p>${esc(a.hook_3s)}</p></div>
      <div class="field-compact"><label>痛点</label><p>${esc(a.pain_points)}</p></div>
      <div class="field-compact"><label>卖点</label><p>${esc(a.selling_points)}</p></div>
      <div class="field-compact"><label>结构</label><p>${esc(a.video_structure)}</p></div>
      <div class="field-compact"><label>字幕布局</label><p>${esc(a.subtitle_layout)}</p></div>
    </div>`;
    const p = prev.product || {};
    syncProductTagPanelFromPreview(p, prev.delivery_tags || {}, prev.selected_tags || {});
    updateLoopBarFromForm(prev);
    syncScriptDownloadZip(prev);
    if (prev.has_script && prev.script_pack) {
      if (!state.scriptTagSnapshot) {
        state.scriptTagSnapshot = scriptTagSnapshotFromPack(prev.script_pack, prev.selected_tags || {});
      }
      syncScriptProduceEmpty(true);
      mountScriptPackEditor(scriptResultBody(), prev.script_pack, prev.script_meta);
    }
    syncFinishButton(Boolean(prev.can_finish), Boolean(prev.delivery_ready));
    showSeedanceProgress(false);
    renderSeedanceFinalPreview(null, null);
  } catch (err) {
    analysisEl.innerHTML = `<div class="result error">${esc(err.message)}</div>`;
    productEl.className = "script-tag-grid script-tag-grid-float detail-empty";
    productEl.innerHTML = "";
    const lp = state.lastPreview || {};
    syncFinishButton(Boolean(lp.can_finish), Boolean(lp.delivery_ready));
  }
}

function onScriptSelectionChange() {
  state.selectedProductId = document.getElementById("scriptProductSelect").value;
  state.tagPoolExtra = { audience: [], scenarios: [], selling: [], pains: [] };
  state.tagSelection = { audience: [], scenarios: [], selling: [], pains: [] };
  state.createPipelineActive = false;
  state.scriptTagSnapshot = null;
  state.lastScriptProductId = null;
  if (scriptResultBody()) scriptResultBody().innerHTML = "";
  showSeedanceProgress(false);
  renderSeedanceFinalPreview(null, null);
  syncScriptProduceEmpty();
}

document.getElementById("scriptMaterialSelect")?.addEventListener("change", async () => {
  const next = Number(document.getElementById("scriptMaterialSelect").value);
  if (state.selectedMaterialId !== next) resetPromptEnhanceUsed();
  state.selectedMaterialId = next;
  onScriptSelectionChange();
  await refreshScriptPreview();
});
document.getElementById("scriptProductSelect")?.addEventListener("change", async () => {
  resetPromptEnhanceUsed();
  state.selectedProductId = document.getElementById("scriptProductSelect").value;
  state.selectedMaterialId = null;
  setImitationPrompt("");
  state.generatePromptSelection = null;
  syncDockPromptSelectSlot();
  const materialPane = document.getElementById("materialDetail");
  if (materialPane) {
    materialPane.className = "detail-empty ref-float-detail";
    materialPane.innerHTML = "选择左侧对标视频查看拆解";
  }
  onScriptSelectionChange();
  repopulateScriptMaterials();
  if (state.selectedProductId) await loadProductTagPanel(state.selectedProductId);
  renderRefFloatMaterialList();
  syncRefFloatProductLine();
  renderGenerateViralGrid();
  await refreshScriptPreview();
  syncProductFloatStatus();
  syncDockProductSlot();
  syncDockRefSlot();
});

async function runScriptGenerate() {
  const linkId = Number(document.getElementById("scriptMaterialSelect").value);
  const productId = document.getElementById("scriptProductSelect").value;
  const audienceTags = readSelectedTags("audience");
  const scenarioTags = readSelectedTags("scenario");
  const sellingTags = readSelectedTags("selling");
  const painTags = readSelectedTags("pain");
  const genBtns = document.querySelectorAll(".js-script-generate");
  const resultEl = scriptResultBody();
  if (!audienceTags.length || !scenarioTags.length || !sellingTags.length || !painTags.length) {
    await openProductFloatPanel();
    return;
  }
  if (!document.getElementById("scriptMaterialSelect")?.value) {
    openRefFloatPanel();
    return;
  }
  if (!materialInProductPool(linkId, productId)) {
    setScriptActionStatus("所选对标与当前产品不匹配，请重新选择同品类对标。");
    openRefFloatPanel();
    return;
  }
  const quota = state.healthCache?.production?.daily_script_quota;
  if (quota?.enabled && quota.remaining <= 0) {
    setScriptActionStatus(`今日 LLM 脚本配额已用完（${quota.used}/${quota.limit}），请明日再试。`);
    openScriptFloatPanel();
    return;
  }
  await refreshScriptPreview();
  if (state.lastPreview?.product_match === false) {
    const warn = document.getElementById("scriptMismatchWarn");
    const msg = warn?.textContent || "对标与产品品类不一致，请更换对标或勾选「显示其他品类」后确认。";
    if (resultEl) resultEl.innerHTML = `<div class="result error">${esc(msg)}</div>`;
    setScriptActionStatus(msg);
    openScriptFloatPanel();
    return;
  }
  setScriptStep("produce");
  openScriptFloatPanel();
  genBtns.forEach((b) => { b.disabled = true; });
  const regenBtn = document.getElementById("scriptFloatRegenBtn");
  const produceBtn = document.getElementById("scriptFloatProduceBtn");
  if (regenBtn) {
    regenBtn.disabled = true;
    regenBtn.dataset.busy = "1";
    regenBtn.textContent = "生成中…";
  }
  if (produceBtn) produceBtn.disabled = true;
  syncDownloadLinks("", false);
  showScriptProgress(true, {
    status: "正在根据产品标签与对标结构生成脚本…",
    indeterminate: true,
    pipeline: state.healthCache?.llm?.label || "",
    countdownSec: SEEDANCE_COUNTDOWN_PHASE_SEC.script,
  });
  if (resultEl) resultEl.innerHTML = "";
  setScriptActionStatus("");
  try {
    const vs = currentVideoSettings();
    const creativeBrief = getImitationPrompt();
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
        aspect_ratio: vs.aspectRatio,
        edit_mode: vs.editMode,
        resolution: vs.resolution,
        duration_sec: vs.durationSec,
        generate_count: vs.generateCount,
        creative_brief: creativeBrief,
        prompt_enhanced: state.promptEnhanceOn,
      }),
    });
    const pack = res.script_pack || res.pack || {};
    state.scriptSlug = res.slug || slugFor(linkId);
    state.scriptTagSnapshot = captureTagSnapshot();
    state.lastScriptProductId = productId;
    if (resultEl) mountScriptPackEditor(resultEl, pack, res.meta);
    if (res.daily_quota) {
      if (!state.healthCache) state.healthCache = {};
      if (!state.healthCache.production) state.healthCache.production = {};
      state.healthCache.production.daily_script_quota = res.daily_quota;
      syncDailyScriptQuota(res.daily_quota);
    } else {
      await refreshHealth();
    }
    syncFinishButton(true, Boolean(state.lastPreview?.delivery_ready));
    syncScriptProduceEmpty(true);
    setScriptStep("produce");
    await refreshScriptPreview();
    resetPromptEnhanceUsed();
  } catch (err) {
    if (resultEl) resultEl.innerHTML = `<div class="result error">${esc(err.message)}</div>`;
    if (String(err.message || "").includes("配额")) syncDailyScriptQuota();
  } finally {
    showScriptProgress(false);
    if (regenBtn) {
      regenBtn.disabled = false;
      delete regenBtn.dataset.busy;
      regenBtn.textContent = "重新生成脚本";
    }
    genBtns.forEach((b) => { b.disabled = false; });
    syncDockRunButtonsDisabled();
    syncDailyScriptQuota();
  }
}

async function runScriptFinish(options = {}) {
  const { keepScript = false, background = false } = options;
  const slug = currentScriptSlug();
  if (!slug) {
    setScriptActionStatus("请先生成脚本");
    if (!background) ensureScriptResultVisible();
    return false;
  }
  state.scriptSlug = slug;
  const finishBtns = document.querySelectorAll("#scriptFinishBtn, .js-script-finish");
  const resultEl = scriptResultBody();
  finishBtns.forEach((b) => { b.disabled = true; });
  if (!background) openScriptFloatPanel();
  if (!keepScript) {
    resultEl.textContent = "正在生成交付包（英文字幕 + 脚本包）…";
  } else {
    setScriptActionStatus("正在生成交付包（英文字幕 + 脚本包）…");
  }
  try {
    const res = await api(`/api/delivery/${slug}/finish`, { method: "POST" });
    if (!keepScript) {
      resultEl.innerHTML = `<div class="result">交付完成：${esc(res.message || "字幕与交付包已生成")}
        <p class="muted">正在继续生成 AI 分镜视频…</p>
        <p class="loop-next">
          <button type="button" class="text-link" id="goFinishedBtn">打开成稿库</button>
          ·
          <button type="button" class="text-link" id="goFeedbackBtn">填写投放反馈</button>
        </p></div>`;
      document.getElementById("goFinishedBtn")?.addEventListener("click", () => switchView("draft-feedback", { sub: "finished" }));
      document.getElementById("goFeedbackBtn")?.addEventListener("click", () => {
        state.selectedFeedbackSlug = slug;
        switchView("draft-feedback", { sub: "feedback" });
      });
    } else {
      setScriptActionStatus(`交付完成：${res.message || "字幕与交付包已生成"}`);
    }
    await refreshScriptPreview();
    await refreshHealth();
    return true;
  } catch (err) {
    if (!keepScript) {
      resultEl.innerHTML = `<div class="result error">${esc(err.message)}</div>`;
    } else {
      setScriptActionStatus(`交付失败：${err.message}`);
    }
    await refreshScriptPreview();
    return false;
  } finally {
    const lp = state.lastPreview || {};
    syncFinishButton(Boolean(lp.can_finish), Boolean(lp.delivery_ready));
  }
}

async function runSeedanceGenerate(options = {}) {
  const force = options.force ?? document.getElementById("seedanceForceRegen")?.checked;
  const background = Boolean(options.background);
  const videoQ = state.healthCache?.production?.daily_video_quota;
  if (videoQ?.enabled && videoQ.remaining <= 0) {
    setScriptActionStatus(`今日成片产出配额已用完（${videoQ.used}/${videoQ.limit}），请明日再试。`);
    return false;
  }
  const slug = currentScriptSlug();
  if (!slug) {
    setScriptActionStatus("请先生成脚本");
    if (!background) ensureScriptResultVisible();
    return false;
  }
  state.scriptSlug = slug;
  if (!background) ensureScriptResultVisible();
  showSeedanceProgress(true, {
    status: force ? "正在强制重生成…" : "正在生成分镜视频…",
    indeterminate: true,
    pipeline: state.healthCache?.seedance?.label || "",
    countdownSec: options.keepCountdown ? undefined : estimateSeedanceVideoSeconds({ force }),
  });
  setScriptActionStatus(force ? "强制重生成中…" : "正在生成分镜视频，请耐心等待…");
  const hintEl = document.getElementById("seedanceHint");
  const vs = currentVideoSettings();
  try {
    const qs = force ? "?force=1" : "";
    const data = await api(`/api/delivery/${encodeURIComponent(slug)}/seedance/run${qs}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        resolution: vs.resolution,
        aspect_ratio: vs.aspectRatio,
        duration_sec: vs.durationSec,
        generate_count: vs.generateCount,
        edit_mode: vs.editMode,
      }),
    });
    renderSeedance(slug, data.seedance, state.healthCache);
    const failed = (data.results || []).filter((r) => r.status === "error");
    const skipped = (data.results || []).filter((r) => r.status === "skipped");
    const okCount = (data.results || []).filter((r) => r.status === "ok").length;
    const finalReady = Boolean(data.seedance?.final_video?.ready || data.assemble?.ok);
    let msg;
    if (failed.length) {
      msg = failed.every((r) => (r.message || "").includes("ARK_API_KEY"))
        ? `火山方舟密钥失效：${failed[0].message}。请到「设置」→ 测试连接，或更新 overseas-loc-mvp/.env 中的 ARK_API_KEY 后重启工作台。`
        : `部分失败：${failed.map((r) => `镜${r.number} ${r.message}`).join("；")}`;
    } else if (finalReady) {
      const prod = data.video_production || {};
      const spec = prod.resolution_ui && prod.aspect_ratio
        ? `（${prod.resolution_ui} · ${prod.aspect_ratio}）`
        : `（${vs.resolution} · ${vs.aspectRatio}）`;
      msg = force
        ? `已强制重生成 ${okCount || "5"} 镜并拼接成片${spec}，可预览 mp4 或下载 zip`
        : `视频生成完成${spec}，可预览 mp4 或下载 zip`;
    } else if (okCount > 0) {
      const asm = data.assemble?.message || "分镜已生成，但成片拼接未完成";
      msg = `${asm}。请确认 ffmpeg 可用后重试；zip 内仅有分镜 mp4。`;
    } else if (skipped.length) {
      msg = force
        ? "本次未覆盖旧视频：请重启工作台（启动页面.cmd）后再勾选强制重生成，或运行 本地生成视频.cmd <编号> --force"
        : "未生成新视频：镜头已有 mp4。请勾选「强制重生成」后重试，或先重新生成脚本以更新 Prompt。";
    } else {
      msg = "视频生成完成，可预览 mp4 或下载 zip";
    }
    if (hintEl) hintEl.textContent = msg;
    stopSeedanceCountdown();
    if (!background) {
      showSeedanceProgress(true, {
        status: finalReady ? "成片已就绪" : msg,
        pipeline: data.seedance?.pipeline || "",
        percent: finalReady ? 100 : undefined,
        indeterminate: !finalReady && !failed.length,
      });
    }
    setScriptActionStatus(msg);
    if (finalReady) {
      syncDownloadLinks(`/api/delivery/${slug}/zip?ts=${Date.now()}`, true);
    }
    if (data.daily_video_quota && state.healthCache?.production) {
      state.healthCache.production.daily_video_quota = data.daily_video_quota;
      syncDailyVideoQuota(data.daily_video_quota);
    }
    if (!background) openScriptFloatPanel();
    return !failed.length && finalReady;
  } catch (err) {
    stopSeedanceCountdown();
    showSeedanceProgress(true, { status: `失败：${err.message}`, percent: 0 });
    setScriptActionStatus(`视频生成失败：${err.message}`);
    return false;
  }
}

async function runProduceVideo(options = {}) {
  const background = Boolean(options.background);
  const slug = currentScriptSlug();
  if (!slug) {
    setScriptActionStatus("请先生成脚本后再产出视频");
    if (!background) ensureScriptResultVisible();
    return false;
  }
  if (!options.skipScriptSave) {
    const saved = await saveScriptEditsIfDirty({ silent: true });
    if (!saved) return false;
  }
  state.scriptSlug = slug;
  if (!background) {
    setScriptStep("produce", { scroll: false });
    ensureScriptResultVisible();
  }
  const forceRegen = document.getElementById("seedanceForceRegen")?.checked;
  const needsDelivery = !Boolean(state.lastPreview?.delivery_ready);
  showSeedanceProgress(true, {
    status: "正在准备交付与分镜生成…",
    indeterminate: true,
    pipeline: state.healthCache?.seedance?.label || "",
    countdownSec: estimateSeedanceVideoSeconds({ force: forceRegen })
      + (needsDelivery ? SEEDANCE_COUNTDOWN_PHASE_SEC.delivery : 0),
  });
  setScriptActionStatus("正在启动：交付包 → AI 分镜视频 → 拼接成片（约 15–30 分钟）…");
  if (!background) openScriptFloatPanel();
  try {
    const lp = state.lastPreview || {};
    if (!lp.delivery_ready) {
      const ok = await runScriptFinish({ keepScript: true, background });
      if (!ok) {
        setScriptActionStatus("交付未完成，无法产出视频。");
        return false;
      }
      await refreshScriptPreview();
    }
    return await runSeedanceGenerate({
      force: forceRegen,
      background,
      keepCountdown: true,
    });
  } catch (err) {
    stopSeedanceCountdown();
    setScriptActionStatus(`产出视频失败：${err.message}`);
    showSeedanceProgress(true, { status: `失败：${err.message}`, persist: true });
    return false;
  } finally {
    syncFinishButton(Boolean(state.lastPreview?.can_finish), Boolean(state.lastPreview?.delivery_ready));
  }
}

document.getElementById("scriptStepProductNext")?.addEventListener("click", () => {
  if (!tagsSelectionOk()) {
    openProductFloatPanel();
    return;
  }
  setScriptStep("ref");
  updateLoopBarFromForm(state.lastPreview || {});
});

document.getElementById("scriptStepRefPrev")?.addEventListener("click", () => {
  setScriptStep("product");
  updateLoopBarFromForm(state.lastPreview || {});
});

document.getElementById("scriptStepProducePrev")?.addEventListener("click", () => {
  setScriptStep("ref");
  updateLoopBarFromForm(state.lastPreview || {});
});

document.getElementById("scriptStepProduceBack")?.addEventListener("click", () => {
  setScriptStep("ref");
  updateLoopBarFromForm(state.lastPreview || {});
});

document.addEventListener("click", (e) => {
  const gen = e.target.closest(".js-script-generate");
  if (gen) {
    e.preventDefault();
    runStartCreate();
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
      <td><a href="${esc(withApiToken(`/api/delivery/${r.slug}/zip`))}">下载 zip</a></td>
    </tr>`).join("")}</tbody></table>`;
}

// ── Feedback ─────────────────────────────────────────────────────────────

async function ensureFeedbackTagDefs() {
  if (state.feedbackTagDefs) return state.feedbackTagDefs;
  try {
    const data = await api("/api/library/feedback-tags");
    state.feedbackTagDefs = data.items || [];
  } catch {
    state.feedbackTagDefs = [];
  }
  return state.feedbackTagDefs;
}

function collectFeedbackIssueTags(form) {
  return [...form.querySelectorAll('input[name="issue_tags"]:checked')].map((el) => el.value);
}

function isFeedbackReviewed(r) {
  if (!r) return false;
  if (r.review_done || r.review_status === "done") return true;
  if (String(r.feedback_reviewed_at || "").trim()) return true;
  if (String(r.manual_edits || "").trim()) return true;
  if ((r.issue_tags || []).length) return true;
  if (String(r.adopted || "") && r.adopted !== "待定") return true;
  const pub = r.publish || {};
  return Boolean(String(pub.views || "").trim() || String(pub.engagement || "").trim() || String(pub.notes || "").trim());
}

function sortFeedbackItems(items) {
  const pending = [];
  const done = [];
  for (const row of items) {
    (isFeedbackReviewed(row) ? done : pending).push(row);
  }
  return [...pending, ...done];
}

function pickInitialFeedbackSlug(items) {
  const sorted = sortFeedbackItems(items);
  const visible = state.feedbackHideReviewed
    ? sorted.filter((r) => !isFeedbackReviewed(r))
    : sorted;
  if (!visible.length) return null;
  const firstPending = sorted.find((r) => !isFeedbackReviewed(r));
  const cur = state.selectedFeedbackSlug
    ? sorted.find((r) => r.slug === state.selectedFeedbackSlug)
    : null;
  if (cur) {
    if (!isFeedbackReviewed(cur)) return cur.slug;
    if (firstPending) return firstPending.slug;
    return cur.slug;
  }
  return (firstPending || visible[0]).slug;
}

function pickNextFeedbackSlug(items, afterSlug) {
  const sorted = sortFeedbackItems(items);
  const pool = state.feedbackHideReviewed
    ? sorted.filter((r) => !isFeedbackReviewed(r))
    : sorted;
  const pending = pool.filter((r) => !isFeedbackReviewed(r));
  if (!pending.length) return pool[0]?.slug || null;
  const idx = pending.findIndex((r) => r.slug === afterSlug);
  if (idx >= 0 && idx + 1 < pending.length) return pending[idx + 1].slug;
  if (idx >= 0) return pending.find((r) => r.slug !== afterSlug)?.slug || null;
  return pending[0].slug;
}

function syncFeedbackEditorTab(tab) {
  state.feedbackEditorTab = tab;
  document.querySelectorAll("#feedbackEditorTabs button[data-fb-tab]").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.fbTab === tab);
  });
  document.querySelectorAll("#feedbackForm .feedback-form-section").forEach((sec) => {
    sec.classList.toggle("hidden", sec.dataset.fbPanel !== tab);
  });
}

async function loadFeedbackView() {
  const data = await api("/api/library/feedback");
  const items = sortFeedbackItems(data.items || []);
  const root = document.getElementById("feedbackList");
  if (!items.length) {
    root.innerHTML = '<div class="detail-empty">暂无反馈记录</div>';
    state.selectedFeedbackSlug = null;
    document.getElementById("feedbackEditor").innerHTML = '<div class="detail-empty">← 选择左侧成稿</div>';
    return;
  }
  const pendingCount = items.filter((r) => !isFeedbackReviewed(r)).length;
  const doneCount = items.length - pendingCount;
  state.selectedFeedbackSlug = pickInitialFeedbackSlug(items);
  const visibleItems = state.feedbackHideReviewed
    ? items.filter((r) => !isFeedbackReviewed(r))
    : items;
  if (!visibleItems.length) {
    root.innerHTML = `
      <p class="feedback-list-summary muted">全部 ${items.length} 条已反馈</p>
      <button type="button" class="secondary compact-btn" id="feedbackShowAllBtn">显示全部成稿</button>`;
    document.getElementById("feedbackShowAllBtn")?.addEventListener("click", () => {
      state.feedbackHideReviewed = false;
      loadFeedbackView();
    });
    if (!state.selectedFeedbackSlug) state.selectedFeedbackSlug = items[0].slug;
    renderFeedbackEditor();
    return;
  }
  root.innerHTML = `
    <div class="feedback-list-shell">
      <div class="feedback-list-head">
        <p class="feedback-list-summary muted">待反馈 ${pendingCount} · 已完成 ${doneCount}</p>
        <label class="feedback-hide-reviewed">
          <input type="checkbox" id="feedbackHideReviewedChk" ${state.feedbackHideReviewed ? "checked" : ""}>
          仅看待反馈
        </label>
      </div>
      <div class="feedback-list-scroll">
        ${visibleItems.map((r) => {
      const reviewed = isFeedbackReviewed(r);
      const tags = (r.issue_tags || []).length ? ` · ${(r.issue_tags || []).length}项问题` : "";
      const badge = reviewed
        ? '<span class="feedback-status-badge done">已反馈</span>'
        : '<span class="feedback-status-badge pending">待反馈</span>';
      return `
    <button type="button" class="card compact feedback-list-card${r.slug === state.selectedFeedbackSlug ? " active" : ""}${reviewed ? " feedback-reviewed" : ""}" data-slug="${esc(r.slug)}">
      <div class="feedback-list-card-main">
        <h3>${esc((r.title || r.slug).slice(0, 42))}</h3>
        <div class="meta">${esc(r.adopted || "待定")}${tags} · ${esc((r.updated_at || "").slice(0, 10))}</div>
      </div>
      ${badge}
    </button>`;
        }).join("")}
      </div>
    </div>`;
  document.getElementById("feedbackHideReviewedChk")?.addEventListener("change", (e) => {
    state.feedbackHideReviewed = e.target.checked;
    loadFeedbackView();
  });
  root.querySelectorAll(".feedback-list-card").forEach((c) =>
    c.addEventListener("click", () => { state.selectedFeedbackSlug = c.dataset.slug; loadFeedbackView(); }),
  );
  renderFeedbackEditor();
}

async function renderFeedbackEditor() {
  const pane = document.getElementById("feedbackEditor");
  const slug = state.selectedFeedbackSlug;
  if (!slug) return;
  const tab = state.feedbackEditorTab || "review";
  try {
    const r = await api(`/api/library/feedback/${encodeURIComponent(slug)}`);
    const pub = r.publish || {};
    const tagDefs = await ensureFeedbackTagDefs();
    const selectedTags = new Set(r.issue_tags || []);
    const tagHtml = tagDefs.map((t) => `
      <label class="feedback-issue-chip" title="${esc(t.hint_zh || t.label)}">
        <input type="checkbox" name="issue_tags" value="${esc(t.id)}" ${selectedTags.has(t.id) ? "checked" : ""}>
        <span class="feedback-issue-chip-text">${esc(t.label)}</span>
      </label>`).join("");
    const scLine = (r.scenario_tags || []).join("、") || "—";
    let loopPreview = "";
    if (r.product_id) {
      try {
        const prev = await api(
          `/api/library/feedback-constraints?product_id=${encodeURIComponent(r.product_id)}&scenario_tags=${encodeURIComponent((r.scenario_tags || []).join(","))}`,
        );
        if (prev.matched_count > 0) {
          loopPreview = `<p class="feedback-loop-banner">闭环已启用：下次生成「${esc(r.product_id)}」且场景匹配时，将自动带入 <strong>${prev.matched_count}</strong> 条已采纳约束。</p>`;
        } else if (r.adopted === "已采纳" || r.adopted === "修改后采纳") {
          loopPreview = `<p class="feedback-loop-banner muted">本条已采纳，将在同产品同场景下次生成时生效。</p>`;
        }
      } catch { /* ignore */ }
    }
    pane.className = "feedback-editor feedback-pane-body feedback-editor-shell";
    pane.innerHTML = `
      <div class="feedback-editor-head">
        <h3>${esc(r.title || slug)}</h3>
        <p class="muted feedback-editor-meta">产品 ${esc(r.product_id || "—")} · 场景 ${esc(scLine)}</p>
      </div>
      ${loopPreview}
      <nav class="feedback-editor-tabs" id="feedbackEditorTabs" aria-label="反馈类型">
        <button type="button" class="${tab === "review" ? "active" : ""}" data-fb-tab="review">成片审核</button>
        <button type="button" class="${tab === "metrics" ? "active" : ""}" data-fb-tab="metrics">投放数据</button>
        <button type="button" data-fb-tab="iterate" disabled title="规划中">迭代优化</button>
      </nav>
      <form id="feedbackForm" class="feedback-form-body">
        <div class="feedback-form-section${tab === "review" ? "" : " hidden"}" data-fb-panel="review">
          <div class="feedback-block">
            <div class="feedback-block-title">问题类型</div>
            <div class="feedback-issue-grid">${tagHtml || '<span class="muted">加载标签…</span>'}</div>
          </div>
          <div class="feedback-block">
            <label class="feedback-block-label">具体问题描述
              <textarea name="manual_edits" rows="2" placeholder="如：杯盖展示不符合实物、倒出口画成宽口直倒等">${esc(r.manual_edits)}</textarea>
            </label>
          </div>
          <div class="feedback-form-row-2">
            <div class="feedback-block">
              <label class="feedback-block-label">采纳状态
                <select name="adopted">
                  ${["待定", "已采纳", "未采纳", "修改后采纳"].map((o) =>
                    `<option ${r.adopted === o ? "selected" : ""}>${o}</option>`).join("")}
                </select>
              </label>
            </div>
            <div class="feedback-block">
              <label class="feedback-block-label">备注
                <textarea name="notes" rows="2" placeholder="补充说明">${esc(r.notes)}</textarea>
              </label>
            </div>
          </div>
        </div>
        <div class="feedback-form-section${tab === "metrics" ? "" : " hidden"}" data-fb-panel="metrics">
          <div class="feedback-form-row-2">
            <div class="feedback-block">
              <label class="feedback-block-label">播放量<input name="publish_views" value="${esc(pub.views)}"></label>
            </div>
            <div class="feedback-block">
              <label class="feedback-block-label">互动率<input name="publish_engagement" placeholder="如 3.2%" value="${esc(pub.engagement)}"></label>
            </div>
          </div>
          <div class="feedback-block">
            <label class="feedback-block-label">投放备注<textarea name="publish_notes" rows="2" placeholder="投放渠道、表现与复盘">${esc(pub.notes)}</textarea></label>
          </div>
          <p class="muted feedback-metrics-hint">高互动率已采纳反馈会作为同产品模板的结构/场景参考。</p>
        </div>
        <div class="feedback-form-section${tab === "iterate" ? "" : " hidden"}" data-fb-panel="iterate">
          <p class="muted module-placeholder-inner compact">基础闭环已接入：已采纳反馈 → 下次同产品同场景生成自动注入约束。</p>
        </div>
      </form>
      <div class="feedback-editor-footer">
        <button type="submit" class="primary" form="feedbackForm">保存并下一条</button>
        <button type="button" class="secondary" id="feedbackSkipBtn">跳过本条</button>
        <p id="fbHint" class="muted"></p>
      </div>`;
    document.getElementById("feedbackEditorTabs")?.addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-fb-tab]:not(:disabled)");
      if (btn) syncFeedbackEditorTab(btn.dataset.fbTab);
    });
    document.getElementById("feedbackForm").addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      const savedSlug = slug;
      try {
        await api(`/api/library/feedback/${encodeURIComponent(slug)}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            manual_edits: fd.get("manual_edits"),
            adopted: fd.get("adopted"),
            notes: fd.get("notes"),
            issue_tags: collectFeedbackIssueTags(e.target),
            publish_views: fd.get("publish_views"),
            publish_engagement: fd.get("publish_engagement"),
            publish_notes: fd.get("publish_notes"),
          }),
        });
        const fresh = await api("/api/library/feedback");
        const items = fresh.items || [];
        const nextSlug = pickNextFeedbackSlug(items, savedSlug);
        state.selectedFeedbackSlug = nextSlug;
        if (!nextSlug || !items.some((r) => !isFeedbackReviewed(r))) {
          state.feedbackHideReviewed = true;
        }
        await loadFeedbackView();
        const hint = document.getElementById("fbHint");
        if (hint) {
          hint.textContent = nextSlug && nextSlug !== savedSlug
            ? "已保存，已切换下一条待反馈"
            : "已保存，全部成稿已反馈完成";
        }
      } catch (err) {
        document.getElementById("fbHint").textContent = err.message;
      }
    });
    document.getElementById("feedbackSkipBtn")?.addEventListener("click", async () => {
      const fresh = await api("/api/library/feedback");
      const nextSlug = pickNextFeedbackSlug(fresh.items || [], slug);
      state.selectedFeedbackSlug = nextSlug;
      await loadFeedbackView();
      const hint = document.getElementById("fbHint");
      if (hint) hint.textContent = nextSlug ? "已跳过，切换下一条" : "没有更多待反馈成稿";
    });
  } catch (err) {
    pane.innerHTML = `<div class="result error">${esc(err.message)}</div>`;
  }
}

// ── Settings / jobs ──────────────────────────────────────────────────────

function renderDoubaoSettings(health) {
  const el = document.getElementById("doubaoSettingsStatus");
  if (!el) return;
  const db = health?.decompose?.doubao || {};
  const policy = health?.decompose?.policy || {};
  if (policy.paused) {
    el.innerHTML = `<span class="warn-inline">拆解已暂停</span> · ${esc(policy.message || "不重复分析已有素材，新素材也不自动分析")}`;
    return;
  }
  if (!db.configured) {
    el.innerHTML = `未配置 · 在 <code>overseas-loc-mvp/.env</code> 填写 <code>ARK_API_KEY</code><br><span class="muted">${esc(db.setup || "")}</span>`;
    return;
  }
  el.innerHTML = `已配置 · 默认模型 <code>${esc(db.turbo_model || "")}</code><br>高精度 <code>${esc(db.pro_model || "")}</code> · ASR ${db.asr_configured ? "已配" : "未配（可选）"}`;
}

async function loadSettingsView() {
  ensureCollectorPanel();
  const h = await api("/api/health");
  state.healthCache = h;
  renderDoubaoSettings(h);
  renderSeedanceSettings(h);
  renderFeishuSettings(h.feishu || {});
  refreshFeishuSettings().catch(() => {});
  const policyNote = h.decompose?.policy?.paused
    ? `<br><span class="warn-inline">拆解已暂停</span>（已有结果不重复调豆包，新素材不分析）`
    : !h.decompose?.policy?.on_view
      ? `<br><span class="muted">省 token：打开素材不自动豆包拆解，需手动「精细拆解」</span>`
      : "";
  const prod = h.production || {};
  const dep = h.deployment || {};
  const quota = prod.daily_script_quota || {};
  const videoQuota = prod.daily_video_quota || {};
  const quotaLine = quota.enabled
    ? `<br>量产配额：脚本 <strong>${quota.used}/${quota.limit}</strong>`
    : "";
  const videoQuotaLine = videoQuota.enabled
    ? `${quota.enabled ? " · " : "<br>量产配额："}成片 <strong>${videoQuota.used}/${videoQuota.limit}</strong>（${prod.script_mode || "pro"} · 最多 ${prod.ai_video_max_shots || "?"} 镜/条）`
    : (quota.enabled ? `（${prod.script_mode || "pro"} · 最多 ${prod.ai_video_max_shots || "?"} 镜/条）` : "");
  const deployEl = document.getElementById("deployInfo");
  if (deployEl) {
    deployEl.innerHTML = `
      监听 <code>${esc(dep.host || "127.0.0.1")}:${esc(String(dep.port || 8788))}</code>
      ${dep.intranet_mode ? ' · <span class="warn-inline">内网模式</span>' : ""}
      ${dep.auth_enabled ? " · 已启用访问令牌" : " · 未启用令牌（仅建议内网可信环境）"}<br>
      数据根目录：<code>${esc(dep.workflow_root || "")}</code><br>
      成片归档：<code>${esc(dep.production_archive || "03_产出库")}</code><br>
      备份目录：<code>${esc(dep.backup_root || "06_备份库")}</code>`;
  }
  document.getElementById("envInfo").innerHTML = `
    UI v${h.ui_version} · 素材 ${h.materials}（已拆解 ${h.analyzed}）· 产品 ${h.products} · 成稿 ${h.finished}<br>
    结构拆解：${h.decompose?.label || "规则模板"}${policyNote}<br>
    脚本生成：${h.llm.label || (h.llm.available ? h.llm.doubao_model || h.llm.anthropic_model : h.llm.fallback)}<br>
    交付引擎：${h.delivery_engine?.label || "overseas-loc-mvp"}<br>
    SeedDance：${h.seedance?.configured ? `已配置 ${h.seedance.provider}` : "未配置"}${quotaLine}${videoQuotaLine}`;
  await pollJobStatus();
}

async function pollJobStatus() {
  const st = await api("/api/jobs/status");
  const el = document.getElementById("jobStatus");
  const log = document.getElementById("jobLog");
  if (st.status === "running") {
    el.textContent = `运行中：${jobLabel(st.job)}（${st.started_at || ""}）`;
    log.textContent = st.output || "";
    if (!state.jobPoll) {
      state.jobPoll = setInterval(async () => {
        const s = await api("/api/jobs/status");
        document.getElementById("jobStatus").textContent = s.status === "running"
          ? `运行中：${jobLabel(s.job)}` : (s.exit_code === 0 ? `✅ ${jobLabel(s.job)} 完成` : `❌ ${jobLabel(s.job)} 失败 (code ${s.exit_code})`);
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
    el.textContent = st.job ? `${st.status}: ${jobLabel(st.job)}` : "就绪";
    log.textContent = st.output || "";
  }
}

document.querySelectorAll(".job-btn").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const job = btn.dataset.job;
    if (job === "prune") {
      const productId = currentProductId() || "";
      const scopeNote = productId
        ? `将先移除非「${productId}」品类素材，再按 MATERIAL_MAX_TOTAL 去重并限额（已拆解/成稿/有脚本默认保留）。`
        : "将按 MATERIAL_MAX_TOTAL 去重并裁剪素材库（已拆解、已成稿、有脚本、模板引用默认保留）。";
      const ok = window.confirm(`${scopeNote}\n\n确定执行？`);
      if (!ok) return;
    }
    const payload = {
      engine: btn.dataset.engine || "auto",
      provider: btn.dataset.provider || "auto",
    };
    if (SCOPED_MATERIAL_JOBS.has(job)) {
      const productId = productIdForScopedCapture();
      if (!productId) return;
      payload.product_id = productId;
    }
    if (job === "prune" && currentProductId()) {
      payload.product_id = currentProductId();
    }
    try {
      await api(`/api/jobs/${job}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      document.getElementById("jobStatus").textContent = `已启动：${job}`;
      await pollJobStatus();
    } catch (err) {
      document.getElementById("jobStatus").textContent = err.message;
    }
  });
});

// ── Init ─────────────────────────────────────────────────────────────────

document.getElementById("openProductsBtn")?.addEventListener("click", () => {
  closeSettingsDrawer();
  switchView("products");
});
document.getElementById("openMaterialLibraryFromSettings")?.addEventListener("click", () => {
  closeSettingsDrawer();
  openMaterialLibraryDrawer();
});
document.getElementById("openProductsFromSettings")?.addEventListener("click", () => {
  closeSettingsDrawer();
  switchView("products");
});
document.getElementById("guideGoCollectorBtn")?.addEventListener("click", () => {
  closeStarterGuidePanel();
  openCollectorEntry();
});
document.getElementById("guideGoLibraryBtn")?.addEventListener("click", () => {
  closeStarterGuidePanel();
  openTikTokLibraryEntry();
});
document.getElementById("starterGuideSkipBtn")?.addEventListener("click", dismissStarterGuide);
document.getElementById("starterGuideCloseBtn")?.addEventListener("click", dismissStarterGuide);
document.getElementById("starterGuideBackdrop")?.addEventListener("click", dismissStarterGuide);

document.getElementById("runWorkspaceBackupBtn")?.addEventListener("click", async () => {
  const el = document.getElementById("backupStatus");
  if (el) el.textContent = "备份中…";
  try {
    const data = await api("/api/admin/backup", { method: "POST" });
    if (el) {
      el.textContent = data.ok
        ? `备份完成：${data.backed_up} 项 → ${data.destination || ""}`
        : "备份未完成，请查看服务端日志";
    }
  } catch (err) {
    if (el) el.textContent = err.message || "备份失败";
  }
});

document.getElementById("settingsOpenBtn")?.addEventListener("click", () => openSettingsDrawer());
document.getElementById("settingsCloseBtn")?.addEventListener("click", () => closeSettingsDrawer());
document.getElementById("settingsBackdrop")?.addEventListener("click", () => closeSettingsDrawer());
document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  const guidePanel = document.getElementById("starterGuidePanel");
  if (guidePanel?.classList.contains("open")) {
    dismissStarterGuide();
    return;
  }
  closeSettingsDrawer();
  closeProductFloatPanel();
  closeRefFloatPanel();
  closeScriptFloatPanel();
  closeMaterialLibraryDrawer();
});

document.getElementById("categorySelect")?.addEventListener("change", (e) => {
  state.filters.category = e.target.value;
  const refCat = document.getElementById("refFloatCategorySelect");
  if (refCat) refCat.value = e.target.value;
  loadMaterials();
});
document.getElementById("refFloatCategorySelect")?.addEventListener("change", (e) => {
  state.filters.category = e.target.value;
  const cat = document.getElementById("categorySelect");
  if (cat) cat.value = e.target.value;
  loadMaterials();
});
document.getElementById("keywordInput")?.addEventListener("input", debounce((e) => {
  state.filters.q = e.target.value.trim();
  const refKw = document.getElementById("refFloatKeywordInput");
  if (refKw) refKw.value = state.filters.q;
  loadMaterials();
}));
document.getElementById("refFloatKeywordInput")?.addEventListener("input", debounce((e) => {
  state.filters.q = e.target.value.trim();
  const kw = document.getElementById("keywordInput");
  if (kw) kw.value = state.filters.q;
  loadMaterials();
}));
document.getElementById("analyzedOnly")?.addEventListener("change", (e) => {
  state.filters.analyzedOnly = e.target.checked;
  const ref = document.getElementById("refFloatAnalyzedOnly");
  if (ref) ref.checked = e.target.checked;
  loadMaterials();
});
document.getElementById("refFloatAnalyzedOnly")?.addEventListener("change", (e) => {
  state.filters.analyzedOnly = e.target.checked;
  const analyzed = document.getElementById("analyzedOnly");
  if (analyzed) analyzed.checked = e.target.checked;
  loadMaterials();
});
document.getElementById("showAllMaterials")?.addEventListener("change", async (e) => {
  state.showAllMaterials = e.target.checked;
  const ref = document.getElementById("refFloatShowAllMaterials");
  if (ref) ref.checked = e.target.checked;
  repopulateScriptMaterials();
  renderRefFloatMaterialList();
  syncRefFloatProductLine();
  renderGenerateViralGrid();
  if (state.selectedMaterialId && document.getElementById("scriptProductSelect")?.value) {
    await refreshScriptPreview();
  }
});
document.getElementById("refFloatShowAllMaterials")?.addEventListener("change", async (e) => {
  state.showAllMaterials = e.target.checked;
  const showAll = document.getElementById("showAllMaterials");
  if (showAll) showAll.checked = e.target.checked;
  repopulateScriptMaterials();
  renderRefFloatMaterialList();
  if (state.selectedMaterialId && document.getElementById("scriptProductSelect")?.value) {
    await refreshScriptPreview();
  }
});

document.getElementById("scriptProduct")?.addEventListener("click", (e) => {
  const chip = e.target.closest(".tag-chip");
  if (chip) {
    toggleTagChip(chip.dataset.group, chip.dataset.value);
    updateLoopBarFromForm(state.lastPreview || {});
    refreshTagGroupsUI();
    syncProductFloatStatus();
    syncDockProductSlot();
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

document.getElementById("scriptProduct")?.addEventListener("keydown", (e) => {
  if (e.key !== "Enter" || !e.target.classList.contains("tag-input")) return;
  e.preventDefault();
  const group = e.target.dataset.group;
  addTagInline(group, e.target.value);
  e.target.value = "";
});

async function runSeedanceTest(hintEl) {
  const target = hintEl || document.getElementById("seedanceHint");
  const prov = state.healthCache?.seedance?.provider === "volcengine-ark" ? "火山方舟 Ark" : "SeedDance";
  if (target) target.textContent = `正在测试 ${prov} 连接（约 30–120 秒）…`;
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

document.getElementById("btnDoubaoTestSettings")?.addEventListener("click", async () => {
  const el = document.getElementById("doubaoSettingsStatus");
  if (el) el.textContent = "正在测试豆包连接…";
  try {
    const data = await api("/api/doubao/test");
    if (el) el.textContent = data.ok ? `✅ ${data.message}` : `❌ ${data.message}`;
    await refreshHealth();
    renderDoubaoSettings(state.healthCache);
  } catch (err) {
    if (el) el.textContent = `❌ ${err.message}`;
  }
});

document.getElementById("btnSeedanceTestSettings")?.addEventListener("click", () => {
  runSeedanceTest(document.getElementById("seedanceSettingsStatus"));
});

document.getElementById("btnFeishuStatusSettings")?.addEventListener("click", async () => {
  const out = document.getElementById("feishuAuthOutput");
  if (out) out.classList.add("hidden");
  await refreshFeishuSettings();
});

document.getElementById("btnFeishuAuthUrlSettings")?.addEventListener("click", async () => {
  const el = document.getElementById("feishuSettingsStatus");
  if (el) el.textContent = "正在生成飞书授权链接…";
  try {
    const data = await api("/api/feishu/auth-url", { method: "POST" });
    showFeishuOutput(data);
    await refreshFeishuSettings();
  } catch (err) {
    if (el) el.textContent = err.message || "生成授权链接失败";
  }
});

document.getElementById("btnFeishuDoctorSettings")?.addEventListener("click", async () => {
  const el = document.getElementById("feishuSettingsStatus");
  if (el) el.textContent = "正在运行飞书 doctor…";
  try {
    const data = await api("/api/feishu/doctor?offline=true");
    showFeishuOutput(data);
    await refreshFeishuSettings();
  } catch (err) {
    if (el) el.textContent = err.message || "飞书 doctor 运行失败";
  }
});

async function bootstrapApp() {
  try {
    initModuleStudios();
  } catch (err) {
    console.error("initModuleStudios failed", err);
  }
  try {
    await refreshHealth();
  } catch {
    /* stats show ? — still load materials below */
  }
  try {
    await loadFilters();
    await loadMaterials();
  } catch (err) {
    console.error("bootstrap load failed", err);
    const root = document.getElementById("materialList");
    if (root) {
      root.innerHTML = `<div class="detail-empty">素材加载失败：${esc(err.message)}。请确认服务已启动（8788）后刷新页面。</div>`;
    }
  }
  syncDockScrollPadding();
  window.addEventListener("resize", syncDockScrollPadding);
  activateView("generate");
  if (!isStarterGuideDismissed()) {
    window.setTimeout(() => openStarterGuidePanel(), 480);
  }
}

bootstrapApp();
