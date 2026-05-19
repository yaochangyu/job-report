import Chart from "https://cdn.jsdelivr.net/npm/chart.js@4.4.7/auto/+esm";

// ── 顏色常數 ──────────────────────────────────────────────────────
const C = {
  blue:   "#4361ee",
  cyan:   "#118ab2",
  purple: "#7209b7",
  pink:   "#f72585",
  green:  "#06d6a0",
  orange: "#fb8500",
  red:    "#e63946",
  teal:   "#14b8a6",
  palette: ["#4361ee","#7209b7","#f72585","#06d6a0","#fb8500","#118ab2","#e63946","#14b8a6","#ffd166","#ef233c"],
};

// ── Chart.js 工具 ─────────────────────────────────────────────────
const chartCache = new Map();

function destroyChart(id) {
  const c = chartCache.get(id);
  if (c) { c.destroy(); chartCache.delete(id); }
}

function makeChart(id, config) {
  destroyChart(id);
  const canvas = document.getElementById(id);
  if (!canvas) return;
  chartCache.set(id, new Chart(canvas, config));
}

const baseOpts = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { position: "bottom" } },
};

function lineChart(id, labels, datasets) {
  makeChart(id, {
    type: "line",
    data: { labels, datasets },
    options: { ...baseOpts, interaction: { mode: "index", intersect: false } },
  });
}

function barChart(id, labels, datasets, opts = {}) {
  makeChart(id, {
    type: "bar",
    data: { labels, datasets },
    options: { ...baseOpts, ...opts },
  });
}

function barHChart(id, labels, datasets) {
  makeChart(id, {
    type: "bar",
    data: { labels, datasets },
    options: {
      ...baseOpts,
      indexAxis: "y",
      plugins: { legend: { display: false } },
    },
  });
}

function doughnutChart(id, rows, labelKey = "name", valueKey = "count") {
  makeChart(id, {
    type: "doughnut",
    data: {
      labels: rows.map(r => r[labelKey]),
      datasets: [{ data: rows.map(r => n(r[valueKey])), backgroundColor: C.palette }],
    },
    options: { ...baseOpts },
  });
}

function emptyChart(id, type = "bar") {
  makeChart(id, {
    type,
    data: { labels: [], datasets: [{ label: "—", data: [] }] },
    options: baseOpts,
  });
}

// ── DOM 工具 ──────────────────────────────────────────────────────
function setText(id, v) { const e = document.getElementById(id); if (e) e.textContent = v; }
function n(v) { return Number(v ?? 0); }
function fmt(v) { return n(v).toLocaleString(); }
function pct(v) { return `${n(v).toFixed(1)}%`; }
function pct2(v) { return `${n(v).toFixed(2)}%`; }

// KPI card helpers
function setKpiCard(id, label, value, sub) {
  setText(`kpi-label-${id}`, label);
  setText(`kpi-${id}`, value);
  setText(`kpi-sub-${id}`, sub ?? "");
}

// table builder helpers
function buildTableHead(id, cols) {
  const el = document.getElementById(id);
  if (!el) return;
  el.innerHTML = `<tr>${cols.map(c => `<th>${c}</th>`).join("")}</tr>`;
}

function buildTableBody(id, rows, mapper) {
  const el = document.getElementById(id);
  if (!el) { return; }
  if (!rows?.length) {
    el.innerHTML = '<tr><td colspan="99" class="empty-cell">查詢沒有結果</td></tr>';
    return;
  }
  el.innerHTML = rows.map((row, i) => mapper(row, i)).join("");
}

// 標準排行 tbody 一行（#, name, value, bar, pct%, extra...）
function rankRow(index, name, val, total, ...extras) {
  const barPct = total ? ((val / total) * 100).toFixed(1) : "0";
  const pctStr = total ? `${((val / total) * 100).toFixed(1)}%` : "—";
  const extCells = extras.map(e => `<td>${e ?? "—"}</td>`).join("");
  return `<tr>
    <td class="rank">${index + 1}</td>
    <td>${name ?? "—"}</td>
    <td>${fmt(val)}</td>
    <td class="bar-cell"><div class="bar-bg"><div class="bar-fill" style="width:${barPct}%"></div></div></td>
    <td class="pct">${pctStr}</td>
    ${extCells}
  </tr>`;
}

