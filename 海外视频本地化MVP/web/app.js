const WORKFLOW_SNAPSHOT_KEY = "wb_workflow_snapshot";
const PARTIAL_QUOTA_NOTE = "（仅分镜成功，未计今日成片次数）";

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
  generateDockMode: "generate",
  pendingScenarioTag: null,
  createPipelineActive: false,
  pipelineOriginView: null,
  seedanceProgressPersist: false,
  scriptGenActive: false,
  videoGenActive: false,
  lastVideoGenError: "",
  videoQueueTicket: null,
  videoQueuePoll: null,
  videoProductionAbort: null,
  scriptGenerationAbort: null,
  clientId: null,
  seedanceVideoComplete: false,
  producePartialReady: false,
  dockFocusDismissed: false,
  awaitingHeroConfirm: false,
  heroConfirmThenProduce: false,
  feedbackConstraintsFlash: false,
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
  hotspotRefreshBusy: false,
  hotspotAutoTimer: null,
};

const HOTSPOT_AUTO_SYNC_KEY = "vl_hotspot_auto_sync";
const HOTSPOT_AUTO_INTERVAL_KEY = "vl_hotspot_auto_interval_min";
const DEFAULT_HOTSPOT_INTERVAL_MIN = 30;

const VIDEO_RESOLUTIONS = ["720P", "1080P"];
const VIDEO_ASPECT_RATIOS = ["9:16", "16:9", "1:1", "3:4", "4:3"];
const VIDEO_DURATIONS = [5, 10, 20];
const GENERATE_COUNTS = [1, 2, 3, 4];
const CAMERA_MOTION_TYPES = ["dolly_in", "dolly_out", "pan_left", "pan_right", "static", "arc", "crash_zoom"];
const CAMERA_MOTION_LABELS = {
  dolly_in: "推近",
  dolly_out: "拉远",
  pan_left: "左摇",
  pan_right: "右摇",
  static: "固定",
  arc: "环绕",
  crash_zoom: "急推",
};

function shotCameraMotionType(shot) {
  const m = shot?.camera_motion;
  if (m && m.type && CAMERA_MOTION_TYPES.includes(m.type)) return m.type;
  const role = shot?.role || "";
  const defaults = { 钩子: "dolly_in", 痛点: "static", 方案: "dolly_in", 证明: "crash_zoom", 行动号召: "static" };
  return defaults[role] || "static";
}

function cameraMotionSelectHtml(shot) {
  const cur = shotCameraMotionType(shot);
  const opts = CAMERA_MOTION_TYPES.map((t) =>
    `<option value="${t}"${t === cur ? " selected" : ""}>${CAMERA_MOTION_LABELS[t] || t}</option>`
  ).join("");
  return `<label class="script-edit-field script-edit-field-inline"><span class="pack-label">运镜</span><select data-shot-field="camera_motion_type" class="camera-motion-select">${opts}</select></label>`;
}

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
    refreshScriptFloatPersonalization();
    return;
  }
  state.tagSelection[key] = sel.includes(value) ? sel.filter((t) => t !== value) : [...sel, value];
  refreshScriptFloatPersonalization();
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

function marketTagsFromPack(pack) {
  const m = pack?.inputs?.market || pack?.inputs?.personalization || {};
  return {
    audience: [...(m.audience_tags || m.audience || [])],
    scenarios: [...(m.scenario_tags || m.scenarios || [])],
    selling: [...(m.selling_tags || m.selling || [])],
    pains: [...(m.pain_tags || m.pains || [])],
  };
}

function applyTagSelectionFromPack(pack) {
  const tags = marketTagsFromPack(pack);
  state.tagSelection = {
    audience: tags.audience.slice(0, 1),
    scenarios: tags.scenarios.slice(0, 1),
    selling: [...tags.selling],
    pains: [...tags.pains],
  };
  state.selectedAudience = state.tagSelection.audience;
  state.selectedScenarios = state.tagSelection.scenarios;
}

function syncProductTagPanelFromPreview(p, deliveryTags, savedTags, scriptPack, opts = {}) {
  const pool = buildTagPool(p, deliveryTags || {});
  state.currentTagPool = pool;
  if (opts.preserveTagSelection || tagsChangedSinceScript()) {
    refreshTagGroupsUI();
    return;
  }
  const packTags = scriptPack ? marketTagsFromPack(scriptPack) : null;
  if (packTags && packTags.audience.length && packTags.scenarios.length) {
    applyTagSelectionFromPack(scriptPack);
    refreshTagGroupsUI();
    return;
  }
  if (!hasActiveTagSelection()) {
    renderProductPanel(p, deliveryTags || {}, savedTags || {});
  } else {
    refreshTagGroupsUI();
  }
}

function refreshScriptFloatPersonalization() {
  const prev = state.lastPreview || {};
  if (!prev.has_script || !prev.script_pack) return;
  const body = scriptResultBody();
  if (body) mountScriptPackEditor(body, prev.script_pack, prev.script_meta);
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
        ${cameraMotionSelectHtml(s)}
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
      camera_motion: s.camera_motion || { type: shotCameraMotionType(s) },
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
      const field = el.dataset.shotField;
      if (field === "camera_motion_type") {
        shot.camera_motion = { ...(shot.camera_motion || {}), type: el.value };
      } else {
        shot[field] = el.value.trim();
      }
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

  const loopHint = document.getElementById("loopHint");
  if (loopHint) loopHint.classList.add("hidden");

  const bannerHtml = formatPersonalizationBanner(pack);
  if (bannerHtml) {
    const bannerWrap = document.createElement("div");
    bannerWrap.className = "script-pack-banner";
    bannerWrap.innerHTML = bannerHtml;
    container.appendChild(bannerWrap);
  }

  const m = pack.inputs?.market || {};
  const provider = meta?.provider || pack.provider || "";
  const model = meta?.model || pack.model || "";
  const providerLine = provider === "doubao"
    ? `豆包 · ${model || "ark"}`
    : provider === "anthropic"
      ? `Claude · ${model || "claude"}`
      : provider === "rule_template"
        ? "规则模板"
        : "";
  const tagSummary = [
    m.audience_tags?.length ? m.audience_tags.join("、") : "",
    m.scenario_tags?.length ? m.scenario_tags.join("、") : "",
  ].filter(Boolean).join(" · ");
  const metaBits = [providerLine, tagSummary, pack.inputs?.scenario_primary].filter(Boolean);
  if (metaBits.length) {
    const metaStrip = document.createElement("p");
    metaStrip.className = "script-pack-meta-strip muted";
    metaStrip.textContent = metaBits.join(" · ");
    container.appendChild(metaStrip);
  }
  const sceneWarn = pack.inputs?.scenario_conflict_note;
  if (sceneWarn) {
    const p = document.createElement("p");
    p.className = "workflow-warn script-pack-warn";
    p.textContent = sceneWarn;
    container.appendChild(p);
  }

  const form = document.createElement("form");
  form.id = "scriptEditForm";
  form.className = "script-pack script-edit-form script-edit-form-flat";
  form.autocomplete = "off";
  form.addEventListener("submit", (e) => e.preventDefault());

  const metaDetails = document.createElement("details");
  metaDetails.className = "pack-meta-details script-pack-fold";
  const metaSummary = document.createElement("summary");
  metaSummary.textContent = "标题与完整口播";
  metaDetails.appendChild(metaSummary);
  appendScriptEditTextarea(metaDetails, "英文标题", "packField", "title", pack.title, 2);
  appendScriptEditTextarea(metaDetails, "英文副标题", "packField", "subtitle", pack.subtitle, 2);
  appendScriptEditTextarea(metaDetails, "完整口播", "packField", "voiceover_20s", pack.voiceover_20s, 3);
  form.appendChild(metaDetails);

  const shotsWrap = document.createElement("div");
  shotsWrap.className = "shot-list-compact shot-list-editable script-shot-list";
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
    head.textContent = `第 ${s.number || idx + 1} 镜 · ${s.role || ""} · ${s.timing || ""}`;
    row.appendChild(head);

    const core = document.createElement("div");
    core.className = "script-shot-core";
    appendScriptEditTextarea(core, "画面", "shotField", "visual", s.visual, 2);
    appendScriptEditTextarea(core, "口播", "shotField", "voiceover_en", s.voiceover_en, 2);
    appendScriptEditTextarea(core, "字幕", "shotField", "subtitle_en", s.subtitle_en, 2);
    row.appendChild(core);

    const advanced = document.createElement("details");
    advanced.className = "script-shot-advanced";
    const advSummary = document.createElement("summary");
    advSummary.textContent = "构图 / 空镜 Prompt";
    advanced.appendChild(advSummary);
    appendScriptEditTextarea(advanced, "构图", "shotField", "visual_prompt", s.visual_prompt, 4);
    const motionWrap = document.createElement("div");
    motionWrap.className = "script-edit-field script-edit-field-inline";
    motionWrap.innerHTML = `<span class="pack-label">运镜</span>`;
    const sel = document.createElement("select");
    sel.dataset.shotField = "camera_motion_type";
    sel.className = "camera-motion-select";
    const cur = shotCameraMotionType(s);
    CAMERA_MOTION_TYPES.forEach((t) => {
      const opt = document.createElement("option");
      opt.value = t;
      opt.textContent = CAMERA_MOTION_LABELS[t] || t;
      if (t === cur) opt.selected = true;
      sel.appendChild(opt);
    });
    motionWrap.appendChild(sel);
    advanced.appendChild(motionWrap);
    appendScriptEditTextarea(advanced, "空镜", "shotField", "seedance_prompt", s.seedance_prompt, 4);
    row.appendChild(advanced);
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

function isAnyFloatPanelOpen() {
  return ["scriptFloatPanel", "productFloatPanel", "refFloatPanel", "promptSelectFloatPanel", "starterGuidePanel", "workflowGuidePanel"]
    .some((id) => document.getElementById(id)?.classList.contains("open"));
}

const SIBLING_FLOAT_PANELS = [
  ["scriptFloatPanel", "scriptFloatBackdrop"],
  ["productFloatPanel", "productFloatBackdrop"],
  ["refFloatPanel", "refFloatBackdrop"],
  ["promptSelectFloatPanel", "promptSelectFloatBackdrop"],
];

function isAutomatedPipelineUi() {
  return Boolean(state.createPipelineActive || state.viralPipelineBusy);
}

function closeSiblingFloatPanels(exceptPanelId = "") {
  for (const [panelId, backdropId] of SIBLING_FLOAT_PANELS) {
    if (panelId === exceptPanelId) continue;
    const panel = document.getElementById(panelId);
    const backdrop = document.getElementById(backdropId);
    if (!panel?.classList.contains("open")) continue;
    panel.classList.remove("open");
    backdrop?.classList.remove("open");
    panel.setAttribute("aria-hidden", "true");
    window.setTimeout(() => {
      if (!panel.classList.contains("open")) {
        panel.hidden = true;
        panel.style.display = "none";
        if (backdrop) backdrop.hidden = true;
      }
    }, 200);
  }
}

function beginAutomatedPipelineUi() {
  state.dockFocusDismissed = false;
  state.pipelineOriginView = state.view;
  closeSiblingFloatPanels("");
  hideProduceCompleteModal();
  hideProduceCompleteBanner();
}

function isDockPreviewVisible() {
  return ["dockProducePreview", "imitateDockProducePreview"].some(
    (id) => !document.getElementById(id)?.classList.contains("hidden"),
  );
}

function isDockProgressVisible() {
  return SEEDANCE_PROGRESS_TARGETS.some((ids) => !document.getElementById(ids.bar)?.classList.contains("hidden"));
}

function hideDockProducePreviews() {
  ["seedanceFinalPreview", "dockProducePreview", "imitateDockProducePreview"].forEach((id) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.add("hidden");
    el.innerHTML = "";
  });
  syncDockReassembleButton(null, null);
}

function syncStudioFocusMode() {
  const modalOpen = !document.getElementById("produceCompleteModal")?.classList.contains("hidden");
  const floatOpen = isAnyFloatPanelOpen();
  const bannerOpen = !document.getElementById("produceCompleteBanner")?.classList.contains("hidden");
  const pipelineBusy = state.createPipelineActive || state.videoGenActive || state.scriptGenActive || state.viralPipelineBusy;
  const errorBanner = !document.getElementById("videoGenErrorBanner")?.classList.contains("hidden");
  const dockChrome = isDockPreviewVisible() || isDockProgressVisible() || errorBanner;
  const shouldFocus = state.dockFocusDismissed
    ? (modalOpen || floatOpen)
    : (modalOpen || floatOpen || bannerOpen || dockChrome || pipelineBusy);
  document.body.classList.toggle("studio-focus-mode", shouldFocus);
  const backdrop = document.getElementById("studioFocusBackdrop");
  if (backdrop) {
    const showBackdrop = shouldFocus && !floatOpen;
    backdrop.classList.toggle("hidden", !showBackdrop);
    backdrop.hidden = !showBackdrop;
  }
  document.querySelectorAll(".studio-dock-close").forEach((btn) => {
    const showClose = shouldFocus || isDockPreviewVisible() || isDockProgressVisible();
    btn.classList.toggle("hidden", !showClose);
  });
}

function dismissStudioFocus() {
  const busy = state.createPipelineActive || state.videoGenActive || state.scriptGenActive || state.viralPipelineBusy;
  const downloadReady = produceDownloadReady(state.lastPreview);
  const slug = currentScriptSlug() || state.lastPreview?.slug;
  state.dockFocusDismissed = true;
  hideProduceCompleteModal();
  hideProduceCompleteBanner();
  closeScriptFloatPanel();
  hideDockProducePreviews();
  state.seedanceProgressPersist = false;
  showSeedanceProgress(false);
  resetScriptProgress();
  if (downloadReady && slug) {
    syncDownloadLinks(`/api/delivery/${encodeURIComponent(slug)}/zip`, true);
    document.querySelectorAll("#scriptDownloadBtnBottom, .js-script-download").forEach((dl) => {
      dl.textContent = produceZipLabel(state.lastPreview?.seedance);
    });
    showProduceCompleteBanner(
      "成片已就绪",
      "已收起工作台浮层，可在顶部条下载 zip；需要预览请重新生成或打开成稿库。",
      slug,
      { engageFocus: false },
    );
  } else {
    syncDownloadLinks("", false);
  }
  if (!busy) {
    clearVideoGenErrorOnly();
  } else {
    setScriptActionStatus("视频仍在后台生成，可切换其他模块；底部工作台可查看进度。", { forceDock: false });
  }
  syncStudioFocusMode();
}

function isFloatPanelOpen(panelId) {
  const el = document.getElementById(panelId);
  if (!el) return false;
  return el.classList.contains("open");
}

function isDrawerOpen(drawerId) {
  const el = document.getElementById(drawerId);
  return Boolean(el && !el.hidden);
}

function closeDockTransientMenus() {
  let closed = false;
  if (!document.getElementById("dockGenerateCountMenu")?.classList.contains("hidden")) {
    closeDockGenerateCountMenu();
    closed = true;
  }
  if (!document.getElementById("imitateGenerateCountMenu")?.classList.contains("hidden")) {
    closeImitateDockGenerateCountMenu();
    closed = true;
  }
  if (document.getElementById("dockVideoSettingsPanel")?.classList.contains("open")) {
    closeDockVideoSettingsPanel();
    closed = true;
  }
  if (document.getElementById("imitateVideoSettingsPanel")?.classList.contains("open")) {
    closeImitateDockVideoSettingsPanel();
    closed = true;
  }
  return closed;
}

function handleGlobalEscapeKey() {
  if (closeDockTransientMenus()) return;
  const guidePanel = document.getElementById("starterGuidePanel");
  if (guidePanel?.classList.contains("open")) {
    dismissStarterGuide();
    return;
  }
  const workflowGuidePanel = document.getElementById("workflowGuidePanel");
  if (workflowGuidePanel?.classList.contains("open")) {
    closeWorkflowGuidePanel();
    return;
  }
  const modal = document.getElementById("produceCompleteModal");
  if (modal && !modal.classList.contains("hidden")) {
    dismissStudioFocus();
    return;
  }
  if (isFloatPanelOpen("promptSelectFloatPanel")) {
    closePromptSelectFloatPanel();
    return;
  }
  if (isFloatPanelOpen("scriptFloatPanel")) {
    closeScriptFloatPanel();
    syncStudioFocusMode();
    return;
  }
  if (isFloatPanelOpen("productFloatPanel")) {
    closeProductFloatPanel();
    return;
  }
  if (isFloatPanelOpen("refFloatPanel")) {
    closeRefFloatPanel();
    return;
  }
  if (isDrawerOpen("materialLibraryDrawer")) {
    closeMaterialLibraryDrawer();
    return;
  }
  if (isDrawerOpen("settingsDrawer")) {
    closeSettingsDrawer();
    return;
  }
  if (
    isDockPreviewVisible()
    || isDockProgressVisible()
    || !document.getElementById("videoGenErrorBanner")?.classList.contains("hidden")
    || document.body.classList.contains("studio-focus-mode")
  ) {
    dismissStudioFocus();
  }
}

function openFloatPanel(panelId, backdropId) {
  closeSiblingFloatPanels(panelId);
  state.dockFocusDismissed = false;
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
    syncStudioFocusMode();
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
      syncStudioFocusMode();
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
  return `<span class="dock-run-icon">✦</span> ${esc(dockRunDefaultText(view))}`;
}

function syncDockRunButtonLabels() {
  forEachDockRunBtn((btn, id) => {
    if (btn.dataset.busy) return;
    const view = id === "imitateDockRun" ? "imitate" : "generate";
    btn.innerHTML = dockRunDefaultHtml(view);
    btn.title = workflowActionTitle(view);
  });
  syncWorkflowGuide();
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
  syncWorkflowGuide();
}

function workflowRefReady() {
  return Boolean(document.getElementById("scriptMaterialSelect")?.value || state.selectedMaterialId);
}

function workflowPromptReady() {
  return Boolean(
    state.generatePromptSelection?.text
    || state.generatePromptSelection?.id
    || getImitationPrompt(),
  );
}

function workflowNeedsPrompt() {
  return state.view === "generate"
    && state.generateDockMode === "generate"
    && scriptNeedsRegenerate(state.lastPreview || {});
}

