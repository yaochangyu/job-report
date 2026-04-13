import * as duckdb from "https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@1.30.0/+esm";
import { executeViewQueries } from "./query-definitions.js";
import { renderDashboard, resetDashboard } from "./dashboard-renderers.js";

// ── Dataset root detection ──────────────────────────────────────────────────
const datasetRootCandidates = [
  new URL("../dataset/", import.meta.url),
  new URL("./dataset/", import.meta.url),
];

const runtime = {
  db: null,
  conn: null,
  hasEventsView: false,
  datasetRoot: null,
};

// ── View metadata ───────────────────────────────────────────────────────────
const VIEW_META = {
  overview: {
    title: "整體概覽",
    subtitle: "Traffic Overview",
    desc: "觀察整體 KPI、趨勢與主要流量分佈。",
  },
  search: {
    title: "搜尋行為",
    subtitle: "Search Behavior",
    desc: "聚焦搜尋入口、AI 搜尋與快速篩選互動。",
  },
  apply: {
    title: "應徵轉換",
    subtitle: "Apply Conversion",
    desc: "檢視應徵量、來源與每日轉換趨勢。",
  },
  feature: {
    title: "功能互動",
    subtitle: "Feature Engagement",
    desc: "查看探索職缺、探索企業、身份辨識與新聞互動。",
  },
  device: {
    title: "裝置平台",
    subtitle: "Device & Platform",
    desc: "分析裝置、OS、browser 與行為差異。",
  },
  ranking: {
    title: "頁面排行",
    subtitle: "Page Ranking",
    desc: "觀察熱門 feature 與主要流量排行。",
  },
  navigation: {
    title: "頁面導航",
    subtitle: "Page Navigation",
    desc: "依 session 還原完整頁面鏈路，查看常見導航序列與入口頁。",
  },
  heatmap: {
    title: "點擊熱點",
    subtitle: "Page Click Heatmap",
    desc: "從點擊量視角觀察熱門互動區塊。",
  },
};

// ── State ────────────────────────────────────────────────────────────────────
const state = {
  selectedView: null,
  lastSuccessfulFilters: null,
  ready: false,
};

// ── DOM helpers ──────────────────────────────────────────────────────────────
function setText(id, value) {
  const node = document.getElementById(id);
  if (node) node.textContent = value;
}
function setStatus(msg) {
  setText("status-bar", msg);
}
function setPill(id, value) {
  const node = document.getElementById(id);
  if (node) node.textContent = value;
}

function setLoading(loading) {
  const btn = document.getElementById("btn-query");
  if (btn) btn.disabled = loading;
  if (loading) {
    setStatus("查詢中…");
  }
}

// ── Date helpers ─────────────────────────────────────────────────────────────
function hydrateDefaultDates() {
  const today = new Date();
  const from = new Date(today);
  from.setDate(today.getDate() - 6);
  document.getElementById("date-from").value = from.toISOString().slice(0, 10);
  document.getElementById("date-to").value = today.toISOString().slice(0, 10);
}

// ── Filters ──────────────────────────────────────────────────────────────────
function collectFilters(viewMode) {
  return {
    dateFrom: document.getElementById("date-from").value,
    dateTo: document.getElementById("date-to").value,
    pagePath: document.getElementById("page-path").value.trim(),
    viewMode,
  };
}

// ── Table render ─────────────────────────────────────────────────────────────
function renderTable(rows) {
  const body = document.getElementById("primary-table-body");
  if (!rows.length) {
    body.innerHTML = '<tr><td colspan="4" class="empty-cell">查詢沒有結果</td></tr>';
    return;
  }
  body.innerHTML = rows
    .slice(0, 20)
    .map((row, i) => {
      const entries = Object.entries(row);
      const [k0, v0] = entries[0] || ["name", "-"];
      const [k1, v1] = entries[1] || ["value", "-"];
      const [k2, v2] = entries[2] || ["extra", "-"];
      return `<tr>
        <td>${i + 1}</td>
        <td>${k0}: ${String(v0 ?? "-")}</td>
        <td>${k1}: ${String(v1 ?? "-")}</td>
        <td>${k2}: ${String(v2 ?? "-")}</td>
      </tr>`;
    })
    .join("");
}

// ── Run query ────────────────────────────────────────────────────────────────
async function runQuery(filters) {
  if (!runtime.conn || !runtime.hasEventsView) {
    setStatus("資料尚未就緒，請稍候…");
    return;
  }
  setLoading(true);
  try {
    const result = await executeViewQueries(runtime.conn, filters);
    state.lastSuccessfulFilters = {
      dateFrom: filters.dateFrom,
      dateTo: filters.dateTo,
      pagePath: filters.pagePath,
    };
    const tableRows = renderDashboard(filters.viewMode, result.outputs);
    renderTable(tableRows);
    setStatus(result.summary);
  } catch (err) {
    setStatus("查詢錯誤：" + (err instanceof Error ? err.message : String(err)));
    renderTable([]);
    resetDashboard();
  } finally {
    setLoading(false);
  }
}