// ── 視角 panel 文字對應 ───────────────────────────────────────────
const VIEW_PANEL_TEXT = {
  overview: {
    chart1: ["每日流量趨勢", "View / Click / Apply + Unique Sessions"],
    chart2: ["裝置分佈", "Mobile vs Desktop"],
    chart3: ["OS 分佈", "Top 16 作業系統"],
    table1: ["OS 詳細數據", ""],
    table2: ["瀏覽器 Top 10", ""],
  },
  search: {
    chart1: ["搜尋功能使用量總覽", "各搜尋類型事件數比較"],
    chart2: ["AI vs 一般搜尋每日趨勢", "click 數量 + AI 佔比"],
    chart3: ["搜尋結果頁分佈", "job / corp / gig / intern 佔比"],
    table1: ["搜尋功能 featureId 詳細數據", ""],
  },
  apply: {
    chart1: ["應徵每日趨勢", "職缺頁瀏覽 + 應徵數"],
    chart2: ["轉換漏斗", "各環節事件數"],
    chart3: ["應徵裝置分佈", "mobile vs desktop"],
    table1: ["應徵裝置詳細", ""],
    table2: ["應徵 OS 分佈", ""],
    table3: ["應徵來源詳細數據", ""],
  },
  feature: {
    chart1: ["探索職缺 — categoryTab 分佈", "各 Tab 點擊分佈"],
    chart2: ["探索企業 — featureId 分佈", "各企業探索入口使用量"],
    chart3: ["身份辨識 — 主身份分佈", "各身份入口點擊數"],
    table1: ["身份辨識詳細數據", ""],
    table2: ["新聞互動詳細數據", ""],
  },
  device: {
    chart1: ["裝置類型每日趨勢", "mobile vs desktop + mobile 佔比（右 Y 軸）"],
    chart2: ["OS 分佈", "Top 15 作業系統"],
    chart3: ["瀏覽器分佈", "Top 10 瀏覽器"],
    table1: ["OS 詳細數據", ""],
    table2: ["瀏覽器詳細數據", ""],
    table3: ["裝置 × 行為交叉分析", "各裝置 view/click/apply 分佈與應徵轉換率"],
    table4: ["OS × 行為交叉分析", "各 OS view/click/apply 分佈"],
  },
  ranking: {
    chart1: ["Top 20 功能流量排行", "依總事件數排序（顏色代表類別）"],
    chart2: ["功能類別佔比", "各功能類別事件數比例"],
    chart3: [],
    table1: ["完整 featureId 排行", ""],
  },
  navigation: {
    chart1: ["初始進入頁面分佈", "無 previousPageName 的首次瀏覽分佈"],
    chart2: ["Top 20 頁面轉換路徑", "previousPage → page 轉換次數"],
    chart3: [],
    table1: ["各頁面 Top 來源（從哪來）", "每個頁面最常見的上一頁 Top 5"],
    table2: ["各頁面 Top 目標（往哪去）", "離開頁面後最常前往的下一頁 Top 5"],
    table3: ["完整轉換路徑排行", ""],
  },
  heatmap: {
    chart1: ["Top 20 點擊功能", "依點擊數排序"],
    chart2: ["頁面點擊分佈", "各頁面點擊量佔比"],
    chart3: [],
    table1: ["featureId 點擊排行", ""],
  },
  "homepage-blocks": {
    chart1: ["各類別每日點擊趨勢", "搜尋 / 身分 / 探索工作 / 探索企業"],
    chart2: ["各類別點擊佔比", "4 大區塊分佈"],
    chart3: ["Top featureId 點擊", "依點擊數排序"],
    table1: ["各 featureId 點擊詳細", "含所屬區塊"],
  },
};

// ── panel title 更新 ─────────────────────────────────────────────
function applyPanelText(viewMode) {
  const t = VIEW_PANEL_TEXT[viewMode] || VIEW_PANEL_TEXT.overview;
  if (t.chart1?.length) { setText("chart1-title", t.chart1[0]); setText("chart1-desc", t.chart1[1]); }
  if (t.chart2?.length) { setText("chart2-title", t.chart2[0]); setText("chart2-desc", t.chart2[1]); }
  if (t.chart3?.length) { setText("chart3-title", t.chart3[0]); setText("chart3-desc", t.chart3[1]); }
  if (t.table1?.length) { setText("table1-title", t.table1[0]); setText("table1-desc", t.table1[1]); }
  if (t.table2?.length) { setText("table2-title", t.table2[0]); setText("table2-desc", t.table2[1]); }
  if (t.table3?.length) { setText("table3-title", t.table3[0]); setText("table3-desc", t.table3[1]); }
  if (t.table4?.length) { setText("table4-title", t.table4[0]); setText("table4-desc", t.table4[1]); }
}

// ── panel 顯示/隱藏 ──────────────────────────────────────────────
function showPanels(viewMode) {
  const isMonthly = viewMode === "monthly-report";

  // monthly-report 用自訂區塊，隱藏所有標準面板
  document.querySelector(".kpi-grid")?.classList.toggle("hidden", isMonthly);
  document.querySelector(".chart-grid")?.classList.toggle("hidden", isMonthly);
  document.getElementById("monthly-section")?.classList.toggle("hidden", !isMonthly);

  if (isMonthly) {
    for (let i = 1; i <= 4; i++) document.getElementById(`table${i}-panel`)?.classList.add("hidden");
    document.getElementById("chart3-panel")?.classList.add("hidden");
    return;
  }

  // chart panels
  const charts3 = ["overview","search","apply","feature","device","homepage-blocks"];
  const charts2 = ["ranking","navigation","heatmap"];
  document.getElementById("chart3-panel")?.classList.toggle("hidden", charts2.includes(viewMode));

  // table panels — 各視角顯示不同數量
  const tableCount = {
    overview: 2, search: 1, apply: 3, feature: 2,
    device: 4, ranking: 1, navigation: 3, heatmap: 1,
    "homepage-blocks": 1,
  };
  const count = tableCount[viewMode] ?? 1;
  for (let i = 1; i <= 4; i++) {
    document.getElementById(`table${i}-panel`)?.classList.toggle("hidden", i > count);
  }
}