function workflowRefLabel() {
  const linkId = Number(document.getElementById("scriptMaterialSelect")?.value || state.selectedMaterialId);
  const item = linkId ? state.items.find((i) => i.link_id === linkId) : null;
  if (!linkId) return "";
  const title = (item?.title || "").trim();
  return title ? `#${linkId} · ${title.slice(0, 12)}` : `#${linkId}`;
}

function workflowStepSnapshot() {
  const productReady = Boolean(document.getElementById("scriptProductSelect")?.value) && tagsSelectionOk();
  const refReady = workflowRefReady();
  const promptReady = workflowPromptReady();
  const promptNeeded = workflowNeedsPrompt();
  const prev = state.lastPreview || {};
  const scriptReady = Boolean(prev.has_script || prev.delivery_ready || currentScriptSlug());
  const finalReady = Boolean(prev?.seedance?.final_video?.ready);
  let activeStep = "create";
  if (!productReady) activeStep = "product";
  else if (promptNeeded && !promptReady) activeStep = "prompt";
  else if (!refReady) activeStep = "ref";
  return { productReady, refReady, promptReady, promptNeeded, scriptReady, finalReady, activeStep };
}

function syncWorkflowStepClasses(snap) {
  document.querySelectorAll("[data-workflow-step]").forEach((el) => {
    const step = el.dataset.workflowStep;
    let done = false;
    if (step === "product") done = snap.productReady;
    if (step === "prompt") done = snap.promptReady || !snap.promptNeeded || snap.scriptReady;
    if (step === "ref") done = snap.refReady;
    if (step === "create") done = snap.finalReady;
    el.classList.toggle("is-done", done);
    el.classList.toggle("is-active", step === snap.activeStep && !done);
  });
}

function workflowActionTitle(view = state.view) {
  const snap = workflowStepSnapshot();
  if (!snap.productReady) return "先点击「产品」完成产品与场景标签配置";
  if (view !== "imitate" && snap.promptNeeded && !snap.promptReady) return "先选择提示词模板或填写创作要求";
  if (!snap.refReady) return "先点击「对标」选择同品类爆款参考";
  if (snap.scriptReady && !snap.finalReady) return "脚本已就绪，继续生成 AI 分镜视频";
  if (snap.finalReady) return "成片已就绪，可下载或继续调整后重生成";
  return view === "imitate" ? "按爆款结构生成脚本并出片" : "生成脚本并产出 AI 分镜视频";
}

function syncWorkflowGuide() {
  const snap = workflowStepSnapshot();
  const productName = currentProductLabel();
  const refLabel = workflowRefLabel();
  const promptLabel = state.generatePromptSelection?.label || (snap.promptReady ? "已填写" : "");
  let title = "可以开始创作";
  let status = "产品、提示词和对标已就绪，点击「开始创作」会先生成脚本预览，再继续产出 AI 分镜视频。";
  if (snap.finalReady) {
    title = "成片已就绪";
    status = "可下载成片 zip，或修改产品标签、提示词、对标后重新生成。";
  } else if (snap.scriptReady && !scriptNeedsRegenerate(state.lastPreview || {})) {
    title = "脚本已就绪，可继续出片";
    status = "请检查脚本浮层中的分镜与口播，确认后继续生成 AI 视频。";
  } else if (!snap.productReady) {
    title = "先配置产品与场景标签";
    status = "选择产品后，为人群、场景、卖点、痛点各选至少一项，避免脚本跑偏。";
  } else if (snap.promptNeeded && !snap.promptReady) {
    title = "选择提示词或填写创作要求";
    status = "提示词用于控制风格和开场，爆款对标只迁移结构节奏，不复制文案。";
  } else if (!snap.refReady) {
    title = "选择同品类爆款对标";
    status = "对标用于抽取镜头节奏和结构，产品外观仍以白底主图锁定。";
  }

  const titleEl = document.getElementById("workflowGuideTitle");
  const statusEl = document.getElementById("workflowGuideStatus");
  if (titleEl) titleEl.textContent = title;
  if (statusEl) statusEl.textContent = status;
  syncWorkflowStepClasses(snap);

  const refBtn = document.getElementById("workflowPickRefBtn");
  if (refBtn) {
    refBtn.disabled = !snap.productReady;
    refBtn.title = snap.productReady ? "选择同品类爆款参考" : "请先配置产品";
  }
  const promptBtn = document.getElementById("workflowPickPromptBtn");
  if (promptBtn) {
    promptBtn.classList.toggle("active", snap.promptReady);
    promptBtn.textContent = promptLabel ? "换提示词" : "选提示词";
  }
  const startBtn = document.getElementById("workflowStartBtn");
  if (startBtn) {
    startBtn.textContent = dockRunDefaultText(state.view);
    startBtn.title = workflowActionTitle(state.view);
  }

  const parts = [
    snap.productReady ? `产品：${productName || "已配置"}` : "产品未配置",
    snap.promptReady ? `提示词：${promptLabel || "已填写"}` : (state.view === "imitate" ? "结构：按对标复刻" : "提示词待选"),
    snap.refReady ? `对标：${refLabel || "已选"}` : "对标未选",
  ];
  const dockText = parts.join(" · ");
  for (const id of ["generateDockStatusLine", "imitateDockStatusLine"]) {
    const el = document.getElementById(id);
    if (!el) continue;
    el.textContent = dockText;
    el.classList.toggle("is-ready", snap.productReady && snap.refReady && (!snap.promptNeeded || snap.promptReady));
    el.classList.toggle("is-warn", !snap.productReady || !snap.refReady || (snap.promptNeeded && !snap.promptReady));
  }
}

function dockRunDefaultText(view = state.view) {
  const snap = workflowStepSnapshot();
  if (!snap.productReady) return "先选产品";
  if (view !== "imitate" && snap.promptNeeded && !snap.promptReady) return "选提示词";
  if (!snap.refReady) return "选对标";
  if (view !== "imitate") {
    const prev = state.lastPreview || {};
    const ready = prev.has_script && !scriptNeedsRegenerate(prev) && !prev?.seedance?.final_video?.ready;
    if (ready && state.healthCache?.seedance?.configured) return "继续出片";
  }
  return view === "imitate" ? "开始复刻" : "开始创作";
}

function syncFinishButton(canFinish, delivered) {
  const canProduce = Boolean(canFinish && currentScriptSlug());
  forEachDockRunBtn((runBtn) => {
    if (runBtn.dataset.busy) return;
    const imitate = runBtn.id === "imitateDockRun";
    runBtn.disabled = !canProduce && Boolean(state.lastPreview?.has_script) === false
      ? !tagsSelectionOk() || !state.selectedMaterialId
      : false;
    runBtn.title = workflowActionTitle(imitate ? "imitate" : "generate");
  });
  syncDockRunButtonsDisabled();
  syncWorkflowGuide();
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

function isWorkbenchProgressActive() {
  return Boolean(
    state.createPipelineActive
    || state.seedanceProgressPersist
    || state.scriptGenActive
    || state.videoGenActive,
  );
}

function hideSeedanceProgressIfIdle() {
  if (!isWorkbenchProgressActive()) showSeedanceProgress(false);
}

function showScriptProgress(show, { status, percent, indeterminate, pipeline, countdownSec } = {}) {
  state.scriptGenActive = Boolean(show);
  if (isAutomatedPipelineUi()) {
    if (show) {
      showSeedanceProgress(true, { status, percent, indeterminate, pipeline, countdownSec, persist: true });
    } else {
      hideSeedanceProgressIfIdle();
    }
    syncGlobalPipelineBadge(status);
    syncPipelineStopButtons();
    return;
  }
  const bar = document.getElementById("scriptGenProgress");
  const statusEl = document.getElementById("scriptGenProgressStatus");
  const fill = document.getElementById("scriptGenProgressFill");
  const meta = document.getElementById("scriptGenProgressMeta");
  const track = bar?.querySelector(".seedance-progress-track");
  if (!bar) {
    if (show) showSeedanceProgress(true, { status, percent, indeterminate, pipeline, countdownSec });
    else hideSeedanceProgressIfIdle();
    return;
  }

  if (show && countdownSec != null && countdownSec > 0) startScriptGenCountdown(countdownSec);
  if (!show) stopScriptGenCountdown();

  bar.classList.toggle("hidden", !show);
  if (!show) {
    fill?.classList.remove("indeterminate");
    if (fill) fill.style.width = "";
    if (statusEl) statusEl.textContent = "准备中…";
    if (meta) meta.textContent = "";
    hideSeedanceProgressIfIdle();
    syncDockScrollPadding();
    syncGlobalPipelineBadge("");
    syncPipelineStopButtons();
    return;
  }

  if (status && statusEl) statusEl.textContent = status;
  if (pipeline != null && meta) meta.textContent = pipeline;
  if (fill) {
    fill.classList.toggle("indeterminate", Boolean(indeterminate));
    if (percent != null) fill.style.width = `${Math.min(100, Math.max(0, percent))}%`;
  }
  if (track && percent != null) track.setAttribute("aria-valuenow", String(Math.round(percent)));

  showSeedanceProgress(true, { status, percent, indeterminate, pipeline, countdownSec });
  syncDockScrollPadding();
  syncGlobalPipelineBadge(status);
  syncPipelineStopButtons();
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

  const visible = Boolean(show && (state.seedanceProgressPersist || isWorkbenchProgressActive()));
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

    const labelEl = bar.querySelector(".seedance-progress-label");
    if (labelEl) labelEl.textContent = state.scriptGenActive ? "AI 镜头脚本" : "AI 分镜";

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
  syncStudioFocusMode();
  syncGlobalPipelineBadge(status);
  syncPipelineStopButtons();
}

function saveWorkflowSnapshot() {
  try {
    const productId = document.getElementById("scriptProductSelect")?.value || state.selectedProductId || "";
    if (!productId && !state.selectedMaterialId) return;
    sessionStorage.setItem(WORKFLOW_SNAPSHOT_KEY, JSON.stringify({
      productId,
      materialId: state.selectedMaterialId,
      tags: readAllSelectedTags(),
      slug: state.scriptSlug || state.lastPreview?.slug || "",
      view: state.view,
      generateDockMode: state.generateDockMode,
      savedAt: Date.now(),
    }));
    syncRestoreWorkflowButton();
  } catch {
    /* ignore */
  }
}

function syncRestoreWorkflowButton() {
  const btn = document.getElementById("restoreWorkflowBtn");
  if (!btn) return;
  try {
    const raw = sessionStorage.getItem(WORKFLOW_SNAPSHOT_KEY);
    const snap = raw ? JSON.parse(raw) : null;
    const show = Boolean(snap?.productId);
    btn.hidden = !show;
    btn.classList.toggle("hidden", !show);
  } catch {
    btn.hidden = true;
    btn.classList.add("hidden");
  }
}

async function restoreWorkflowSnapshot() {
  try {
    const raw = sessionStorage.getItem(WORKFLOW_SNAPSHOT_KEY);
    if (!raw) return;
    const snap = JSON.parse(raw);
    if (!snap.productId) return;
    state.selectedProductId = snap.productId;
    const ps = document.getElementById("scriptProductSelect");
    if (ps?.querySelector(`option[value="${snap.productId}"]`)) ps.value = snap.productId;
    if (snap.tags) {
      state.tagSelection = {
        audience: [...(snap.tags.audience || [])],
        scenarios: [...(snap.tags.scenarios || [])],
        selling: [...(snap.tags.selling || [])],
        pains: [...(snap.tags.pains || [])],
      };
      state.selectedAudience = state.tagSelection.audience;
      state.selectedScenarios = state.tagSelection.scenarios;
      refreshTagGroupsUI();
    }
    if (snap.materialId) await selectMaterial(snap.materialId, { loadDetail: false });
    if (snap.slug) state.scriptSlug = snap.slug;
    const targetView = snap.view === "imitate" || snap.generateDockMode === "imitate" ? "imitate" : "generate";
    switchView(targetView);
    if (targetView === "generate") syncGenerateDockMode("generate");
    await refreshScriptPreview({ preserveTagSelection: true });
    syncDockProductSlot();
    syncDockRefSlot();
    repopulateScriptMaterials();
    renderAllImitationViralGrids();
    setScriptActionStatus("已恢复上次工作配置");
  } catch (err) {
    setScriptActionStatus(`恢复失败：${err.message}`, { isError: true });
  }
}

function syncGlobalPipelineBadge(statusText = "") {
  const badge = document.getElementById("globalPipelineBadge");
  if (!badge) return;
  const busy = state.videoGenActive || state.createPipelineActive || state.viralPipelineBusy || state.scriptGenActive;
  if (!busy) state.pipelineOriginView = null;
  badge.hidden = !busy;
  badge.classList.toggle("hidden", !busy);
  if (!busy) return;
  const st = statusText
    || document.getElementById("seedanceProgressStatus")?.textContent
    || document.getElementById("imitateSeedanceProgressStatus")?.textContent
    || document.getElementById("scriptGenProgressStatus")?.textContent
    || "任务进行中…";
  badge.textContent = state.scriptGenActive ? `脚本：${String(st).slice(0, 24)}` : `出片：${String(st).slice(0, 24)}`;
}

function resetSeedanceProgressDock() {
  stopSeedanceCountdown();
  state.seedanceProgressPersist = false;
  state.scriptGenActive = false;
  state.videoGenActive = false;
  state.producePartialReady = false;
  clearVideoGenErrorUi();
  for (const ids of SEEDANCE_PROGRESS_TARGETS) {
    const bar = document.getElementById(ids.bar);
    const fill = document.getElementById(ids.fill);
    if (fill) {
      fill.classList.remove("indeterminate");
      fill.style.width = "";
    }
    const labelEl = bar?.querySelector(".seedance-progress-label");
    if (labelEl) labelEl.textContent = "AI 分镜";
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
  syncStudioFocusMode();
  syncGlobalPipelineBadge("");
  syncPipelineStopButtons();
}

function renderSeedanceFinalPreview(slug, seedance, options = {}) {
  renderProduceResultPanel(slug, seedance, options);
}

function shotAssetsReady(seedance) {
  return (seedance?.shots || []).some((s) => s.ready);
}

const REASSEMBLE_LABEL = "重新合成";
const REASSEMBLE_BUSY_LABEL = "合成中…";

/** 分镜 mp4 已齐但 final-video 未就绪 → 仅需 ffmpeg 拼接 */
function needsReassemble(seedance) {
  return shotAssetsReady(seedance) && !Boolean(seedance?.final_video?.ready);
}

function syncDockReassembleButton(slug, seedance) {
  const show = Boolean(slug && needsReassemble(seedance));
  ["generateDockReassemble", "imitateDockReassemble"].forEach((id) => {
    const btn = document.getElementById(id);
    if (!btn) return;
    btn.classList.toggle("hidden", !show);
    if (show) btn.dataset.retrySlug = slug;
    else delete btn.dataset.retrySlug;
    if (!btn.disabled) btn.textContent = REASSEMBLE_LABEL;
  });
}

function produceDownloadReady(prev = state.lastPreview || {}) {
  const sd = prev?.seedance || {};
  return Boolean(sd.final_video?.ready || shotAssetsReady(sd) || prev?.delivery_ready);
}

function produceZipLabel(seedance) {
  return shotAssetsReady(seedance) && !seedance?.final_video?.ready
    ? "下载分镜 zip"
    : "下载成片 zip";
}

/** 有分镜或成片时：同步下载按钮、脚本浮层内预览区、底部 dock 预览 */
function syncProduceAssetsUi(prev = state.lastPreview || {}) {
  const slug = prev?.slug || currentScriptSlug();
  const seedance = prev?.seedance;
  if (!slug || !produceDownloadReady(prev)) {
    syncDownloadLinks("", false);
    return false;
  }
  if (shotAssetsReady(seedance) && !seedance?.final_video?.ready) {
    state.producePartialReady = true;
  }
  syncDownloadLinks(`/api/delivery/${encodeURIComponent(slug)}/zip`, true);
  document.querySelectorAll("#scriptDownloadBtnBottom, .js-script-download").forEach((dl) => {
    dl.textContent = produceZipLabel(seedance);
  });
  renderProduceResultPanel(slug, seedance, { engageFocus: false, scope: "active" });
  syncDockReassembleButton(slug, seedance);
  return true;
}

function hideProduceCompleteBanner() {
  document.getElementById("produceCompleteBanner")?.classList.add("hidden");
  syncStudioFocusMode();
}

function hideProduceCompleteModal() {
  const modal = document.getElementById("produceCompleteModal");
  const backdrop = document.getElementById("produceCompleteModalBackdrop");
  modal?.classList.add("hidden");
  backdrop?.classList.add("hidden");
  if (modal) {
    modal.hidden = true;
    modal.setAttribute("aria-hidden", "true");
  }
  if (backdrop) backdrop.hidden = true;
  syncStudioFocusMode();
}

function buildProduceResultHtml(slug, seedance, { assembleMessage = "" } = {}) {
  const shots = (seedance?.shots || []).filter((row) => row.ready && row.file);
  const final = seedance?.final_video || {};
  const finalReady = Boolean(final.ready && final.file && slug);
  const hint = videoOutputHint(slug);
  const shotLinks = shots.map((row) => {
    const href = withApiToken(`/api/delivery/${encodeURIComponent(slug)}/files/${encodeURI(row.file)}`);
    return `<li><a class="seedance-final-link" href="${href}" target="_blank">预览 镜${row.number} · ${esc(row.role || row.timing || "分镜")}</a></li>`;
  }).join("");
  const finalBlock = finalReady
    ? `<a class="seedance-final-link produce-final-link" href="${withApiToken(`/api/delivery/${encodeURIComponent(slug)}/files/${encodeURI(final.file)}`)}" target="_blank">▶ 预览成片 final-video.mp4</a>`
    : "";
  const zipHref = withApiToken(`/api/delivery/${encodeURIComponent(slug)}/zip`);
  const zipBlock = (finalReady || shots.length)
    ? `<a class="seedance-final-link produce-zip-link primary pill-btn" href="${zipHref}" download>${finalReady ? "⬇ 下载成片 zip" : "⬇ 下载分镜 zip（含已生成 mp4）"}</a>`
    : "";
  const retryBlock = !finalReady && shots.length
    ? `<button type="button" class="primary pill-btn produce-retry-assemble" data-retry-slug="${esc(slug)}">${REASSEMBLE_LABEL}</button>
       <p class="muted produce-assemble-hint">${esc(assembleMessage || "分镜 mp4 已就绪，点击「重新合成」仅拼接成片，不会重新生成各镜")}</p>`
    : "";
  return `<div class="produce-result-panel ${finalReady ? "is-complete" : "is-partial"}">
    <div class="produce-result-head">
      <p class="produce-result-title">${finalReady ? "✓ 成片已生成" : shots.length ? "分镜已生成（可预览/下载）" : "暂无可预览视频"}</p>
      <button type="button" class="produce-result-dismiss" data-action="dismiss-studio" aria-label="返回主页面" title="返回主页面">×</button>
    </div>
    ${finalBlock}
    ${zipBlock}
    ${shotLinks ? `<ul class="produce-shot-list">${shotLinks}</ul>` : ""}
    ${retryBlock}
    ${hint ? `<p class="muted seedance-final-path">${esc(hint)}</p>` : ""}
  </div>`;
}

function wireProduceResultPanel(root, slug) {
  if (!root) return;
  root.querySelectorAll("[data-action='dismiss-studio']").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      dismissStudioFocus();
    });
  });
  root.querySelectorAll(".produce-retry-assemble").forEach((btn) => {
    btn.addEventListener("click", () => {
      void retryAssembleVideo(btn.getAttribute("data-retry-slug") || slug);
    });
  });
}

