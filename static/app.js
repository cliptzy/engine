const $ = (id) => document.getElementById(id);

const I18N = {
  id: {
    "top.tagline": "Scan Most Replayed, potong otomatis, subtitle rapi.",
    "label.url": "YouTube URL",
    "ph.url": "https://www.youtube.com/watch?v=...",
    "help.url": "Tempel link video/shorts. Nanti keluar preview.",
    "label.mode": "Mode",
    "opt.mode.heatmap": "Scan heatmap (Most Replayed)",
    "opt.mode.custom": "Custom start/end (manual)",
    "help.mode": "Scan = cari momen paling rame. Custom = potong dari waktu yang kamu tentuin.",
    "label.ratio": "Ratio",
    "opt.ratio.9_16": "9:16 (Shorts)",
    "opt.ratio.original": "Original",
    "help.ratio": "Pilih bentuk output video. 9:16 buat Shorts/Reels/TikTok.",
    "label.crop": "Crop",
    "opt.crop.default": "Default",
    "opt.crop.split_left": "Split Left",
    "opt.crop.split_right": "Split Right",
    "help.crop": "Split itu buat gaming: atas gameplay, bawah facecam.",
    "label.padding": "Padding (detik)",
    "help.padding": "Nambah detik sebelum & sesudah momen biar nggak “kepotong nanggung”.",
    "label.max_clips": "Max clips",
    "help.max_clips": "Berapa potongan yang mau dihasilkan dari heatmap.",
    "label.subtitle": "Subtitle",
    "opt.no": "No",
    "opt.yes": "Yes",
    "help.subtitle": "Kalau Yes, audio ditranskrip jadi teks lalu dibakar ke video.",
    "label.whisper_model": "Model (Whisper)",
    "help.whisper_model": "Ini model AI buat transkripsi suara ke teks. Makin besar makin akurat, makin berat.",
    "label.subtitle_font": "Font Subtitle",
    "opt.custom": "Custom…",
    "ph.subtitle_font_custom": "Nama font custom (mis. Poppins)",
    "help.subtitle_font": "Kalau font-nya ada di folder fonts, isi Fonts dir = fonts.",
    "label.subtitle_location": "Subtitle Location",
    "opt.subtitle_location.bottom": "Bottom",
    "opt.subtitle_location.center": "Centered",
    "help.subtitle_location": "Bottom = lebih natural buat Shorts. Centered = lebih “in your face”.",
    "label.subtitle_fontsdir": "Fonts dir (opsional)",
    "help.subtitle_fontsdir": "Folder berisi file .ttf/.otf buat subtitle. Default: folder project <b>fonts</b>.",
    "label.start": "Start (detik atau mm:ss)",
    "ph.start": "689 atau 11:29",
    "label.end": "End (detik atau mm:ss)",
    "ph.end": "742 atau 12:22",
    "btn.scan": "Scan Heatmap",
    "btn.clip": "Buat Clip",
    "help.actions": "Scan Heatmap = ambil daftar momen “Most Replayed”. Buat Clip = download + crop + (opsional) subtitle.",
    "panel.segments": "Segments",
    "btn.select_all": "Select All",
    "btn.clear": "Clear",
    "btn.create_selected": "Create Selected Clip",
    "panel.progress": "Progress",
    "js.modal.preview_segment": "Preview Segment",
    "js.modal.preview_clip": "Preview Clip",
    "js.segments.empty": "Belum ada segment. Klik Scan Heatmap dulu.",
    "js.preview.loading": "Loading preview…",
    "js.progress.count": "{done}/{total} selesai • {success} sukses",
    "js.selected.count": "{count} dipilih",
    "js.stage.download": "Download",
    "js.stage.crop": "Crop",
    "js.stage.subtitle": "Subtitle",
    "js.stage.subtitle_model_load": "Load model",
    "js.stage.subtitle_transcribe": "Transcribe",
    "js.stage.subtitle_write": "Tulis subtitle",
    "js.stage.burn_subtitle": "Burn subtitle",
    "js.stage.finalize": "Finalize",
    "js.stage.done_clip": "Selesai",
    "js.topprogress.processing": "Processing",
  },
  en: {
    "top.tagline": "Scan Most Replayed, auto cut, clean subtitles.",
    "label.url": "YouTube URL",
    "ph.url": "https://www.youtube.com/watch?v=...",
    "help.url": "Paste a video/shorts link. Preview will show up.",
    "label.mode": "Mode",
    "opt.mode.heatmap": "Scan heatmap (Most Replayed)",
    "opt.mode.custom": "Custom start/end (manual)",
    "help.mode": "Scan = find the hottest moments. Custom = cut by your timestamps.",
    "label.ratio": "Ratio",
    "opt.ratio.9_16": "9:16 (Shorts)",
    "opt.ratio.original": "Original",
    "help.ratio": "Choose output aspect ratio. 9:16 is for Shorts/Reels/TikTok.",
    "label.crop": "Crop",
    "opt.crop.default": "Default",
    "opt.crop.split_left": "Split Left",
    "opt.crop.split_right": "Split Right",
    "help.crop": "Split is for gaming: gameplay on top, facecam below.",
    "label.padding": "Padding (seconds)",
    "help.padding": "Adds seconds before & after, so it doesn’t cut awkwardly.",
    "label.max_clips": "Max clips",
    "help.max_clips": "How many clips to generate from the heatmap.",
    "label.subtitle": "Subtitle",
    "opt.no": "No",
    "opt.yes": "Yes",
    "help.subtitle": "If Yes, audio is transcribed to text and burned into the video.",
    "label.whisper_model": "Model (Whisper)",
    "help.whisper_model": "AI model for speech-to-text. Bigger = more accurate, heavier.",
    "label.subtitle_font": "Subtitle Font",
    "opt.custom": "Custom…",
    "ph.subtitle_font_custom": "Custom font name (e.g. Poppins)",
    "help.subtitle_font": "If the font is in fonts folder, set Fonts dir = fonts.",
    "label.subtitle_location": "Subtitle Location",
    "opt.subtitle_location.bottom": "Bottom",
    "opt.subtitle_location.center": "Centered",
    "help.subtitle_location": "Bottom looks natural for Shorts. Centered is more “in your face”.",
    "label.subtitle_fontsdir": "Fonts dir (optional)",
    "help.subtitle_fontsdir": "Folder containing .ttf/.otf for subtitles. Default: project <b>fonts</b> folder.",
    "label.start": "Start (seconds or mm:ss)",
    "ph.start": "689 or 11:29",
    "label.end": "End (seconds or mm:ss)",
    "ph.end": "742 or 12:22",
    "btn.scan": "Scan Heatmap",
    "btn.clip": "Create Clip",
    "help.actions": "Scan Heatmap = fetch “Most Replayed” moments. Create Clip = download + crop + (optional) subtitles.",
    "panel.segments": "Segments",
    "btn.select_all": "Select All",
    "btn.clear": "Clear",
    "btn.create_selected": "Create Selected Clip",
    "panel.progress": "Progress",
    "js.modal.preview_segment": "Preview Segment",
    "js.modal.preview_clip": "Preview Clip",
    "js.segments.empty": "No segments yet. Click Scan Heatmap first.",
    "js.preview.loading": "Loading preview…",
    "js.progress.count": "{done}/{total} done • {success} success",
    "js.selected.count": "{count} selected",
    "js.stage.download": "Download",
    "js.stage.crop": "Crop",
    "js.stage.subtitle": "Subtitle",
    "js.stage.subtitle_model_load": "Load model",
    "js.stage.subtitle_transcribe": "Transcribe",
    "js.stage.subtitle_write": "Write subtitles",
    "js.stage.burn_subtitle": "Burn subtitles",
    "js.stage.finalize": "Finalize",
    "js.stage.done_clip": "Done",
    "js.topprogress.processing": "Processing",
  },
};

