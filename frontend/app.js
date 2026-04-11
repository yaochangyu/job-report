const defaultState = {
  manifestLoaded: false,
  duckdbReady: false,
  lastQuery: null,
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
  setText("query-log", JSON.stringify(state, null, 2));
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

function bootstrap() {
  const state = { ...defaultState };
  hydrateDefaultDates();
  bindQueryForm(state);
  renderState(state);
}

bootstrap();