function showProduceCompleteBanner(title, message, slug, { partial = false, engageFocus = true } = {}) {
  closeSiblingFloatPanels("");
  const banner = document.getElementById("produceCompleteBanner");
  const titleEl = document.getElementById("produceCompleteBannerTitle");
  const textEl = document.getElementById("produceCompleteBannerText");
  const dl = document.getElementById("produceCompleteDownloadBtn");
  if (!banner || !titleEl || !textEl) return;
  titleEl.textContent = title;
  textEl.textContent = message;
  banner.classList.toggle("is-partial", Boolean(partial));
  banner.classList.remove("hidden");
  if (dl && slug && produceDownloadReady({ slug, seedance: state.lastPreview?.seedance, delivery_ready: state.lastPreview?.delivery_ready })) {
    dl.href = withApiToken(`/api/delivery/${encodeURIComponent(slug)}/zip`);
    dl.textContent = produceZipLabel(state.lastPreview?.seedance);
    dl.classList.remove("hidden");
  } else if (dl) {
    dl.classList.add("hidden");
  }
  if (engageFocus) state.dockFocusDismissed = false;
  syncStudioFocusMode();
}

function showProduceCompleteModal(title, message, slug, seedance, { partial = false } = {}) {
  closeSiblingFloatPanels("");
  const modal = document.getElementById("produceCompleteModal");
  const backdrop = document.getElementById("produceCompleteModalBackdrop");
  const titleEl = document.getElementById("produceCompleteModalTitle");
  const textEl = document.getElementById("produceCompleteModalText");
  const iconEl = document.getElementById("produceCompleteModalIcon");
  const previewEl = document.getElementById("produceCompleteModalPreview");
  const dl = document.getElementById("produceCompleteModalDownload");
  if (!modal || !backdrop || !titleEl || !textEl || !previewEl) return;
  titleEl.textContent = title;
  textEl.textContent = message;
  modal.classList.toggle("is-partial", Boolean(partial));
  if (iconEl) iconEl.textContent = partial ? "!" : "✓";
  const zipReady = slug && produceDownloadReady({ slug, seedance, delivery_ready: state.lastPreview?.delivery_ready });
  if (dl) {
    if (zipReady) {
      dl.href = withApiToken(`/api/delivery/${encodeURIComponent(slug)}/zip`);
      dl.textContent = produceZipLabel(seedance);
      dl.classList.remove("hidden");
    } else {
      dl.classList.add("hidden");
    }
  }
  if (slug && seedance && (shotAssetsReady(seedance) || seedance.final_video?.ready)) {
    previewEl.innerHTML = buildProduceResultHtml(slug, seedance, {
      assembleMessage: partial ? message : "",
    });
    wireProduceResultPanel(previewEl, slug);
    previewEl.classList.remove("hidden");
  } else {
    previewEl.innerHTML = "";
    previewEl.classList.add("hidden");
  }
  modal.classList.remove("hidden");
  backdrop.classList.remove("hidden");
  modal.hidden = false;
  backdrop.hidden = false;
  modal.setAttribute("aria-hidden", "false");
  state.dockFocusDismissed = false;
  syncStudioFocusMode();
}

function restoreProduceUiFromPreview(prev = state.lastPreview || {}) {
  if (!prev.slug || !prev.seedance) {
    hideProduceCompleteBanner();
    hideProduceCompleteModal();
    hideDockProducePreviews();
    syncDockReassembleButton(null, null);
    return;
  }
  const { slug, seedance } = prev;
  if (seedance.final_video?.ready) {
    state.producePartialReady = false;
    state.seedanceVideoComplete = true;
    clearVideoGenErrorOnly();
    syncDownloadLinks(`/api/delivery/${encodeURIComponent(slug)}/zip`, true);
    if (!state.dockFocusDismissed) {
      syncProduceAssetsUi(prev);
      syncProducePreviewAllDocks(prev);
    }
    return;
  }
  if (shotAssetsReady(seedance)) {
    state.producePartialReady = true;
    for (const ids of SEEDANCE_PROGRESS_TARGETS) {
      const bar = document.getElementById(ids.bar);
      bar?.classList.remove("seedance-progress-error");
      const labelEl = bar?.querySelector(".seedance-progress-label");
      if (labelEl) labelEl.textContent = "AI 分镜";
    }
    clearVideoGenErrorOnly();
    if (!state.dockFocusDismissed) {
      syncProduceAssetsUi(prev);
      syncProducePreviewAllDocks(prev);
    }
  } else {
    syncDockReassembleButton(null, null);
    syncProduceAssetsUi(prev);
  }
  syncStudioFocusMode();
}

function producePreviewTargets(scope = "active") {
  const map = {
    script: document.getElementById("seedanceFinalPreview"),
    generate: document.getElementById("dockProducePreview"),
    imitate: document.getElementById("imitateDockProducePreview"),
  };
  if (scope === "all") return Object.values(map).filter(Boolean);
  if (scope === "script") return map.script ? [map.script] : [];
  if (scope === "imitate") return map.imitate ? [map.imitate] : [];
  if (state.view === "imitate") return map.imitate ? [map.imitate] : [];
  return [map.generate, map.script].filter(Boolean);
}

function syncProducePreviewForActiveView() {
  syncProducePreviewAllDocks(state.lastPreview || {});
}

function heroFrameGateEnabled() {
  return Boolean(state.healthCache?.hero_frame_gate);
}

function heroFramePanelTargets(scope = "active") {
  const map = {
    script: document.getElementById("scriptHeroFramePanel"),
    generate: document.getElementById("dockHeroFramePanel"),
    imitate: document.getElementById("imitateDockHeroFramePanel"),
  };
  if (scope === "all") return Object.values(map).filter(Boolean);
  if (scope === "script") return map.script ? [map.script] : [];
  if (scope === "imitate") return map.imitate ? [map.imitate] : [];
  if (state.view === "imitate") return map.imitate ? [map.imitate] : [];
  return [map.generate, map.script].filter(Boolean);
}

function hideHeroFramePanels() {
  heroFramePanelTargets("all").forEach((el) => {
    el.classList.add("hidden");
    el.innerHTML = "";
  });
}

function buildHeroFramePanelHtml(slug, status) {
  const confirmed = Boolean(status.confirmed);
  const shots = status.shots || [];
  const cards = shots.map((shot) => {
    const num = shot.number;
    const img = shot.hero_file
      ? `/api/delivery/${encodeURIComponent(slug)}/files/${shot.hero_file}`
      : "";
    const thumb = img
      ? `<img src="${esc(img)}" alt="镜${num}关键帧" class="hero-frame-thumb" loading="lazy">`
      : `<div class="hero-frame-thumb hero-frame-thumb--empty">无参考图</div>`;
    return `
      <article class="hero-frame-card" data-shot="${num}">
        <div class="hero-frame-card-media">${thumb}</div>
        <div class="hero-frame-card-meta">
          <div class="hero-frame-card-title">镜 ${num} · ${esc(shot.role || "分镜")}</div>
          <div class="hero-frame-card-motion muted">${esc(shot.motion_summary || shot.timing || "")}</div>
          <p class="hero-frame-card-visual muted">${esc((shot.visual || "").slice(0, 72))}${(shot.visual || "").length > 72 ? "…" : ""}</p>
          <button type="button" class="secondary pill-btn hero-frame-regen-btn" data-shot="${num}" ${confirmed ? "disabled" : ""}>重生成关键帧</button>
        </div>
      </article>`;
  }).join("");
  const confirmBtn = confirmed
    ? `<p class="hero-frame-confirmed-note">✓ 关键帧已确认，可生成动态视频</p>`
    : `<button type="button" class="primary primary-dark hero-frame-confirm-all" data-slug="${esc(slug)}">确认全部关键帧，开始生成视频</button>`;
  return `
    <div class="hero-frame-gate-inner">
      <div class="hero-frame-gate-head">
        <h4>分镜关键帧确认</h4>
        <p class="muted">确认各镜构图与运镜后再生成动态视频（此步不消耗 SeedDance 成片额度）。</p>
      </div>
      <div class="hero-frame-grid">${cards}</div>
      <footer class="hero-frame-gate-foot">${confirmBtn}</footer>
    </div>`;
}

function wireHeroFramePanelEvents(slug, root = document) {
  root.querySelectorAll(".hero-frame-regen-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const num = Number(btn.dataset.shot);
      btn.disabled = true;
      try {
        const data = await api(`/api/delivery/${encodeURIComponent(slug)}/hero-frames/${num}/regenerate`, { method: "POST" });
        renderHeroFramePanels(slug, data);
        setScriptActionStatus(`镜 ${num} 关键帧已更新，请重新确认全部关键帧。`, { forceDock: true });
      } catch (err) {
        setScriptActionStatus(`关键帧重生成失败：${err.message}`, { isError: true });
      } finally {
        btn.disabled = false;
      }
    });
  });
  root.querySelectorAll(".hero-frame-confirm-all").forEach((btn) => {
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      try {
        await submitHeroFrameConfirm(slug);
      } catch (err) {
        setScriptActionStatus(`确认失败：${err.message}`, { isError: true });
      } finally {
        btn.disabled = false;
      }
    });
  });
}

function renderHeroFramePanels(slug, status, { scope = "active" } = {}) {
  const panels = heroFramePanelTargets(scope);
  if (!heroFrameGateEnabled() || !status?.shots?.length) {
    hideHeroFramePanels();
    return;
  }
  const html = buildHeroFramePanelHtml(slug, status);
  panels.forEach((panel) => {
    panel.classList.remove("hidden");
    panel.innerHTML = html;
    wireHeroFramePanelEvents(slug, panel);
  });
}

async function submitHeroFrameConfirm(slug) {
  const data = await api(`/api/delivery/${encodeURIComponent(slug)}/hero-frames/confirm`, { method: "POST" });
  state.awaitingHeroConfirm = false;
  renderHeroFramePanels(slug, data);
  setScriptActionStatus("关键帧已确认，正在启动动态视频生成…", { forceDock: true });
  if (state.heroConfirmThenProduce) {
    state.heroConfirmThenProduce = false;
    await runSeedanceGenerate({ background: true, keepCountdown: true });
  }
  return data;
}

async function ensureHeroFramesGate(slug, { background = false } = {}) {
  if (!heroFrameGateEnabled()) return true;
  let status = await api(`/api/delivery/${encodeURIComponent(slug)}/hero-frames`);
  if (!status.shots?.length || !status.all_ready) {
    setScriptActionStatus("正在准备各镜关键帧预览…", { forceDock: true });
    status = await api(`/api/delivery/${encodeURIComponent(slug)}/hero-frames/generate`, { method: "POST" });
  }
  if (status.confirmed) {
    state.awaitingHeroConfirm = false;
    hideHeroFramePanels();
    return true;
  }
  state.awaitingHeroConfirm = true;
  renderHeroFramePanels(slug, status);
  setScriptActionStatus("请先确认各镜关键帧构图，再开始生成动态视频。", { forceDock: true });
  if (!background) openScriptFloatPanel();
  showSeedanceProgress(true, {
    status: "等待关键帧确认…",
    indeterminate: true,
    persist: true,
  });
  activeStudioDock()?.scrollIntoView({ behavior: "smooth", block: "end" });
  return false;
}

function syncProducePreviewAllDocks(prev = state.lastPreview || {}) {
  const lp = prev;
  const boxIds = ["dockProducePreview", "imitateDockProducePreview"];
  if (!lp.slug || !lp.seedance || !produceDownloadReady(lp)) {
    boxIds.forEach((id) => {
      const box = document.getElementById(id);
      if (!box) return;
      box.classList.add("hidden");
      box.innerHTML = "";
    });
    return;
  }
  if (state.dockFocusDismissed) {
    syncDockReassembleButton(lp.slug, lp.seedance);
    syncStudioFocusMode();
    return;
  }
  const html = buildProduceResultHtml(lp.slug, lp.seedance, {});
  boxIds.forEach((id) => {
    const box = document.getElementById(id);
    if (!box) return;
    box.classList.remove("hidden");
    box.innerHTML = html;
    wireProduceResultPanel(box, lp.slug);
  });
  syncDockReassembleButton(lp.slug, lp.seedance);
  syncStudioFocusMode();
}

function renderProduceResultPanel(slug, seedance, { assembleMessage = "", engageFocus = false, scope = "active" } = {}) {
  const targets = producePreviewTargets(scope);
  const hideOthers = scope === "active"
    ? producePreviewTargets("all").filter((el) => !targets.includes(el))
    : [];
  const s = slug || currentScriptSlug();
  const shots = (seedance?.shots || []).filter((row) => row.ready && row.file);
  const finalReady = Boolean(seedance?.final_video?.ready && seedance?.final_video?.file && s);
  if (!s || (!finalReady && !shots.length)) {
    [...targets, ...hideOthers].forEach((box) => {
      box.classList.add("hidden");
      box.innerHTML = "";
    });
    syncDockReassembleButton(null, null);
    syncStudioFocusMode();
    return;
  }
  const html = buildProduceResultHtml(s, seedance, { assembleMessage });
  targets.forEach((box) => {
    box.classList.remove("hidden");
    box.innerHTML = html;
    wireProduceResultPanel(box, s);
  });
  hideOthers.forEach((box) => {
    box.classList.add("hidden");
    box.innerHTML = "";
  });
  syncDockReassembleButton(s, seedance);
  if (engageFocus && html && !state.dockFocusDismissed) state.dockFocusDismissed = false;
  syncStudioFocusMode();
}

async function retryAssembleVideo(slug) {
  const s = slug || currentScriptSlug();
  if (!s) return;
  const busy = (btn) => {
    btn.disabled = true;
    btn.textContent = REASSEMBLE_BUSY_LABEL;
  };
  const idle = (btn) => {
    btn.disabled = false;
    btn.textContent = REASSEMBLE_LABEL;
  };
  document.querySelectorAll(".produce-retry-assemble, .studio-dock-reassemble").forEach(busy);
  setScriptActionStatus("正在重新合成成片（仅拼接分镜，不重新生成各镜）…", { forceDock: true });
  showSeedanceProgress(true, {
    status: "正在合成 final-video.mp4…",
    indeterminate: true,
    pipeline: state.lastPreview?.seedance?.pipeline || state.healthCache?.seedance?.label || "",
    persist: true,
  });
  try {
    const data = await api(`/api/delivery/${encodeURIComponent(s)}/assemble`, { method: "POST" });
    await refreshScriptPreview();
    const seedance = data.seedance || state.lastPreview?.seedance;
    renderProduceOutcome(s, seedance, {
      message: data.assemble?.message,
      assemble: data.assemble,
    });
  } catch (err) {
    showVideoGenError(`合成失败：${err.message}`);
    if (needsReassemble(state.lastPreview?.seedance)) {
      syncDockReassembleButton(s, state.lastPreview?.seedance);
    }
  } finally {
    document.querySelectorAll(".produce-retry-assemble, .studio-dock-reassemble").forEach(idle);
  }
}

/** @returns {"complete"|"partial"|"error"} */
function renderProduceOutcome(slug, seedance, { message = "", assemble = null, failed = false } = {}) {
  const s = slug || currentScriptSlug();
  const finalReady = Boolean(seedance?.final_video?.ready);
  const shotsReady = shotAssetsReady(seedance);
  const hardFailed = Boolean(failed && !finalReady && !shotsReady);
  if (finalReady && s) {
    const msg = message || "视频生成完成，可下载 zip 或预览成片";
    renderDockProduceComplete(s, msg);
    return "complete";
  }
  if (shotsReady && s && !hardFailed) {
    clearVideoGenErrorUi();
    state.producePartialReady = true;
    state.seedanceProgressPersist = true;
    const asmMsg = assemble?.message || message || "分镜已生成，成片合成未完成";
    const friendly = asmMsg.includes("ffmpeg")
      ? `${asmMsg}${PARTIAL_QUOTA_NOTE}。可先预览下方分镜 mp4 或下载 zip，再点「重新合成」。`
      : `${asmMsg}${PARTIAL_QUOTA_NOTE}。可先预览分镜或下载 zip，再点「重新合成」（仅拼接，不重生成各镜）。`;
    renderProduceResultPanel(s, seedance, { assembleMessage: asmMsg, engageFocus: true, scope: "active" });
    syncProduceAssetsUi({ ...(state.lastPreview || {}), slug: s, seedance });
    showSeedanceProgress(true, {
      status: friendly,
      percent: 90,
      pipeline: seedance?.pipeline || state.healthCache?.seedance?.label || "",
      persist: true,
    });
    setScriptActionStatus(friendly, { forceDock: true });
    updateLoopBarFromForm(state.lastPreview || {});
    activeStudioDock()?.scrollIntoView({ behavior: "smooth", block: "end" });
    return "partial";
  }
  const lp = state.lastPreview || {};
  const sd = seedance || lp.seedance;
  if (s && shotAssetsReady(sd)) {
    return renderProduceOutcome(s, sd, { message, assemble, failed: false });
  }
  showVideoGenError(message || state.lastVideoGenError || "视频生成未成功，请查看错误说明");
  syncProduceAssetsUi(lp);
  return "error";
}