let currentLang = "id";

function t(key, vars) {
  const base = I18N[currentLang] || I18N.id;
  const fallback = I18N.id || {};
  let s = base[key] ?? fallback[key] ?? key;
  if (vars && typeof s === "string") {
    Object.entries(vars).forEach(([k, v]) => {
      s = s.replaceAll(`{${k}}`, String(v));
    });
  }
  return s;
}

const TOP_PROGRESS = {
  pct: 0,
  titleBase: document.title || "YouTube Heatmap Clipper",
  hideTimer: null,
};

function clamp(n, a, b) {
  return Math.min(b, Math.max(a, n));
}

function easeOutCubic(x) {
  const t = clamp(x, 0, 1);
  return 1 - Math.pow(1 - t, 3);
}

function stageLabel(stage) {
  const key = {
    download: "js.stage.download",
    crop: "js.stage.crop",
    subtitle: "js.stage.subtitle",
    subtitle_model_load: "js.stage.subtitle_model_load",
    subtitle_transcribe: "js.stage.subtitle_transcribe",
    subtitle_write: "js.stage.subtitle_write",
    burn_subtitle: "js.stage.burn_subtitle",
    finalize: "js.stage.finalize",
    done_clip: "js.stage.done_clip",
  }[stage];
  return key ? t(key) : stage || "";
}

