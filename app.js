import * as duckdb from "https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@1.30.0/+esm";
import { executeViewQueries } from "./query-definitions.js";
import { renderDashboard, resetDashboard } from "./dashboard-renderers.js";

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

const defaultState = {
  manifestLoaded: false,
  duckdbReady: false,
  lastQuery: null,
  registeredDates: [],
  rowCount: null,
  queryResult: null,
  selectedViewMode: "overview",
  theme: "light",
  lastSuccessfulFilters: null,
  sidebarCollapsed: false,
};

const THEME_STORAGE_KEY = "job-report-theme";
const SIDEBAR_STORAGE_KEY = "job-report-sidebar-collapsed";

// 各視角是否顯示「頁面路徑」欄位
const VIEW_FILTER_FIELDS = {
  overview:   { pagePath: true  },
  search:     { pagePath: false },
  apply:      { pagePath: false },
  feature:    { pagePath: false },
  device:     { pagePath: false },
  ranking:    { pagePath: true  },
  navigation: { pagePath: true  },
  heatmap:    { pagePath: true  },
};

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

function isValidViewMode(viewMode) {
  return Boolean(viewMode && viewMode in VIEW_META);
}

function setText(id, value) {
  const node = document.getElementById(id);
  if (node) {
    node.textContent = value;
  }
}

function safeJson(value) {
  return JSON.stringify(
    value,
    (_, current) => (typeof current === "bigint" ? Number(current) : current),
    2,
  );
}

function applyTheme(theme, state) {
  document.documentElement.dataset.theme = theme;
  state.theme = theme;
  localStorage.setItem(THEME_STORAGE_KEY, theme);
  setText("theme-toggle", theme === "light" ? "切換暗黑版" : "切換光亮版");
}

function applySidebarState(collapsed, state) {
  const pageLayout = document.getElementById("page-layout");
  pageLayout.classList.toggle("is-sidebar-collapsed", collapsed);
  state.sidebarCollapsed = collapsed;
  localStorage.setItem(SIDEBAR_STORAGE_KEY, collapsed ? "true" : "false");
  document.getElementById("sidebar-toggle").setAttribute("aria-expanded", collapsed ? "false" : "true");
  document.getElementById("sidebar-toggle").setAttribute("aria-label", collapsed ? "展開側邊導覽" : "收合側邊導覽");
  setText("sidebar-toggle-icon", collapsed ? "▶" : "◀");
}

function renderViewMeta(state) {
  const meta = VIEW_META[state.selectedViewMode] || VIEW_META.overview;
  setText("current-view-title", meta.title);
  setText("current-view-subtitle", meta.subtitle);
  setText("current-view-desc", meta.desc);

  document.querySelectorAll("[data-view-mode]").forEach((button) => {
    const active = button.dataset.viewMode === state.selectedViewMode;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-current", active ? "page" : "false");
  });

  updateFilterFields(state.selectedViewMode);
}

function summarizeQueryResult(outputs) {
  return outputs.map((item) => ({
    name: item.name,
    rowCount: item.rows.length,
    sample: item.rows.slice(0, 3),
  }));
}

function renderState(state) {
  // 只更新右側 query-status 顯示
  const parts = [];
  if (!state.manifestLoaded) parts.push("資料載入中…");
  else if (!state.duckdbReady) parts.push("DuckDB 初始化中…");
  else if (state.rowCount != null) parts.push(`已載入 ${state.registeredDates.length} 個日期分區 · ${state.rowCount.toLocaleString()} 筆`);
  if (state.lastQuery) parts.push(state.lastQuery);
  setText("query-status", parts.join("  ·  "));
}


function getQueryForm() {
  return document.getElementById("query-form");
}

function collectFormFilters(form, viewMode) {
  const formData = new FormData(form);
  const payload = Object.fromEntries(formData.entries());
  return {
    dateFrom: payload.date_from,
    dateTo: payload.date_to,
    pagePath: payload.page_path?.trim() || "",
    viewMode,
  };
}

function updateFilterFields(viewMode) {
  const config = VIEW_FILTER_FIELDS[viewMode] || { pagePath: true };
  const wrap = document.getElementById("filter-page-path-wrap");
  if (wrap) {
    wrap.classList.toggle("filter-field--hidden", !config.pagePath);
    // 視角不支援 pagePath 時清空值，避免帶入查詢
    if (!config.pagePath) {
      const input = document.getElementById("page-path");
      if (input) input.value = "";
    }
  }
}

function applyFiltersToForm(filters) {
  document.getElementById("date-from").value  = filters.dateFrom;
  document.getElementById("date-to").value    = filters.dateTo;
  document.getElementById("page-path").value  = filters.pagePath;
}

async function runQuery(state, filters) {
  if (!runtime.conn || !runtime.hasEventsView) {
    state.lastQuery = "目前沒有 events view，可先執行 extract_events.py 匯出 Parquet";
    state.queryResult = null;
    resetDashboard();
    renderState(state);
    return false;
  }

  try {
    syncUrlParams(filters);
    const result = await executeViewQueries(runtime.conn, filters);
    state.lastQuery = result.summary;
    state.queryResult = summarizeQueryResult(result.outputs);
    state.lastSuccessfulFilters = {
      dateFrom: filters.dateFrom,
      dateTo:   filters.dateTo,
      pagePath: filters.pagePath,
    };
    renderDashboard(filters.viewMode, result.outputs);
    renderState(state);
    return true;
  } catch (error) {
    state.lastQuery = error instanceof Error ? error.message : String(error);
    state.queryResult = null;
    resetDashboard();
    renderState(state);
    return false;
  }
}