async function runStartCreate() {
  const ps = document.getElementById("scriptProductSelect");
  if (ps?.value) {
    state.selectedProductId = ps.value;
    await refreshScriptPreview();
  }
  if (!tagsSelectionOk()) {
    setScriptActionStatus("请先配置产品、人群、场景、卖点与痛点。", { forceDock: true });
    await openProductFloatPanel();
    return;
  }
  const linkId = Number(document.getElementById("scriptMaterialSelect")?.value || state.selectedMaterialId);
  if (!linkId) {
    setScriptActionStatus("请先选择同品类爆款对标，用来迁移镜头节奏和结构。", { forceDock: true });
    openRefFloatPanel();
    return;
  }

  const prev = state.lastPreview || {};
  const isGenerateMode = state.view === "generate" && state.generateDockMode === "generate";
  if (isGenerateMode && scriptNeedsRegenerate(prev)) {
    const brief = getImitationPrompt();
    const picked = Boolean(state.generatePromptSelection?.text || state.generatePromptSelection?.id);
    if (!brief && !picked) {
      setScriptActionStatus("请先选择或填写创作提示词（点「提示词选择」），再开始生成。", { isError: true, forceDock: true });
      openPromptSelectFloatPanel();
      return;
    }
  }

  forEachDockRunBtn((runBtn) => {
    runBtn.disabled = true;
    runBtn.dataset.busy = "1";
    runBtn.innerHTML = '<span class="dock-run-icon">✦</span> 创作中…';
  });
  state.createPipelineActive = true;
  state.dockFocusDismissed = false;
  beginAutomatedPipelineUi();
  activeStudioDock()?.scrollIntoView({ behavior: "smooth", block: "end" });
  showSeedanceProgress(true, { status: "准备创作…", indeterminate: true });

  try {
    if (scriptNeedsRegenerate(prev)) {
      await runScriptGenerate();
      if (!currentScriptSlug() && !state.lastPreview?.has_script) return;
      openScriptFloatPanel();
      return;
    }
    refreshScriptFloatFromPreview(prev);
    const slug = currentScriptSlug();
    const finalReady = Boolean(prev?.seedance?.final_video?.ready);
    const seedanceOk = Boolean(state.healthCache?.seedance?.configured);
    const videoQ = state.healthCache?.production?.daily_video_quota;
    const videoBlocked = videoQ?.enabled && videoQ.remaining <= 0;

    if (slug && seedanceOk && !finalReady && !videoBlocked) {
      setScriptActionStatus("脚本已就绪，继续生成成片…", { forceDock: true });
      closeScriptFloatPanel();
      const queueLabel = `${slug} · ${currentProductLabel() || "成片"}`;
      await withVideoProductionQueue(slug, queueLabel, () => runProduceVideo({ background: true }));
      await refreshScriptPreview();
      return;
    }
    if (slug && !seedanceOk && !finalReady) {
      setScriptActionStatus(
        "脚本已就绪。请先在 overseas-loc-mvp/.env 配置 SeedDance 密钥，再点脚本浮层内「确认生成视频」。",
        { forceDock: true },
      );
    }
    openScriptFloatPanel();
  } finally {
    state.createPipelineActive = false;
    hideSeedanceProgressIfIdle();
    forEachDockRunBtn((runBtn) => {
      delete runBtn.dataset.busy;
      runBtn.disabled = false;
      runBtn.innerHTML = dockRunDefaultHtml(runBtn.id === "imitateDockRun" ? "imitate" : "generate");
    });
    syncFinishButton(Boolean(state.lastPreview?.can_finish), Boolean(state.lastPreview?.delivery_ready));
  }
}

function shouldUseDockOnlyProduceFeedback() {
  return state.view === "imitate"
    || state.view === "generate"
    || isAutomatedPipelineUi()
    || Boolean(state.createPipelineActive || state.viralPipelineBusy);
}

function renderDockProduceComplete(slug, message) {
  const msg = message || "视频生成完成，可下载 zip 或预览成片";
  hideProduceCompleteBanner();
  clearVideoGenErrorUi();
  setSeedanceVideoComplete(true, slug);
  setScriptActionStatus(msg, { forceDock: true });
  resetSeedanceProgressDock();
  renderProduceResultPanel(slug, state.lastPreview?.seedance, { engageFocus: true, scope: "active" });
  syncDownloadLinks(`/api/delivery/${encodeURIComponent(slug)}/zip`, true);
  document.querySelectorAll("#scriptDownloadBtnBottom, .js-script-download").forEach((dl) => {
    dl.textContent = produceZipLabel(state.lastPreview?.seedance);
  });
  if (!shouldUseDockOnlyProduceFeedback()) {
    showProduceCompleteModal("成片已就绪", msg, slug, state.lastPreview?.seedance);
  }
  state.dockFocusDismissed = false;
  syncStudioFocusMode();
}

function setSeedanceVideoComplete(complete, slug) {
  state.seedanceVideoComplete = Boolean(complete);
  const s = slug || currentScriptSlug() || state.lastPreview?.slug;
  if (s && produceDownloadReady(state.lastPreview)) {
    syncProduceAssetsUi(state.lastPreview);
  } else if (!complete && !state.producePartialReady) {
    syncDownloadLinks("", false);
  }
  updateLoopBarFromForm(state.lastPreview || {});
}

async function runConfirmProduceVideo() {
  const produceBtn = document.getElementById("scriptFloatProduceBtn");
  if (produceBtn?.disabled) {
    const tip = produceBtn.title || "当前无法生成视频，请检查今日成片配额或 SeedDance 配置";
    showVideoGenError(tip);
    return;
  }

  let slug = currentScriptSlug();
  const linkId = Number(document.getElementById("scriptMaterialSelect")?.value || state.selectedMaterialId);
  if (!slug && linkId) {
    slug = slugFor(linkId);
    state.scriptSlug = slug;
  }
  if (!slug) {
    showVideoGenError("请先生成脚本");
    return;
  }

  const videoQ = state.healthCache?.production?.daily_video_quota;
  if (videoQ?.enabled && videoQ.remaining <= 0) {
    showVideoGenError(`今日成片产出配额已用完（${videoQ.used}/${videoQ.limit}），请明日再试`);
    return;
  }

  if (scriptEditsDirty()) {
    const saved = await saveScriptEditsIfDirty();
    if (!saved) {
      showVideoGenError("保存脚本修改失败，无法开始生成视频");
      openScriptFloatPanel();
      return;
    }
  }

  clearVideoGenErrorUi();
  state.seedanceProgressPersist = false;
  state.producePartialReady = false;
  state.dockFocusDismissed = false;
  syncDockReassembleButton(null, null);
  setSeedanceVideoComplete(false);
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
  beginAutomatedPipelineUi();
  showSeedanceProgress(true, {
    status: "正在启动视频生成流水线…",
    indeterminate: true,
    pipeline: state.healthCache?.seedance?.label || "",
  });
  setScriptActionStatus("正在启动：交付包 → AI 分镜视频 → 拼接成片（约 15–30 分钟）…", { forceDock: true });
  activeStudioDock()?.scrollIntoView({ behavior: "smooth", block: "end" });

  try {
    const queueLabel = `${slug} · ${currentProductLabel() || "成片"}`;
    await withVideoProductionQueue(slug, queueLabel, () => runProduceVideo({
      background: true,
      skipScriptSave: true,
    }));
    await refreshScriptPreview();
    updateLoopBarFromForm(state.lastPreview || {});
  } catch (err) {
    await refreshScriptPreview();
    const lp = state.lastPreview || {};
    if (produceDownloadReady(lp)) {
      renderProduceOutcome(currentScriptSlug(), lp.seedance, {
        message: err.message,
        failed: !shotAssetsReady(lp.seedance),
      });
    } else {
      showVideoGenError(`视频生成失败：${err.message}`);
    }
  } finally {
    state.createPipelineActive = false;
    if (!state.seedanceProgressPersist) {
      resetSeedanceProgressDock();
    } else {
      state.videoGenActive = false;
      state.scriptGenActive = false;
    }
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
    syncDockRunButtonsDisabled();
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
    document.getElementById("loopHint")?.classList.remove("hidden");
  }
  updateLoopBarFromForm(prev);
  syncProduceAssetsUi(prev);
}

function isScriptFloatPanelOpen() {
  const panel = document.getElementById("scriptFloatPanel");
  return Boolean(panel?.classList.contains("open"));
}

function videoOutputHint(slug) {
  const s = slug || currentScriptSlug() || state.lastPreview?.slug;
  if (!s) return "";
  return `服务器路径：overseas-loc-mvp/runs/${s}/broll/final-video.mp4 · 归档：03_产出库/${s}/`;
}

function friendlyApiErrorMessage(msg, path = "") {
  const text = String(msg || "").trim();
  if (!text || text === "Internal Server Error") {
    const busy = state.videoGenActive || state.createPipelineActive;
    if (busy) {
      return "服务繁忙：正在生成交付或视频，请稍候勿重复点击；完成后刷新页面查看成片。";
    }
    return "服务器内部错误：请重启「启动工作台.cmd」后重试；若仍失败请检查 overseas-loc-mvp/.env 中 ARK_API_KEY 与 ffmpeg。";
  }
  return text;
}

function mirrorStatusToDock(msg) {
  if (!msg) return;
  for (const id of ["seedanceProgressStatus", "imitateSeedanceProgressStatus"]) {
    const el = document.getElementById(id);
    if (el) el.textContent = msg;
  }
}

function ensureClientId() {
  if (state.clientId) return state.clientId;
  let id = "";
  try {
    id = sessionStorage.getItem("wb_client_id") || "";
  } catch {
    id = "";
  }
  if (!id) {
    id = Math.random().toString(36).slice(2, 10);
    try {
      sessionStorage.setItem("wb_client_id", id);
    } catch {
      /* ignore */
    }
  }
  state.clientId = id;
  return id;
}

function formatQueueDuration(sec) {
  const s = Math.max(0, Math.round(Number(sec) || 0));
  if (s < 60) return `约 ${s} 秒`;
  const m = Math.ceil(s / 60);
  if (m < 60) return `约 ${m} 分钟`;
  return `约 ${Math.floor(m / 60)} 小时 ${m % 60} 分`;
}

function queueStatusLabel(row) {
  const st = row?.status || "";
  if (st === "running") return `生成中 · 剩余 ${formatQueueDuration(row.remain_sec)}`;
  if (st === "active") return "轮到您";
  if (st === "queued") return `排队 · ${formatQueueDuration(row.wait_sec)}`;
  if (st === "done") return "已完成";
  if (st === "cancelled") return "已取消";
  if (st === "error") return "失败";
  return st || "—";
}

function shouldShowVideoQueuePanel(joined) {
  const items = joined?.queue?.items || joined?.items || [];
  if (items.length > 1) return true;
  const pos = Number(joined?.position ?? 0);
  return pos > 0;
}

function showVideoQueuePanel(show) {
  document.getElementById("videoQueuePanel")?.classList.toggle("hidden", !show);
}

function renderVideoQueuePanel(queue, mine) {
  const myStatus = document.getElementById("videoQueueMyStatus");
  const eta = document.getElementById("videoQueueEta");
  const list = document.getElementById("videoQueueList");
  const cancelBtn = document.getElementById("videoQueueCancelBtn");
  if (!list) return;
  const items = queue?.items || [];
  if (mine && myStatus) {
    if (mine.status === "active" || mine.status === "running") {
      myStatus.textContent = mine.status === "running" ? "正在生成您的成片…" : "轮到您了，即将开始生成";
    } else {
      myStatus.textContent = `您排在第 ${Math.max(1, (mine.position ?? 0) + 1)} 位`;
    }
  }
  if (eta && mine) {
    if (mine.status === "running") {
      eta.textContent = `本单预计剩余 ${formatQueueDuration(mine.remain_sec)}`;
    } else if ((mine.position ?? 0) > 0) {
      eta.textContent = `预计等待 ${formatQueueDuration(mine.wait_sec)}（按每单约 18 分钟估算）`;
    } else {
      eta.textContent = "即将开始，请勿关闭页面";
    }
  }
  list.innerHTML = items.map((row) => {
    const isMe = mine && row.ticket_id === mine.ticket_id;
    const cls = [
      "video-queue-item",
      isMe ? "is-me" : "",
      row.status === "running" || row.status === "active" ? "is-active" : "",
    ].filter(Boolean).join(" ");
    return `<li class="${cls}">
      <span class="video-queue-item-label">${esc(row.label || row.slug || "成片")}</span>
      <span class="video-queue-item-meta">${esc(row.client_label || "协作者")}</span>
      <span class="video-queue-item-status">${esc(queueStatusLabel(row))}</span>
    </li>`;
  }).join("") || '<li class="video-queue-item"><span class="video-queue-item-label muted">队列为空</span></li>';
  if (cancelBtn) {
    const canCancel = mine && ["queued", "active", "running"].includes(mine.status);
    cancelBtn.classList.toggle("hidden", !canCancel);
    cancelBtn.textContent = mine?.status === "running" ? "取消生成" : "取消排队";
  }
}

function isAbortError(err) {
  return err?.name === "AbortError" || String(err?.message || "").includes("已取消");
}

function beginVideoProductionAbort() {
  if (state.videoProductionAbort) {
    try {
      state.videoProductionAbort.abort();
    } catch {
      /* ignore */
    }
  }
  state.videoProductionAbort = new AbortController();
  return state.videoProductionAbort;
}

function abortVideoProduction() {
  if (state.videoProductionAbort) {
    try {
      state.videoProductionAbort.abort();
    } catch {
      /* ignore */
    }
    state.videoProductionAbort = null;
  }
  state.videoGenActive = false;
  state.createPipelineActive = false;
}

function beginScriptGenerationAbort() {
  if (state.scriptGenerationAbort) {
    try {
      state.scriptGenerationAbort.abort();
    } catch {
      /* ignore */
    }
  }
  state.scriptGenerationAbort = new AbortController();
  return state.scriptGenerationAbort;
}

function abortScriptGeneration() {
  if (state.scriptGenerationAbort) {
    try {
      state.scriptGenerationAbort.abort();
    } catch {
      /* ignore */
    }
    state.scriptGenerationAbort = null;
  }
  state.scriptGenActive = false;
}

function scriptGenerationSignal() {
  return state.scriptGenerationAbort?.signal;
}

function syncPipelineStopButtons() {
  const busy = state.scriptGenActive
    || state.videoGenActive
    || state.createPipelineActive
    || state.viralPipelineBusy;
  const label = state.scriptGenActive && !state.videoGenActive ? "停止脚本" : "停止生成";
  document.querySelectorAll(".pipeline-stop-btn").forEach((btn) => {
    btn.classList.toggle("hidden", !busy);
    btn.textContent = label;
    btn.title = "停止当前脚本请求/排队；若 SeedDance 已进入单镜生成，服务端可能会在当前镜完成后释放。";
    btn.disabled = false;
  });
}

function restorePipelineUiAfterCancel() {
  state.createPipelineActive = false;
  state.viralPipelineBusy = false;
  state.awaitingHeroConfirm = false;
  state.heroConfirmThenProduce = false;
  forEachDockRunBtn((runBtn) => {
    delete runBtn.dataset.busy;
    runBtn.disabled = false;
    runBtn.innerHTML = dockRunDefaultHtml(runBtn.id === "imitateDockRun" ? "imitate" : "generate");
  });
  const regenBtn = document.getElementById("scriptFloatRegenBtn");
  if (regenBtn) {
    regenBtn.disabled = false;
    delete regenBtn.dataset.busy;
    regenBtn.textContent = "重新生成脚本";
  }
  const produceBtn = document.getElementById("scriptFloatProduceBtn");
  if (produceBtn) {
    produceBtn.disabled = false;
    delete produceBtn.dataset.busy;
    produceBtn.textContent = "确认生成视频";
  }
  document.querySelectorAll(".js-script-generate").forEach((b) => { b.disabled = false; });
  syncDockRunButtonsDisabled();
  syncFinishButton(Boolean(state.lastPreview?.can_finish), Boolean(state.lastPreview?.delivery_ready));
  syncPipelineStopButtons();
}

async function cancelActivePipelineGeneration() {
  const wasScript = state.scriptGenActive;
  const wasVideo = state.videoGenActive;
  const ticket = state.videoQueueTicket;
  const wasRunning = wasVideo && Boolean(ticket);

  abortScriptGeneration();
  abortVideoProduction();
  stopVideoQueuePoll();

  document.querySelectorAll(".pipeline-stop-btn").forEach((btn) => { btn.disabled = true; });

  if (ticket) {
    try {
      await api(`/api/video-queue/${encodeURIComponent(ticket)}?client_id=${encodeURIComponent(ensureClientId())}`, {
        method: "DELETE",
      });
    } catch (err) {
      if (!isAbortError(err)) {
        /* queue may already be gone */
      }
    }
    state.videoQueueTicket = null;
    showVideoQueuePanel(false);
  }

  showScriptProgress(false);
  resetSeedanceProgressDock();
  restorePipelineUiAfterCancel();

  let msg = "已停止";
  if (wasScript && wasVideo) msg = "已停止脚本与视频生成";
  else if (wasScript) msg = "已停止脚本生成，可修改标签或提示词后重试";
  else if (wasRunning) msg = "已请求停止视频生成；若单镜已进入 SeedDance 生成，会在当前请求结束后释放";
  else if (wasVideo) msg = "已取消排队";
  setScriptActionStatus(msg, { forceDock: true });
}

function videoProductionSignal() {
  return state.videoProductionAbort?.signal;
}

function stopVideoQueuePoll() {
  if (state.videoQueuePoll) {
    clearInterval(state.videoQueuePoll);
    state.videoQueuePoll = null;
  }
}