function computeJobPct(job) {
  if (!job) return { pct: 0, text: "", active: false };
  const status = job.status || "";
  if (status !== "running" && status !== "queued") {
    const done = Number(job.done || 0);
    const total = Number(job.total || 0);
    const pct = total > 0 ? clamp((done / total) * 100, 0, 100) : 0;
    return { pct, text: "", active: false };
  }

  const total = Math.max(1, Number(job.total || 1));
  const done = clamp(Number(job.done || 0), 0, total);
  const subtitleEnabled = Boolean(job.subtitle_enabled);
  const stage = job.stage || "";
  const stageAt = job.stage_at ? Number(job.stage_at) : 0;
  const elapsed = stageAt ? Date.now() - stageAt : 0;
  const clipIndexRaw = Number(job.stage_clip || job.current || (done + 1) || 1);
  const clipIndex = clamp(clipIndexRaw, 1, total);

  const mapNoSub = {
    download: { a: 0.04, b: 0.62, d: 14000 },
    crop: { a: 0.62, b: 0.96, d: 9000 },
    finalize: { a: 0.96, b: 0.995, d: 2500 },
    done_clip: { a: 1, b: 1, d: 0 },
  };
  const mapSub = {
    download: { a: 0.03, b: 0.55, d: 14000 },
    crop: { a: 0.55, b: 0.86, d: 9000 },
    subtitle: { a: 0.86, b: 0.87, d: 1200 },
    subtitle_model_load: { a: 0.87, b: 0.885, d: 2500 },
    subtitle_transcribe: { a: 0.885, b: 0.93, d: 20000 },
    subtitle_write: { a: 0.93, b: 0.94, d: 1800 },
    burn_subtitle: { a: 0.94, b: 0.985, d: 12000 },
    finalize: { a: 0.985, b: 0.995, d: 2500 },
    done_clip: { a: 1, b: 1, d: 0 },
  };

  const table = subtitleEnabled ? mapSub : mapNoSub;
  const s = table[stage] || (subtitleEnabled ? mapSub.download : mapNoSub.download);
  const within = s.d > 0 ? s.a + (s.b - s.a) * easeOutCubic(clamp(elapsed / s.d, 0, 0.98)) : s.a;
  const pctBase = ((clipIndex - 1) + within) / total * 100;
  const pctFloor = (done / total) * 100;
  const pct = clamp(Math.max(pctBase, pctFloor), 0, 99.5);

  const clipText = total > 0 ? `clip ${clipIndex}/${total}` : "";
  const sLabel = stageLabel(stage);
  const text = [t("js.topprogress.processing"), clipText, sLabel].filter(Boolean).join(" • ");
  return { pct, text, active: true };
}