// ════════════════════════════════════════════════════════════════
// 1. 整體概覽
// ════════════════════════════════════════════════════════════════
function overviewRenderer(data) {
  const kpi = data.kpi?.[0] ?? {};
  const total = n(kpi.total);
  const views = n(kpi.views);
  const clicks = n(kpi.clicks);
  const applies = n(kpi.applies);
  const sessions = n(kpi.sessions);
  const ctr = total ? (clicks / total) * 100 : 0;
  const applyRate = views ? (applies / views) * 100 : 0;

  setKpiCard("1", "總事件數", fmt(total), "View + Click");
  setKpiCard("2", "View",    fmt(views),   `佔 ${total ? ((views/total)*100).toFixed(1) : 0}%`);
  setKpiCard("3", "Click",   fmt(clicks),  `佔 ${total ? ((clicks/total)*100).toFixed(1) : 0}%`);
  setKpiCard("4", "Apply",   fmt(applies), `轉換率 ${pct2(applyRate)}（Apply / Job Page View）`);
  setKpiCard("5", "Unique Sessions", fmt(sessions), "依 sessionId 去重");
  setKpiCard("6", "Click Rate",  pct(ctr),       "Click / 總事件數");
  setKpiCard("7", "Apply Rate",  pct2(applyRate), "Apply / 總事件數中的 View");

  // Mobile % 從 device_dist 計算
  const deviceDist = data.device_dist ?? [];
  const mobileRow  = deviceDist.find(r => r.name === "mobile");
  const mobileCount = mobileRow ? n(mobileRow.count) : 0;
  const deviceTotal = deviceDist.reduce((s, r) => s + n(r.count), 0);
  const mobilePct = deviceTotal ? (mobileCount / deviceTotal) * 100 : 0;
  setKpiCard("8", "Mobile %", pct(mobilePct), `共 ${fmt(mobileCount)} 筆`);

  // 圖表 1 — 每日流量趨勢
  const trend = data.daily_trend ?? [];
  lineChart("chart1", trend.map(r => r.date), [
    { label: "View",    data: trend.map(r => n(r.views)),    borderColor: C.blue,   tension: 0.3, fill: false },
    { label: "Click",   data: trend.map(r => n(r.clicks)),   borderColor: C.purple, tension: 0.3, fill: false },
    { label: "Apply",   data: trend.map(r => n(r.applies)),  borderColor: C.pink,   tension: 0.3, fill: false, yAxisID: "y1" },
    { label: "Sessions",data: trend.map(r => n(r.sessions)), borderColor: C.green,  tension: 0.3, fill: false, yAxisID: "y1" },
  ]);

  // 圖表 2 — 裝置分佈
  doughnutChart("chart2", data.device_dist ?? []);

  // 圖表 3 — OS 分佈
  const osDist = data.os_dist ?? [];
  barHChart("chart3", osDist.map(r => r.name), [
    { label: "事件數", data: osDist.map(r => n(r.count)), backgroundColor: C.palette },
  ]);

  // 表格 1 — OS 詳細
  buildTableHead("table1-head", ["#","OS","事件數","佔比"]);
  const osTotal = osDist.reduce((s, r) => s + n(r.count), 0);
  buildTableBody("table1-body", osDist, (r, i) => rankRow(i, r.name, n(r.count), osTotal));

  // 表格 2 — 瀏覽器 Top 10
  buildTableHead("table2-head", ["#","瀏覽器","事件數","佔比"]);
  const bTop = data.browser_top ?? [];
  const bTotal = bTop.reduce((s, r) => s + n(r.count), 0);
  buildTableBody("table2-body", bTop, (r, i) => rankRow(i, r.name, n(r.count), bTotal));
}

// ════════════════════════════════════════════════════════════════
// 2. 搜尋行為
// ════════════════════════════════════════════════════════════════
function searchRenderer(data) {
  const kpi = data.kpi?.[0] ?? {};
  const genClick = n(kpi.general_click_total);
  const genView  = n(kpi.general_view_total);
  const aiClick  = n(kpi.ai_click_total);
  const aiView   = n(kpi.ai_view_total);
  const aiPct    = (genClick + aiClick) ? (aiClick / (genClick + aiClick)) * 100 : 0;

  setKpiCard("1", "一般搜尋 Click", fmt(genClick),  "keyword/submit/general");
  setKpiCard("2", "一般搜尋 View",  fmt(genView),   "keyword/submit/general");
  setKpiCard("3", "AI 搜尋 Click",  fmt(aiClick),   `AI 佔搜尋 Click ${pct(aiPct)}`);
  setKpiCard("4", "AI 搜尋 View",   fmt(aiView),    "search-ai-*");
  setKpiCard("5", "快速篩選 Click", fmt(n(kpi.quick_click_total)),        "地區 / 職類篩選");
  setKpiCard("6", "快速篩選 View",  fmt(n(kpi.quick_view_total)),         "地區 / 職類篩選");
  setKpiCard("7", "搜尋結果頁 Click", fmt(n(kpi.search_page_click_total)), "job/corp/gig/intern");
  setKpiCard("8", "搜尋結果頁 View",  fmt(n(kpi.search_page_view_total)),  "job/corp/gig/intern");

  // 圖表 1 — 各搜尋類型 click bar
  const detail = (data.feature_detail ?? []).filter(r => r.event_type === "click");
  barChart("chart1", detail.map(r => r.feature_id), [
    { label: "Click 數", data: detail.map(r => n(r.count)), backgroundColor: C.palette },
  ], { indexAxis: "y", plugins: { legend: { display: false } } });

  // 圖表 2 — AI vs 一般搜尋每日趨勢（click 實線／view 虛線）
  const dt = data.daily_trend ?? [];
  lineChart("chart2", dt.map(r => r.date), [
    { label: "一般搜尋 Click", data: dt.map(r => n(r.general_click)), borderColor: C.blue,   tension: 0.3, fill: false },
    { label: "AI 搜尋 Click",  data: dt.map(r => n(r.ai_click)),      borderColor: C.purple, tension: 0.3, fill: false },
    { label: "一般搜尋 View",  data: dt.map(r => n(r.general_view)),  borderColor: C.blue,   tension: 0.3, fill: false, borderDash: [4,3] },
    { label: "AI 搜尋 View",   data: dt.map(r => n(r.ai_view)),       borderColor: C.purple, tension: 0.3, fill: false, borderDash: [4,3] },
  ]);

  // 圖表 3 — 搜尋結果頁分佈（click）
  doughnutChart("chart3", data.search_page_dist ?? []);

  // 表格 1 — featureId × event_type 詳細
  buildTableHead("table1-head", ["#","featureId","featureName","event_type","事件數","佔比","類別"]);
  const allDetail = data.feature_detail ?? [];
  const fTotal = allDetail.reduce((s, r) => s + n(r.count), 0);
  buildTableBody("table1-body", allDetail, (r, i) => {
    const pctStr = fTotal ? `${((n(r.count) / fTotal) * 100).toFixed(1)}%` : "—";
    return `<tr>
      <td class="rank">${i + 1}</td>
      <td>${r.feature_id}</td>
      <td>${r.feature_name ?? "—"}</td>
      <td>${r.event_type}</td>
      <td>${fmt(n(r.count))}</td>
      <td class="pct">${pctStr}</td>
      <td>${r.category ?? "—"}</td>
    </tr>`;
  });
}