function waitVideoQueueTurn(ticketId, signal) {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException("已取消", "AbortError"));
      return;
    }
    const onAbort = () => {
      stopVideoQueuePoll();
      reject(new DOMException("已取消", "AbortError"));
    };
    signal?.addEventListener("abort", onAbort, { once: true });
    const finish = (fn) => {
      signal?.removeEventListener("abort", onAbort);
      fn();
    };
    const poll = async () => {
      if (signal?.aborted) {
        stopVideoQueuePoll();
        finish(() => reject(new DOMException("已取消", "AbortError")));
        return;
      }
      try {
        const row = await api(`/api/video-queue?ticket=${encodeURIComponent(ticketId)}`, { signal });
        renderVideoQueuePanel(row.queue, row);
        if (row.status === "cancelled") {
          stopVideoQueuePoll();
          finish(() => reject(new Error(row.message || "排队已取消")));
          return;
        }
        if (row.status === "active" || row.status === "running") {
          stopVideoQueuePoll();
          showSeedanceProgress(true, {
            status: row.status === "running" ? "正在生成成片…" : "轮到您了，正在启动生成…",
            indeterminate: true,
            persist: true,
          });
          finish(() => resolve(row));
          return;
        }
        const pos = Math.max(1, (row.position ?? 0) + 1);
        const waitLabel = formatQueueDuration(row.wait_sec);
        setScriptActionStatus(`排队中：第 ${pos} 位，预计 ${waitLabel}`, { forceDock: true });
        showSeedanceProgress(true, {
          status: `排队中（第 ${pos} 位）· 预计 ${waitLabel}`,
          indeterminate: true,
          persist: true,
        });
      } catch (err) {
        stopVideoQueuePoll();
        finish(() => reject(err));
      }
    };
    stopVideoQueuePoll();
    state.videoQueuePoll = setInterval(poll, 2500);
    poll();
  });
}

async function releaseVideoQueue(ticketId, ok, message = "") {
  if (!ticketId) return;
  try {
    const row = await api(`/api/video-queue?ticket=${encodeURIComponent(ticketId)}`);
    if (!row || !["queued", "active", "running"].includes(row.status)) return;
    await api(`/api/video-queue/${encodeURIComponent(ticketId)}/complete`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ok: Boolean(ok), message, client_id: ensureClientId() }),
    });
  } catch {
    /* ignore */
  }
}

async function withVideoProductionQueue(slug, label, fn) {
  const ac = beginVideoProductionAbort();
  let ticketId = null;
  let ok = false;
  try {
    const joined = await api("/api/video-queue/join", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ slug, label, client_id: ensureClientId() }),
      signal: ac.signal,
    });
    ticketId = joined.ticket_id;
    state.videoQueueTicket = ticketId;
    if (shouldShowVideoQueuePanel(joined)) showVideoQueuePanel(true);
    renderVideoQueuePanel(joined.queue, joined);
    await waitVideoQueueTurn(ticketId, ac.signal);
    ok = Boolean(await fn());
    return ok;
  } catch (err) {
    if (isAbortError(err)) return false;
    throw err;
  } finally {
    stopVideoQueuePoll();
    await releaseVideoQueue(ticketId, ok);
    state.videoQueueTicket = null;
    state.videoProductionAbort = null;
    if (!state.videoGenActive && !state.createPipelineActive) showVideoQueuePanel(false);
  }
}

function clearVideoGenErrorOnly() {
  state.lastVideoGenError = "";
  const statusEl = document.getElementById("scriptActionStatus");
  if (statusEl) statusEl.classList.remove("script-action-error");
  for (const ids of SEEDANCE_PROGRESS_TARGETS) {
    document.getElementById(ids.bar)?.classList.remove("seedance-progress-error");
  }
  document.getElementById("videoGenErrorBanner")?.classList.add("hidden");
}

function clearVideoGenErrorUi() {
  clearVideoGenErrorOnly();
  hideProduceCompleteBanner();
  hideProduceCompleteModal();
}

/** 视频生成失败：顶部横幅 + 底部进度条 + 脚本浮层同时展示，避免静默无反馈 */
function showVideoGenError(msg, { openPanel = true, scrollDock = true } = {}) {
  const text = friendlyApiErrorMessage(msg);
  const lp = state.lastPreview || {};
  if (produceDownloadReady(lp)) {
    const s = currentScriptSlug() || lp.slug;
    renderProduceOutcome(s, lp.seedance, {
      message: text,
      failed: !shotAssetsReady(lp.seedance),
    });
    return;
  }
  state.lastVideoGenError = text;
  state.seedanceProgressPersist = true;
  state.videoGenActive = false;
  state.createPipelineActive = false;
  hideProduceCompleteModal();
  hideProduceCompleteBanner();

  const banner = document.getElementById("videoGenErrorBanner");
  const bannerText = document.getElementById("videoGenErrorBannerText");
  if (banner && bannerText) {
    bannerText.textContent = text;
    banner.classList.remove("hidden");
  }

  const statusEl = document.getElementById("scriptActionStatus");
  if (statusEl) {
    statusEl.textContent = text;
    statusEl.classList.add("script-action-error");
  }

  mirrorStatusToDock(text);
  for (const ids of SEEDANCE_PROGRESS_TARGETS) {
    const bar = document.getElementById(ids.bar);
    const fill = document.getElementById(ids.fill);
    const st = document.getElementById(ids.status);
    if (bar) {
      bar.classList.remove("hidden");
      bar.classList.add("seedance-progress-error");
      const labelEl = bar.querySelector(".seedance-progress-label");
      if (labelEl) labelEl.textContent = "生成失败";
    }
    if (st) st.textContent = text;
    if (fill) {
      fill.classList.remove("indeterminate");
      fill.style.width = "0%";
    }
  }
  stopSeedanceCountdown();
  syncDockScrollPadding();
  if (scrollDock) activeStudioDock()?.scrollIntoView({ behavior: "smooth", block: "end" });
  if (openPanel) openScriptFloatPanel();
  else syncProduceAssetsUi(state.lastPreview || {});
  syncStudioFocusMode();
}

function setScriptActionStatus(msg, { forceDock = false, isError = false } = {}) {
  const text = String(msg || "").trim();
  const el = document.getElementById("scriptActionStatus");
  const keepErrorStyle = isError || Boolean(text && state.lastVideoGenError && text === state.lastVideoGenError);
  if (el) {
    el.textContent = text;
    if (keepErrorStyle) el.classList.add("script-action-error");
    else if (text) el.classList.remove("script-action-error");
  }
  if (!text) return;
  if (forceDock || !isScriptFloatPanelOpen()) {
    mirrorStatusToDock(text);
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
  return produceDownloadReady(prev);
}

function syncScriptDownloadZip(prev = state.lastPreview || {}) {
  syncProduceAssetsUi(prev);
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
  refreshScriptFloatPersonalization();
}

function tagsSelectionOk() {
  const sel = readAllSelectedTags();
  return sel.audience.length > 0 && sel.scenarios.length > 0
    && sel.selling.length > 0 && sel.pains.length > 0;
}

function applyDefaultProductTags() {
  const productId = document.getElementById("scriptProductSelect")?.value;
  if (!productId) {
    setScriptActionStatus("请先选择产品");
    return;
  }
  const p = state.products.find((x) => x.product_id === productId) || {};
  const pool = buildTagPool(p, p.delivery_tags || state.lastPreview?.delivery_tags);
  const selected = defaultSelectedTags(pool, {});
  state.tagSelection = {
    audience: [...selected.audience].slice(0, 1),
    scenarios: [...selected.scenarios].slice(0, 1),
    selling: [...selected.selling],
    pains: [...selected.pains],
  };
  state.selectedAudience = state.tagSelection.audience;
  state.selectedScenarios = state.tagSelection.scenarios;
  refreshTagGroupsUI();
  syncProductFloatStatus();
  syncDockProductSlot();
  syncDockRefSlot();
  syncReverseDockProduct();
  updateLoopBarFromForm(state.lastPreview || {});
  syncDockPromptFromScenarioTags();
  refreshScriptFloatPersonalization();
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
  if (!document.getElementById("scriptProductSelect")?.value || !tagsSelectionOk()) {
    void openProductFloatPanel();
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

function radarVideoCardHtml(item) {
  const active = item.link_id === state.selectedMaterialId ? " selected" : "";
  const thumb = item.thumbnail_url
    ? `<img class="viral-video-thumb" src="${esc(item.thumbnail_url)}" alt="">`
    : `<span class="feature-card-bg g-video-rev"></span>`;
  const title = (item.title || "").trim().slice(0, 28) || `#${item.link_id}`;
  const score = item.radar_score != null ? Number(item.radar_score).toFixed(0) : "—";
  const tags = (item.radar_tags || []).slice(0, 3).map((t) => `<span class="radar-tag">${esc(t)}</span>`).join("");
  const why = esc((item.why_pick || "").slice(0, 64));
  return `<div class="radar-card-wrap">
    <button type="button" class="feature-card viral-video-card radar-video-card${active}" data-link-id="${item.link_id}" data-radar-card="1">
      ${thumb}
      <span class="radar-score-badge" title="雷达综合分">${score}</span>
      <span class="feature-card-label"><strong>${esc(title)}</strong><span class="radar-why-pick">${why}</span></span>
      <span class="radar-tag-row">${tags}</span>
    </button>
    <button type="button" class="btn-text radar-reverse-btn" data-radar-reverse="${item.link_id}" title="反推结构到提示词库">反推</button>
  </div>`;
}

function bindRadarCards(root) {
  if (!root) return;
  root.querySelectorAll(".radar-video-card[data-link-id]").forEach((card) => {
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
  root.querySelectorAll("[data-radar-reverse]").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const linkId = Number(btn.dataset.radarReverse);
      state.reverseMaterialId = linkId;
      state.selectedMaterialId = linkId;
      syncReverseDockMaterial();
      if (!currentProductId()) {
        await openProductFloatPanel();
        return;
      }
      switchView("reverse");
      document.getElementById("reverseDock")?.scrollIntoView({ behavior: "smooth", block: "end" });
    });
  });
}

async function renderRadarGrid(gridId, descId) {
  const root = document.getElementById(gridId);
  const desc = document.getElementById(descId);
  if (!root) return;
  const productId = currentProductId();
  if (!productId) {
    if (desc) desc.textContent = "请先在底部配置「产品」与场景标签，雷达将按品类推荐值得跟拍的爆款。";
    root.innerHTML = '<p class="muted module-feature-empty">配置产品后显示雷达推荐</p>';
    return;
  }
  root.innerHTML = '<p class="muted">雷达扫描中…</p>';
  try {
    const data = await api(`/api/radar/feed?product_id=${encodeURIComponent(productId)}&limit=12`);
    const items = data.items || [];
    if (desc) {
      desc.textContent = items.length
        ? `综合播放、互动与结构拆解，为「${currentProductLabel()}」推荐 ${items.length} 条选题（CreatOK 式雷达）`
        : `当前产品暂无已拆解对标，请先在设置同步 TikTok 或打开「对标」浏览`;
    }
    if (!items.length) {
      root.innerHTML = '<p class="muted module-feature-empty">暂无雷达推荐，请先同步并拆解同品类素材。</p>';
      return;
    }
    root.classList.add("has-viral-videos");
    root.innerHTML = items.map((item) => radarVideoCardHtml(item)).join("");
    bindRadarCards(root);
  } catch (err) {
    root.innerHTML = `<p class="muted">雷达加载失败：${esc(friendlyApiErrorMessage(err.message))}</p>`;
  }
}

function renderAllRadarGrids() {
  renderRadarGrid("generateRadarGrid", "generateRadarDesc");
  renderRadarGrid("imitateRadarGrid", "imitateRadarDesc");
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
  renderAllRadarGrids();
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
  const videoQ = state.healthCache?.production?.daily_video_quota;
  if (videoQ?.enabled && videoQ.remaining <= 0) {
    setScriptActionStatus("今日成片产出配额已满，无法一键出片。明日再试或调高 DAILY_VIDEO_QUOTA。", { isError: true });
    return;
  }
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
  state.dockFocusDismissed = false;
  beginAutomatedPipelineUi();
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
    const scriptOk = await runScriptGenerate();
    if (!scriptOk) {
      setScriptActionStatus("脚本生成失败，请检查产品标签与 API 配置", { isError: true });
      showSeedanceProgress(true, { status: "脚本生成失败", persist: true });
      return;
    }
    await refreshScriptPreview();

    if (!state.lastPreview?.has_script && !currentScriptSlug()) {
      setScriptActionStatus("脚本生成失败，请检查产品标签与 API 配置");
      showSeedanceProgress(true, { status: "脚本生成失败", persist: true });
      return;
    }

    const slug = currentScriptSlug();
    const queueLabel = `${slug || "ref"} · 对标流水线`;
    await (slug
      ? withVideoProductionQueue(slug, queueLabel, () => runProduceVideo({ background: true }))
      : runProduceVideo({ background: true }));
    await refreshScriptPreview();
  } catch (err) {
    stopSeedanceCountdown();
    if (isAbortError(err)) {
      setScriptActionStatus("已取消生成", { forceDock: true });
      resetSeedanceProgressDock();
      return;
    }
    showVideoGenError(err.message);
  } finally {
    state.viralPipelineBusy = false;
    state.createPipelineActive = false;
    if (!state.seedanceProgressPersist) {
      resetSeedanceProgressDock();
    } else {
      state.videoGenActive = false;
      state.scriptGenActive = false;
    }
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
  if (tab === "audit") {
    switchDraftFeedbackSub("feedback");
    document.getElementById("draftFeedbackBody")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }
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
  state.generateDockMode = mode || "generate";
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
      ? "① 产品场景 → ② 提示词模板/创作要求 → ③ 对标爆款节奏 → ④ 开始创作"
      : "① 点击「产品」配置场景标签 → ② 点击上方爆款卡片（自动拆解+出片）或底部「开始创作」";
  }
  syncDockPromptSelectSlot();
  syncProducePreviewForActiveView();
  syncDockScrollPadding();
  syncWorkflowGuide();
}

function syncDockPromptSelectSlot() {
  const btn = document.getElementById("dockOpenPromptSelectBtn");
  if (!btn) return;
  const sel = state.generatePromptSelection;
  const promptText = document.getElementById("generateDockPrompt")?.value?.trim() || "";
  const hasText = Boolean(sel?.text || promptText);
  btn.classList.toggle("has-value", hasText);
  btn.title = sel?.label ? `已选：${sel.label}` : (hasText ? "已填写创作提示词，点击更换" : "选择创作提示词模板");
  syncWorkflowGuide();
}

async function renderPromptSelectList() {
  const root = document.getElementById("promptSelectList");
  if (!root) return;
  root.innerHTML = '<p class="muted">加载提示词…</p>';
  const items = [];
  try {
    const productId = currentProductId() || "";
    const qs = new URLSearchParams({ for_selection: "1" });
    if (productId) qs.set("product_id", productId);
    const lib = await api(`/api/prompt-library?${qs.toString()}`);
    for (const row of lib.presets || []) {
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
    for (const row of lib.approved_scripts || []) {
      const text = row.prompt_text || row.prompt_text_en || "";
      if (!text) continue;
      const usage = Number(row.usage_count) || 0;
      items.push({
        id: `approved-${row.prompt_id}`,
        promptId: row.prompt_id,
        label: row.label || "已审核成稿",
        sub: row.sub || `成稿脚本 · 使用 ${usage} 次`,
        text,
        kind: "approved",
        usageCount: usage,
        sortOrder: 20,
      });
    }
  } catch {
    /* fall through */
  }
  items.sort((a, b) => {
    const order = { preset: 0, approved: 1 };
    const ao = order[a.kind] ?? 9;
    const bo = order[b.kind] ?? 9;
    if (ao !== bo) return ao - bo;
    if (a.kind === "preset") return (a.sortOrder || 99) - (b.sortOrder || 99);
    if (a.kind === "approved") return (b.usageCount || 0) - (a.usageCount || 0);
    return 0;
  });
  if (!items.length) {
    root.innerHTML = '<p class="muted">暂无可用提示词。内置模板将自动加载；自生成脚本需在成稿反馈中标记「已采纳」后才会出现在此。</p>';
    return;
  }
  const activeId = state.generatePromptSelection?.id || "";
  const cardGrad = (kind) => {
    if (kind === "approved") return "g-brand";
    if (kind === "preset") return "g-template";
    return "g-bedroom";
  };
  root.innerHTML = items.map((item, idx) => `
    <button type="button" class="feature-card prompt-select-card${activeId === item.id ? " selected" : ""}${item.kind === "approved" ? " prompt-approved-card" : ""}"
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
    if (!currentProductId() && !item) {
      chip.textContent = "请先点「产品」配置，以便过滤素材与提示词库";
    } else if (item) {
      chip.textContent = `已选 #${linkId} · ${reverseType === "script" ? "脚本" : "视频"}反推`;
    } else {
      chip.textContent = "拆解 · 反推入库";
    }
  }
}

function syncReverseDockProduct() {
  const btn = document.getElementById("reverseDockProductBtn");
  const label = document.getElementById("reverseDockProductLabel");
  if (!btn || !label) return;
  const ps = document.getElementById("scriptProductSelect");
  const productName = ps?.selectedOptions?.[0]?.textContent?.trim() || "";
  const ready = Boolean(ps?.value);
  btn.classList.toggle("has-value", ready);
  label.textContent = ready && productName ? productName.slice(0, 8) : "产品";
  btn.title = ready && productName ? `已选：${productName}` : "选择产品以过滤素材与提示词库";
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
  syncReverseDockProduct();
  renderReversePromptLibrary();
  if (!currentProductId()) {
    const chip = document.getElementById("reverseDockStatusChip");
    if (chip && !state.reverseMaterialId) {
      chip.textContent = "请先点「产品」配置，以便过滤素材与提示词库";
    }
  }
}