// ── Card selection ────────────────────────────────────────────────────────────
function selectCard(viewMode) {
  state.selectedView = viewMode;

  // highlight active card
  document.querySelectorAll(".report-card").forEach((btn) => {
    btn.classList.toggle("is-active", btn.dataset.view === viewMode);
  });

  // update filter panel label
  const meta = VIEW_META[viewMode] || {};
  setText("filter-panel-title", meta.title || viewMode);
  setText("filter-panel-desc", meta.desc || "");

  // show dashboard section
  const section = document.getElementById("dashboard-section");
  section.classList.remove("is-hidden");

  // scroll to dashboard
  section.scrollIntoView({ behavior: "smooth", block: "start" });

  // auto-query if already ready
  if (runtime.hasEventsView) {
    const filters = state.lastSuccessfulFilters
      ? { ...state.lastSuccessfulFilters, viewMode }
      : collectFilters(viewMode);
    runQuery(filters);
  } else {
    resetDashboard();
    setStatus("資料載入中，就緒後可按查詢…");
  }
}

// ── Bind events ───────────────────────────────────────────────────────────────
function bindCards() {
  document.querySelectorAll(".report-card").forEach((btn) => {
    btn.addEventListener("click", () => selectCard(btn.dataset.view));
  });
}

function bindForm() {
  document.getElementById("query-form").addEventListener("submit", (e) => {
    e.preventDefault();
    if (!state.selectedView) return;
    runQuery(collectFilters(state.selectedView));
  });
}

// ── DuckDB bootstrap ──────────────────────────────────────────────────────────
async function loadManifest() {
  for (const candidate of datasetRootCandidates) {
    const res = await fetch(new URL("manifest.json", candidate));
    if (res.ok) {
      runtime.datasetRoot = candidate;
      return res.json();
    }
  }
  throw new Error("manifest 載入失敗：404");
}

async function initDuckDB() {
  const bundle = await duckdb.selectBundle(duckdb.getJsDelivrBundles());
  const workerUrl = URL.createObjectURL(
    new Blob([`importScripts("${bundle.mainWorker}");`], { type: "text/javascript" }),
  );
  const worker = new Worker(workerUrl);
  const db = new duckdb.AsyncDuckDB(new duckdb.ConsoleLogger(), worker);
  await db.instantiate(bundle.mainModule, bundle.pthreadWorker);
  URL.revokeObjectURL(workerUrl);
  const conn = await db.connect();
  return { db, conn };
}

async function registerParquetFiles(db, manifest) {
  const entries = manifest.available_dates
    .map((date) => ({ date, meta: manifest.dates?.[date] }))
    .filter((e) => e.meta?.path);
  if (!entries.length) return [];
  for (const entry of entries) {
    const alias = `events_${entry.date.replaceAll("-", "_")}.parquet`;
    const url = new URL(entry.meta.path, runtime.datasetRoot).href;
    await db.registerFileURL(alias, url, duckdb.DuckDBDataProtocol.HTTP, false);
    entry.alias = alias;
  }
  return entries;
}

async function buildEventsView(conn, files) {
  if (!files.length) return 0;
  const list = files.map((e) => `'${e.alias}'`).join(", ");
  await conn.query(`CREATE OR REPLACE VIEW events AS SELECT * FROM read_parquet([${list}])`);
  const result = await conn.query("SELECT COUNT(*) AS total_rows FROM events");
  return result.toArray()[0].total_rows;
}

// ── Main ──────────────────────────────────────────────────────────────────────
async function bootstrap() {
  hydrateDefaultDates();
  bindCards();
  bindForm();

  setPill("pill-status", "載入 manifest…");

  try {
    const manifest = await loadManifest();
    const dates = manifest.available_dates || [];
    setPill("pill-dates", `${dates.length} 個日期分區`);
    setPill("pill-status", "初始化 DuckDB…");

    const { db, conn } = await initDuckDB();
    runtime.db = db;
    runtime.conn = conn;

    const files = await registerParquetFiles(db, manifest);
    const rowCount = await buildEventsView(conn, files);
    runtime.hasEventsView = files.length > 0;

    setPill("pill-rows", rowCount.toLocaleString() + " 筆事件");
    setPill("pill-status", runtime.hasEventsView ? "✓ 就緒" : "無可查詢資料");

    // if user already clicked a card while loading, auto-query now
    if (state.selectedView && runtime.hasEventsView) {
      const filters = state.lastSuccessfulFilters
        ? { ...state.lastSuccessfulFilters, viewMode: state.selectedView }
        : collectFilters(state.selectedView);
      runQuery(filters);
    }
  } catch (err) {
    setPill("pill-status", "錯誤：" + (err instanceof Error ? err.message : String(err)));
  }
}

bootstrap();
