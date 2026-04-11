import * as duckdb from "https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@1.30.0/+esm";

const datasetRoot = new URL("../dataset/", import.meta.url);

const defaultState = {
  manifestLoaded: false,
  duckdbReady: false,
  lastQuery: null,
  registeredDates: [],
  rowCount: null,
};

function setText(id, value) {
  const node = document.getElementById(id);
  if (node) {
    node.textContent = value;
  }
}

function renderState(state) {
  setText("manifest-status", state.manifestLoaded ? "已載入" : "尚未載入");
  setText("duckdb-status", state.duckdbReady ? "已初始化" : "尚未初始化");
  setText("query-summary", state.lastQuery || "尚未執行");
  setText("loaded-dates", String(state.registeredDates.length));
  setText("loaded-rows", state.rowCount == null ? "--" : String(state.rowCount));
  setText("query-log", JSON.stringify({
    manifestLoaded: state.manifestLoaded,
    duckdbReady: state.duckdbReady,
    registeredDates: state.registeredDates,
    rowCount: state.rowCount,
    lastQuery: state.lastQuery,
  }, null, 2));
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
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const formData = new FormData(form);
    const payload = Object.fromEntries(formData.entries());
    state.lastQuery = `待 Step 5 接入 DuckDB：${payload.date_from} ~ ${payload.date_to} / ${payload.view_mode}`;
    renderState(state);
  });
}

async function loadManifest() {
  const response = await fetch(new URL("manifest.json", datasetRoot));
  if (!response.ok) {
    throw new Error(`manifest 載入失敗：${response.status}`);
  }
  return response.json();
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
    const sourceUrl = new URL(entry.meta.path, datasetRoot).href;
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
  renderState(state);

  try {
    const manifest = await loadManifest();
    state.manifestLoaded = true;
    state.registeredDates = manifest.available_dates || [];
    renderState(state);

    const runtime = await initDuckDB();
    state.duckdbReady = true;
    renderState(state);

    const registeredFiles = await registerParquetFiles(runtime.db, manifest);
    state.registeredDates = registeredFiles.map((entry) => entry.date);
    state.rowCount = await buildEventsView(runtime.conn, registeredFiles);
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