function renderTopProgress(job) {
  const wrap = $("topProgressWrap");
  const bar = $("topProgressBar");
  const textEl = $("topProgressText");
  if (!wrap || !bar || !textEl) return;

  const { pct, text, active } = computeJobPct(job);

  if (!active) {
    if (job && (job.status === "done" || job.status === "error")) {
      bar.style.width = "100%";
      textEl.textContent = job.status === "error" ? "Error" : "";
      wrap.classList.remove("hide");
      clearTimeout(TOP_PROGRESS.hideTimer);
      TOP_PROGRESS.hideTimer = setTimeout(() => {
        wrap.classList.add("hide");
        bar.style.width = "0%";
        textEl.textContent = "";
      }, 650);
      document.title = TOP_PROGRESS.titleBase;
      TOP_PROGRESS.pct = 0;
      return;
    }
    wrap.classList.add("hide");
    bar.style.width = "0%";
    textEl.textContent = "";
    document.title = TOP_PROGRESS.titleBase;
    TOP_PROGRESS.pct = 0;
    return;
  }

  clearTimeout(TOP_PROGRESS.hideTimer);
  wrap.classList.remove("hide");
  TOP_PROGRESS.pct = Math.max(TOP_PROGRESS.pct, pct);
  bar.style.width = `${TOP_PROGRESS.pct.toFixed(1)}%`;
  textEl.textContent = text;
  document.title = `${TOP_PROGRESS.titleBase} (${Math.round(TOP_PROGRESS.pct)}%)`;
}

function applyI18n() {
  document.documentElement.lang = currentLang;
  $("langId")?.classList.toggle("isActive", currentLang === "id");
  $("langEn")?.classList.toggle("isActive", currentLang === "en");

  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.dataset.i18n;
    if (!key) return;
    el.innerHTML = t(key);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    const key = el.dataset.i18nPlaceholder;
    if (!key) return;
    el.setAttribute("placeholder", t(key));
  });
}

function setLang(lang) {
  currentLang = lang === "en" ? "en" : "id";
  localStorage.setItem("lang", currentLang);
  applyI18n();
  renderSegments(lastScanSegments);
  updateSelectedUi();
}

function fmtTime(s) {
  const sec = Math.max(0, Math.floor(Number(s) || 0));
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const r = sec % 60;
  if (h > 0) return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(r).padStart(2, "0")}`;
  return `${String(m).padStart(2, "0")}:${String(r).padStart(2, "0")}`;
}

async function postJson(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.ok === false) {
    throw new Error(data.error || `HTTP ${res.status}`);
  }
  return data;
}

function openModal(title, bodyEl) {
  $("modalTitle").textContent = title || "";
  const root = $("modalBody");
  root.innerHTML = "";
  root.appendChild(bodyEl);
  $("modal").classList.remove("hide");
}

function closeModal() {
  $("modal").classList.add("hide");
  $("modalBody").innerHTML = "";
}

function debounce(fn, wait) {
  let t = null;
  return (...args) => {
    if (t) clearTimeout(t);
    t = setTimeout(() => fn(...args), wait);
  };
}

function readPayload() {
  const fontSel = $("subtitle_font_select").value;
  const fontCustom = ($("subtitle_font_custom").value || "").trim();
  const subtitleFont = fontSel === "custom" ? fontCustom : fontSel;
  return {
    url: $("url").value,
    mode: $("mode").value,
    ratio: $("ratio").value,
    crop: $("crop").value,
    padding: Number($("padding").value || 0),
    max_clips: Number($("max_clips").value || 6),
    subtitle: $("subtitle").value === "y",
    whisper_model: $("whisper_model").value,
    subtitle_font: subtitleFont,
    subtitle_location: $("subtitle_location").value,
    subtitle_delay: Number($("subtitle_delay").value || 0.0),
    subtitle_fontsdir: $("subtitle_fontsdir").value || "",
    start: $("start").value || "",
    end: $("end").value || "",
  };
}

function setBusy(busy) {
  $("scanBtn").disabled = busy;
  $("clipBtn").disabled = busy;
  $("segSelectAllBtn").disabled = busy;
  $("segClearBtn").disabled = busy;
  $("segCreateBtn").disabled = busy || selectedKeys.size === 0;
}

function getVideoThumb(videoId, fallback) {
  if (!videoId) return fallback || "";
  return `https://i.ytimg.com/vi_webp/${videoId}/hqdefault.webp`;
}

function openYouTubePreview(videoId, startSec, endSec, title) {
  const start = Math.max(0, Math.floor(Number(startSec) || 0));
  const end = Math.max(0, Math.floor(Number(endSec) || 0));
  const url = `https://www.youtube.com/embed/${encodeURIComponent(videoId)}?start=${start}${end > start ? `&end=${end}` : ""}&autoplay=1&playsinline=1&rel=0`;
  const iframe = document.createElement("iframe");
  iframe.className = "embed";
  iframe.src = url;
  iframe.allow = "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share";
  iframe.allowFullscreen = true;
  openModal(title || t("js.modal.preview_segment"), iframe);
}

