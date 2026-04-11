import Chart from "https://cdn.jsdelivr.net/npm/chart.js@4.4.7/auto/+esm";

const chartCache = new Map();
const colors = ["#38bdf8", "#8b5cf6", "#22c55e", "#f59e0b", "#ef4444", "#14b8a6"];

function destroyChart(id) {
  const chart = chartCache.get(id);
  if (chart) {
    chart.destroy();
    chartCache.delete(id);
  }
}

function renderChart(id, config) {
  destroyChart(id);
  const canvas = document.getElementById(id);
  const chart = new Chart(canvas, config);
  chartCache.set(id, chart);
}

function setKpi(id, value) {
  const node = document.getElementById(id);
  node.textContent = value;
}

function number(value) {
  return Number(value || 0);
}

function percent(value) {
  return `${Number(value || 0).toFixed(1)}%`;
}

function resetKpis() {
  setKpi("kpi-total", "--");
  setKpi("kpi-views", "--");
  setKpi("kpi-clicks", "--");
  setKpi("kpi-applies", "--");
  setKpi("kpi-sessions", "--");
  setKpi("kpi-ctr", "--");
  setKpi("kpi-apply-rate", "--");
  setKpi("kpi-mobile-rate", "--");
}

function renderEmptyCharts() {
  const empty = {
    labels: [],
    datasets: [{ label: "No data", data: [] }],
  };
  renderChart("trend-chart", { type: "line", data: empty });
  renderChart("distribution-chart", { type: "doughnut", data: empty });
  renderChart("ranking-chart", { type: "bar", data: empty });
}

function byName(outputs) {
  return Object.fromEntries(outputs.map((item) => [item.name, item.rows]));
}

function lineConfig(labels, datasets) {
  return {
    type: "line",
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
    },
  };
}

function doughnutConfig(rows) {
  return {
    type: "doughnut",
    data: {
      labels: rows.map((row) => row.name),
      datasets: [{
        data: rows.map((row) => number(row.count)),
        backgroundColor: rows.map((_, index) => colors[index % colors.length]),
      }],
    },
  };
}