async function runReversePrompt() {
  const linkId = state.reverseMaterialId;
  if (!linkId) {
    window.alert("请先从素材库选择对标视频");
    openMaterialLibraryDrawer();
    return;
  }
  if (!currentProductId()) {
    window.alert("请先点底部「产品」选择商品，以便按品类过滤提示词库");
    await openProductFloatPanel();
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
  if (item) {
    if (item.content_line) state.selectedProductId = item.content_line;
    await selectMaterial(item.link_id, { loadDetail: false });
    repopulateScriptMaterials();
    syncMaterialSelectFromState();
  }
  state.scriptSlug = slug;
  const targetView = state.view === "imitate" ? "imitate" : "generate";
  switchView(targetView);
  if (targetView === "generate") syncGenerateDockMode("generate");
  await refreshScriptPreview();
  refreshScriptFloatFromPreview(state.lastPreview || {});
  openScriptFloatPanel();
  setScriptActionStatus(`已打开成稿 ${slug}，可继续预览脚本或下载成片。`);
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
      await selectMaterial(Number(btn.dataset.linkId), { fromRefFloat: true });
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

function initDockToolbarMobileMore() {
  document.querySelectorAll(".studio-dock-toolbar").forEach((toolbar) => {
    const more = toolbar.querySelector(".dock-toolbar-more-btn");
    if (!more || toolbar.dataset.mobileMoreInit) return;
    toolbar.dataset.mobileMoreInit = "1";
    more.addEventListener("click", () => {
      const open = toolbar.classList.toggle("dock-toolbar-more-open");
      more.setAttribute("aria-expanded", open ? "true" : "false");
    });
  });
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
      switchView("imitate");
      document.getElementById("imitateDock")?.scrollIntoView({ behavior: "smooth", block: "end" });
    });
  document.querySelector('#generateDock .studio-dock-modes [data-gen-mode="generate"]')
    ?.addEventListener("click", () => openGenerateModule());
  document.getElementById("generateDockRun")?.addEventListener("click", () => runStartCreate());
  document.getElementById("imitateDockRun")?.addEventListener("click", () => runStartCreate());
  function workflowGuideAction(fn) {
    return () => {
      closeWorkflowGuidePanel();
      fn();
    };
  }
  document.getElementById("workflowPickProductBtn")?.addEventListener("click", workflowGuideAction(() => openProductFloatPanel()));
  document.getElementById("workflowPickPromptBtn")?.addEventListener("click", workflowGuideAction(() => openPromptSelectFloatPanel()));
  document.getElementById("workflowPickRefBtn")?.addEventListener("click", workflowGuideAction(() => openRefFloatPanel()));
  document.getElementById("workflowStartBtn")?.addEventListener("click", workflowGuideAction(() => runStartCreate()));
  document.getElementById("dockOpenMaterialsBtn")?.addEventListener("click", () => openRefFloatPanel());
  document.getElementById("imitateOpenMaterialsBtn")?.addEventListener("click", () => openRefFloatPanel());
  document.getElementById("dockOpenProductBtn")?.addEventListener("click", () => openProductFloatPanel());
  document.getElementById("dockOpenPromptSelectBtn")?.addEventListener("click", () => openPromptSelectFloatPanel());
  document.getElementById("promptSelectFloatCloseBtn")?.addEventListener("click", closePromptSelectFloatPanel);
  document.getElementById("promptSelectFloatBackdrop")?.addEventListener("click", closePromptSelectFloatPanel);
  document.getElementById("promptSelectFloatConfirmBtn")?.addEventListener("click", confirmPromptSelectFloatPanel);
  document.getElementById("imitateOpenProductBtn")?.addEventListener("click", () => openProductFloatPanel());
  document.getElementById("reverseDockProductBtn")?.addEventListener("click", () => openProductFloatPanel());
  document.getElementById("productFloatDefaultTagsBtn")?.addEventListener("click", () => applyDefaultProductTags());
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
    saveWorkflowSnapshot();
    const pendingViral = state.pendingViralLinkId;
    state.pendingViralLinkId = null;
    if (pendingViral) {
      await runViralBenchmarkPipeline(pendingViral);
      return;
    }
    if (hadScript && (tagsChanged || productChanged)) {
      await runScriptGenerate();
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
  document.getElementById("scriptFloatProduceBtn")?.addEventListener("click", (e) => {
    e.preventDefault();
    void runConfirmProduceVideo();
  });
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
  syncGenerateDockMode(state.generateDockMode || "generate");
  initDockToolbarMobileMore();
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
    const label = `脚本配额 ${q.used}/${q.limit}`;
    chips.forEach((chip) => {
      chip.classList.remove("hidden", "quota-warn", "quota-full");
      chip.textContent = label;
      chip.title = "今日 LLM 脚本生成次数（非当前任务进度）";
      if (blocked) chip.classList.add("quota-full");
      else if (q.remaining <= 2) chip.classList.add("quota-warn");
    });
  }
  syncDockRunButtonsDisabled();
  syncDockRunButtonLabels();
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
    const label = `成片配额 ${q.used}/${q.limit}`;
    chips.forEach((chip) => {
      chip.classList.remove("hidden", "quota-warn", "quota-full");
      chip.textContent = label;
      chip.title = "今日可完成拼接/导出的成片次数";
      if (blocked) chip.classList.add("quota-full");
      else if (q.remaining <= 2) chip.classList.add("quota-warn");
    });
  }
  syncDockRunButtonsDisabled();
  syncDockRunButtonLabels();
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
  document.querySelectorAll("#generateDockRun, #imitateDockRun").forEach((btn) => {
    btn.disabled = scriptBlocked;
    const view = btn.id === "imitateDockRun" ? "imitate" : "generate";
    btn.title = scriptBlocked
      ? "今日 LLM 脚本配额已满，明日再试或调高 DAILY_SCRIPT_QUOTA"
      : workflowActionTitle(view);
  });
  const produceBtn = document.getElementById("scriptFloatProduceBtn");
  if (produceBtn) {
    produceBtn.disabled = videoBlocked;
    produceBtn.title = videoBlocked
      ? "今日成片产出配额已满，明日再试或调高 DAILY_VIDEO_QUOTA"
      : "按当前脚本生成分镜视频并拼接成片";
  }
  syncWorkflowGuide();
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
  try {
    const forceRaw = localStorage.getItem("vl_seedance_force_regen");
    const forceCb = document.getElementById("seedanceForceRegen");
    if (forceCb && forceRaw != null) forceCb.checked = forceRaw === "1";
  } catch { /* ignore */ }
}

function syncDockVideoSettingsLabel() {
  const vs = currentVideoSettings();
  const text = `${vs.resolution} · ${vs.aspectRatio} · ${vs.durationSec}s`;
  const countText = `脚本变体 ${vs.generateCount}`;
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
  const durationHtml = VIDEO_DURATIONS.map((sec) =>
    `<button type="button" class="dock-settings-pill${sec === vs.durationSec ? " active" : ""}" data-duration-sec="${sec}">${sec}s</button>`
  ).join("");

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
  for (const id of ["dockDurationRow", "imitateDockDurationRow"]) {
    const row = document.getElementById(id);
    if (!row) continue;
    row.innerHTML = durationHtml;
    row.querySelectorAll("[data-duration-sec]").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.videoSettings.durationSec = Number(btn.dataset.durationSec);
        persistVideoSettings();
        renderDockVideoSettingsPanel();
        syncDockVideoSettingsLabel();
      });
    });
  }
  const forceCb = document.getElementById("seedanceForceRegen");
  if (forceCb && !forceCb.dataset.bound) {
    forceCb.dataset.bound = "1";
    forceCb.addEventListener("change", () => {
      try {
        localStorage.setItem("vl_seedance_force_regen", forceCb.checked ? "1" : "0");
      } catch { /* ignore */ }
    });
  }
}

function renderDockGenerateCountMenu() {
  const vs = currentVideoSettings();
  const html = GENERATE_COUNTS.map((n) =>
    `<button type="button" class="dock-gen-count-option${n === vs.generateCount ? " active" : ""}" role="menuitem" data-count="${n}">脚本变体 ${n}</button>`
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
    `画幅 ${vs.aspectRatio} · ${vs.resolution} · 脚本变体 ${vs.generateCount}`,
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
    if (e.key === "Escape") handleGlobalEscapeKey();
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
  const prevView = state.view;
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
    syncGenerateDockMode("generate");
  }
  if (name === "imitate") {
    loadImitateView();
  }
  if (name === "reverse") loadReverseView();
  if (name === "products") loadProductsView();
  if (name === "draft-feedback") {
    const sub = options.sub || state.draftFeedbackSub || "finished";
    switchDraftFeedbackSub(sub);
    renderDraftFeedbackStats();
    renderDraftFeedbackHistory();
  }
  if (prevView !== name) {
    syncDockProductSlot();
    syncDockRefSlot();
    syncDockChipsFromHealth();
    syncProducePreviewForActiveView();
    syncStudioFocusMode();
    syncGlobalPipelineBadge();
    if (name === "generate" || name === "imitate") {
      syncDockRunButtonLabels();
      syncFinishButton(Boolean(state.lastPreview?.can_finish), Boolean(state.lastPreview?.delivery_ready));
    }
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
    } else if (state.scriptStep === "produce" && state.seedanceVideoComplete) {
      hint.textContent = "成片已完成：请在底部工作台点「⬇ 下载成片 zip」，或打开脚本浮层下载。";
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
  const { signal, ...rest } = options;
  const res = await fetch(path, { ...rest, headers, signal });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail;
    let msg = res.statusText || "请求失败";
    if (typeof detail === "string") msg = detail;
    else if (Array.isArray(detail)) {
      msg = detail.map((d) => (typeof d === "string" ? d : d.msg || String(d))).join("；");
    } else if (detail && typeof detail === "object" && detail.msg) {
      msg = detail.msg;
    } else if (detail != null) {
      msg = String(detail);
    }
    throw new Error(friendlyApiErrorMessage(msg, path));
  }
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

function closeTransientWorkspaceChrome(fromView, toView) {
  const leavingWorkspace = fromView === "generate" || fromView === "imitate";
  const enteringWorkspace = toView === "generate" || toView === "imitate";
  if (leavingWorkspace && !enteringWorkspace) {
    closeScriptFloatPanel();
    closeProductFloatPanel();
    closeRefFloatPanel();
    closePromptSelectFloatPanel();
  }
  const busy = state.createPipelineActive || state.videoGenActive || state.scriptGenActive || state.viralPipelineBusy;
  if (busy && fromView !== toView) {
    setScriptActionStatus("任务仍在后台运行，可点顶栏「出片中」徽章定位进度。", { forceDock: false });
  }
}

function switchView(name, options = {}) {
  const prevView = state.view;
  name = normalizeView(name);
  if (prevView !== name) {
    closeTransientWorkspaceChrome(prevView, name);
    saveWorkflowSnapshot();
  }
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
  syncDockRunButtonLabels();
  syncFinishButton(Boolean(state.lastPreview?.can_finish), Boolean(state.lastPreview?.delivery_ready));
  syncHotspotStatusUi();
  syncDockScrollPadding();
  void maybeRunHotspotAutoOnLoad();
}

async function loadImitateView() {
  if (!state.items.length) await loadMaterials();
  if (!state.products.length) await loadScriptView();
  renderAllImitationViralGrids();
  syncDockChipsFromHealth();
  syncDockProductSlot();
  syncDockRefSlot();
  syncImitationPromptFields();
  syncProducePreviewForActiveView();
  syncDockRunButtonLabels();
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
  switchView("generate");
  openSettingsDrawer();
  window.setTimeout(() => {
    const block = document.getElementById("settingsMaintenanceBlock");
    if (block) block.open = true;
    document.getElementById("hotspotSyncBar")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    document.getElementById("hotspotCollectBtn")?.focus();
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
const WORKFLOW_GUIDE_DISMISSED_KEY = "vl_workflow_guide_dismissed";

function isStarterGuideDismissed() {
  return (
    localStorage.getItem(STARTER_GUIDE_DISMISSED_KEY) === "1"
    || localStorage.getItem("vl_starter_guide_closed") === "1"
  );
}

function isWorkflowGuideDismissed() {
  return localStorage.getItem(WORKFLOW_GUIDE_DISMISSED_KEY) === "1";
}

function dismissStarterGuide() {
  localStorage.setItem(STARTER_GUIDE_DISMISSED_KEY, "1");
  localStorage.removeItem("vl_starter_guide_closed");
  closeStarterGuidePanel();
  maybeOpenWorkflowGuidePanel();
}

function dismissWorkflowGuide() {
  localStorage.setItem(WORKFLOW_GUIDE_DISMISSED_KEY, "1");
  closeWorkflowGuidePanel();
}

function openStarterGuidePanel() {
  if (isStarterGuideDismissed()) return;
  openFloatPanel("starterGuidePanel", "starterGuideBackdrop");
}

function closeStarterGuidePanel() {
  closeFloatPanel("starterGuidePanel", "starterGuideBackdrop");
}

function openWorkflowGuidePanel({ manual = false } = {}) {
  if (!manual && isWorkflowGuideDismissed()) return;
  syncWorkflowGuide();
  openFloatPanel("workflowGuidePanel", "workflowGuideBackdrop");
}

function closeWorkflowGuidePanel() {
  closeFloatPanel("workflowGuidePanel", "workflowGuideBackdrop");
}

function maybeOpenWorkflowGuidePanel() {
  if (isWorkflowGuideDismissed() || isAnyFloatPanelOpen()) return;
  window.setTimeout(() => openWorkflowGuidePanel(), 320);
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
  if (/login|captcha|验证码|限流|rate-limited|verification/i.test(raw)) {
    return [
      "TikTok 要求登录或人机验证（常见于新 IP / 频繁搜索）：",
      "1. 确认用「启动工作台.cmd」启动（不要用 Cursor 终端）",
      "2. 点击「开始采集」后留意弹出的 Chrome/Edge 窗口",
      "3. 在窗口中登录 TikTok 并完成滑块/验证码",
      "4. 登录成功后关闭弹窗或等待自动继续，再点一次「开始采集」",
      "5. 若仍失败：删除 tiktok_collector\\data\\browser_profile 后重试，或隔 10–30 分钟再采",
      "6. 确认 tiktok_collector/.env 中 TIKTOK_COLLECTOR_HEADLESS=false",
    ].join("\n");
  }
  return "";
}

function formatHotspotLastSync(iso) {
  if (!iso) return "尚未同步";
  try {
    const t = new Date(iso).getTime();
    if (!Number.isFinite(t)) return "尚未同步";
    const diffMin = Math.round((Date.now() - t) / 60000);
    if (diffMin < 1) return "刚刚更新";
    if (diffMin < 60) return `${diffMin} 分钟前更新`;
    const h = Math.floor(diffMin / 60);
    if (h < 24) return `${h} 小时前更新`;
    return new Date(iso).toLocaleString();
  } catch {
    return "尚未同步";
  }
}

function hotspotIntervalMs() {
  try {
    const min = Number(localStorage.getItem(HOTSPOT_AUTO_INTERVAL_KEY));
    if (Number.isFinite(min) && min >= 5 && min <= 240) return min * 60 * 1000;
  } catch { /* ignore */ }
  return DEFAULT_HOTSPOT_INTERVAL_MIN * 60 * 1000;
}

function isHotspotAutoSyncEnabled() {
  try {
    return localStorage.getItem(HOTSPOT_AUTO_SYNC_KEY) === "1";
  } catch {
    return false;
  }
}

function setHotspotAutoSyncEnabled(on) {
  try {
    localStorage.setItem(HOTSPOT_AUTO_SYNC_KEY, on ? "1" : "0");
  } catch { /* ignore */ }
  const cb = document.getElementById("hotspotAutoSync");
  if (cb) cb.checked = Boolean(on);
  if (on) scheduleHotspotAutoSync();
  else clearHotspotAutoSync();
}

function syncHotspotStatusUi(hotspot = state.healthCache?.hotspot, maintenance = state.healthCache?.maintenance) {
  const statusEl = document.getElementById("hotspotSyncStatus");
  const bar = document.getElementById("hotspotSyncBar");
  if (!statusEl) return;
  const mysql = Boolean(state.healthCache?.tiktok_collector?.mysql_enabled);
  const productId = currentProductId();
  const total = maintenance?.materials_total ?? hotspot?.materials_total ?? state.healthCache?.materials ?? 0;
  const analyzed = maintenance?.materials_analyzed ?? hotspot?.materials_analyzed ?? state.healthCache?.analyzed ?? 0;
  const maxTotal = maintenance?.max_total ?? 80;
  let line = `素材 ${total}/${maxTotal} · 已拆解 ${analyzed}`;
  if (productId) {
    line += ` · ${currentProductLabel() || productId}`;
  } else {
    line += " · 请先配置底部「产品」";
  }
  const lastMaint = maintenance?.last_run_at || hotspot?.last_refresh_at;
  line += ` · ${formatHotspotLastSync(lastMaint)}`;
  if (!mysql) {
    line += " · 无 MySQL 时需浏览器采集";
  }
  statusEl.textContent = line;
  bar?.classList.toggle("is-busy", Boolean(state.hotspotRefreshBusy));
}

function clearHotspotAutoSync() {
  if (state.hotspotAutoTimer) {
    clearInterval(state.hotspotAutoTimer);
    state.hotspotAutoTimer = null;
  }
}

function scheduleHotspotAutoSync() {
  clearHotspotAutoSync();
  if (!isHotspotAutoSyncEnabled()) return;
  state.hotspotAutoTimer = window.setInterval(() => {
    if (state.hotspotRefreshBusy || state.viralPipelineBusy) return;
    if (!currentProductId()) return;
    void runMaterialMaintenance({ silent: true });
  }, hotspotIntervalMs());
}

async function maybeRunHotspotAutoOnLoad() {
  if (!isHotspotAutoSyncEnabled() || state.hotspotRefreshBusy) return;
  if (!currentProductId()) return;
  const lastAt = state.healthCache?.maintenance?.last_run_at || state.healthCache?.hotspot?.last_refresh_at;
  if (lastAt) {
    try {
      const age = Date.now() - new Date(lastAt).getTime();
      if (age < hotspotIntervalMs() * 0.9) return;
    } catch { /* continue */ }
  }
  await runMaterialMaintenance({ silent: true });
}

async function runMaterialMaintenance({ sync = true, trim = true, prune = true, silent = false } = {}) {
  if (state.hotspotRefreshBusy) return false;
  const productId = productIdForScopedCapture() || currentProductId();
  if (!productId) {
    if (!silent) {
      setScriptActionStatus("请先配置产品后再维护素材", { isError: true });
      await openProductFloatPanel();
    }
    return false;
  }
  if (!silent) {
    const ok = window.confirm(
      `将按「${currentProductLabel() || productId}」执行素材维护：\n`
      + `${sync ? "① 同步 MySQL 热点\n" : ""}`
      + `${trim ? "② 移除非本品类素材\n" : ""}`
      + `${prune ? "③ 去重并限额（已拆解/成稿/有脚本保留）\n" : ""}\n`
      + "确定继续？",
    );
    if (!ok) return false;
  }

  state.hotspotRefreshBusy = true;
  const busyIds = ["hotspotMaintainBtn", "hotspotRefreshBtn", "hotspotPruneBtn", "hotspotDecomposeBtn", "hotspotCollectBtn", "hotspotClearLibraryBtn"];
  busyIds.forEach((id) => { const el = document.getElementById(id); if (el) el.disabled = true; });
  const statusEl = document.getElementById("hotspotSyncStatus");
  syncHotspotStatusUi();
  if (statusEl && !silent) statusEl.textContent = "正在维护素材库…";

  try {
    const data = await api("/api/materials/maintenance/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ product_id: productId, sync, trim, prune, dry_run: false }),
    });
    if (state.healthCache) {
      state.healthCache.maintenance = {
        ...(state.healthCache.maintenance || {}),
        last_run_at: data.refreshed_at,
        last_product_id: productId,
        last_message: data.message,
        materials_total: data.materials_total,
        materials_analyzed: data.materials_analyzed,
      };
      state.healthCache.materials = data.materials_total;
      state.healthCache.analyzed = data.materials_analyzed;
    }
    await loadMaterials();
    renderAllImitationViralGrids();
    repopulateScriptMaterials();
    syncHotspotStatusUi();
    if (!silent && data.message) setScriptActionStatus(data.message);
    return Boolean(data.ok);
  } catch (err) {
    if (!silent) setScriptActionStatus(friendlyApiErrorMessage(err.message), { isError: true });
    syncHotspotStatusUi();
    return false;
  } finally {
    state.hotspotRefreshBusy = false;
    busyIds.forEach((id) => { const el = document.getElementById(id); if (el) el.disabled = false; });
    syncHotspotStatusUi();
  }
}

async function runMaterialPruneOnly() {
  return runMaterialMaintenance({ sync: false, trim: true, prune: true, silent: false });
}

async function runClearMaterialLibrary() {
  const ok = window.confirm(
    "将清空全部对标素材、拆解结果、封面缓存与反推提示词，保留产品资料和内置提示词预设。\n\n确定要清空并重新测试素材流程吗？",
  );
  if (!ok) return;
  const btn = document.getElementById("hotspotClearLibraryBtn");
  const statusEl = document.getElementById("hotspotSyncStatus");
  if (btn) btn.disabled = true;
  if (statusEl) statusEl.textContent = "正在清空素材库…";
  try {
    const data = await api("/api/materials/maintenance/clear", { method: "POST" });
    state.selectedMaterialId = null;
    state.reverseMaterialId = null;
    if (state.healthCache) {
      state.healthCache.materials = 0;
      state.healthCache.analyzed = 0;
      state.healthCache.hotspot = {};
      state.healthCache.maintenance = {};
    }
    await loadMaterials();
    repopulateScriptMaterials();
    renderAllImitationViralGrids();
    renderRefFloatMaterialList();
    syncDockRefSlot();
    syncHotspotStatusUi();
    setScriptActionStatus(data.message || "对标素材库已清空，可重新采集测试。");
  } catch (err) {
    setScriptActionStatus(friendlyApiErrorMessage(err.message), { isError: true });
    syncHotspotStatusUi();
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function runDecomposeNewMaterials() {
  const productId = productIdForScopedCapture() || currentProductId();
  if (!productId) {
    setScriptActionStatus("请先配置产品", { isError: true });
    await openProductFloatPanel();
    return;
  }
  const ok = window.confirm("将对未拆解素材批量执行规则拆解（免费，不消耗豆包）。后台运行，可点顶栏「后台任务」查看进度。\n\n确定？");
  if (!ok) return;
  try {
    await api("/api/jobs/decompose", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider: "rule", product_id: productId }),
    });
    setScriptActionStatus("已启动规则拆解，完成后素材卡片将自动刷新");
    await pollJobStatus();
  } catch (err) {
    setScriptActionStatus(friendlyApiErrorMessage(err.message), { isError: true });
  }
}

async function runHotspotRefresh(mode = "auto", { silent = false } = {}) {
  if (state.hotspotRefreshBusy) return false;
  const productId = productIdForScopedCapture() || currentProductId();
  if (!productId) {
    if (!silent) {
      setScriptActionStatus("请先配置产品后再更新热点", { isError: true });
      await openProductFloatPanel();
    }
    return false;
  }
  if (mode === "collect" && !silent) {
    const ok = window.confirm(
      "将打开浏览器抓取 TikTok 新热点（需登录/验证码）。\n\n建议内网先完成一次登录后再批量采集。继续？",
    );
    if (!ok) return false;
  }

  state.hotspotRefreshBusy = true;
  const refreshBtn = document.getElementById("hotspotRefreshBtn");
  const collectBtn = document.getElementById("hotspotCollectBtn");
  const statusEl = document.getElementById("hotspotSyncStatus");
  if (refreshBtn) refreshBtn.disabled = true;
  if (collectBtn) collectBtn.disabled = true;
  syncHotspotStatusUi();
  if (statusEl && !silent) {
    statusEl.textContent = mode === "collect" ? "浏览器采集中…若弹出窗口请完成 TikTok 登录" : "正在同步热点对标…";
  }

  try {
    const data = await api("/api/hotspot/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        product_id: productId,
        mode,
        limit: 80,
        limit_per_keyword: 30,
      }),
    });
    if (state.healthCache) {
      state.healthCache.hotspot = {
        ...(state.healthCache.hotspot || {}),
        last_refresh_at: data.refreshed_at,
        last_product_id: productId,
        last_mode: mode,
        materials_total: data.materials_total,
        materials_analyzed: data.materials_analyzed,
      };
      state.healthCache.materials = data.materials_total;
      state.healthCache.analyzed = data.materials_analyzed;
    }
    await loadMaterials();
    renderAllImitationViralGrids();
    repopulateScriptMaterials();
    syncHotspotStatusUi(state.healthCache?.hotspot);
    if (!silent && data.message) {
      setScriptActionStatus(data.message);
    }
    return Boolean(data.ok);
  } catch (err) {
    if (!silent) {
      setScriptActionStatus(friendlyApiErrorMessage(err.message), { isError: true });
    }
    syncHotspotStatusUi();
    return false;
  } finally {
    state.hotspotRefreshBusy = false;
    if (refreshBtn) refreshBtn.disabled = false;
    if (collectBtn) collectBtn.disabled = false;
    syncHotspotStatusUi();
  }
}

