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
  const searchTotal = n(kpi.search_total);
  const genTotal    = n(kpi.general_total);
  const aiTotal     = n(kpi.ai_total);
  const aiPct       = (genTotal + aiTotal) ? (aiTotal / (genTotal + aiTotal)) * 100 : 0;

  setKpiCard("1", "搜尋相關事件",  fmt(searchTotal), "含搜尋頁、互動與篩選");
  setKpiCard("2", "搜尋結果頁瀏覽", fmt(n(kpi.search_page_total)), "job/corp/gig/intern");
  setKpiCard("3", "一般搜尋互動",  fmt(genTotal), "keyword/submit/general");
  setKpiCard("4", "AI 搜尋互動",   fmt(aiTotal), `AI 佔搜尋互動 ${pct(aiPct)}`);
  setKpiCard("5", "快速篩選",      fmt(n(kpi.quick_total)), "地區 / 職類篩選");
  setKpiCard("6", "—", "—", "");
  setKpiCard("7", "—", "—", "");
  setKpiCard("8", "—", "—", "");

  // 圖表 1 — 各搜尋類型 bar
  const detail = data.feature_detail ?? [];
  barChart("chart1", detail.map(r => r.feature_id), [
    { label: "事件數", data: detail.map(r => n(r.count)), backgroundColor: C.palette },
  ], { indexAxis: "y", plugins: { legend: { display: false } } });

  // 圖表 2 — AI vs 一般搜尋每日趨勢
  const dt = data.daily_trend ?? [];
  lineChart("chart2", dt.map(r => r.date), [
    { label: "一般搜尋", data: dt.map(r => n(r.general)), borderColor: C.blue,   tension: 0.3, fill: false },
    { label: "AI 搜尋",  data: dt.map(r => n(r.ai)),      borderColor: C.purple, tension: 0.3, fill: false },
  ]);

  // 圖表 3 — 搜尋結果頁分佈
  doughnutChart("chart3", data.search_page_dist ?? []);

  // 表格 1 — featureId 詳細
  buildTableHead("table1-head", ["#","featureId","事件數","佔比","類別"]);
  const fTotal = detail.reduce((s, r) => s + n(r.count), 0);
  buildTableBody("table1-body", detail, (r, i) => rankRow(i, r.feature_id, n(r.count), fTotal, r.category));
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
  setKpiCard("1", "探索職缺",  fmt(n(kpi.explore_jobs)),  "organic + corp");
  setKpiCard("2", "探索企業",  fmt(n(kpi.explore_corp)),  "各企業探索入口");
  setKpiCard("3", "身份辨識",  fmt(n(kpi.identity_total)), "含 identify-* 延伸互動");
  setKpiCard("4", "新聞互動",  fmt(n(kpi.news_total)),    "news-card 點擊");
  setKpiCard("5", "—", "—", "");
  setKpiCard("6", "—", "—", "");
  setKpiCard("7", "—", "—", "");
  setKpiCard("8", "—", "—", "");

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

  // 表格 1 — 完整排行 (#, featureId, 總計, View, Click, CTR, 類別)
  buildTableHead("table1-head", ["#","featureId","總計","View","Click","CTR","類別"]);
  buildTableBody("table1-body", ranking, (r, i) => {
    const ctr = n(r.total) ? (n(r.clicks) / n(r.total)) * 100 : 0;
    return `<tr>
      <td class="rank">${i + 1}</td>
      <td>${r.feature_id}</td>
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
  setKpiCard("1", "導航事件總數", fmt(n(kpi.nav_total)),   "全部 from→to 轉換事件");
  setKpiCard("2", "初始進入事件", fmt(n(kpi.entry_total)), "無 previousPageName");
  setKpiCard("3", "追蹤頁面數",  fmt(n(kpi.page_count)),  "有導航記錄的頁面");
  setKpiCard("4", "—", "—", "");
  setKpiCard("5", "—", "—", "");
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
  buildTableHead("table1-head", ["#","featureId","點擊數","佔比","頁面"]);
  const total = ranking.reduce((s, r) => s + n(r.count), 0);
  buildTableBody("table1-body", ranking, (r, i) => rankRow(i, r.feature_id, n(r.count), total, r.page_path ?? ""));
}

// ════════════════════════════════════════════════════════════════
// 9. 首頁區塊點擊
// ════════════════════════════════════════════════════════════════
function homepageBlocksRenderer(data) {
  const kpi      = data.kpi?.[0] ?? {};
  const total    = n(kpi.total_clicks);
  const search   = n(kpi.search_total);
  const identity = n(kpi.identity_total);
  const jobs     = n(kpi.explore_jobs_total);
  const corp     = n(kpi.explore_corp_total);

  setKpiCard("1", "總點擊數",  fmt(total),    "4 大類別合計");
  setKpiCard("2", "搜尋類別",  fmt(search),   total ? `佔 ${pct(search / total * 100)}` : "—");
  setKpiCard("3", "身分類別",  fmt(identity), total ? `佔 ${pct(identity / total * 100)}` : "—");
  setKpiCard("4", "探索工作",  fmt(jobs),     total ? `佔 ${pct(jobs / total * 100)}` : "—");
  setKpiCard("5", "探索企業",  fmt(corp),     total ? `佔 ${pct(corp / total * 100)}` : "—");
  setKpiCard("6", "—", "—", "");
  setKpiCard("7", "—", "—", "");
  setKpiCard("8", "—", "—", "");

  // 圖表 1 — 每日趨勢 (line)
  const trend = data.daily_trend ?? [];
  lineChart("chart1", trend.map(r => r.date), [
    { label: "搜尋類別", data: trend.map(r => n(r.search_total)),       borderColor: C.blue,   tension: 0.3, fill: false },
    { label: "身分類別", data: trend.map(r => n(r.identity_total)),     borderColor: C.purple, tension: 0.3, fill: false },
    { label: "探索工作", data: trend.map(r => n(r.explore_jobs_total)), borderColor: C.green,  tension: 0.3, fill: false },
    { label: "探索企業", data: trend.map(r => n(r.explore_corp_total)), borderColor: C.orange, tension: 0.3, fill: false },
  ]);

  // 圖表 2 — 類別佔比 (doughnut)
  doughnutChart("chart2", [
    { name: "搜尋類別", count: search },
    { name: "身分類別", count: identity },
    { name: "探索工作", count: jobs },
    { name: "探索企業", count: corp },
  ]);

  // 圖表 3 — Top featureId (bar-H)
  const detail = data.click_detail ?? [];
  const top20  = detail.slice(0, 20);
  barHChart("chart3", top20.map(r => r.feature_id), [
    { label: "點擊數", data: top20.map(r => n(r.count)), backgroundColor: C.palette },
  ]);

  // 表格 1 — 各 featureId 點擊詳細
  buildTableHead("table1-head", ["#", "featureId", "點擊數", "佔比", "所屬區塊"]);
  buildTableBody("table1-body", detail, (r, i) => rankRow(i, r.feature_id, n(r.count), total, r.block ?? "—"));
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

function monthlyBuildCatTable(rows) {
  if (!rows.length) return "<p class='monthly-empty'>無資料</p>";
  const total = rows.reduce((s, r) => s + r.count, 0);
  const trs = rows.map((r, i) => {
    const pct = total ? ((r.count / total) * 100).toFixed(1) : "0.0";
    const bar = total ? Math.round((r.count / total) * 80) : 0;
    return `<tr>
      <td class="cat-rank">${i + 1}</td>
      <td class="cat-id">${r.feature_id}</td>
      <td class="cat-count">${r.count.toLocaleString()}</td>
      <td class="cat-bar"><span style="width:${bar}px"></span></td>
      <td class="cat-pct">${pct}%</td>
    </tr>`;
  }).join("");
  return `<table class="cat-table">
    <thead><tr><th>#</th><th>功能</th><th>點擊</th><th></th><th>佔比</th></tr></thead>
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
      `report/homepage-blocks/date=${date}/click_counts.parquet`,
      runtime.datasetRoot
    ).href;
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const buf = new Uint8Array(await resp.arrayBuffer());
    const alias = `monthly_${date.replace(/-/g, "_")}.parquet`;
    await runtime.db.dropFile(alias).catch(() => {});
    await runtime.db.registerFileBuffer(alias, buf);

    const result = await runtime.conn.query(
      `SELECT feature_id, CAST(count AS BIGINT) AS cnt FROM "${alias}" ORDER BY cnt DESC`
    );
    const rows = result.toArray().map(r => ({
      feature_id: String(r.feature_id),
      count: Number(r.cnt),
    }));

    const totalClicks = rows.reduce((s, r) => s + r.count, 0);
    const catSections = MONTHLY_CATEGORIES.map(cat => {
      const catRows = rows.filter(r => cat.test(r.feature_id));
      const catTotal = catRows.reduce((s, r) => s + r.count, 0);
      return `<div class="cat-section">
        <div class="cat-header">
          <h4>${cat.label}</h4>
          <span class="cat-total">${catTotal.toLocaleString()} 次</span>
        </div>
        ${monthlyBuildCatTable(catRows)}
      </div>`;
    }).join("");

    detail.innerHTML = `
      <div class="day-detail-header">
        <h3>${monthlyFormatDate(date)} 日報表</h3>
        <span class="day-total">總點擊：${totalClicks.toLocaleString()}</span>
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

  const monthBlocks = months.map((ym, idx) => {
    const days = [...datesByMonth[ym]].sort().reverse();
    const dayBtns = days.map(d =>
      `<button class="day-btn" data-date="${d}" type="button">${monthlyFormatDate(d)}</button>`
    ).join("");
    return `<details class="month-group" ${idx === 0 ? "open" : ""}>
      <summary class="month-summary">
        <span class="month-label">${monthlyFormatMonth(ym)}</span>
        <span class="month-count">${days.length} 天</span>
      </summary>
      <div class="day-list">${dayBtns}</div>
    </details>`;
  }).join("");

  section.innerHTML = `
    <div class="monthly-layout">
      <nav class="monthly-nav">${monthBlocks}</nav>
      <div class="monthly-detail">
        <div id="monthly-day-detail" class="monthly-day-detail hidden">
          <p class="monthly-empty">點選左側日期查看當日明細</p>
        </div>
      </div>
    </div>`;

  // 初始提示設為可見
  document.getElementById("monthly-day-detail")?.classList.remove("hidden");

  section.querySelectorAll(".day-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      section.querySelectorAll(".day-btn").forEach(b => b.classList.remove("is-active"));
      btn.classList.add("is-active");
      await monthlyFetchDay(btn.dataset.date, runtime);
    });
  });
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