function openClipPreview(title, src) {
  const v = document.createElement("video");
  v.className = "video";
  v.controls = true;
  v.autoplay = true;
  v.muted = true;
  v.playsInline = true;
  v.src = src;
  openModal(title || t("js.modal.preview_clip"), v);
}

function segKey(seg) {
  const start = Math.round(Number(seg.start || 0) * 1000);
  const dur = Math.round(Number(seg.duration || 0) * 1000);
  return `${start}:${dur}`;
}

function setSegControlsVisible(visible) {
  $("segControls").classList.toggle("hide", !visible);
}

function updateSelectedUi() {
  const count = selectedKeys.size;
  $("segSelectedMeta").textContent = count > 0 ? t("js.selected.count", { count }) : "";
  $("segCreateBtn").disabled = count === 0 || $("scanBtn").disabled;
  setSegControlsVisible($("mode").value === "heatmap" && lastScanSegments.length > 0);
}

function selectAllSegments() {
  selectedKeys = new Set(lastScanSegments.map(segKey));
  renderSegments(lastScanSegments);
  updateSelectedUi();
}

function clearSelectedSegments() {
  selectedKeys = new Set();
  renderSegments(lastScanSegments);
  updateSelectedUi();
}

async function clipSelected() {
  if ($("mode").value !== "heatmap") return;
  if (selectedKeys.size === 0) return;
  
  const btn = $("segCreateBtn");
  const prevTxt = btn.innerText;
  btn.innerText = "Creating...";
  setBusy(true);
  
  try {
    const payload = readPayload();
    const picked = lastScanSegments.filter((s) => selectedKeys.has(segKey(s)));
    const data = await postJson("/api/clip", { ...payload, segments: picked });
    const jobId = data.job_id;
    await pollJob(jobId);
  } catch (e) {
    renderProgress({ status: "error", error: e.message, total: 0, done: 0, id: "" });
  } finally {
    btn.innerText = prevTxt;
    setBusy(false);
    updateSelectedUi();
  }
}

function renderSegments(segments) {
  const root = $("segments");
  root.innerHTML = "";
  if (!segments || segments.length === 0) {
    root.innerHTML = `<div class="small">${t("js.segments.empty")}</div>`;
    updateSelectedUi();
    return;
  }
  segments.forEach((s, idx) => {
    const start = Number(s.start || 0);
    const dur = Number(s.duration || 0);
    const end = start + dur;
    const score = Number(s.score || 0);
    const el = document.createElement("div");
    const key = segKey(s);
    el.className = "flex gap-4 border-4 border-black p-2 bg-white brutal-shadow cursor-pointer transition-transform hover:-translate-y-1 mb-4" + (selectedKeys.has(key) ? " bg-pink-200" : "");
    const thumb = getVideoThumb(currentVideoId, currentPreview?.thumbnail);
    el.innerHTML = `
      <div class="relative w-32 shrink-0 border-4 border-black bg-black">
        <img alt="" src="${thumb}" class="w-full h-full object-cover opacity-80 hover:opacity-100" />
        <div class="absolute bottom-1 right-1 bg-black text-white font-bold text-xs px-1 border-2 border-white">${fmtTime(start)}</div>
      </div>
      <div class="flex-1 flex flex-col justify-center">
        <div class="font-bold text-lg uppercase">#${idx + 1} ${fmtTime(start)} → ${fmtTime(end)}</div>
        <div class="text-sm font-bold opacity-80">durasi ${Math.round(dur)}s</div>
      </div>
      <div class="flex flex-col justify-between items-end">
        <div class="bg-yellow-400 border-2 border-black font-bold px-2 py-1 text-sm brutal-shadow-hover">${score.toFixed(2)}</div>
        <button class="bg-cyan-300 border-2 border-black font-bold px-2 py-1 text-sm brutal-shadow-hover" type="button" data-preview="1">Preview</button>
      </div>
    `;
    el.addEventListener("click", (ev) => {
      const target = ev.target;
      if (target && target.dataset && target.dataset.preview) {
        ev.preventDefault();
        ev.stopPropagation();
        if (currentVideoId) openYouTubePreview(currentVideoId, start, end, currentPreview?.title || "Preview Segment");
        return;
      }
      if ($("mode").value === "custom") {
        $("start").value = Math.floor(start);
        $("end").value = Math.floor(end);
        return;
      }
      if (selectedKeys.has(key)) {
        selectedKeys.delete(key);
        el.classList.remove("bg-pink-200");
      } else {
        selectedKeys.add(key);
        el.classList.add("bg-pink-200");
      }
      updateSelectedUi();
    });
    root.appendChild(el);
  });
  updateSelectedUi();
}