function initHotspotSync() {
  const autoCb = document.getElementById("hotspotAutoSync");
  if (autoCb) {
    autoCb.checked = isHotspotAutoSyncEnabled();
    autoCb.addEventListener("change", () => setHotspotAutoSyncEnabled(autoCb.checked));
  }
  document.getElementById("hotspotMaintainBtn")?.addEventListener("click", () => {
    void runMaterialMaintenance();
  });
  document.getElementById("hotspotRefreshBtn")?.addEventListener("click", () => {
    void runHotspotRefresh("auto");
  });
  document.getElementById("hotspotPruneBtn")?.addEventListener("click", () => {
    void runMaterialPruneOnly();
  });
  document.getElementById("hotspotDecomposeBtn")?.addEventListener("click", () => {
    void runDecomposeNewMaterials();
  });
  document.getElementById("hotspotCollectBtn")?.addEventListener("click", () => {
    void runHotspotRefresh("collect");
  });
  document.getElementById("decomposeLibraryBtn")?.addEventListener("click", () => openMaterialLibraryDrawer());
  document.getElementById("hotspotClearLibraryBtn")?.addEventListener("click", () => {
    void runClearMaterialLibrary();
  });
  syncHotspotStatusUi();
  if (isHotspotAutoSyncEnabled()) scheduleHotspotAutoSync();
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
    statusEl.textContent = `正在采集「${currentProductLabel()}」同品类 TikTok 数据…若弹出浏览器，请在其中完成 TikTok 登录/验证码`;
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
  const ps = document.getElementById("scriptProductSelect");
  const ready = Boolean(ps?.value) && tagsSelectionOk();
  const productName = ps?.selectedOptions?.[0]?.textContent?.trim() || "";
  for (const id of ["dockOpenProductBtn", "imitateOpenProductBtn"]) {
    const btn = document.getElementById(id);
    if (!btn) continue;
    btn.classList.toggle("has-value", ready);
    const spans = btn.querySelectorAll("span");
    const labelSpan = spans[spans.length - 1];
    if (labelSpan) {
      labelSpan.textContent = ready && productName
        ? productName.slice(0, 10)
        : "产品";
    }
    btn.title = ready && productName ? `已选：${productName}` : "先选产品与场景标签";
  }
  syncReverseDockProduct();
  syncWorkflowGuide();
}