// ════════════════════════════════════════════════════════════════
// 3. 應徵轉換
// ════════════════════════════════════════════════════════════════
function applyRenderer(data) {
  const kpi      = data.kpi?.[0] ?? {};
  const applies  = n(kpi.applies);
  const jobViews = n(kpi.job_views);
  const days     = n(kpi.days) || 1;
  const applyRate = jobViews ? (applies / jobViews) * 100 : 0;

  setKpiCard("1", "總應徵數",   fmt(applies),  "action=apply 事件數");
  setKpiCard("2", "每日平均應徵", fmt(Math.round(applies / days)), "區間內日平均");
  setKpiCard("3", "職缺頁瀏覽", fmt(jobViews), "job-page view 事件數");
  setKpiCard("4", "應徵轉換率", pct2(applyRate), "Apply / Job Page View");
  setKpiCard("5", "—", "—", "");
  setKpiCard("6", "—", "—", "");
  setKpiCard("7", "—", "—", "");
  setKpiCard("8", "—", "—", "");

  // 圖表 1 — 每日趨勢
  const trend = data.daily_trend ?? [];
  lineChart("chart1", trend.map(r => r.date), [
    { label: "職缺頁瀏覽", data: trend.map(r => n(r.job_views)), borderColor: C.blue,   tension: 0.3, fill: false },
    { label: "應徵",       data: trend.map(r => n(r.applies)),   borderColor: C.pink,   tension: 0.3, fill: false, yAxisID: "y1" },
  ]);

  // 圖表 2 — 轉換漏斗
  const funnel = data.funnel ?? [];
  barChart("chart2", funnel.map(r => r.name), [
    { label: "事件數", data: funnel.map(r => n(r.cnt)), backgroundColor: C.palette },
  ]);

  // 圖表 3 — 應徵裝置分佈
  doughnutChart("chart3", data.device_dist ?? []);

  // 表格 1 — 裝置詳細
  buildTableHead("table1-head", ["#","裝置","應徵數","佔比"]);
  const dd = data.device_detail ?? [];
  const dTotal = dd.reduce((s, r) => s + n(r.count), 0);
  buildTableBody("table1-body", dd, (r, i) => rankRow(i, r.device, n(r.count), dTotal));

  // 表格 2 — OS 分佈
  buildTableHead("table2-head", ["#","OS","應徵數","佔比"]);
  const od = data.os_detail ?? [];
  const oTotal = od.reduce((s, r) => s + n(r.count), 0);
  buildTableBody("table2-body", od, (r, i) => rankRow(i, r.os, n(r.count), oTotal));

  // 表格 3 — 來源詳細
  buildTableHead("table3-head", ["#","來源","應徵數","佔比"]);
  const sd = data.source_dist ?? [];
  const sTotal = sd.reduce((s, r) => s + n(r.count), 0);
  buildTableBody("table3-body", sd, (r, i) => rankRow(i, r.name, n(r.count), sTotal));
}

// ════════════════════════════════════════════════════════════════
// 4. 功能互動
// ════════════════════════════════════════════════════════════════
function featureRenderer(data) {
  const kpi = data.kpi?.[0] ?? {};
  setKpiCard("1", "探索職缺 Click", fmt(n(kpi.explore_jobs_click)), "organic + corp");
  setKpiCard("2", "探索職缺 View",  fmt(n(kpi.explore_jobs_view)),  "organic + corp");
  setKpiCard("3", "探索企業 Click", fmt(n(kpi.explore_corp_click)), "各企業探索入口");
  setKpiCard("4", "探索企業 View",  fmt(n(kpi.explore_corp_view)),  "各企業探索入口");
  setKpiCard("5", "身份辨識 Click", fmt(n(kpi.identity_click)),     "含 identify-* 延伸互動");
  setKpiCard("6", "身份辨識 View",  fmt(n(kpi.identity_view)),      "含 identify-* 延伸互動");
  setKpiCard("7", "新聞互動 Click", fmt(n(kpi.news_click)),         "news-card 點擊");
  setKpiCard("8", "新聞互動 View",  fmt(n(kpi.news_view)),          "news-card 曝光");

  // 圖表 1 — 探索職缺 categoryTab 分佈（doughnut）
  doughnutChart("chart1", data.explore_job_category ?? []);

  // 圖表 2 — 探索企業 featureId 分佈（bar）
  const corpFeat = data.explore_corp_feature ?? [];
  barHChart("chart2", corpFeat.map(r => r.name), [
    { label: "事件數", data: corpFeat.map(r => n(r.count)), backgroundColor: C.palette },
  ]);

  // 圖表 3 — 身份辨識分佈（bar）
  const idDist = data.identity_dist ?? [];
  barHChart("chart3", idDist.map(r => r.name), [
    { label: "點擊數", data: idDist.map(r => n(r.count)), backgroundColor: C.palette },
  ]);

  // 表格 1 — 身份辨識詳細
  buildTableHead("table1-head", ["#","身份","事件數","佔比"]);
  const idTotal = idDist.reduce((s, r) => s + n(r.count), 0);
  buildTableBody("table1-body", idDist, (r, i) => rankRow(i, r.name, n(r.count), idTotal));

  // 表格 2 — 新聞互動詳細
  buildTableHead("table2-head", ["#","featureId","點擊數","佔比"]);
  const news = data.news_dist ?? [];
  const nTotal = news.reduce((s, r) => s + n(r.count), 0);
  buildTableBody("table2-body", news, (r, i) => rankRow(i, r.name, n(r.count), nTotal));
}