function renderProgress(job) {
  const root = $("progress");
  const meta = $("jobMeta");
  const out = $("outputs");
  root.innerHTML = "";
  out.innerHTML = "";
  meta.textContent = "";
  if (!job) return;
  renderTopProgress(job);
  const total = Number(job.total || 0);
  const done = Number(job.done || 0);
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;
  const stage = stageLabel(job.stage || "");
  meta.textContent = `${job.status} • ${(job.status_text || "").trim()}${stage ? " • " + stage : ""}`.trim();

  const bar = document.createElement("div");
  bar.innerHTML = `<div class="w-full h-6 border-4 border-black bg-white brutal-shadow relative overflow-hidden"><div class="absolute top-0 left-0 h-full bg-cyan-300 border-r-4 border-black transition-all duration-300" style="width:${pct}%"></div></div>`;
  root.appendChild(bar);

  const line = document.createElement("div");
  line.className = "text-sm font-bold mt-2";
  line.textContent =
    total > 0
      ? t("js.progress.count", { done, total, success: job.success || 0 })
      : "";
  root.appendChild(line);

  if (job.status === "error") {
    const err = document.createElement("div");
    err.className = "small";
    err.textContent = job.error || "error";
    root.appendChild(err);
  }

  if (Array.isArray(job.outputs) && job.outputs.length > 0) {
    job.outputs.forEach((f) => {
      const el = document.createElement("div");
      el.className = "flex justify-between items-center bg-white border-4 border-black p-4 brutal-shadow";
      const href = `/clips/${job.id}/${encodeURIComponent(f.name)}`;
      el.innerHTML = `
        <div>
          <a href="${href}" target="_blank" rel="noreferrer" class="font-bold text-lg underline hover:text-blue-600">${f.name}</a>
          <div class="text-sm font-bold opacity-80">${Math.round((f.size || 0) / 1024)} KB</div>
        </div>
        <div class="flex gap-2">
          <button class="bg-yellow-400 border-2 border-black font-bold px-4 py-2 brutal-shadow-hover" type="button" data-play="1">Play</button>
          <a class="bg-cyan-300 border-2 border-black font-bold px-4 py-2 brutal-shadow-hover text-black no-underline" href="${href}" download>Download</a>
        </div>
      `;
      el.querySelector("[data-play]")?.addEventListener("click", (ev) => {
        ev.preventDefault();
        openClipPreview(f.name, href);
      });
      out.appendChild(el);
    });
  }

  const consoleLog = $("consoleLog");
  if (consoleLog) {
    if (job.logs && job.logs.length > 0) {
      consoleLog.classList.remove("hide");
      const isScrolledToBottom = consoleLog.scrollHeight - consoleLog.clientHeight <= consoleLog.scrollTop + 5;
      
      consoleLog.textContent = job.logs.join("\n");
      
      if (isScrolledToBottom) {
        consoleLog.scrollTop = consoleLog.scrollHeight;
      }
    } else {
      consoleLog.classList.add("hide");
      consoleLog.textContent = "";
    }
  }
}

let lastScanSegments = [];
let lastPreviewUrl = "";
let currentPreview = null;
let currentVideoId = "";
let selectedKeys = new Set();

async function scan() {
  const btn = $("scanBtn");
  const prevTxt = btn.innerText;
  btn.innerText = "Scanning...";
  setBusy(true);
  
  try {
    const { url } = readPayload();
    const data = await postJson("/api/scan", { url });
    lastScanSegments = data.segments || [];
    selectedKeys = new Set();
    currentVideoId = data.video_id || currentVideoId;
    $("segMeta").textContent = `${lastScanSegments.length} segments • durasi ~${fmtTime(data.duration || 0)}`;
    renderSegments(lastScanSegments);
  } catch (e) {
    $("segMeta").textContent = e.message;
    renderSegments([]);
  } finally {
    btn.innerText = prevTxt;
    setBusy(false);
    updateSelectedUi();
  }
}

