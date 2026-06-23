const $ = (s) => document.querySelector(s);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
}[c]));

function toast(msg) {
  const el = $("#toast");
  el.textContent = msg;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 3200);
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `请求失败 ${res.status}`);
  return data;
}

function currentSlug() {
  return $("#projectSelect").value;
}

function setPanel(ready) {
  $("#actionPanel").classList.toggle("hidden", ready);
  $("#readyPanel").classList.toggle("hidden", !ready);
}

async function downloadZip() {
  const slug = currentSlug();
  if (!slug) return;
  const res = await fetch(`/api/projects/${encodeURIComponent(slug)}/delivery.zip`);
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    if (res.status === 404 && !data.detail) {
      throw new Error("请双击「重启出海出稿.cmd」后刷新本页");
    }
    throw new Error(data.detail || `下载失败 (${res.status})`);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${slug}-delivery.zip`;
  link.click();
  URL.revokeObjectURL(url);
}

function renderHead(brief) {
  const head = $("#projectHead");
  if (!brief?.from_competitor) {
    head.innerHTML = `<p class="muted">请先在 <a href="http://127.0.0.1:8788">竞品库</a> 选视频并生成脚本。</p>`;
    return;
  }
  const link = brief.source_tiktok_url
    ? `<a href="${esc(brief.source_tiktok_url)}" target="_blank">TikTok 原链</a>`
    : "";
  head.innerHTML = `
    <p class="project-label">${esc(brief.label || currentSlug())}</p>
    ${link ? `<p class="project-link">${link}</p>` : ""}`;
}

function renderDownloads(slug, deliverables) {
  const box = $("#downloadBox");
  if (!deliverables?.length) {
    box.innerHTML = "";
    return;
  }
  box.innerHTML = deliverables.map((d) => {
    const primary = d.name === "交付脚本包.md" ? " download-card primary-file" : " download-card";
    return `
    <a class="${primary.trim()}" target="_blank"
       href="/api/projects/${encodeURIComponent(slug)}/files/${encodeURI(d.path)}">
      <strong>${esc(d.name)}</strong>
      <span>${esc(d.label)}</span>
    </a>`;
  }).join("");
}

async function loadProjects() {
  const data = await api("/api/projects");
  const select = $("#projectSelect");
  const list = (data.projects || []).filter((p) => p.from_competitor);
  const projects = list.length ? list : data.projects || [];

  if (!projects.length) {
    select.innerHTML = '<option value="">（暂无项目）</option>';
    renderHead({});
    return;
  }

  select.innerHTML = projects.map((p) =>
    `<option value="${esc(p.slug)}">${esc(p.label || p.slug)}</option>`
  ).join("");

  const urlRef = new URLSearchParams(location.search).get("ref");
  if (urlRef && projects.some((p) => p.slug === urlRef)) {
    select.value = urlRef;
  }

  $("#projectSwitch").classList.toggle("hidden", projects.length <= 1);
}

let healthCache = {};

function renderSeedance(slug, seedance, health) {
  const panel = $("#seedancePanel");
  const statusEl = $("#seedanceStatus");
  const configured = health?.seedance?.configured;
  const pipeline = seedance?.pipeline || health?.seedance?.label || "";

  $("#seedancePipeline").textContent = pipeline;

  if (!configured) {
    statusEl.innerHTML = `未连接 · 请双击 <strong>配置SeedDance.cmd</strong> 填写 <code>FAL_KEY</code> 后重启服务`;
    $("#seedanceShots").innerHTML = "";
    $("#btnSeedance").disabled = true;
    $("#seedanceHint").textContent = health?.seedance?.setup || "";
    panel.classList.remove("hidden");
    return;
  }

  statusEl.innerHTML = `已连接 fal.ai · 模型 <code>${esc(health.seedance.text_model || "")}</code>`;
  $("#btnSeedance").disabled = false;

  if (!seedance?.available) {
    $("#seedanceShots").innerHTML = `<p class="muted">当前项目无 AI 空镜镜头。请在竞品库重新「生成并去出稿」（规则模板会在第 2 镜生成 AI 空镜）。</p>`;
    $("#seedanceHint").textContent = "可先点「测试连接」验证密钥";
    panel.classList.remove("hidden");
    return;
  }

  $("#seedanceHint").textContent = "生成后 mp4 保存在 runs/…/broll/，并写入成稿库";
  $("#seedanceShots").innerHTML = (seedance.shots || []).map((s) => {
    const status = s.ready
      ? `<a href="/api/projects/${encodeURIComponent(slug)}/files/${encodeURI(s.file)}" target="_blank">下载 mp4</a>`
      : `<span class="muted">待生成</span>`;
    return `<div class="seedance-shot">
      <strong>镜 ${esc(s.number)} · ${esc(s.timing)}</strong>
      <p class="muted">${esc((s.prompt || "（无 Prompt）").slice(0, 160))}</p>
      ${status}
    </div>`;
  }).join("");
  panel.classList.remove("hidden");
}

function renderFeedback(feedback, ready) {
  const panel = $("#feedbackPanel");
  if (!ready || !feedback) {
    panel.classList.add("hidden");
    return;
  }
  panel.classList.remove("hidden");
  $("#fbEdits").value = feedback.manual_edits || "";
  $("#fbAdopted").value = feedback.adopted || "待定";
  $("#fbViews").value = (feedback.publish && feedback.publish.views) || "";
}

async function loadProject() {
  const slug = currentSlug();
  if (!slug) return;

  const data = await api(`/api/projects/${slug}`);
  if (!healthCache.seedance) {
    try {
      healthCache = await api("/api/health");
    } catch {
      healthCache = {};
    }
  }
  renderHead(data.brief);
  renderDownloads(slug, data.deliverables);
  renderSeedance(slug, data.seedance, healthCache);
  const ready = Boolean(data.delivery_ready);
  setPanel(ready);
  renderFeedback(data.feedback, ready);
}

function setBusy(btn, busy) {
  btn.disabled = busy;
  btn.dataset.orig ||= btn.textContent;
  btn.textContent = busy ? "生成中…" : btn.dataset.orig;
}

$("#btnFinish").addEventListener("click", async () => {
  const btn = $("#btnFinish");
  setBusy(btn, true);
  try {
    const data = await api(`/api/quick/${currentSlug()}/finish`, { method: "POST" });
    renderDownloads(currentSlug(), data.deliverables);
    if (!healthCache.seedance) healthCache = await api("/api/health");
    renderSeedance(currentSlug(), data.seedance, healthCache);
    setPanel(true);
    toast(data.message || "交付完成");
  } catch (err) {
    toast(err.message);
  } finally {
    setBusy(btn, false);
  }
});

$("#btnZip").addEventListener("click", async () => {
  const btn = $("#btnZip");
  setBusy(btn, true);
  try {
    await downloadZip();
    toast("已开始下载");
  } catch (err) {
    toast(err.message);
  } finally {
    setBusy(btn, false);
  }
});

$("#projectSelect").addEventListener("change", () => {
  history.replaceState(null, "", `?ref=${encodeURIComponent(currentSlug())}`);
  loadProject();
});

$("#btnSeedanceTest").addEventListener("click", async () => {
  const btn = $("#btnSeedanceTest");
  setBusy(btn, true);
  try {
    const data = await api("/api/seedance/test");
    if (data.ok) {
      toast(`连接成功（${data.latency_ms}ms）`);
      healthCache = await api("/api/health");
      await loadProject();
    } else {
      toast(data.message || "连接失败");
    }
  } catch (err) {
    toast(err.message);
  } finally {
    setBusy(btn, false);
  }
});

$("#btnFeedback").addEventListener("click", async () => {
  const slug = currentSlug();
  try {
    await api(`/api/library/feedback/${slug}`, {
      method: "POST",
      body: JSON.stringify({
        manual_edits: $("#fbEdits").value,
        adopted: $("#fbAdopted").value,
        publish_views: $("#fbViews").value,
      }),
    });
    toast("反馈已写入反馈库");
  } catch (err) {
    toast(err.message);
  }
});

$("#btnSeedance").addEventListener("click", async () => {
  const btn = $("#btnSeedance");
  setBusy(btn, true);
  try {
    const data = await api(`/api/projects/${currentSlug()}/seedance/run`, { method: "POST" });
    renderSeedance(currentSlug(), data.seedance);
    const failed = (data.seedance_results || []).filter((r) => r.status === "error");
    toast(failed.length ? failed[0].message : "AI 空镜处理完成");
  } catch (err) {
    toast(err.message);
  } finally {
    setBusy(btn, false);
  }
});

(async () => {
  await loadProjects();
  await loadProject();
  const params = new URLSearchParams(location.search);
  if (params.get("auto") === "1" && currentSlug()) {
    $("#btnFinish").click();
  }
})().catch((err) => toast(err.message));