function barConfig(rows, valueKey = "count", labelKey = "name", label = "Count") {
  return {
    type: "bar",
    data: {
      labels: rows.map((row) => row[labelKey]),
      datasets: [{
        label,
        data: rows.map((row) => number(row[valueKey])),
        backgroundColor: colors[0],
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
    },
  };
}

function overviewRenderer(data) {
  const kpi = data.kpi?.[0] || {};
  const ctr = kpi.total ? (number(kpi.clicks) / number(kpi.total)) * 100 : 0;
  const applyRate = kpi.views ? (number(kpi.applies) / number(kpi.views)) * 100 : 0;

  setKpi("kpi-total", number(kpi.total).toLocaleString());
  setKpi("kpi-views", number(kpi.views).toLocaleString());
  setKpi("kpi-clicks", number(kpi.clicks).toLocaleString());
  setKpi("kpi-applies", number(kpi.applies).toLocaleString());
  setKpi("kpi-sessions", number(kpi.sessions).toLocaleString());
  setKpi("kpi-ctr", percent(ctr));
  setKpi("kpi-apply-rate", percent(applyRate));
  setKpi("kpi-mobile-rate", "--");

  renderChart("trend-chart", lineConfig(
    data.trend.map((row) => row.date),
    [
      { label: "Total", data: data.trend.map((row) => number(row.total)), borderColor: colors[0] },
      { label: "Views", data: data.trend.map((row) => number(row.views)), borderColor: colors[1] },
      { label: "Clicks", data: data.trend.map((row) => number(row.clicks)), borderColor: colors[2] },
      { label: "Applies", data: data.trend.map((row) => number(row.applies)), borderColor: colors[3] },
    ],
  ));
  renderChart("distribution-chart", doughnutConfig(data.distribution || []));
  renderChart("ranking-chart", barConfig((data.ranking || []).slice(0, 10)));
  return data.ranking || [];
}

function searchRenderer(data) {
  const kpi = data.kpi?.[0] || {};
  const total = number(kpi.general_total) + number(kpi.ai_total);
  setKpi("kpi-total", total.toLocaleString());
  setKpi("kpi-views", number(kpi.search_page_total).toLocaleString());
  setKpi("kpi-clicks", number(kpi.quick_total).toLocaleString());
  setKpi("kpi-applies", "--");
  setKpi("kpi-sessions", "--");
  setKpi("kpi-ctr", percent(total ? (number(kpi.ai_total) / total) * 100 : 0));
  setKpi("kpi-apply-rate", "--");
  setKpi("kpi-mobile-rate", "--");

  renderChart("trend-chart", lineConfig(
    data.trend.map((row) => row.date),
    [
      { label: "General", data: data.trend.map((row) => number(row.general)), borderColor: colors[0] },
      { label: "AI", data: data.trend.map((row) => number(row.ai)), borderColor: colors[1] },
    ],
  ));
  renderChart("distribution-chart", doughnutConfig(data.distribution || []));
  renderChart("ranking-chart", barConfig(data.distribution || []));
  return data.distribution || [];
}

function applyRenderer(data) {
  const kpi = data.kpi?.[0] || {};
  const applyRate = kpi.job_views ? (number(kpi.applies) / number(kpi.job_views)) * 100 : 0;
  setKpi("kpi-total", number(kpi.job_views).toLocaleString());
  setKpi("kpi-views", number(kpi.home_page_views).toLocaleString());
  setKpi("kpi-clicks", number(kpi.search_page_views).toLocaleString());
  setKpi("kpi-applies", number(kpi.applies).toLocaleString());
  setKpi("kpi-sessions", "--");
  setKpi("kpi-ctr", "--");
  setKpi("kpi-apply-rate", percent(applyRate));
  setKpi("kpi-mobile-rate", "--");

  renderChart("trend-chart", lineConfig(
    data.trend.map((row) => row.date),
    [
      { label: "Applies", data: data.trend.map((row) => number(row.applies)), borderColor: colors[3] },
      { label: "Job Views", data: data.trend.map((row) => number(row.job_views)), borderColor: colors[0] },
    ],
  ));
  renderChart("distribution-chart", doughnutConfig(data.distribution || []));
  renderChart("ranking-chart", barConfig(data.hourly || [], "apply_count", "hour", "Apply"));
  return data.distribution || [];
}

function featureRenderer(data) {
  const kpi = data.kpi?.[0] || {};
  setKpi("kpi-total", number(kpi.explore_jobs).toLocaleString());
  setKpi("kpi-views", number(kpi.explore_corp).toLocaleString());
  setKpi("kpi-clicks", number(kpi.identity_total).toLocaleString());
  setKpi("kpi-applies", number(kpi.news_total).toLocaleString());
  setKpi("kpi-sessions", "--");
  setKpi("kpi-ctr", "--");
  setKpi("kpi-apply-rate", "--");
  setKpi("kpi-mobile-rate", "--");

  renderChart("trend-chart", barConfig(data.distribution || []));
  renderChart("distribution-chart", doughnutConfig(data.categories || []));
  renderChart("ranking-chart", barConfig(data.categories || []));
  return data.distribution || [];
}

function deviceRenderer(data) {
  const kpi = data.kpi?.[0] || {};
  const mobileRate = (number(kpi.mobile_total) + number(kpi.desktop_total))
    ? (number(kpi.mobile_total) / (number(kpi.mobile_total) + number(kpi.desktop_total))) * 100
    : 0;
  setKpi("kpi-total", (number(kpi.mobile_total) + number(kpi.desktop_total)).toLocaleString());
  setKpi("kpi-views", number(kpi.mobile_total).toLocaleString());
  setKpi("kpi-clicks", number(kpi.desktop_total).toLocaleString());
  setKpi("kpi-applies", "--");
  setKpi("kpi-sessions", "--");
  setKpi("kpi-ctr", "--");
  setKpi("kpi-apply-rate", "--");
  setKpi("kpi-mobile-rate", percent(mobileRate));

  renderChart("trend-chart", lineConfig(
    data.trend.map((row) => row.date),
    [
      { label: "Mobile", data: data.trend.map((row) => number(row.mobile)), borderColor: colors[0] },
      { label: "Desktop", data: data.trend.map((row) => number(row.desktop)), borderColor: colors[1] },
    ],
  ));
  renderChart("distribution-chart", doughnutConfig(data.distribution || []));
  renderChart("ranking-chart", barConfig(data.browser || []));
  return data.distribution || [];
}

function rankingRenderer(data) {
  const top = data.ranking || [];
  const total = top.reduce((sum, row) => sum + number(row.total), 0);
  setKpi("kpi-total", total.toLocaleString());
  setKpi("kpi-views", number(top[0]?.views).toLocaleString());
  setKpi("kpi-clicks", number(top[0]?.clicks).toLocaleString());
  setKpi("kpi-applies", "--");
  setKpi("kpi-sessions", "--");
  setKpi("kpi-ctr", "--");
  setKpi("kpi-apply-rate", "--");
  setKpi("kpi-mobile-rate", "--");

  renderChart("trend-chart", barConfig(top.slice(0, 10), "total", "name", "Total"));
  renderChart("distribution-chart", barConfig(top.slice(0, 10), "views", "name", "Views"));
  renderChart("ranking-chart", barConfig(top.slice(0, 10), "clicks", "name", "Clicks"));
  return top;
}

function navigationRenderer(data) {
  const ranking = data.ranking || [];
  const entry = data.entry || [];
  setKpi("kpi-total", ranking.length.toLocaleString());
  setKpi("kpi-views", number(ranking[0]?.count).toLocaleString());
  setKpi("kpi-clicks", entry.length.toLocaleString());
  setKpi("kpi-applies", "--");
  setKpi("kpi-sessions", "--");
  setKpi("kpi-ctr", "--");
  setKpi("kpi-apply-rate", "--");
  setKpi("kpi-mobile-rate", "--");

  renderChart("trend-chart", barConfig(ranking.slice(0, 10), "count", "target", "Flow"));
  renderChart("distribution-chart", doughnutConfig(entry));
  renderChart("ranking-chart", barConfig(entry));
  return ranking;
}

function heatmapRenderer(data) {
  const ranking = data.ranking || [];
  const total = ranking.reduce((sum, row) => sum + number(row.count), 0);
  setKpi("kpi-total", total.toLocaleString());
  setKpi("kpi-views", ranking.length.toLocaleString());
  setKpi("kpi-clicks", number(ranking[0]?.count).toLocaleString());
  setKpi("kpi-applies", "--");
  setKpi("kpi-sessions", "--");
  setKpi("kpi-ctr", "--");
  setKpi("kpi-apply-rate", "--");
  setKpi("kpi-mobile-rate", "--");

  renderChart("trend-chart", barConfig(ranking.slice(0, 10)));
  renderChart("distribution-chart", doughnutConfig(ranking.slice(0, 8)));
  renderChart("ranking-chart", barConfig(ranking.slice(0, 10)));
  return ranking;
}

const renderers = {
  overview: overviewRenderer,
  search: searchRenderer,
  apply: applyRenderer,
  feature: featureRenderer,
  device: deviceRenderer,
  ranking: rankingRenderer,
  navigation: navigationRenderer,
  heatmap: heatmapRenderer,
};

export function renderDashboard(viewMode, outputs) {
  const data = byName(outputs);
  const renderer = renderers[viewMode];
  if (!renderer) {
    resetKpis();
    renderEmptyCharts();
    return [];
  }
  return renderer(data);
}

export function resetDashboard() {
  resetKpis();
  renderEmptyCharts();
}