async function preview() {
  const url = $("url").value.trim();
  if (!url || url === lastPreviewUrl) return;
  lastPreviewUrl = url;
  const box = $("preview");
  const title = $("pvTitle");
  const sub = $("pvSub");
  const img = $("thumbImg");
  try {
    title.textContent = t("js.preview.loading");
    sub.textContent = "";
    img.removeAttribute("src");
    box.classList.remove("hide");
    const data = await postJson("/api/preview", { url });
    const p = data.preview || {};
    currentPreview = p;
    if (p.id) currentVideoId = p.id;
    title.textContent = p.title || "Untitled";
    const dur = p.duration != null ? fmtTime(p.duration) : "";
    const uploader = p.uploader || "";
    sub.textContent = [uploader, dur].filter(Boolean).join(" • ");
    if (p.thumbnail) img.src = p.thumbnail;
  } catch (e) {
    box.classList.add("hide");
  }
}

async function clip() {
  const btn = $("clipBtn");
  const prevTxt = btn.innerText;
  btn.innerText = "Creating...";
  setBusy(true);
  
  try {
    const payload = readPayload();
    const data = await postJson("/api/clip", payload);
    const jobId = data.job_id;
    await pollJob(jobId);
  } catch (e) {
    renderProgress({ status: "error", error: e.message, total: 0, done: 0, id: "" });
  } finally {
    btn.innerText = prevTxt;
    setBusy(false);
  }
}

async function pollJob(jobId) {
  const started = Date.now();
  while (true) {
    const res = await fetch(`/api/job/${jobId}`);
    const data = await res.json().catch(() => null);
    if (!data || !data.ok) throw new Error("Job not found");
    renderProgress(data.job);
    if (data.job.status === "done" || data.job.status === "error") return;
    if (Date.now() - started > 1000 * 60 * 30) throw new Error("Timeout");
    await new Promise((r) => setTimeout(r, 1500));
  }
}

function toggleMode() {
  const isCustom = $("mode").value === "custom";
  $("customBox").classList.toggle("hide", !isCustom);
  $("scanBtn").classList.toggle("hide", isCustom);
  if (isCustom) {
    setSegControlsVisible(false);
    $("segSelectedMeta").textContent = "";
  } else {
    setSegControlsVisible(lastScanSegments.length > 0);
    updateSelectedUi();
  }
}

function toggleFont() {
  const isCustom = $("subtitle_font_select").value === "custom";
  $("subtitle_font_custom").classList.toggle("hide", !isCustom);
}

$("mode").addEventListener("change", toggleMode);
$("subtitle_font_select").addEventListener("change", toggleFont);
$("cekUrlBtn")?.addEventListener("click", preview);
$("scanBtn").addEventListener("click", scan);
$("clipBtn").addEventListener("click", clip);
$("segSelectAllBtn").addEventListener("click", selectAllSegments);
$("segClearBtn").addEventListener("click", clearSelectedSegments);
$("segCreateBtn").addEventListener("click", clipSelected);
$("modalClose").addEventListener("click", closeModal);
$("modalBackdrop").addEventListener("click", closeModal);
$("langId")?.addEventListener("click", () => setLang("id"));
$("langEn")?.addEventListener("click", () => setLang("en"));

$("themeToggle")?.addEventListener("click", () => {
  document.documentElement.classList.toggle("dark");
  const isDark = document.documentElement.classList.contains("dark");
  localStorage.setItem("theme", isDark ? "dark" : "light");
});