// ════════════════════════════════════════════════════════════════
// 5. 裝置平台
// ════════════════════════════════════════════════════════════════
function deviceRenderer(data) {
  const kpi      = data.kpi?.[0] ?? {};
  const mobile   = n(kpi.mobile_total);
  const desktop  = n(kpi.desktop_total);
  const totalDev = mobile + desktop;
  const mobilePct = totalDev ? (mobile / totalDev) * 100 : 0;

  setKpiCard("1", "Mobile 事件數", fmt(mobile),  `佔 ${pct(mobilePct)}`);
  setKpiCard("2", "Desktop 事件數", fmt(desktop), `佔 ${pct(100 - mobilePct)}`);
  setKpiCard("3", "OS 種類",       fmt(n(kpi.os_count)),      "完整 distinct 數");
  setKpiCard("4", "瀏覽器種類",    fmt(n(kpi.browser_count)), "完整 distinct 數");
  setKpiCard("5", "—", "—", "");
  setKpiCard("6", "—", "—", "");
  setKpiCard("7", "—", "—", "");
  setKpiCard("8", "—", "—", "");

  // 圖表 1 — 每日趨勢 (line)
  const trend = data.daily_trend ?? [];
  lineChart("chart1", trend.map(r => r.date), [
    { label: "Mobile",  data: trend.map(r => n(r.mobile)),  borderColor: C.blue,   tension: 0.3, fill: false },
    { label: "Desktop", data: trend.map(r => n(r.desktop)), borderColor: C.orange, tension: 0.3, fill: false },
  ]);

  // 圖表 2 — OS 分佈 (doughnut)
  doughnutChart("chart2", data.os_dist ?? []);

  // 圖表 3 — 瀏覽器分佈 (bar-H)
  const bDist = data.browser_dist ?? [];
  barHChart("chart3", bDist.map(r => r.name), [
    { label: "事件數", data: bDist.map(r => n(r.count)), backgroundColor: C.palette },
  ]);

  // 表格 1 — OS 詳細
  buildTableHead("table1-head", ["#","OS","事件數","佔比"]);
  const osDist = data.os_dist ?? [];
  const osTotal = osDist.reduce((s, r) => s + n(r.count), 0);
  buildTableBody("table1-body", osDist, (r, i) => rankRow(i, r.name, n(r.count), osTotal));

  // 表格 2 — 瀏覽器詳細
  buildTableHead("table2-head", ["#","瀏覽器","事件數","佔比"]);
  const bTotal = bDist.reduce((s, r) => s + n(r.count), 0);
  buildTableBody("table2-body", bDist, (r, i) => rankRow(i, r.name, n(r.count), bTotal));

  // 表格 3 — 裝置×行為
  buildTableHead("table3-head", ["裝置","總事件","View","Click","Apply","Apply 轉換率"]);
  const db = data.device_behavior ?? [];
  buildTableBody("table3-body", db, r => {
    const ar = n(r.views) ? (n(r.applies) / n(r.views)) * 100 : 0;
    return `<tr>
      <td>${r.device}</td>
      <td>${fmt(r.total)}</td>
      <td>${fmt(r.views)}</td>
      <td>${fmt(r.clicks)}</td>
      <td>${fmt(r.applies)}</td>
      <td class="pct">${pct2(ar)}</td>
    </tr>`;
  });

  // 表格 4 — OS×行為
  buildTableHead("table4-head", ["OS","總事件","View","Click","Apply"]);
  const ob = data.os_behavior ?? [];
  buildTableBody("table4-body", ob, r => `<tr>
    <td>${r.os}</td>
    <td>${fmt(r.total)}</td>
    <td>${fmt(r.views)}</td>
    <td>${fmt(r.clicks)}</td>
    <td>${fmt(r.applies)}</td>
  </tr>`);
}

// ════════════════════════════════════════════════════════════════
// 6. 頁面排行
// ════════════════════════════════════════════════════════════════
function rankingRenderer(data) {
  const kpi = data.kpi?.[0] ?? {};
  setKpiCard("1", "總事件數",  fmt(n(kpi.total)),         "所有 featureId 合計");
  setKpiCard("2", "功能數量",  fmt(n(kpi.feature_count)), "不重複 featureId 數");
  setKpiCard("3", "Top 1 功能", String(kpi.top_feature ?? "—"), `區間聚合 ${fmt(n(kpi.top_count))} 次`);
  setKpiCard("4", "—", "—", "");
  setKpiCard("5", "—", "—", "");
  setKpiCard("6", "—", "—", "");
  setKpiCard("7", "—", "—", "");
  setKpiCard("8", "—", "—", "");

  // 圖表 1 — Top 20 水平 bar
  const ranking = data.ranking ?? [];
  const top20 = ranking.slice(0, 20);
  barHChart("chart1", top20.map(r => r.feature_id), [
    { label: "總事件", data: top20.map(r => n(r.total)), backgroundColor: C.palette },
  ]);

  // 圖表 2 — 類別佔比 doughnut
  const catRows = data.categories ?? [];
  doughnutChart("chart2", catRows);

  // 表格 1 — 完整排行 (#, featureId, featureName, 總計, View, Click, CTR, 類別)
  buildTableHead("table1-head", ["#","featureId","featureName","總計","View","Click","CTR","類別"]);
  buildTableBody("table1-body", ranking, (r, i) => {
    const ctr = n(r.total) ? (n(r.clicks) / n(r.total)) * 100 : 0;
    return `<tr>
      <td class="rank">${i + 1}</td>
      <td>${r.feature_id}</td>
      <td>${r.feature_name ?? "—"}</td>
      <td>${fmt(r.total)}</td>
      <td>${fmt(r.views)}</td>
      <td>${fmt(r.clicks)}</td>
      <td class="pct">${pct2(ctr)}</td>
      <td>${r.category ?? "—"}</td>
    </tr>`;
  });
}

