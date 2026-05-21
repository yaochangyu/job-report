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
  // 清除 canvas 上任何未被 chartCache 追蹤的殘留 chart instance
  const stale = Chart.getChart(canvas);
  if (stale) stale.destroy();
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
    options: { ...baseOpts },
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
  "apply-journey": {
    chart1: ["Top 20 應徵路徑排行", "最常見的頁面路徑（前 20）"],
    chart2: ["步數分佈", "應徵前經過的頁面數量"],
    chart3: ["進入頁分佈", "應徵 session 的第一個頁面"],
    table1: ["完整路徑排行", ""],
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
  "apply-job-category": {
    chart1: ["應徵職類 TOP 20", "依應徵次數排序（水平長條）"],
    chart2: ["應徵產業 TOP 20", "依應徵次數排序（水平長條）"],
    chart3: ["TOP 5 職類每日趨勢", "各職類每日應徵次數變化"],
    table1: ["職類排行（TOP 30）", ""],
    table2: ["產業排行（TOP 30）", ""],
  },
  "apply-demographics": {
    chart1: ["性別分佈", "應徵者性別佔比"],
    chart2: ["年齡層分佈", "應徵者年齡層佔比"],
    chart3: ["性別每日趨勢", "各性別每日應徵次數變化"],
    table1: ["性別統計", ""],
    table2: ["年齡層統計", ""],
  },
  "apply-demographics-category": {
    chart1: ["性別 × TOP 職類", "各性別在熱門職類的應徵分佈"],
    chart2: ["年齡層 × TOP 職類", "各年齡層在熱門職類的應徵分佈"],
    chart3: ["性別 × TOP 產業", "各性別在熱門產業的應徵分佈"],
    table1: ["性別 × 職類交叉表", ""],
    table2: ["年齡層 × 職類交叉表", ""],
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
  const isPeriodReport = viewMode === "period-report" || viewMode === "monthly-report";

  // period-report 用自訂區塊，隱藏所有標準面板
  document.querySelector(".kpi-grid")?.classList.toggle("hidden", isPeriodReport);
  document.querySelector(".chart-grid")?.classList.toggle("hidden", isPeriodReport);
  document.getElementById("monthly-section")?.classList.toggle("hidden", !isPeriodReport);

  if (isPeriodReport) {
    for (let i = 1; i <= 4; i++) document.getElementById(`table${i}-panel`)?.classList.add("hidden");
    document.getElementById("chart3-panel")?.classList.add("hidden");
    return;
  }

  // chart panels
  const charts3 = ["overview","search","apply","apply-journey","feature","device","homepage-blocks","apply-job-category","apply-demographics","apply-demographics-category"];
  const charts2 = ["ranking","navigation","heatmap"];
  document.getElementById("chart3-panel")?.classList.toggle("hidden", charts2.includes(viewMode));

  // table panels — 各視角顯示不同數量
  const tableCount = {
    overview: 2, search: 1, apply: 3, "apply-journey": 1, feature: 2,
    device: 4, ranking: 1, navigation: 3, heatmap: 1,
    "homepage-blocks": 1, "apply-job-category": 2, "apply-demographics": 2,
    "apply-demographics-category": 2,
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
// 4. 應徵路徑
// ════════════════════════════════════════════════════════════════
function applyJourneyRenderer(data) {
  const kpi           = data.kpi?.[0] ?? {};
  const applies       = n(kpi.applies);
  const applySessions = n(kpi.apply_sessions);
  const avgSteps      = n(kpi.avg_steps);
  const topPath       = data.path_ranking?.[0]?.path ?? "—";
  const topCount      = n(data.path_ranking?.[0]?.count ?? 0);

  setKpiCard("1", "總應徵次數",    fmt(applies),       "action=apply 事件數");
  setKpiCard("2", "涉及 Session 數", fmt(applySessions), "有應徵行為的 session");
  setKpiCard("3", "平均步數",      avgSteps.toFixed(1), "應徵前平均頁面數（含 apply）");
  setKpiCard("4", "Top 1 路徑",    `${fmt(topCount)} 次`, topPath);
  setKpiCard("5", "—", "—", "");
  setKpiCard("6", "—", "—", "");
  setKpiCard("7", "—", "—", "");
  setKpiCard("8", "—", "—", "");

  // 圖表 1 — Top 20 路徑排行（bar-H）
  const ranking = data.path_ranking ?? [];
  const top20   = ranking.slice(0, 20);
  barHChart("chart1", top20.map(r => r.path), [
    { label: "次數", data: top20.map(r => n(r.count)), backgroundColor: C.palette },
  ]);

  // 圖表 2 — 步數分佈（doughnut）
  const stepLabels = { 1: "1步", 2: "2步", 3: "3步", 4: "4步", 5: "5步以上" };
  const stepDist = (data.step_distribution ?? []).map(r => ({
    name:  stepLabels[n(r.steps_group)] ?? `${n(r.steps_group)}步`,
    count: n(r.count),
  }));
  doughnutChart("chart2", stepDist);

  // 圖表 3 — 進入頁分佈（doughnut）
  doughnutChart("chart3", data.entry_page ?? []);

  // 表格 1 — 完整路徑排行
  buildTableHead("table1-head", ["#", "路徑", "步數", "次數", "佔比"]);
  const total = ranking.reduce((s, r) => s + n(r.count), 0);
  buildTableBody("table1-body", ranking, (r, i) => {
    const pctStr = total ? `${((n(r.count) / total) * 100).toFixed(1)}%` : "—";
    return `<tr>
      <td class="rank">${i + 1}</td>
      <td>${r.path ?? "—"}</td>
      <td>${n(r.step_count)}</td>
      <td>${fmt(n(r.count))}</td>
      <td class="pct">${pctStr}</td>
    </tr>`;
  });
}

// ════════════════════════════════════════════════════════════════
// 5. 功能互動
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
// 11. 應徵職類／產業分析
// ════════════════════════════════════════════════════════════════
function applyJobCategoryRenderer(data) {
  const kpi        = data.kpi?.[0] ?? {};
  const total      = n(kpi.total_applies);
  const withMeta   = n(kpi.applies_with_metadata);
  const coverage   = kpi.avg_coverage_rate != null ? (kpi.avg_coverage_rate * 100).toFixed(1) + "%" : "—";

  setKpiCard("1", "總應徵數",     fmt(total),   "action=apply 事件數");
  setKpiCard("2", "有職缺資料",   fmt(withMeta), "成功對應到職缺資訊的應徵");
  setKpiCard("3", "職缺覆蓋率",   coverage,      "已對應職缺 / 總應徵");
  setKpiCard("4", "—", "—", "");
  setKpiCard("5", "—", "—", "");
  setKpiCard("6", "—", "—", "");
  setKpiCard("7", "—", "—", "");
  setKpiCard("8", "—", "—", "");

  // 圖表 1 — 職類 TOP 20（水平長條）
  const jpTop = (data.job_position_top ?? []).slice(0, 20);
  const jpLabels = jpTop.map(r => r.name);
  const jpCounts = jpTop.map(r => n(r.count));
  barHChart("chart1", jpLabels, [
    { label: "應徵次數", data: jpCounts, backgroundColor: C.palette.slice(0, jpLabels.length).map(() => C.blue) },
  ]);

  // 圖表 2 — 產業 TOP 20（水平長條）
  const ciTop = (data.company_industry_top ?? []).slice(0, 20);
  const ciLabels = ciTop.map(r => r.name);
  const ciCounts = ciTop.map(r => n(r.count));
  barHChart("chart2", ciLabels, [
    { label: "應徵次數", data: ciCounts, backgroundColor: ciLabels.map(() => C.teal) },
  ]);

  // 圖表 3 — TOP 5 職類每日趨勢（折線）
  const jpDaily = data.job_position_daily ?? [];
  const jpDates = [...new Set(jpDaily.map(r => r.date))].sort();
  const jpNames = [...new Set(jpDaily.map(r => r.name))].slice(0, 5);
  const countMap = {};
  jpDaily.forEach(r => { countMap[`${r.date}__${r.name}`] = n(r.count); });
  lineChart("chart3", jpDates, jpNames.map((name, i) => ({
    label: name,
    data: jpDates.map(d => countMap[`${d}__${name}`] ?? 0),
    borderColor: C.palette[i % C.palette.length],
    tension: 0.3,
    fill: false,
  })));

  // 表格 1 — 職類排行 TOP 30
  const jpAll = data.job_position_top ?? [];
  const jpTotal = jpAll.reduce((s, r) => s + n(r.count), 0);
  buildTableHead("table1-head", ["#", "職類", "應徵次數", "", "佔比"]);
  buildTableBody("table1-body", jpAll, (r, i) => rankRow(i, r.name, n(r.count), jpTotal));

  // 表格 2 — 產業排行 TOP 30
  const ciAll = data.company_industry_top ?? [];
  const ciTotal = ciAll.reduce((s, r) => s + n(r.count), 0);
  buildTableHead("table2-head", ["#", "產業", "應徵次數", "", "佔比"]);
  buildTableBody("table2-body", ciAll, (r, i) => rankRow(i, r.name, n(r.count), ciTotal));
}

// ════════════════════════════════════════════════════════════════
// 12. 應徵者性別／年齡分析
// ════════════════════════════════════════════════════════════════
function applyDemographicsRenderer(data) {
  const kpi      = data.kpi?.[0] ?? {};
  const total    = n(kpi.total_applies);
  const withMeta = n(kpi.applies_with_metadata);
  const coverage = kpi.avg_coverage_rate != null ? (kpi.avg_coverage_rate * 100).toFixed(1) + "%" : "—";

  setKpiCard("1", "總應徵數",   fmt(total),    "action=apply 事件數");
  setKpiCard("2", "有履歷資料", fmt(withMeta), "成功對應到應徵者資料");
  setKpiCard("3", "覆蓋率",     coverage,      "有履歷資料 / 總應徵數");
  setKpiCard("4", "—", "—", "");
  setKpiCard("5", "—", "—", "");
  setKpiCard("6", "—", "—", "");
  setKpiCard("7", "—", "—", "");
  setKpiCard("8", "—", "—", "");

  // 圖表 1 — 性別分佈 (doughnut)
  doughnutChart("chart1", data.gender_dist ?? []);

  // 圖表 2 — 年齡層分佈 (doughnut)
  doughnutChart("chart2", data.age_groups_dist ?? [], "age_group");

  // 圖表 3 — 性別每日趨勢 (line)
  const gd = data.gender_daily ?? [];
  const gdDates = [...new Set(gd.map(r => r.date))].sort();
  const genders = [...new Set(gd.map(r => r.gender))];
  const gdMap = {};
  gd.forEach(r => { gdMap[`${r.date}__${r.gender}`] = n(r.count); });
  const colorMap = { "男": C.blue, "女": C.pink, "未知": C.orange };
  lineChart("chart3", gdDates, genders.map(g => ({
    label: g,
    data: gdDates.map(d => gdMap[`${d}__${g}`] ?? 0),
    borderColor: colorMap[g] ?? C.green,
    tension: 0.3,
    fill: false,
  })));

  // 表格 1 — 性別統計
  const genderRows = data.gender_dist ?? [];
  const genderTotal = genderRows.reduce((s, r) => s + n(r.count), 0);
  buildTableHead("table1-head", ["#", "性別", "應徵次數", "", "佔比"]);
  buildTableBody("table1-body", genderRows, (r, i) => rankRow(i, r.gender, n(r.count), genderTotal));

  // 表格 2 — 年齡層統計
  const ageRows = data.age_groups_dist ?? [];
  const ageTotal = ageRows.reduce((s, r) => s + n(r.count), 0);
  buildTableHead("table2-head", ["#", "年齡層", "應徵次數", "", "佔比"]);
  buildTableBody("table2-body", ageRows, (r, i) => rankRow(i, r.age_group, n(r.count), ageTotal));
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
// 10. 週期報表瀏覽器 — period-report
// ════════════════════════════════════════════════════════════════

const MONTHLY_CATEGORIES = [
  { key: "search",   label: "搜尋類別", navId: "cat-search",   test: id => id.startsWith("search-") || id.startsWith("T-job-") },
  { key: "identity", label: "身分類別", navId: "cat-identity", test: id => id.startsWith("identify-") },
  { key: "jobs",     label: "探索工作", navId: "cat-jobs",     test: id => id.startsWith("explore-jobs-") },
  { key: "corp",     label: "探索企業", navId: "cat-corp",     test: id => id.startsWith("explore-company-") },
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

function initCatNav(detail) {
  const btns     = detail.querySelectorAll(".cat-sidebar-item");
  const sections = detail.querySelectorAll(".cat-section");
  function activate(navId) {
    btns.forEach(b => b.classList.toggle("is-active", b.dataset.nav === navId));
    sections.forEach(s => s.classList.toggle("is-active", s.id === navId));
  }
  btns.forEach(btn => btn.addEventListener("click", () => activate(btn.dataset.nav)));
  if (btns.length) activate(btns[0].dataset.nav);
}

function periodFormatLabel(type, period) {
  if (type === "monthly") return `${period.slice(0, 4)}年${period.slice(5, 7)}月 月報`;
  if (type === "quarterly") { const [y, q] = period.split("-"); return `${y}年 ${q} 季報`; }
  if (type === "yearly") return `${period}年 年報`;
  return period;
}

// ══ Period Report Categories ════════════════════════════════════
const PERIOD_REPORT_CATEGORIES = [
  { key: "traffic-overview",   label: "整體流量", kpiCols: ["total","views","clicks","applies","sessions"],                                   kpiLabels: ["總事件","View","Click","Apply","Sessions"],         mainMetric: "clicks",             breakdowns: [] },
  { key: "search-behavior",    label: "搜尋行為", kpiCols: ["general_click","ai_click","quick_click"],                                         kpiLabels: ["一般搜尋","AI 搜尋","快速篩選"],                     mainMetric: "general_click",      breakdowns: ["feature_counts.parquet"] },
  { key: "apply-conversion",   label: "應徵轉換", kpiCols: ["applies","job_views"],                                                            kpiLabels: ["應徵數","職缺頁瀏覽"],                               mainMetric: "applies",            breakdowns: ["source.parquet","funnel.parquet"] },
  { key: "apply-journey",      label: "應徵路徑", kpiCols: ["applies","apply_sessions","total_steps"],                                         kpiLabels: ["應徵數","有效 Session","總步數"],                     mainMetric: "applies",            breakdowns: ["path_ranking.parquet","entry_page.parquet"] },
  { key: "feature-engagement", label: "功能互動", kpiCols: ["explore_jobs_click","explore_corp_click","identity_click","news_click"],           kpiLabels: ["探索職缺","探索企業","身份辨識","新聞"],               mainMetric: "explore_jobs_click", breakdowns: [] },
  { key: "device-platform",    label: "裝置平台", kpiCols: ["mobile","desktop"],                                                               kpiLabels: ["Mobile","Desktop"],                                  mainMetric: "mobile",             breakdowns: [] },
  { key: "page-ranking",       label: "頁面排行", kpiCols: ["total_events","total_features"],                                                  kpiLabels: ["總事件","功能數"],                                   mainMetric: "total_events",       breakdowns: ["features.parquet","categories.parquet"] },
  { key: "page-navigation",    label: "頁面導航", kpiCols: ["nav_click","nav_view","entry_click","entry_view"],                                kpiLabels: ["導航 Click","導航 View","進入 Click","進入 View"],   mainMetric: "nav_click",          breakdowns: ["nav_pairs.parquet","entry_pages.parquet"] },
  { key: "click-heatmap",      label: "點擊熱點", kpiCols: ["total_clicks"],                                                                   kpiLabels: ["總點擊"],                                            mainMetric: "total_clicks",       breakdowns: ["click_counts.parquet"] },
  { key: "homepage-blocks",    label: "首頁區塊", kpiCols: ["total_clicks","total_views"],                                                     kpiLabels: ["總點擊","總瀏覽"],                                   mainMetric: "total_clicks",       breakdowns: ["feature_counts.parquet"] },
];

// ══ Period Report: Data Fetching ════════════════════════════════

async function _loadParquetRows(url, db, conn, alias) {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`HTTP ${resp.status} ${url}`);
  const buf = new Uint8Array(await resp.arrayBuffer());
  const fname = alias + ".parquet";
  await db.dropFile(fname).catch(() => {});
  await db.registerFileBuffer(fname, buf);
  const result = await conn.query(`SELECT * FROM read_parquet('${fname}')`);
  return result.toArray().map(r =>
    Object.fromEntries(Object.entries(r).map(([k, v]) => [k, typeof v === "bigint" ? Number(v) : v]))
  );
}

async function fetchPeriodReport(category, periodType, period, runtime) {
  const catCfg = PERIOD_REPORT_CATEGORIES.find(c => c.key === category);
  const dir = `report/${category}/${periodType}=${period}`;
  const safe = s => String(s).replace(/[^a-z0-9]/gi, "_");
  const base = `pr_${safe(category)}_${safe(periodType)}_${safe(period)}`;

  const summaryUrl = new URL(`${dir}/period_summary.parquet`, runtime.datasetRoot).href;
  const summary = await _loadParquetRows(summaryUrl, runtime.db, runtime.conn, `${base}_sum`);

  const breakdowns = {};
  for (const fn of catCfg?.breakdowns ?? []) {
    const bdUrl = new URL(`${dir}/${fn}`, runtime.datasetRoot).href;
    try {
      breakdowns[fn] = await _loadParquetRows(bdUrl, runtime.db, runtime.conn, `${base}_${safe(fn)}`);
    } catch {
      breakdowns[fn] = [];
    }
  }
  return { summary, breakdowns };
}

// ══ Period Report: Rendering ════════════════════════════════════

function _buildSimpleRankHtml(title, rows, nameKey, valueKey) {
  if (!rows.length) return `<p class="monthly-empty">${title}：無資料</p>`;
  const agg = new Map();
  for (const r of rows) {
    const k = String(r[nameKey] ?? "—");
    agg.set(k, (agg.get(k) ?? 0) + n(r[valueKey]));
  }
  const sorted = [...agg.entries()].sort((a, b) => b[1] - a[1]);
  const total = sorted.reduce((s, [, v]) => s + v, 0);
  const trs = sorted.map(([name, val], i) => rankRow(i, name, val, total)).join("");
  return `<div class="period-breakdown-section">
    <h4 class="period-breakdown-title">${title}</h4>
    <table><thead><tr><th>#</th><th>名稱</th><th>數量</th><th></th><th>佔比</th></tr></thead>
    <tbody>${trs}</tbody></table>
  </div>`;
}

function renderPeriodBreakdown(container, category, breakdowns) {
  let html = "";
  switch (category) {
    case "search-behavior": {
      const fc = breakdowns["feature_counts.parquet"] ?? [];
      const agg = new Map();
      for (const r of fc) {
        const k = String(r.feature_id);
        const e = agg.get(k);
        const cnt = n(r.count);
        if (e) { if (r.event_type === "click") e.click += cnt; else e.view += cnt; }
        else agg.set(k, { feature_id: k, feature_name: r.feature_name, click: r.event_type === "click" ? cnt : 0, view: r.event_type === "view" ? cnt : 0 });
      }
      const rows = [...agg.values()].sort((a, b) => b.click - a.click);
      const tot = rows.reduce((s, r) => s + r.click, 0);
      const trs = rows.map((r, i) => {
        const p = tot ? `${((r.click / tot) * 100).toFixed(1)}%` : "—";
        return `<tr><td class="rank">${i+1}</td><td>${r.feature_id}</td><td>${r.feature_name || "—"}</td><td>${fmt(r.click)}</td><td>${fmt(r.view)}</td><td class="pct">${p}</td></tr>`;
      }).join("");
      html += `<div class="period-breakdown-section">
        <h4 class="period-breakdown-title">搜尋功能使用量</h4>
        <table><thead><tr><th>#</th><th>featureId</th><th>featureName</th><th>Click</th><th>View</th><th>佔比</th></tr></thead>
        <tbody>${trs}</tbody></table>
      </div>`;
      break;
    }
    case "apply-conversion": {
      html += _buildSimpleRankHtml("應徵來源", breakdowns["source.parquet"] ?? [], "name", "count");
      html += _buildSimpleRankHtml("應徵漏斗", breakdowns["funnel.parquet"] ?? [], "name", "count");
      break;
    }
    case "apply-journey": {
      const pr = breakdowns["path_ranking.parquet"] ?? [];
      const pathAgg = new Map();
      for (const r of pr) {
        const k = String(r.path);
        const e = pathAgg.get(k);
        if (e) e.count += n(r.count);
        else pathAgg.set(k, { path: k, step_count: n(r.step_count), count: n(r.count) });
      }
      const pathRows = [...pathAgg.values()].sort((a, b) => b.count - a.count).slice(0, 30);
      const pathTot = pathRows.reduce((s, r) => s + r.count, 0);
      const pathTrs = pathRows.map((r, i) => {
        const p = pathTot ? `${((r.count / pathTot) * 100).toFixed(1)}%` : "—";
        return `<tr><td class="rank">${i+1}</td><td>${r.path}</td><td>${r.step_count}</td><td>${fmt(r.count)}</td><td class="pct">${p}</td></tr>`;
      }).join("");
      html += `<div class="period-breakdown-section">
        <h4 class="period-breakdown-title">Top 30 應徵路徑 <small style="color:var(--muted);font-weight:400">（僅顯示前 30 筆）</small></h4>
        <table><thead><tr><th>#</th><th>路徑</th><th>步數</th><th>次數</th><th>佔比</th></tr></thead>
        <tbody>${pathTrs}</tbody></table>
      </div>`;
      html += _buildSimpleRankHtml("進入頁分佈", breakdowns["entry_page.parquet"] ?? [], "name", "count");
      break;
    }
    case "page-ranking": {
      const feats = breakdowns["features.parquet"] ?? [];
      const featAgg = new Map();
      for (const r of feats) {
        const k = String(r.featureId);
        const e = featAgg.get(k);
        if (e) { e.total += n(r.total); e.views += n(r.views); e.clicks += n(r.clicks); }
        else featAgg.set(k, { featureId: k, feature_name: r.feature_name, category: r.category, total: n(r.total), views: n(r.views), clicks: n(r.clicks) });
      }
      const featRows = [...featAgg.values()].sort((a, b) => b.total - a.total).slice(0, 50);
      const featTrs = featRows.map((r, i) => {
        const ctr = r.views ? (r.clicks / r.views * 100).toFixed(2) : "0.00";
        return `<tr><td class="rank">${i+1}</td><td>${r.featureId}</td><td>${r.feature_name || "—"}</td><td>${fmt(r.total)}</td><td>${fmt(r.views)}</td><td>${fmt(r.clicks)}</td><td class="pct">${ctr}%</td><td>${r.category || "—"}</td></tr>`;
      }).join("");
      html += `<div class="period-breakdown-section">
        <h4 class="period-breakdown-title">Top 50 功能排行</h4>
        <table><thead><tr><th>#</th><th>featureId</th><th>featureName</th><th>總計</th><th>View</th><th>Click</th><th>CTR</th><th>類別</th></tr></thead>
        <tbody>${featTrs}</tbody></table>
      </div>`;
      html += _buildSimpleRankHtml("功能類別佔比", breakdowns["categories.parquet"] ?? [], "name", "count");
      break;
    }
    case "page-navigation": {
      const np = (breakdowns["nav_pairs.parquet"] ?? []).filter(r => r.event_type === "click");
      const pairAgg = new Map();
      for (const r of np) {
        const k = `${r.from}→${r.to}`;
        const e = pairAgg.get(k);
        if (e) e.count += n(r.count);
        else pairAgg.set(k, { from: r.from, to: r.to, count: n(r.count) });
      }
      const pairRows = [...pairAgg.values()].sort((a, b) => b.count - a.count).slice(0, 30);
      const pairTrs = pairRows.map((r, i) =>
        `<tr><td class="rank">${i+1}</td><td>${r.from || "—"}</td><td>${r.to || "—"}</td><td>${fmt(r.count)}</td></tr>`
      ).join("");
      html += `<div class="period-breakdown-section">
        <h4 class="period-breakdown-title">Top 30 頁面轉換路徑（Click）<small style="color:var(--muted);font-weight:400;margin-left:8px">（僅顯示前 30 筆）</small></h4>
        <table><thead><tr><th>#</th><th>來源頁</th><th>目標頁</th><th>次數</th></tr></thead>
        <tbody>${pairTrs}</tbody></table>
      </div>`;
      const ep = (breakdowns["entry_pages.parquet"] ?? []).filter(r => r.event_type === "click");
      html += _buildSimpleRankHtml("進入頁分佈（Click）", ep, "name", "count");
      break;
    }
    case "click-heatmap": {
      const cc = breakdowns["click_counts.parquet"] ?? [];
      const ccAgg = new Map();
      for (const r of cc) {
        const k = `${r.page_path}||${r.feature_id}`;
        const e = ccAgg.get(k);
        if (e) e.count += n(r.count);
        else ccAgg.set(k, { page_path: r.page_path, feature_id: r.feature_id, feature_name: r.feature_name, count: n(r.count) });
      }
      const ccRows = [...ccAgg.values()].sort((a, b) => b.count - a.count).slice(0, 50);
      const ccTot = ccRows.reduce((s, r) => s + r.count, 0);
      const ccTrs = ccRows.map((r, i) => {
        const p = ccTot ? `${((r.count / ccTot) * 100).toFixed(1)}%` : "—";
        return `<tr><td class="rank">${i+1}</td><td>${r.feature_id}</td><td>${r.feature_name || "—"}</td><td>${fmt(r.count)}</td><td class="pct">${p}</td><td>${r.page_path || "—"}</td></tr>`;
      }).join("");
      html += `<div class="period-breakdown-section">
        <h4 class="period-breakdown-title">Top 50 點擊功能排行</h4>
        <table><thead><tr><th>#</th><th>featureId</th><th>featureName</th><th>點擊數</th><th>佔比</th><th>頁面</th></tr></thead>
        <tbody>${ccTrs}</tbody></table>
      </div>`;
      break;
    }
    case "homepage-blocks": {
      const fc = breakdowns["feature_counts.parquet"] ?? [];
      const clickAgg = new Map();
      const viewAgg = {};
      for (const r of fc) {
        if (r.event_type === "view") { viewAgg[r.feature_id] = (viewAgg[r.feature_id] ?? 0) + n(r.count); continue; }
        const k = String(r.feature_id);
        const e = clickAgg.get(k);
        if (e) e.count += n(r.count);
        else clickAgg.set(k, { feature_id: k, feature_name: r.feature_name, count: n(r.count) });
      }
      const clickRows = [...clickAgg.values()].sort((a, b) => b.count - a.count);
      const catSections = MONTHLY_CATEGORIES.map(cat => {
        const catRows = clickRows.filter(r => cat.test(r.feature_id));
        return `<div style="margin-bottom:16px"><strong>${cat.label}</strong>${monthlyBuildCatTable(catRows, viewAgg)}</div>`;
      }).join("");
      html += `<div class="period-breakdown-section">
        <h4 class="period-breakdown-title">首頁區塊 featureId 明細</h4>
        ${catSections}
      </div>`;
      break;
    }
  }
  container.innerHTML = html;
}

async function fetchDailyBreakdown(category, date, runtime) {
  const catCfg = PERIOD_REPORT_CATEGORIES.find(c => c.key === category);
  const dir = `report/${category}/date=${date}`;
  const safe = s => String(s).replace(/[^a-z0-9]/gi, "_");
  const base = `dd_${safe(category)}_${safe(date)}`;
  const breakdowns = {};
  for (const fn of catCfg?.breakdowns ?? []) {
    const bdUrl = new URL(`${dir}/${fn}`, runtime.datasetRoot).href;
    try {
      breakdowns[fn] = await _loadParquetRows(bdUrl, runtime.db, runtime.conn, `${base}_${safe(fn)}`);
    } catch {
      breakdowns[fn] = [];
    }
  }
  return breakdowns;
}


function renderPeriodReport(container, category, periodType, period, data, runtime = null) {
  const catCfg = PERIOD_REPORT_CATEGORIES.find(c => c.key === category) ?? PERIOD_REPORT_CATEGORIES[0];
  const { summary, breakdowns } = data;

  const kpi = Object.fromEntries(catCfg.kpiCols.map(col => [col, summary.reduce((s, r) => s + n(r[col]), 0)]));
  const kpiCards = catCfg.kpiCols.map((col, i) =>
    `<div class="period-kpi-card">
      <div class="period-kpi-label">${catCfg.kpiLabels[i]}</div>
      <div class="period-kpi-value">${fmt(kpi[col])}</div>
    </div>`
  ).join("");

  const sorted = [...summary].sort((a, b) => String(a.period).localeCompare(String(b.period)));
  const mainLabelIdx = catCfg.kpiCols.indexOf(catCfg.mainMetric);

  container.innerHTML = `
    <div class="day-detail-header">
      <h3>${catCfg.label} — ${periodFormatLabel(periodType, period)}</h3>
    </div>
    <div class="period-kpi-row">${kpiCards}</div>
    <div class="period-trend-wrap">
      <canvas id="period-trend-chart"></canvas>
    </div>
    <div id="period-breakdown-container"></div>`;

  lineChart("period-trend-chart", sorted.map(r => r.period), [{
    label: catCfg.kpiLabels[mainLabelIdx] ?? catCfg.mainMetric,
    data: sorted.map(r => n(r[catCfg.mainMetric])),
    borderColor: C.blue,
    tension: 0.3,
    fill: false,
  }]);

  const bdContainer = document.getElementById("period-breakdown-container");
  if (bdContainer) renderPeriodBreakdown(bdContainer, category, breakdowns);
}

// ════════════════════════════════════════════════════════════════
// 10. 週期報表中心 — period-report
// ════════════════════════════════════════════════════════════════
function periodReportRenderer(runtime) {
  const section = document.getElementById("monthly-section");
  if (!section || !runtime) return;

  const params = new URLSearchParams(location.search);
  const initPeriodType = ["monthly","quarterly","yearly"].includes(params.get("period_type"))
    ? params.get("period_type") : "monthly";
  const initPeriod   = runtime.pendingPeriod ?? params.get("period") ?? null;
  const initCategory = runtime.pendingCategory ?? params.get("report_category") ?? PERIOD_REPORT_CATEGORIES[0].key;
  const initSubView  = ["monthly","daily"].includes(params.get("sub_view")) ? params.get("sub_view") : "monthly";
  const initDay      = params.get("day") ?? null;

  const catTabsHtml = PERIOD_REPORT_CATEGORIES.map(c =>
    `<button class="report-category-tab${c.key === initCategory ? " is-active" : ""}" data-cat="${c.key}" type="button">${c.label}</button>`
  ).join("");

  const ptTabsHtml = [
    { key: "monthly",   label: "月報" },
    { key: "quarterly", label: "季報" },
    { key: "yearly",    label: "年報" },
  ].map(t =>
    `<button class="period-type-tab${t.key === initPeriodType ? " is-active" : ""}" data-ptype="${t.key}" type="button">${t.label}</button>`
  ).join("");

  section.innerHTML = `
    <div class="monthly-layout">
      <nav class="report-category-tabs">${catTabsHtml}</nav>
      <nav class="period-type-tabs">${ptTabsHtml}</nav>
      <div class="period-selector"></div>
      <div class="monthly-detail">
        <div id="monthly-day-detail" class="monthly-day-detail">
          <p class="monthly-empty">點選上方期間查看明細</p>
        </div>
      </div>
    </div>`;

  let currentCategory   = initCategory;
  let currentPeriodType = initPeriodType;
  let currentPeriod     = initPeriod;
  let currentSubView    = initSubView;
  let currentDay        = initDay;
  let lastData          = null;

  const selectorEl = section.querySelector(".period-selector");
  const detailEl   = () => document.getElementById("monthly-day-detail");

  function updateUrl() {
    const p = new URLSearchParams(location.search);
    p.set("view", "period-report");
    p.set("period_type", currentPeriodType);
    p.set("report_category", currentCategory);
    if (currentPeriod) p.set("period", currentPeriod);
    else p.delete("period");
    if (currentPeriodType === "monthly") {
      p.set("sub_view", currentSubView);
      if (currentSubView === "daily" && currentDay) p.set("day", currentDay);
      else p.delete("day");
    } else {
      p.delete("sub_view");
      p.delete("day");
    }
    p.delete("date_from"); p.delete("date_to");
    history.replaceState(null, "", `?${p.toString()}`);
  }

  function buildSubViewTabs(container) {
    container.innerHTML = `
      <div class="sub-view-tabs">
        <button class="sub-view-tab${currentSubView === "monthly" ? " is-active" : ""}" data-subview="monthly" type="button">月報</button>
        <button class="sub-view-tab${currentSubView === "daily"   ? " is-active" : ""}" data-subview="daily"   type="button">日報</button>
      </div>`;
    container.querySelectorAll(".sub-view-tab").forEach(btn => {
      btn.addEventListener("click", () => {
        if (btn.dataset.subview === currentSubView) return;
        container.querySelectorAll(".sub-view-tab").forEach(b => b.classList.remove("is-active"));
        btn.classList.add("is-active");
        currentSubView = btn.dataset.subview;
        updateUrl();
        if (lastData) renderForSubView(lastData);
      });
    });
  }

  function renderForSubView(data) {
    const d = detailEl();
    if (!d) return;
    if (currentSubView === "daily") {
      renderDailyView(d, data, currentCategory, runtime);
    } else {
      renderPeriodReport(d, currentCategory, "monthly", currentPeriod, data, runtime);
    }
  }

  function renderDailyView(container, data, cat, rt) {
    const catCfg = PERIOD_REPORT_CATEGORIES.find(c => c.key === cat) ?? PERIOD_REPORT_CATEGORIES[0];
    const summary = data.summary ?? [];
    const asc = [...summary].sort((a, b) => String(a.period).localeCompare(String(b.period)));
    const firstDay = asc[0] ? String(asc[0].period) : null;
    if (!currentDay || !asc.find(r => String(r.period) === currentDay)) {
      currentDay = firstDay;
    }

    const btnHtml = asc.map(r => {
      const d = String(r.period);
      const [, mm, dd] = d.split("-");
      return `<button class="daily-date-btn${d === currentDay ? " is-active" : ""}" data-date="${d}" data-loaded="false" type="button">${Number(mm)}/${Number(dd)}</button>`;
    }).join("");

    container.innerHTML = `<div class="daily-date-tabs">${btnHtml}</div><div id="period-daily-drilldown"></div>`;

    const byDate = Object.fromEntries(summary.map(r => [String(r.period), r]));
    const hasBreakdowns = catCfg.breakdowns.length > 0;

    async function loadDay(date) {
      const ddEl = document.getElementById("period-daily-drilldown");
      if (!ddEl) return;
      const btn = container.querySelector(`.daily-date-btn[data-date="${date}"]`);
      if (!btn || btn.dataset.loaded === "true") return;
      if (!hasBreakdowns) {
        const r = byDate[date];
        const kpiCards = catCfg.kpiCols.map((col, i) =>
          `<div class="period-kpi-card">
            <div class="period-kpi-label">${catCfg.kpiLabels[i]}</div>
            <div class="period-kpi-value">${fmt(n(r[col]))}</div>
          </div>`).join("");
        ddEl.innerHTML = `<div class="period-kpi-row" style="padding:12px 0">${kpiCards}</div>`;
        btn.dataset.loaded = "true";
        return;
      }
      btn.dataset.loaded = "loading";
      ddEl.innerHTML = `<p class="monthly-loading">載入中…</p>`;
      try {
        const breakdowns = await fetchDailyBreakdown(cat, date, rt);
        ddEl.innerHTML = "";
        renderPeriodBreakdown(ddEl, cat, breakdowns);
        if (!ddEl.innerHTML.trim()) ddEl.innerHTML = `<p class="monthly-empty">無明細資料</p>`;
        btn.dataset.loaded = "true";
      } catch (e) {
        ddEl.innerHTML = `<p class="monthly-error">載入失敗：${e.message}</p>`;
        btn.dataset.loaded = "false";
      }
    }

    container.querySelectorAll(".daily-date-btn").forEach(btn => {
      btn.addEventListener("click", async () => {
        const isActive = btn.classList.contains("is-active");
        container.querySelectorAll(".daily-date-btn").forEach(b => b.classList.remove("is-active"));
        const ddEl = document.getElementById("period-daily-drilldown");
        if (isActive) {
          currentDay = null;
          updateUrl();
          if (ddEl) ddEl.innerHTML = "";
          return;
        }
        btn.classList.add("is-active");
        currentDay = btn.dataset.date;
        updateUrl();
        await loadDay(currentDay);
      });
    });

    if (currentDay) {
      updateUrl();
      loadDay(currentDay);
    }
  }

  async function loadAndRender(cat, ptype, period) {
    const d = detailEl();
    if (!d) return;
    const catLabel = PERIOD_REPORT_CATEGORIES.find(c => c.key === cat)?.label ?? cat;
    d.innerHTML = `<p class="monthly-loading">載入 ${periodFormatLabel(ptype, period)} · ${catLabel} 中…</p>`;
    try {
      const data = await fetchPeriodReport(cat, ptype, period, runtime);
      lastData = data;
      if (ptype === "monthly") {
        renderForSubView(data);
      } else {
        renderPeriodReport(d, cat, ptype, period, data, runtime);
      }
    } catch (err) {
      d.innerHTML = `<p class="monthly-error">載入失敗：${err.message}</p>`;
    }
  }

  function buildPeriodSelector(ptype) {
    const listMap = { monthly: runtime.availableMonths ?? [], quarterly: runtime.availableQuarters ?? [], yearly: runtime.availableYears ?? [] };
    const labelFn = {
      monthly:   p => `${p.slice(0,4)}年${p.slice(5,7)}月`,
      quarterly: p => { const [y,q] = p.split("-"); return `${y}年 ${q}`; },
      yearly:    p => `${p}年`,
    };
    const items = listMap[ptype] ?? [];
    if (!items.length) {
      selectorEl.innerHTML = `<p class="monthly-empty" style="padding:8px 12px">尚無${ptype}資料，請先執行 build_period_summary.py</p>`;
      return;
    }
    const tabs = items.map(p =>
      `<button class="month-tab${p === currentPeriod ? " is-active" : ""}" data-period="${p}" type="button">${labelFn[ptype](p)}</button>`
    ).join("");
    selectorEl.innerHTML = `<nav class="monthly-nav-months">${tabs}</nav>${ptype === "monthly" ? '<div class="sub-view-tabs-container"></div>' : ""}`;
    if (ptype === "monthly") buildSubViewTabs(selectorEl.querySelector(".sub-view-tabs-container"));

    selectorEl.querySelectorAll("[data-period]").forEach(btn => {
      btn.addEventListener("click", async () => {
        selectorEl.querySelectorAll("[data-period]").forEach(b => b.classList.remove("is-active"));
        btn.classList.add("is-active");
        currentPeriod = btn.dataset.period;
        currentSubView = "monthly";
        currentDay = null;
        lastData = null;
        const stc = selectorEl.querySelector(".sub-view-tabs-container");
        if (stc) buildSubViewTabs(stc);
        updateUrl();
        await loadAndRender(currentCategory, currentPeriodType, currentPeriod);
      });
    });

    // Auto-select: URL period → first available
    const initBtn = currentPeriod
      ? selectorEl.querySelector(`[data-period="${currentPeriod}"]`)
      : selectorEl.querySelector("[data-period]");
    if (initBtn) {
      initBtn.classList.add("is-active");
      currentPeriod = initBtn.dataset.period;
    }
  }

  // Category tab handlers
  section.querySelectorAll(".report-category-tab").forEach(tab => {
    tab.addEventListener("click", () => {
      section.querySelectorAll(".report-category-tab").forEach(t => t.classList.remove("is-active"));
      tab.classList.add("is-active");
      currentCategory = tab.dataset.cat;
      currentSubView = "monthly";
      currentDay = null;
      lastData = null;
      const stc = selectorEl.querySelector(".sub-view-tabs-container");
      if (stc) buildSubViewTabs(stc);
      updateUrl();
      if (currentPeriod) loadAndRender(currentCategory, currentPeriodType, currentPeriod);
    });
  });

  // Period-type tab handlers
  section.querySelectorAll(".period-type-tab").forEach(tab => {
    tab.addEventListener("click", async () => {
      section.querySelectorAll(".period-type-tab").forEach(t => t.classList.remove("is-active"));
      tab.classList.add("is-active");
      currentPeriodType = tab.dataset.ptype;
      currentPeriod = null;
      buildPeriodSelector(currentPeriodType);
      updateUrl();
      if (currentPeriod) await loadAndRender(currentCategory, currentPeriodType, currentPeriod);
    });
  });


  // Initial render
  buildPeriodSelector(currentPeriodType);
  if (currentPeriod) loadAndRender(currentCategory, currentPeriodType, currentPeriod);
}

// ════════════════════════════════════════════════════════════════
// 13. 性別／年齡層 × 職類／產業交叉分析
// ════════════════════════════════════════════════════════════════

function _pivotCrossBar(id, rows, dimCol, topN = 10) {
  const catTotals = {};
  rows.forEach(r => { catTotals[r.category] = (catTotals[r.category] ?? 0) + n(r.count); });
  const cats = Object.entries(catTotals).sort((a, b) => b[1] - a[1]).slice(0, topN).map(([c]) => c);
  const dims = [...new Set(rows.map(r => r[dimCol]))];
  const countMap = {};
  rows.forEach(r => { countMap[`${r[dimCol]}__${r.category}`] = n(r.count); });
  barChart(id, cats, dims.map((dim, i) => ({
    label: dim,
    data: cats.map(cat => countMap[`${dim}__${cat}`] ?? 0),
    backgroundColor: C.palette[i % C.palette.length],
  })), { plugins: { legend: { position: "bottom" } } });
}

function applyDemographicsCategoryRenderer(data) {
  const kpi        = data.kpi?.[0] ?? {};
  const total      = n(kpi.total_applies);
  const coverDemo  = n(kpi.coverage_demo);
  const coverJob   = n(kpi.coverage_job);

  setKpiCard("1", "總應徵數",   fmt(total),     "action=apply 事件數");
  setKpiCard("2", "有履歷資料", fmt(coverDemo),  `覆蓋率 ${total ? pct(coverDemo / total * 100) : "—"}`);
  setKpiCard("3", "有職缺資料", fmt(coverJob),   `覆蓋率 ${total ? pct(coverJob  / total * 100) : "—"}`);
  setKpiCard("4", "—", "—", "");
  setKpiCard("5", "—", "—", "");
  setKpiCard("6", "—", "—", "");
  setKpiCard("7", "—", "—", "");
  setKpiCard("8", "—", "—", "");

  const gjp = data.gender_job_position        ?? [];
  const ajp = data.age_group_job_position     ?? [];
  const gci = data.gender_company_industry    ?? [];

  _pivotCrossBar("chart1", gjp, "gender",    10);
  _pivotCrossBar("chart2", ajp, "age_group", 10);
  _pivotCrossBar("chart3", gci, "gender",    10);

  // 表格 1 — 性別 × 職類
  buildTableHead("table1-head", ["#", "性別", "職類", "應徵次數", "", "佔比"]);
  const gjpTotal = gjp.reduce((s, r) => s + n(r.count), 0);
  buildTableBody("table1-body", gjp, (r, i) => {
    const val = n(r.count);
    const barPct = gjpTotal ? ((val / gjpTotal) * 100).toFixed(1) : "0";
    const pctStr = gjpTotal ? `${((val / gjpTotal) * 100).toFixed(1)}%` : "—";
    return `<tr>
      <td class="rank">${i + 1}</td>
      <td>${r.gender ?? "—"}</td>
      <td>${r.category ?? "—"}</td>
      <td>${fmt(val)}</td>
      <td class="bar-cell"><div class="bar-bg"><div class="bar-fill" style="width:${barPct}%"></div></div></td>
      <td class="pct">${pctStr}</td>
    </tr>`;
  });

  // 表格 2 — 年齡層 × 職類
  buildTableHead("table2-head", ["#", "年齡層", "職類", "應徵次數", "", "佔比"]);
  const ajpTotal = ajp.reduce((s, r) => s + n(r.count), 0);
  buildTableBody("table2-body", ajp, (r, i) => {
    const val = n(r.count);
    const barPct = ajpTotal ? ((val / ajpTotal) * 100).toFixed(1) : "0";
    const pctStr = ajpTotal ? `${((val / ajpTotal) * 100).toFixed(1)}%` : "—";
    return `<tr>
      <td class="rank">${i + 1}</td>
      <td>${r.age_group ?? "—"}</td>
      <td>${r.category ?? "—"}</td>
      <td>${fmt(val)}</td>
      <td class="bar-cell"><div class="bar-bg"><div class="bar-fill" style="width:${barPct}%"></div></div></td>
      <td class="pct">${pctStr}</td>
    </tr>`;
  });
}

// ── 路由 ────────────────────────────────────────────────────────
const renderers = {
  overview:   overviewRenderer,
  search:     searchRenderer,
  apply:           applyRenderer,
  "apply-journey": applyJourneyRenderer,
  feature:         featureRenderer,
  device:     deviceRenderer,
  ranking:    rankingRenderer,
  navigation:          navigationRenderer,
  heatmap:             heatmapRenderer,
  "homepage-blocks":     homepageBlocksRenderer,
  "apply-job-category":  applyJobCategoryRenderer,
  "apply-demographics":  applyDemographicsRenderer,
  "apply-demographics-category": applyDemographicsCategoryRenderer,
};

export function renderDashboard(viewMode, outputs, runtime = null) {
  showPanels(viewMode);
  applyPanelText(viewMode);
  if (viewMode === "period-report" || viewMode === "monthly-report") {
    periodReportRenderer(runtime);
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