function syncDockRefSlot() {
  const ready = productWorkflowReady();
  for (const id of ["dockOpenMaterialsBtn", "imitateOpenMaterialsBtn"]) {
    const btn = document.getElementById(id);
    if (!btn) continue;
    btn.disabled = !ready;
    btn.classList.toggle("dock-upload-slot-locked", !ready);
    btn.classList.toggle("has-value", ready && Boolean(state.selectedMaterialId));
    const item = state.items.find((i) => i.link_id === state.selectedMaterialId);
    const refTitle = item ? (item.title || "").trim().slice(0, 10) || `#${item.link_id}` : "";
    const spans = btn.querySelectorAll("span");
    const labelSpan = spans[spans.length - 1];
    if (labelSpan) {
      labelSpan.textContent = ready && state.selectedMaterialId && refTitle ? refTitle : "对标";
    }
    btn.title = ready
      ? (state.selectedMaterialId ? `已选对标：${refTitle}` : "选择同品类对标视频")
      : "请先点击「产品」完成配置";
  }
  syncWorkflowGuide();
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
    syncHotspotStatusUi(h.hotspot, h.maintenance);
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

function syncFeishuActionButtons(enabled) {
  ["btnFeishuStatusSettings", "btnFeishuAuthUrlSettings", "btnFeishuDoctorSettings"].forEach((id) => {
    const btn = document.getElementById(id);
    if (!btn) return;
    btn.disabled = !enabled;
    btn.classList.toggle("hidden", !enabled);
  });
}

function renderFeishuSettings(status) {
  const el = document.getElementById("feishuSettingsStatus");
  if (!el) return;
  const fs = status?.feishu || status || {};
  if (fs.integrated === false || (!fs.installed && fs.message)) {
    syncFeishuActionButtons(false);
    el.innerHTML = `<span class="muted">${esc(fs.message || "工作台未集成飞书 CLI")}</span>`;
    return;
  }
  syncFeishuActionButtons(true);
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
    hideSeedanceProgressIfIdle();
    renderSeedanceFinalPreview(null, null);
    return;
  }

  const finalReady = Boolean(seedance.final_video?.ready);
  renderSeedanceFinalPreview(slug, seedance);

  if (!state.createPipelineActive && !state.videoGenActive) {
    hideSeedanceProgressIfIdle();
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
          <button type="button" class="primary primary-dark" id="goScriptBtn">${state.view === "reverse" ? "用于反推" : "生成脚本"}</button>
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
        <button type="button" class="primary primary-dark" id="goScriptBtn">${state.view === "reverse" ? "用于反推" : "生成脚本"}</button>
      </div>
    </div>`;
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function fetchMaterialAnalysis(linkId, pane, { autoStart = true } = {}) {
  const qs = autoStart ? "" : "?auto_start=0";
  for (let i = 0; i < 80; i++) {
    const detail = await api(`/api/materials/${linkId}/analysis/detail${qs}`);
    if (detail.status === "running") {
      if (!autoStart) return detail;
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

async function selectMaterial(linkId, { fromDrawer = false, fromRefFloat = false, keepDetail = false, loadDetail } = {}) {
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
  const shouldLoadDetail = loadDetail ?? !(fromDrawer || fromRefFloat);
  if (!shouldLoadDetail) {
    if (document.getElementById("scriptProductSelect")?.value) {
      await refreshScriptPreview({ preserveTagSelection: true });
    }
    const pane = document.getElementById("materialDetail");
    if (pane) {
      const item = state.items.find((i) => i.link_id === linkId);
      const title = esc((item?.title || "").slice(0, 40) || `素材 #${linkId}`);
      pane.className = "detail dissector-detail ref-float-detail muted";
      pane.innerHTML = `已选：<strong>${title}</strong>。<button type="button" class="pill-btn" id="loadMaterialDetailBtn">加载拆解详情</button> <span class="muted">（不会自动触发豆包）</span>`;
      document.getElementById("loadMaterialDetailBtn")?.addEventListener("click", () => {
        void selectMaterial(linkId, { loadDetail: true, keepDetail: false });
      });
    }
    if (state.view === "reverse") syncReverseDockMaterial();
    return;
  }
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
      if (state.view === "reverse") {
        state.reverseMaterialId = linkId;
        state.selectedMaterialId = linkId;
        syncReverseDockMaterial();
        closeMaterialLibraryDrawer();
        closeRefFloatPanel();
        if (!currentProductId()) {
          await openProductFloatPanel();
          return;
        }
        document.getElementById("reverseDock")?.scrollIntoView({ behavior: "smooth", block: "end" });
        return;
      }
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
    try {
      await refreshHealth();
    } catch (healthErr) {
      console.warn("refreshHealth after selectMaterial", healthErr);
    }
  } catch (err) {
    pane.innerHTML = `<div class="result error">${esc(friendlyApiErrorMessage(err.message))}</div>`;
    const status = document.getElementById("refFloatStatus");
    if (status) status.textContent = `加载失败：${friendlyApiErrorMessage(err.message)}`;
    return;
  }
  try {
    if (document.getElementById("scriptProductSelect")?.value) {
      await refreshScriptPreview();
    } else {
      updateLoopBarFromForm(state.lastPreview || {});
    }
  } catch (err) {
    const status = document.getElementById("refFloatStatus");
    if (status) status.textContent = `预览同步失败：${friendlyApiErrorMessage(err.message)}`;
    showVideoGenError(friendlyApiErrorMessage(err.message), { openPanel: false, scrollDock: false });
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

async function refreshScriptPreview(options = {}) {
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
    if (options.mergePreview) {
      state.lastPreview = { ...prev, ...options.mergePreview };
    } else {
      state.lastPreview = prev;
    }
    const merged = state.lastPreview;
    state.scriptSlug = merged.slug;

    const warnEl = document.getElementById("scriptMismatchWarn");
    const mismatch = merged.product_match === false;
    if (mismatch) {
      warnEl.classList.remove("hidden");
      warnEl.textContent =
        `品类不一致：参考偏「${merged.content_line || "其他"}」，产品为「${productId}」。建议换同品类参考，或勾选「显示其他品类」后确认再生成。`;
    } else {
      warnEl.classList.add("hidden");
      warnEl.textContent = "";
    }
    const a = merged.material?.analysis || {};
    const brandHint = merged.brand_product && mismatch
      ? `<p class="brand-hint muted">成片品牌：${esc(merged.brand_product)}</p>`
      : "";
    analysisEl.innerHTML = `${brandHint}<div class="field-grid-compact">
      <div class="field-compact"><label>钩子 0-3s</label><p>${esc(a.hook_3s)}</p></div>
      <div class="field-compact"><label>痛点</label><p>${esc(a.pain_points)}</p></div>
      <div class="field-compact"><label>卖点</label><p>${esc(a.selling_points)}</p></div>
      <div class="field-compact"><label>结构</label><p>${esc(a.video_structure)}</p></div>
      <div class="field-compact"><label>字幕布局</label><p>${esc(a.subtitle_layout)}</p></div>
    </div>`;
    const p = merged.product || {};
    syncProductTagPanelFromPreview(
      p,
      merged.delivery_tags || {},
      merged.selected_tags || {},
      merged.script_pack,
      { preserveTagSelection: Boolean(options.preserveTagSelection) },
    );
    updateLoopBarFromForm(merged);
    syncScriptDownloadZip(merged);
    if (!options.skipScriptRemount && merged.has_script && merged.script_pack) {
      if (!state.scriptTagSnapshot) {
        state.scriptTagSnapshot = scriptTagSnapshotFromPack(merged.script_pack, merged.selected_tags || {});
      }
      syncScriptProduceEmpty(true);
      mountScriptPackEditor(scriptResultBody(), merged.script_pack, merged.script_meta);
    }
    syncFinishButton(Boolean(merged.can_finish), Boolean(merged.delivery_ready));
    hideSeedanceProgressIfIdle();
    restoreProduceUiFromPreview(merged);
    syncDockRunButtonLabels();
  } catch (err) {
    analysisEl.innerHTML = `<div class="result error">${esc(friendlyApiErrorMessage(err.message))}</div>`;
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
  state.scriptGenActive = false;
  state.scriptTagSnapshot = null;
  state.lastScriptProductId = null;
  setSeedanceVideoComplete(false);
  hideProduceCompleteBanner();
  hideProduceCompleteModal();
  if (scriptResultBody()) scriptResultBody().innerHTML = "";
  hideSeedanceProgressIfIdle();
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
    return false;
  }
  if (!document.getElementById("scriptMaterialSelect")?.value) {
    openRefFloatPanel();
    return false;
  }
  if (!materialInProductPool(linkId, productId)) {
    setScriptActionStatus("所选对标与当前产品不匹配，请重新选择同品类对标。");
    openRefFloatPanel();
    return false;
  }
  const quota = state.healthCache?.production?.daily_script_quota;
  if (quota?.enabled && quota.remaining <= 0) {
    setScriptActionStatus(`今日 LLM 脚本配额已用完（${quota.used}/${quota.limit}），请明日再试。`);
    openScriptFloatPanel();
    return false;
  }
  await refreshScriptPreview({ skipScriptRemount: true, preserveTagSelection: true });
  if (state.lastPreview?.product_match === false) {
    const warn = document.getElementById("scriptMismatchWarn");
    const msg = warn?.textContent || "对标与产品品类不一致，请更换对标或勾选「显示其他品类」后确认。";
    if (resultEl) resultEl.innerHTML = `<div class="result error">${esc(msg)}</div>`;
    setScriptActionStatus(msg);
    openScriptFloatPanel();
    return false;
  }
  setScriptStep("produce");
  if (!isAutomatedPipelineUi()) {
    openScriptFloatPanel();
  }
  genBtns.forEach((b) => { b.disabled = true; });
  const regenBtn = document.getElementById("scriptFloatRegenBtn");
  const produceBtn = document.getElementById("scriptFloatProduceBtn");
  if (regenBtn) {
    regenBtn.disabled = true;
    regenBtn.dataset.busy = "1";
    regenBtn.textContent = "生成中…";
  }
  if (produceBtn) produceBtn.disabled = true;
  setSeedanceVideoComplete(false);
  const scriptStatus = "正在根据产品标签与对标结构生成脚本…";
  showScriptProgress(true, {
    status: scriptStatus,
    indeterminate: true,
    pipeline: state.healthCache?.llm?.label || "",
    countdownSec: SEEDANCE_COUNTDOWN_PHASE_SEC.script,
  });
  if (resultEl) resultEl.innerHTML = "";
  setScriptActionStatus(scriptStatus);
  beginScriptGenerationAbort();
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
      signal: scriptGenerationSignal(),
    });
    const pack = res.script_pack || res.pack || {};
    applyTagSelectionFromPack(pack);
    state.scriptSlug = res.slug || slugFor(linkId);
    state.scriptTagSnapshot = captureTagSnapshot();
    state.lastScriptProductId = productId;
    saveWorkflowSnapshot();
    const previewPatch = {
      script_pack: pack,
      script_meta: res.meta,
      has_script: true,
      selected_tags: readAllSelectedTags(),
    };
    if (state.lastPreview) {
      Object.assign(state.lastPreview, previewPatch);
    }
    if (resultEl) mountScriptPackEditor(resultEl, pack, res.meta);
    setSeedanceVideoComplete(false);
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
    await refreshScriptPreview({
      skipScriptRemount: true,
      preserveTagSelection: true,
      mergePreview: previewPatch,
    });
    resetPromptEnhanceUsed();
    return true;
  } catch (err) {
    if (isAbortError(err)) {
      setScriptActionStatus("已停止脚本生成，可修改标签或提示词后重试", { forceDock: true });
      return false;
    }
    if (resultEl) resultEl.innerHTML = `<div class="result error">${esc(err.message)}</div>`;
    setScriptActionStatus(friendlyApiErrorMessage(err.message), { isError: true, forceDock: true });
    if (String(err.message || "").includes("配额")) syncDailyScriptQuota();
    return false;
  } finally {
    abortScriptGeneration();
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
    const res = await api(`/api/delivery/${slug}/finish`, {
      method: "POST",
      signal: scriptGenerationSignal() || videoProductionSignal(),
    });
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
    if (isAbortError(err)) {
      setScriptActionStatus("已停止交付生成", { forceDock: true });
      return false;
    }
    if (!keepScript) {
      resultEl.innerHTML = `<div class="result error">${esc(err.message)}</div>`;
    } else {
      showVideoGenError(`交付失败：${err.message}`, { openPanel: !background });
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
    showVideoGenError(`今日成片产出配额已用完（${videoQ.used}/${videoQ.limit}），请明日再试。`);
    return false;
  }
  const slug = currentScriptSlug();
  if (!slug) {
    showVideoGenError("请先生成脚本");
    if (!background) ensureScriptResultVisible();
    return false;
  }
  state.scriptSlug = slug;
  if (!background) ensureScriptResultVisible();
  state.videoGenActive = true;
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
    const ticket = state.videoQueueTicket || "";
    const ticketQs = ticket ? `${qs ? "&" : "?"}ticket=${encodeURIComponent(ticket)}` : "";
    if (!ticket) {
      showVideoGenError("缺少生产排队号，请重新点击「确认生成视频」");
      return false;
    }
    const data = await api(`/api/delivery/${encodeURIComponent(slug)}/seedance/run${qs}${ticketQs}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        resolution: vs.resolution,
        aspect_ratio: vs.aspectRatio,
        duration_sec: vs.durationSec,
        generate_count: vs.generateCount,
        edit_mode: vs.editMode,
      }),
      signal: videoProductionSignal(),
    });
    renderSeedance(slug, data.seedance, state.healthCache);
    const blocked = (data.results || []).filter((r) => r.status === "blocked");
    if (blocked.length) {
      const bmsg = blocked[0].message || "关键帧未确认";
      showVideoGenError(bmsg);
      await ensureHeroFramesGate(slug, { background });
      state.heroConfirmThenProduce = true;
      return false;
    }
    const failed = (data.results || []).filter((r) => r.status === "error");
    const skipped = (data.results || []).filter((r) => r.status === "skipped");
    const okCount = (data.results || []).filter((r) => r.status === "ok").length;
    const finalReady = Boolean(data.seedance?.final_video?.ready || data.assemble?.ok);
    let msg;
    if (failed.length) {
      msg = failed.every((r) => (r.message || "").includes("ARK_API_KEY"))
        ? `火山方舟密钥失效：${failed[0].message}。请到「设置」→ 测试连接，或更新 overseas-loc-mvp/.env 中的 ARK_API_KEY 后重启工作台。`
        : `部分镜生成失败：${failed.map((r) => `镜${r.number} ${r.message}`).join("；")}。已成功的分镜可预览或下载 zip。`;
    } else if (finalReady) {
      const prod = data.video_production || {};
      const spec = prod.resolution_ui && prod.aspect_ratio
        ? `（${prod.resolution_ui} · ${prod.aspect_ratio}）`
        : `（${vs.resolution} · ${vs.aspectRatio}）`;
      msg = force
        ? `已强制重生成 ${okCount || "5"} 镜并拼接成片${spec}，可预览 mp4 或下载 zip`
        : `视频生成完成${spec}，可预览 mp4 或下载 zip`;
    } else if (okCount > 0) {
      const asm = data.assemble?.message || "分镜已生成，但成片合成未完成";
      msg = `${asm}${PARTIAL_QUOTA_NOTE}。请确认 ffmpeg 可用后点「重新合成」；zip 内仅有分镜 mp4。`;
    } else if (skipped.length) {
      msg = force
        ? "本次未覆盖旧视频：请重启工作台（启动页面.cmd）后再勾选强制重生成，或运行 本地生成视频.cmd <编号> --force"
        : "未生成新视频：镜头已有 mp4。请勾选「强制重生成」后重试，或先重新生成脚本以更新 Prompt。";
    } else {
      msg = "视频生成完成，可预览 mp4 或下载 zip";
    }
    if (hintEl) hintEl.textContent = msg;
    stopSeedanceCountdown();
    if (data.daily_video_quota && state.healthCache?.production) {
      state.healthCache.production.daily_video_quota = data.daily_video_quota;
      syncDailyVideoQuota(data.daily_video_quota);
    }
    const level = renderProduceOutcome(slug, data.seedance, {
      message: msg,
      assemble: data.assemble,
      failed: Boolean(failed.length && !shotAssetsReady(data.seedance) && !okCount),
    });
    if (state.lastPreview) state.lastPreview.seedance = data.seedance;
    return level !== "error";
  } catch (err) {
    stopSeedanceCountdown();
    if (isAbortError(err) || String(err.message || "").includes("生成已取消")) {
      setScriptActionStatus("已取消生成", { forceDock: true });
      resetSeedanceProgressDock();
      return false;
    }
    await refreshScriptPreview();
    const lp = state.lastPreview || {};
    const s = slug || currentScriptSlug();
    if (produceDownloadReady(lp)) {
      renderProduceOutcome(s, lp.seedance, {
        message: `视频生成失败：${err.message}`,
        failed: !shotAssetsReady(lp.seedance),
      });
    } else {
      showVideoGenError(`视频生成失败：${err.message}`, { openPanel: !background });
    }
    return false;
  } finally {
    if (background && !state.createPipelineActive) {
      state.videoGenActive = false;
      hideSeedanceProgressIfIdle();
    }
  }
}

async function runProduceVideo(options = {}) {
  const background = Boolean(options.background);
  const slug = currentScriptSlug();
  if (!slug) {
    showVideoGenError("请先生成脚本后再产出视频", { openPanel: !background });
    return false;
  }
  if (!options.skipScriptSave) {
    const saved = await saveScriptEditsIfDirty({ silent: true });
    if (!saved) {
      showVideoGenError("保存脚本修改失败，无法开始生成视频");
      return false;
    }
  }
  state.scriptSlug = slug;
  if (!background) {
    setScriptStep("produce", { scroll: false });
    ensureScriptResultVisible();
  }
  state.videoGenActive = true;
  if (!state.scriptGenerationAbort) beginScriptGenerationAbort();
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
        showVideoGenError(state.lastVideoGenError || "交付未完成，无法产出视频。");
        return false;
      }
      await refreshScriptPreview();
    }
    const gateOk = await ensureHeroFramesGate(slug, { background });
    if (!gateOk) {
      state.heroConfirmThenProduce = true;
      return false;
    }
    return await runSeedanceGenerate({
      force: forceRegen,
      background,
      keepCountdown: true,
    });
  } catch (err) {
    stopSeedanceCountdown();
    if (isAbortError(err)) {
      setScriptActionStatus("已取消生成", { forceDock: true });
      resetSeedanceProgressDock();
      return false;
    }
    showVideoGenError(`产出视频失败：${err.message}`);
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

function buildActiveConstraintsHtml(prev, { highlight = false } = {}) {
  if (!prev?.matched_count) return "";
  const items = (prev.constraints_zh || [])
    .map((line) => `<li>${esc(line)}</li>`)
    .join("");
  const sources = (prev.sources || [])
    .filter((s) => s.slug)
    .map(
      (s) => `<span class="feedback-constraint-source" title="场景 ${esc(s.scenario_tags || "—")}">${esc(s.slug)} · ${esc(s.adopted || "")}</span>`,
    )
    .join("");
  return `
    <section class="feedback-active-constraints${highlight ? " feedback-active-constraints--flash" : ""}" aria-label="已生效约束">
      <div class="feedback-active-constraints-head">
        <strong>已生效约束</strong>
        <span class="muted">下次生成将参考以下 ${prev.matched_count} 条反馈</span>
      </div>
      <ul class="feedback-constraint-list">${items}</ul>
      ${sources ? `<div class="feedback-constraint-sources">${sources}</div>` : ""}
    </section>`;
}

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
  const flashConstraints = Boolean(state.feedbackConstraintsFlash);
  state.feedbackConstraintsFlash = false;
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
    let constraintsBlock = "";
    if (r.product_id) {
      try {
        const prev = await api(
          `/api/library/feedback-constraints?product_id=${encodeURIComponent(r.product_id)}&scenario_tags=${encodeURIComponent((r.scenario_tags || []).join(","))}`,
        );
        constraintsBlock = buildActiveConstraintsHtml(prev, { highlight: flashConstraints });
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
      ${constraintsBlock}
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
        const adopted = String(fd.get("adopted") || "");
        if (adopted === "已采纳" || adopted === "修改后采纳") {
          state.feedbackConstraintsFlash = true;
        }
        let libraryNote = "";
        if (adopted === "已采纳" || adopted === "修改后采纳") {
          libraryNote = " · 已收入提示词库（视频生成 → 提示词选择可选用）";
        }
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
            ? `已保存${libraryNote}，已切换下一条待反馈`
            : `已保存${libraryNote}，全部成稿已反馈完成`;
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
  const h = await api("/api/health");
  state.healthCache = h;
  renderDoubaoSettings(h);
  renderSeedanceSettings(h);
  const policyNote = h.decompose?.policy?.paused
    ? " · 拆解已暂停"
    : !h.decompose?.policy?.on_view
      ? " · 打开素材不自动豆包拆解"
      : "";
  const prod = h.production || {};
  const dep = h.deployment || {};
  const quota = prod.daily_script_quota || {};
  const videoQuota = prod.daily_video_quota || {};
  const deployEl = document.getElementById("deployInfo");
  if (deployEl) {
    deployEl.innerHTML = `
      ${esc(dep.host || "127.0.0.1")}:${esc(String(dep.port || 8788))}
      ${dep.intranet_mode ? " · 内网" : ""}${dep.auth_enabled ? " · 令牌" : ""}<br>
      归档 <code>${esc(dep.production_archive || "03_产出库")}</code>`;
  }
  const envEl = document.getElementById("envInfo");
  if (envEl) {
    envEl.innerHTML = `UI v${h.ui_version} · 素材 ${h.materials}（拆解 ${h.analyzed}）`
      + `<br>拆解：${h.decompose?.label || "规则"}${policyNote}`
      + `<br>脚本：${h.llm?.label || "—"} · SeedDance：${h.seedance?.configured ? "已配置" : "未配置"}`
      + (quota.enabled ? `<br>配额：脚本 ${quota.used}/${quota.limit}` : "")
      + (videoQuota.enabled ? ` · 成片 ${videoQuota.used}/${videoQuota.limit}` : "");
  }
  await pollJobStatus();
}

async function pollJobStatus() {
  const st = await api("/api/jobs/status");
  const el = document.getElementById("jobStatus");
  const log = document.getElementById("jobLog");
  syncGlobalJobBadge(st);
  if (!el) return;
  if (st.status === "running") {
    el.textContent = `运行中：${jobLabel(st.job)}（${st.started_at || ""}）`;
    if (log) log.textContent = st.output || "";
    if (!state.jobPoll) {
      state.jobPoll = setInterval(async () => {
        const s = await api("/api/jobs/status");
        syncGlobalJobBadge(s);
        document.getElementById("jobStatus").textContent = s.status === "running"
          ? `运行中：${jobLabel(s.job)}` : (s.exit_code === 0 ? `✅ ${jobLabel(s.job)} 完成` : `❌ ${jobLabel(s.job)} 失败 (code ${s.exit_code})`);
        const logEl = document.getElementById("jobLog");
        if (logEl) logEl.textContent = s.output || "";
        if (s.status !== "running") {
          clearInterval(state.jobPoll);
          state.jobPoll = null;
          syncGlobalJobBadge(s);
          await refreshHealth();
          await loadMaterials();
          renderAllImitationViralGrids();
        }
      }, 2000);
    }
  } else {
    el.textContent = st.job ? `${st.status}: ${jobLabel(st.job)}` : "";
    if (log) log.textContent = st.output || "";
  }
}

function syncGlobalJobBadge(st) {
  const badge = document.getElementById("globalJobBadge");
  if (!badge) return;
  const running = st?.status === "running";
  badge.hidden = !running;
  badge.classList.toggle("hidden", !running);
  if (running) {
    badge.textContent = `后台：${jobLabel(st.job)}…`;
    badge.title = "后台任务运行中（如规则拆解），完成后素材卡片自动刷新";
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

document.getElementById("openProductsFromSettings")?.addEventListener("click", () => {
  closeSettingsDrawer();
  switchView("products");
});
document.getElementById("openMaterialLibraryFromSettings")?.addEventListener("click", () => {
  closeSettingsDrawer();
  openMaterialLibraryDrawer();
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
document.getElementById("openWorkflowGuideBtn")?.addEventListener("click", () => openWorkflowGuidePanel({ manual: true }));
document.getElementById("workflowGuideGotItBtn")?.addEventListener("click", () => closeWorkflowGuidePanel());
document.getElementById("workflowGuideSkipBtn")?.addEventListener("click", dismissWorkflowGuide);
document.getElementById("workflowGuideCloseBtn")?.addEventListener("click", () => closeWorkflowGuidePanel());
document.getElementById("workflowGuideBackdrop")?.addEventListener("click", () => closeWorkflowGuidePanel());

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
document.getElementById("globalJobBadge")?.addEventListener("click", () => openSettingsDrawer());
document.getElementById("globalPipelineBadge")?.addEventListener("click", () => {
  const origin = state.pipelineOriginView;
  const targetView = origin === "imitate" || origin === "generate"
    ? origin
    : (state.view === "imitate" ? "imitate" : "generate");
  if (state.view !== targetView) switchView(targetView);
  activeStudioDock()?.scrollIntoView({ behavior: "smooth", block: "end" });
});
document.getElementById("restoreWorkflowBtn")?.addEventListener("click", () => { void restoreWorkflowSnapshot(); });
document.getElementById("settingsCloseBtn")?.addEventListener("click", () => closeSettingsDrawer());
document.getElementById("settingsBackdrop")?.addEventListener("click", () => closeSettingsDrawer());

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

document.getElementById("videoGenErrorBannerClose")?.addEventListener("click", () => {
  clearVideoGenErrorOnly();
  if (!state.videoGenActive && !state.scriptGenActive && !state.createPipelineActive) {
    resetSeedanceProgressDock();
  } else {
    syncStudioFocusMode();
  }
});

document.getElementById("produceCompleteBannerClose")?.addEventListener("click", () => {
  hideProduceCompleteBanner();
});

document.getElementById("produceCompleteModalCloseBtn")?.addEventListener("click", () => {
  dismissStudioFocus();
});

document.getElementById("produceCompleteModalCloseX")?.addEventListener("click", () => {
  dismissStudioFocus();
});

document.getElementById("produceCompleteModalBackdrop")?.addEventListener("click", () => {
  dismissStudioFocus();
});

document.getElementById("studioFocusBackdrop")?.addEventListener("click", () => {
  dismissStudioFocus();
});

["generateDockCloseBtn", "imitateDockCloseBtn"].forEach((id) => {
  document.getElementById(id)?.addEventListener("click", () => dismissStudioFocus());
});

document.getElementById("scriptFloatBackBtn")?.addEventListener("click", () => {
  closeScriptFloatPanel();
  syncStudioFocusMode();
});

["generateDockReassemble", "imitateDockReassemble"].forEach((id) => {
  document.getElementById(id)?.addEventListener("click", (e) => {
    const btn = e.currentTarget;
    void retryAssembleVideo(btn?.dataset?.retrySlug || currentScriptSlug());
  });
});

document.getElementById("videoQueueCloseBtn")?.addEventListener("click", () => {
  showVideoQueuePanel(false);
  if (state.videoQueuePoll && state.videoQueueTicket) {
    setScriptActionStatus("仍在排队生成视频，关闭面板不影响进度。可点「取消排队」终止。", { forceDock: true });
  }
});

document.getElementById("videoQueueCancelBtn")?.addEventListener("click", async () => {
  await cancelActivePipelineGeneration();
});

document.querySelectorAll(".pipeline-stop-btn").forEach((btn) => {
  btn.addEventListener("click", () => { void cancelActivePipelineGeneration(); });
});

async function bootstrapApp() {
  ensureClientId();
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
  syncRestoreWorkflowButton();
  initHotspotSync();
  activateView("generate");
  if (!isStarterGuideDismissed()) {
    window.setTimeout(() => openStarterGuidePanel(), 480);
  } else if (!isWorkflowGuideDismissed()) {
    window.setTimeout(() => openWorkflowGuidePanel(), 480);
  }
}

bootstrapApp();