// ════════════════════════════════════════════════════════════════
// 7. 頁面導航
// ════════════════════════════════════════════════════════════════
function navigationRenderer(data) {
  const kpi = data.kpi?.[0] ?? {};
  setKpiCard("1", "導航 View 總數",  fmt(n(kpi.nav_view)),   "from→to view 轉換事件");
  setKpiCard("2", "導航 Click 總數", fmt(n(kpi.nav_click)),  "from→to click 事件");
  setKpiCard("3", "進入頁 View",     fmt(n(kpi.entry_view)), "無 previousPage view");
  setKpiCard("4", "進入頁 Click",    fmt(n(kpi.entry_click)),"無 previousPage click");
  setKpiCard("5", "追蹤頁面數",      fmt(n(kpi.page_count)), "有 view 導航記錄的頁面");
  setKpiCard("6", "—", "—", "");
  setKpiCard("7", "—", "—", "");
  setKpiCard("8", "—", "—", "");

  // 圖表 1 — 初始進入頁面分佈 (doughnut)
  doughnutChart("chart1", data.entry_dist ?? []);

  // 圖表 2 — Top 20 轉換路徑 (bar)
  const trans = data.transition_ranking ?? [];
  const top20 = trans.slice(0, 20);
  barHChart("chart2", top20.map(r => `${r.from_page} → ${r.to_page}`), [
    { label: "次數", data: top20.map(r => n(r.count)), backgroundColor: C.palette },
  ]);

  // 表格 1 — 各頁面 Top 來源
  const pageSources = (data.page_sources ?? []).slice(0, 100);
  buildTableHead("table1-head", ["目標頁面","來源頁面","次數"]);
  buildTableBody("table1-body", pageSources, r => `<tr>
    <td>${r.target ?? "—"}</td>
    <td>${r.source ?? "—"}</td>
    <td>${fmt(r.count)}</td>
  </tr>`);

  // 表格 2 — 各頁面 Top 目標
  const pageTargets = (data.page_targets ?? []).slice(0, 100);
  buildTableHead("table2-head", ["來源頁面","目標頁面","次數"]);
  buildTableBody("table2-body", pageTargets, r => `<tr>
    <td>${r.source ?? "—"}</td>
    <td>${r.target ?? "—"}</td>
    <td>${fmt(r.count)}</td>
  </tr>`);

  // 表格 3 — 完整轉換路徑排行
  buildTableHead("table3-head", ["#","來源頁","目標頁","次數"]);
  buildTableBody("table3-body", trans, (r, i) => `<tr>
    <td class="rank">${i + 1}</td>
    <td>${r.from_page ?? "—"}</td>
    <td>${r.to_page ?? "—"}</td>
    <td>${fmt(r.count)}</td>
  </tr>`);
}

// ════════════════════════════════════════════════════════════════
// 8. 點擊熱點
// ════════════════════════════════════════════════════════════════
function heatmapRenderer(data) {
  const kpi = data.kpi?.[0] ?? {};
  setKpiCard("1", "總點擊數",   fmt(n(kpi.total_clicks)),  "event_type=click");
  setKpiCard("2", "不重複功能數", fmt(n(kpi.feature_count)), "不重複 featureId");
  setKpiCard("3", "Top 1 功能", String(kpi.top_feature ?? "—"), `${fmt(n(kpi.top_count))} 次`);
  setKpiCard("4", "—", "—", "");
  setKpiCard("5", "—", "—", "");
  setKpiCard("6", "—", "—", "");
  setKpiCard("7", "—", "—", "");
  setKpiCard("8", "—", "—", "");

  // 圖表 1 — Top 20 點擊 bar-H
  const ranking = data.ranking ?? [];
  const top20 = ranking.slice(0, 20);
  barHChart("chart1", top20.map(r => r.feature_id), [
    { label: "點擊數", data: top20.map(r => n(r.count)), backgroundColor: C.palette },
  ]);

  // 圖表 2 — 頁面點擊分佈 doughnut
  doughnutChart("chart2", data.page_dist ?? []);

  // 表格 1 — featureId 點擊排行
  buildTableHead("table1-head", ["#","featureId","featureName","點擊數","佔比","頁面"]);
  const total = ranking.reduce((s, r) => s + n(r.count), 0);
  buildTableBody("table1-body", ranking, (r, i) => {
    const pctStr = total ? `${((n(r.count) / total) * 100).toFixed(1)}%` : "—";
    return `<tr>
      <td class="rank">${i + 1}</td>
      <td>${r.feature_id}</td>
      <td>${r.feature_name ?? "—"}</td>
      <td>${fmt(n(r.count))}</td>
      <td class="pct">${pctStr}</td>
      <td>${r.page_path ?? "—"}</td>
    </tr>`;
  });
}