$("uploadCookiesBtn")?.addEventListener("click", async () => {
  const fileInput = $("cookies_file");
  if (!fileInput.files.length) {
    alert("Please select a cookies.txt file first!");
    return;
  }

  const btn = $("uploadCookiesBtn");
  const prevText = btn.innerText;
  btn.innerText = "Uploading...";
  btn.disabled = true;

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  try {
    const res = await fetch("/api/cookies", {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    if (data.ok) {
      $("cookieStatus").classList.remove("hide");
      checkCookieStatus();
      setTimeout(() => {
        $("cookieStatus").classList.add("hide");
      }, 3000);
    } else {
      alert("Upload failed: " + data.error);
    }
  } catch (e) {
    alert("Error: " + e.message);
  } finally {
    btn.innerText = prevText;
    btn.disabled = false;
  }
});

$("uploadIntroBtn")?.addEventListener("click", async () => {
  const fileInput = $("intro_file");
  if (!fileInput.files.length) return alert("Select intro video first!");
  const btn = $("uploadIntroBtn");
  const prev = btn.innerText;
  btn.innerText = "Uploading...";
  btn.disabled = true;
  const fd = new FormData();
  fd.append("file", fileInput.files[0]);
  try {
    const res = await fetch("/api/intro", { method: "POST", body: fd });
    const data = await res.json();
    if (data.ok) checkAssetStatus();
    else alert("Upload failed: " + data.error);
  } catch (e) {
    alert("Error: " + e.message);
  } finally {
    btn.innerText = prev;
    btn.disabled = false;
  }
});

$("uploadOutroBtn")?.addEventListener("click", async () => {
  const fileInput = $("outro_file");
  if (!fileInput.files.length) return alert("Select outro video first!");
  const btn = $("uploadOutroBtn");
  const prev = btn.innerText;
  btn.innerText = "Uploading...";
  btn.disabled = true;
  const fd = new FormData();
  fd.append("file", fileInput.files[0]);
  try {
    const res = await fetch("/api/outro", { method: "POST", body: fd });
    const data = await res.json();
    if (data.ok) checkAssetStatus();
    else alert("Upload failed: " + data.error);
  } catch (e) {
    alert("Error: " + e.message);
  } finally {
    btn.innerText = prev;
    btn.disabled = false;
  }
});

$("clearLogsBtn")?.addEventListener("click", async () => {
  try {
    const res = await fetch("/api/logs", { method: "DELETE" });
    const data = await res.json();
    if (data.ok) {
      alert("Logs cleared successfully.");
      const consoleLog = $("consoleLog");
      if (consoleLog) {
        consoleLog.textContent = "";
        consoleLog.classList.add("hide");
      }
    } else {
      alert("Failed to clear logs: " + data.error);
    }
  } catch (e) {
    alert("Error: " + e.message);
  }
});

async function checkCookieStatus() {
  try {
    const res = await fetch("/api/cookies/status");
    const data = await res.json();
    const statusText = $("cookieStatusText");
    if (statusText) {
      if (data.exists) {
        statusText.textContent = "Cookies are loaded and active.";
        statusText.classList.remove("text-red-600");
        statusText.classList.add("text-green-600");
      } else {
        statusText.textContent = "No cookies loaded.";
        statusText.classList.remove("text-green-600");
        statusText.classList.add("text-red-600");
      }
    }
  } catch (e) {
    console.error("Failed to check cookie status", e);
  }
}

async function checkAssetStatus() {
  try {
    const res = await fetch("/api/assets/status");
    const data = await res.json();
    if ($("introStatusText")) {
      if (data.has_intro) {
        $("introStatusText").textContent = "Intro loaded.";
        $("introStatusText").className = "text-xs font-bold text-green-600 mt-1";
      } else {
        $("introStatusText").textContent = "No intro loaded.";
        $("introStatusText").className = "text-xs font-bold text-red-600 mt-1";
      }
    }
    if ($("outroStatusText")) {
      if (data.has_outro) {
        $("outroStatusText").textContent = "Outro loaded.";
        $("outroStatusText").className = "text-xs font-bold text-green-600 mt-1";
      } else {
        $("outroStatusText").textContent = "No outro loaded.";
        $("outroStatusText").className = "text-xs font-bold text-red-600 mt-1";
      }
    }
  } catch (e) {}
}

checkCookieStatus();
checkAssetStatus();

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeModal();
});

currentLang = localStorage.getItem("lang") || document.documentElement.lang || "id";
currentLang = currentLang === "en" ? "en" : "id";
if (localStorage.getItem("theme") === "dark") {
  document.documentElement.classList.add("dark");
}
applyI18n();
toggleMode();
toggleFont();
renderSegments([]);
checkCookieStatus();