function buildDefaultFilters() {
  const today = new Date();
  const from = new Date(today);
  from.setDate(today.getDate() - 6);
  return {
    dateFrom: from.toISOString().slice(0, 10),
    dateTo: today.toISOString().slice(0, 10),
    pagePath: "",
  };
}

function readInitialFilters(viewMode) {
  const params = new URLSearchParams(window.location.search);
  const defaults = buildDefaultFilters();
  return {
    dateFrom: params.get("date_from") || defaults.dateFrom,
    dateTo: params.get("date_to") || defaults.dateTo,
    pagePath: params.get("page_path") || defaults.pagePath,
    viewMode,
  };
}

function syncUrlParams(filters) {
  const url = new URL(window.location.href);
  url.searchParams.set("view", filters.viewMode);
  url.searchParams.set("date_from", filters.dateFrom);
  url.searchParams.set("date_to", filters.dateTo);
  if (filters.pagePath) url.searchParams.set("page_path", filters.pagePath);
  else url.searchParams.delete("page_path");
  history.replaceState(null, "", `${url.pathname}${url.search}`);
}

function resolveInitialViewMode() {
  const params = new URLSearchParams(window.location.search);
  const viewFromUrl = params.get("view");
  if (isValidViewMode(viewFromUrl)) return viewFromUrl;
  const bodyView = document.body.dataset.initialView;
  if (isValidViewMode(bodyView)) return bodyView;
  return "overview";
}

function bindThemeToggle(state) {
  document.getElementById("theme-toggle").addEventListener("click", () => {
    applyTheme(state.theme === "light" ? "dark" : "light", state);
  });
}

function bindSidebarToggle(state) {
  document.getElementById("sidebar-toggle").addEventListener("click", () => {
    applySidebarState(!state.sidebarCollapsed, state);
  });
}

function bindSidebar(state) {
  document.querySelectorAll("[data-view-mode]").forEach((button) => {
    button.addEventListener("click", async () => {
      state.selectedViewMode = button.dataset.viewMode;
      renderViewMeta(state);
      const form = getQueryForm();

      if (state.lastSuccessfulFilters) {
        const filters = {
          ...state.lastSuccessfulFilters,
          viewMode: state.selectedViewMode,
        };
        applyFiltersToForm(filters);
        await runQuery(state, filters);
        return;
      }

      await runQuery(state, collectFormFilters(form, state.selectedViewMode));
    });
  });
}

function bindQueryForm(state) {
  const form = getQueryForm();
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    await runQuery(state, collectFormFilters(form, state.selectedViewMode));
  });
}

async function loadManifest() {
  for (const candidate of datasetRootCandidates) {
    const response = await fetch(new URL("manifest.json", candidate));
    if (response.ok) {
      runtime.datasetRoot = candidate;
      return response.json();
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
    .filter((entry) => entry.meta?.path);

  if (!entries.length) {
    return [];
  }

  for (const entry of entries) {
    const alias = `events_${entry.date.replaceAll("-", "_")}.parquet`;
    const sourceUrl = new URL(entry.meta.path, runtime.datasetRoot).href;
    await db.registerFileURL(alias, sourceUrl, duckdb.DuckDBDataProtocol.HTTP, false);
    entry.alias = alias;
  }

  return entries;
}

async function buildEventsView(conn, registeredFiles) {
  if (!registeredFiles.length) {
    return 0;
  }

  const files = registeredFiles.map((entry) => `'${entry.alias}'`).join(", ");
  await conn.query(`CREATE OR REPLACE VIEW events AS SELECT * FROM read_parquet([${files}])`);
  const result = await conn.query("SELECT COUNT(*) AS total_rows FROM events");
  return result.toArray()[0].total_rows;
}

async function bootstrap() {
  const state = { ...defaultState };
  state.selectedViewMode = resolveInitialViewMode();

  const savedTheme = localStorage.getItem(THEME_STORAGE_KEY);
  const savedSidebarState = localStorage.getItem(SIDEBAR_STORAGE_KEY);
  applyTheme(savedTheme === "dark" ? "dark" : "light", state);
  applySidebarState(savedSidebarState === "true", state);
  applyFiltersToForm(readInitialFilters(state.selectedViewMode));
  bindThemeToggle(state);
  bindSidebarToggle(state);
  bindSidebar(state);
  bindQueryForm(state);
  renderViewMeta(state);
  resetDashboard();
  renderState(state);

  try {
    const manifest = await loadManifest();
    state.manifestLoaded = true;
    state.registeredDates = manifest.available_dates || [];
    renderState(state);

    const duckdbRuntime = await initDuckDB();
    state.duckdbReady = true;
    runtime.db = duckdbRuntime.db;
    runtime.conn = duckdbRuntime.conn;
    renderState(state);

    const registeredFiles = await registerParquetFiles(runtime.db, manifest);
    state.registeredDates = registeredFiles.map((entry) => entry.date);
    state.rowCount = await buildEventsView(runtime.conn, registeredFiles);
    runtime.hasEventsView = registeredFiles.length > 0;
    state.lastQuery = registeredFiles.length
      ? `DuckDB 已載入 ${registeredFiles.length} 個日期分區`
      : "manifest 已載入，但目前沒有可查詢的 Parquet 檔";

    // DuckDB 載入完成後自動執行查詢
    if (runtime.hasEventsView) {
      renderState(state);
      const form = document.getElementById("query-form");
      const filters = collectFormFilters(form, state.selectedViewMode);
      await runQuery(state, filters);
      return;
    }
  } catch (error) {
    state.lastQuery = error instanceof Error ? error.message : String(error);
  }

  renderState(state);
}

bootstrap().catch((error) => {
  setText("query-status", `Bootstrap 失敗：${error instanceof Error ? error.message : String(error)}`);
});