// ════════════════════════════════════════════════════════════════
// 9. 首頁區塊點擊
// ════════════════════════════════════════════════════════════════
function homepageBlocksRenderer(data) {
  const kpi           = data.kpi?.[0] ?? {};
  const totalClicks   = n(kpi.total_clicks);
  const totalViews    = n(kpi.total_views);
  const searchClick   = n(kpi.search_click);
  const identityClick = n(kpi.identity_click);
  const jobsClick     = n(kpi.explore_jobs_click);
  const corpClick     = n(kpi.explore_corp_click);

  setKpiCard("1", "總點擊數",        fmt(totalClicks),   "4 大類別合計");
  setKpiCard("2", "總瀏覽數",        fmt(totalViews),    "4 大類別合計");
  setKpiCard("3", "搜尋類別 Click",  fmt(searchClick),   totalClicks ? `佔 ${pct(searchClick / totalClicks * 100)}` : "—");
  setKpiCard("4", "身分類別 Click",  fmt(identityClick), totalClicks ? `佔 ${pct(identityClick / totalClicks * 100)}` : "—");
  setKpiCard("5", "探索工作 Click",  fmt(jobsClick),     totalClicks ? `佔 ${pct(jobsClick / totalClicks * 100)}` : "—");
  setKpiCard("6", "探索企業 Click",  fmt(corpClick),     totalClicks ? `佔 ${pct(corpClick / totalClicks * 100)}` : "—");
  setKpiCard("7", "—", "—", "");
  setKpiCard("8", "—", "—", "");

  // 圖表 1 — 每日趨勢：click 實線 / view 虛線
  const trend = data.daily_trend ?? [];
  lineChart("chart1", trend.map(r => r.date), [
    { label: "搜尋 Click",   data: trend.map(r => n(r.search_click)),       borderColor: C.blue,   tension: 0.3, fill: false },
    { label: "搜尋 View",    data: trend.map(r => n(r.search_view)),        borderColor: C.blue,   tension: 0.3, fill: false, borderDash: [4, 3] },
    { label: "身分 Click",   data: trend.map(r => n(r.identity_click)),     borderColor: C.purple, tension: 0.3, fill: false },
    { label: "身分 View",    data: trend.map(r => n(r.identity_view)),      borderColor: C.purple, tension: 0.3, fill: false, borderDash: [4, 3] },
    { label: "探索工作 Click", data: trend.map(r => n(r.explore_jobs_click)), borderColor: C.green,  tension: 0.3, fill: false },
    { label: "探索工作 View",  data: trend.map(r => n(r.explore_jobs_view)),  borderColor: C.green,  tension: 0.3, fill: false, borderDash: [4, 3] },
    { label: "探索企業 Click", data: trend.map(r => n(r.explore_corp_click)), borderColor: C.orange, tension: 0.3, fill: false },
    { label: "探索企業 View",  data: trend.map(r => n(r.explore_corp_view)),  borderColor: C.orange, tension: 0.3, fill: false, borderDash: [4, 3] },
  ]);

  // 圖表 2 — Click 類別佔比 (doughnut)
  doughnutChart("chart2", [
    { name: "搜尋類別", count: searchClick },
    { name: "身分類別", count: identityClick },
    { name: "探索工作", count: jobsClick },
    { name: "探索企業", count: corpClick },
  ]);

  // 圖表 3 — Top featureId by click (bar-H)
  const detail     = data.feature_detail ?? [];
  const clickRows  = detail.filter(r => r.event_type === "click");
  const top20click = clickRows.slice(0, 20);
  barHChart("chart3", top20click.map(r => r.feature_id), [
    { label: "點擊數", data: top20click.map(r => n(r.count)), backgroundColor: C.palette },
  ]);

  // 表格 1 — 各 featureId click / view 詳細
  const viewMap = Object.fromEntries(detail.filter(r => r.event_type === "view").map(r => [r.feature_id, n(r.count)]));
  buildTableHead("table1-head", ["#", "featureId", "featureName", "Click", "View", "所屬區塊"]);
  buildTableBody("table1-body", clickRows, (r, i) => {
    const v = viewMap[r.feature_id] ?? 0;
    return `<tr>
      <td class="rank">${i + 1}</td>
      <td>${r.feature_id}</td>
      <td>${r.feature_name ?? "—"}</td>
      <td>${fmt(n(r.count))}</td>
      <td>${fmt(v)}</td>
      <td>${r.block ?? "—"}</td>
    </tr>`;
  });
}

// ── 重置 ────────────────────────────────────────────────────────
function resetKpis() {
  for (let i = 1; i <= 8; i++) setKpiCard(String(i), "—", "--", "");
}

function resetCharts() {
  emptyChart("chart1", "line");
  emptyChart("chart2", "doughnut");
  emptyChart("chart3", "bar");
}

function resetTables() {
  for (let i = 1; i <= 4; i++) {
    const body = document.getElementById(`table${i}-body`);
    if (body) body.innerHTML = '<tr><td colspan="99" class="empty-cell">尚未載入資料</td></tr>';
    const head = document.getElementById(`table${i}-head`);
    if (head) head.innerHTML = "<tr><th>#</th><th>名稱</th><th>數值</th><th></th><th>佔比</th></tr>";
  }
}

// ════════════════════════════════════════════════════════════════
// 10. 月報表瀏覽器 — monthly-report
// ════════════════════════════════════════════════════════════════

const MONTHLY_CATEGORIES = [
  { key: "search",   label: "搜尋類別", test: id => id.startsWith("search-") || id.startsWith("T-job-") },
  { key: "identity", label: "身分類別", test: id => id.startsWith("identify-") },
  { key: "jobs",     label: "探索工作", test: id => id.startsWith("explore-jobs-") },
  { key: "corp",     label: "探索企業", test: id => id.startsWith("explore-company-") },
];

function monthlyFormatDate(iso) {
  const [y, m, d] = iso.split("-");
  return `${y}/${m}/${d}`;
}

function monthlyFormatMonth(ym) {
  const [y, m] = ym.split("-");
  return `${y}年${m}月`;
}

function monthlyBuildCatTable(clickRows, viewMap) {
  if (!clickRows.length) return "<p class='monthly-empty'>無資料</p>";
  const totalClicks = clickRows.reduce((s, r) => s + r.count, 0);
  const trs = clickRows.map((r, i) => {
    const clickPct = totalClicks ? ((r.count / totalClicks) * 100).toFixed(1) : "0.0";
    const bar = totalClicks ? Math.round((r.count / totalClicks) * 80) : 0;
    const views = viewMap[r.feature_id] ?? 0;
    return `<tr>
      <td class="cat-rank">${i + 1}</td>
      <td class="cat-id">${r.feature_id}</td>
      <td class="cat-id">${r.feature_name || "—"}</td>
      <td class="cat-count">${r.count.toLocaleString()}</td>
      <td class="cat-count" style="color:var(--muted)">${views.toLocaleString()}</td>
      <td class="cat-bar"><span style="width:${bar}px"></span></td>
      <td class="cat-pct">${clickPct}%</td>
    </tr>`;
  }).join("");
  return `<table class="cat-table">
    <thead><tr><th>#</th><th>功能</th><th>featureName</th><th>點擊</th><th>瀏覽</th><th></th><th>佔比</th></tr></thead>
    <tbody>${trs}</tbody>
  </table>`;
}

