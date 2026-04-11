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
};

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

function summarizeQueryResult(outputs) {
  return outputs.map((item) => ({
    name: item.name,
    rowCount: item.rows.length,
    sample: item.rows.slice(0, 3),
  }));
}

function renderState(state) {
  setText("manifest-status", state.manifestLoaded ? "已載入" : "尚未載入");
  setText("duckdb-status", state.duckdbReady ? "已初始化" : "尚未初始化");
  setText("query-summary", state.lastQuery || "尚未執行");
  setText("loaded-dates", String(state.registeredDates.length));
  setText("loaded-rows", state.rowCount == null ? "--" : String(state.rowCount));
  setText("query-log", safeJson({
    manifestLoaded: state.manifestLoaded,
    duckdbReady: state.duckdbReady,
    registeredDates: state.registeredDates,
    rowCount: state.rowCount,
    lastQuery: state.lastQuery,
    queryResult: state.queryResult,
  }));
}

function renderPrimaryTable(rows) {
  const body = document.getElementById("primary-table-body");
  if (!rows.length) {
    body.innerHTML = '<tr><td colspan="4" class="empty-cell">查詢沒有結果</td></tr>';
    return;
  }

  body.innerHTML = rows
    .slice(0, 12)
    .map((row, index) => {
      const entries = Object.entries(row);
      const [firstKey, firstValue] = entries[0] || ["name", "-"];
      const [secondKey, secondValue] = entries[1] || ["value", "-"];
      const [thirdKey, thirdValue] = entries[2] || ["extra", "-"];
      return `
        <tr>
          <td>${index + 1}</td>
          <td>${firstKey}: ${String(firstValue ?? "-")}</td>
          <td>${secondKey}: ${String(secondValue ?? "-")}</td>
          <td>${thirdKey}: ${String(thirdValue ?? "-")}</td>
        </tr>
      `;
    })
    .join("");
}

function hydrateDefaultDates() {
  const today = new Date();
  const from = new Date(today);
  from.setDate(today.getDate() - 6);

  document.getElementById("date-from").value = from.toISOString().slice(0, 10);
  document.getElementById("date-to").value = today.toISOString().slice(0, 10);
}

function bindQueryForm(state) {
  const form = document.getElementById("query-form");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(form);
    const payload = Object.fromEntries(formData.entries());
    const filters = {
      dateFrom: payload.date_from,
      dateTo: payload.date_to,
      viewMode: payload.view_mode,
      pagePath: payload.page_path?.trim() || "",
    };

    if (!runtime.conn || !runtime.hasEventsView) {
      state.lastQuery = "目前沒有 events view，可先執行 extract_events.py 匯出 Parquet";
      state.queryResult = null;
      renderPrimaryTable([]);
      resetDashboard();
      renderState(state);
      return;
    }

    const result = await executeViewQueries(runtime.conn, filters);
    state.lastQuery = result.summary;
    state.queryResult = summarizeQueryResult(result.outputs);
    renderPrimaryTable(renderDashboard(filters.viewMode, result.outputs));
    renderState(state);
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
  hydrateDefaultDates();
  bindQueryForm(state);
  renderPrimaryTable([]);
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
  } catch (error) {
    state.lastQuery = error instanceof Error ? error.message : String(error);
  }

  renderState(state);
}

bootstrap().catch((error) => {
  setText("query-log", `Bootstrap 失敗：${error instanceof Error ? error.message : String(error)}`);
});