async function monthlyFetchDay(date, runtime) {
  const detail = document.getElementById("monthly-day-detail");
  if (!detail) return;

  detail.innerHTML = `<p class='monthly-loading'>載入 ${monthlyFormatDate(date)} 資料中…</p>`;
  detail.classList.remove("hidden");

  try {
    const url = new URL(
      `report/homepage-blocks/date=${date}/feature_counts.parquet`,
      runtime.datasetRoot
    ).href;
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const buf = new Uint8Array(await resp.arrayBuffer());
    const alias = `monthly_${date.replace(/-/g, "_")}.parquet`;
    await runtime.db.dropFile(alias).catch(() => {});
    await runtime.db.registerFileBuffer(alias, buf);

    const result = await runtime.conn.query(
      `SELECT feature_id, feature_name, event_type, CAST(count AS BIGINT) AS cnt FROM "${alias}" ORDER BY event_type, cnt DESC`
    );
    const rows = result.toArray().map(r => ({
      feature_id: String(r.feature_id),
      feature_name: r.feature_name ? String(r.feature_name) : "",
      event_type: String(r.event_type),
      count: Number(r.cnt),
    }));

    const clickRows = rows.filter(r => r.event_type === "click");
    const viewMap   = Object.fromEntries(rows.filter(r => r.event_type === "view").map(r => [r.feature_id, r.count]));
    const totalClicks = clickRows.reduce((s, r) => s + r.count, 0);
    const totalViews  = rows.filter(r => r.event_type === "view").reduce((s, r) => s + r.count, 0);

    const catSections = MONTHLY_CATEGORIES.map(cat => {
      const catClick = clickRows.filter(r => cat.test(r.feature_id));
      const catClickTotal = catClick.reduce((s, r) => s + r.count, 0);
      const catViewTotal  = catClick.reduce((s, r) => s + (viewMap[r.feature_id] ?? 0), 0);
      return `<div class="cat-section">
        <div class="cat-header">
          <h4>${cat.label}</h4>
          <span class="cat-total">點擊 ${catClickTotal.toLocaleString()} / 瀏覽 ${catViewTotal.toLocaleString()}</span>
        </div>
        ${monthlyBuildCatTable(catClick, viewMap)}
      </div>`;
    }).join("");

    detail.innerHTML = `
      <div class="day-detail-header">
        <h3>${monthlyFormatDate(date)} 日報表</h3>
        <span class="day-total">總點擊：${totalClicks.toLocaleString()} ／ 總瀏覽：${totalViews.toLocaleString()}</span>
      </div>
      <div class="cat-grid">${catSections}</div>`;
  } catch (err) {
    detail.innerHTML = `<p class='monthly-error'>載入失敗：${err.message}</p>`;
  }
}

function monthlyReportRenderer(runtime) {
  const section = document.getElementById("monthly-section");
  if (!section || !runtime) return;

  const datesByMonth = runtime.datesByMonth ?? {};
  const months = Object.keys(datesByMonth).sort().reverse();

  if (!months.length) {
    section.innerHTML = `<p class="monthly-empty">目前沒有可用資料</p>`;
    return;
  }

  const urlDate = new URLSearchParams(location.search).get("date_from");
  const urlMonth = urlDate ? urlDate.slice(0, 7) : null;
  const initialMonth = (urlMonth && datesByMonth[urlMonth]) ? urlMonth : months[0];

  function buildDayButtons(ym) {
    const days = [...(datesByMonth[ym] ?? [])].sort().reverse();
    return days.map(d =>
      `<button class="day-btn" data-date="${d}" type="button">${d.slice(5)}</button>`
    ).join("");
  }

  const monthTabs = months.map(ym =>
    `<button class="month-tab${ym === initialMonth ? " is-active" : ""}" data-month="${ym}" type="button">${monthlyFormatMonth(ym)}</button>`
  ).join("");

  section.innerHTML = `
    <div class="monthly-layout">
      <nav class="monthly-nav-months">${monthTabs}</nav>
      <div class="monthly-nav-days">${buildDayButtons(initialMonth)}</div>
      <div class="monthly-detail">
        <div id="monthly-day-detail" class="monthly-day-detail">
          <p class="monthly-empty">點選上方日期查看當日明細</p>
        </div>
      </div>
    </div>`;

  function bindDayButtons() {
    section.querySelectorAll(".day-btn").forEach(btn => {
      btn.addEventListener("click", async () => {
        section.querySelectorAll(".day-btn").forEach(b => b.classList.remove("is-active"));
        btn.classList.add("is-active");
        await monthlyFetchDay(btn.dataset.date, runtime);
      });
    });
  }

  section.querySelectorAll(".month-tab").forEach(tab => {
    tab.addEventListener("click", () => {
      section.querySelectorAll(".month-tab").forEach(t => t.classList.remove("is-active"));
      tab.classList.add("is-active");
      section.querySelector(".monthly-nav-days").innerHTML = buildDayButtons(tab.dataset.month);
      const detail = document.getElementById("monthly-day-detail");
      if (detail) detail.innerHTML = `<p class="monthly-empty">點選上方日期查看當日明細</p>`;
      bindDayButtons();
    });
  });

  bindDayButtons();

  // URL date_from 自動選取對應日期
  if (urlDate) {
    const target = section.querySelector(`.day-btn[data-date="${urlDate}"]`);
    if (target) {
      target.scrollIntoView({ block: "nearest", inline: "center" });
      target.click();
    }
  }
}

// ── 路由 ────────────────────────────────────────────────────────
const renderers = {
  overview:   overviewRenderer,
  search:     searchRenderer,
  apply:      applyRenderer,
  feature:    featureRenderer,
  device:     deviceRenderer,
  ranking:    rankingRenderer,
  navigation:          navigationRenderer,
  heatmap:             heatmapRenderer,
  "homepage-blocks":   homepageBlocksRenderer,
};

export function renderDashboard(viewMode, outputs, runtime = null) {
  showPanels(viewMode);
  applyPanelText(viewMode);
  if (viewMode === "monthly-report") {
    monthlyReportRenderer(runtime);
    return;
  }
  const data = Object.fromEntries(outputs.map(o => [o.name, o.rows]));
  const renderer = renderers[viewMode];
  if (!renderer) { resetKpis(); resetCharts(); resetTables(); return; }
  renderer(data);
}

export function resetDashboard(viewMode = null) {
  if (viewMode) showPanels(viewMode);
  resetKpis();
  resetCharts();
  resetTables();
}
