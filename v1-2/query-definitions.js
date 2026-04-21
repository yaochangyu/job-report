// ── feature id 常數 ────────────────────────────────────────────
const SEARCH_GENERAL_IDS = ["search-general-keyword", "search-general-submit", "search-general"];
const SEARCH_AI_IDS = [
  "search-ai-keyword", "search-ai-submit", "search-ai",
  "search-ai-voice-input", "search-ai-chat-mode",
];
const SEARCH_PAGE_IDS = ["search-job-page", "search-corp-page", "search-gig-page", "search-intern-page"];
const QUICK_FILTER_IDS = ["T-job-location", "T-job-category"];
const EXPLORE_JOB_IDS = ["explore-jobs-organic", "explore-jobs-organic-corp"];
const EXPLORE_CORP_IDS = [
  "explore-company-corp", "explore-company-job1", "explore-company-job2",
  "explore-company-job-more", "explore-company-manufacturing",
  "explore-company-service", "explore-company-next",
];
const IDENTITY_IDS = [
  "identify-returning", "identify-student", "identify-worker",
  "identify-professional", "identify-senior", "identify-fresh", "identify-personal",
];
const NEWS_IDS = ["news-card-1", "news-card-2", "news-card-3", "news-card-4", "news-workplace", "news-industry"];

// ── 輔助 ────────────────────────────────────────────────────────
function quote(value) { return `'${String(value).replaceAll("'", "''")}'`; }
function inList(values) { return `(${values.map(quote).join(", ")})`; }

// ════════════════════════════════════════════════════════════════
// 1. 整體概覽 — traffic-overview
// ════════════════════════════════════════════════════════════════
function overviewPlan(f) {
  const base = `${f.datasetRoot}report/traffic-overview/range=${f.dateFrom}_${f.dateTo}/`;
  const t = (file) => `'__ov_${file}'`;
  return {
    summary: `整體概覽（T2）：${f.dateFrom} ~ ${f.dateTo}`,
    registerFiles: [
      { alias: "__ov_kpi.parquet",        url: `${base}kpi.parquet` },
      { alias: "__ov_daily.parquet",       url: `${base}daily.parquet` },
      { alias: "__ov_device_type.parquet", url: `${base}device_type.parquet` },
      { alias: "__ov_os.parquet",          url: `${base}os.parquet` },
      { alias: "__ov_browser.parquet",     url: `${base}browser.parquet` },
    ],
    queries: {
      kpi:         `SELECT total, views, clicks, applies, sessions FROM read_parquet([${t("kpi.parquet")}])`,
      daily_trend: `SELECT date, views, clicks, applies, sessions FROM read_parquet([${t("daily.parquet")}]) ORDER BY date`,
      device_dist: `SELECT name, count FROM read_parquet([${t("device_type.parquet")}]) ORDER BY count DESC`,
      os_dist:     `SELECT name, count FROM read_parquet([${t("os.parquet")}]) ORDER BY count DESC LIMIT 16`,
      browser_top: `SELECT name, count FROM read_parquet([${t("browser.parquet")}]) ORDER BY count DESC LIMIT 10`,
    },
  };
}

// ════════════════════════════════════════════════════════════════
// 2. 搜尋行為 — search-behavior
// ════════════════════════════════════════════════════════════════
function searchPlan(f) {
  const base = `${f.datasetRoot}report/search-behavior/range=${f.dateFrom}_${f.dateTo}/`;
  const t = (file) => `'__sr_${file}'`;
  return {
    summary: `搜尋行為（T2）：${f.dateFrom} ~ ${f.dateTo}`,
    registerFiles: [
      { alias: "__sr_summary.parquet",          url: `${base}summary.parquet` },
      { alias: "__sr_feature_counts.parquet",   url: `${base}feature_counts.parquet` },
      { alias: "__sr_daily_trend.parquet",      url: `${base}daily_trend.parquet` },
      { alias: "__sr_search_page_dist.parquet", url: `${base}search_page_dist.parquet` },
    ],
    queries: {
      kpi: `
        SELECT
          (search_page_total + general_total + ai_total + quick_total) AS search_total,
          search_page_total, general_total, ai_total, quick_total
        FROM read_parquet([${t("summary.parquet")}])
      `,
      daily_trend:      `SELECT date, general, ai FROM read_parquet([${t("daily_trend.parquet")}]) ORDER BY date`,
      search_page_dist: `SELECT name, count FROM read_parquet([${t("search_page_dist.parquet")}]) ORDER BY count DESC`,
      feature_detail: `
        SELECT feature_id, count,
          CASE
            WHEN feature_id IN ${inList(SEARCH_PAGE_IDS)}    THEN '搜尋結果頁'
            WHEN feature_id IN ${inList(SEARCH_GENERAL_IDS)} THEN '一般搜尋'
            WHEN feature_id IN ${inList(SEARCH_AI_IDS)}      THEN 'AI 搜尋'
            WHEN feature_id IN ${inList(QUICK_FILTER_IDS)}   THEN '快速篩選'
            ELSE '其他'
          END AS category
        FROM read_parquet([${t("feature_counts.parquet")}])
        ORDER BY count DESC
      `,
    },
  };
}

// ════════════════════════════════════════════════════════════════
// 3. 應徵轉換 — apply-conversion
// ════════════════════════════════════════════════════════════════
function applyPlan(f) {
  const days = Math.max(
    1,
    Math.round((new Date(f.dateTo) - new Date(f.dateFrom)) / 86400000) + 1
  );
  const base = `${f.datasetRoot}report/apply-conversion/range=${f.dateFrom}_${f.dateTo}/`;
  const t = (file) => `'__ap_${file}'`;
  return {
    summary: `應徵轉換（T2）：${f.dateFrom} ~ ${f.dateTo}`,
    registerFiles: [
      { alias: "__ap_kpi.parquet",    url: `${base}kpi.parquet` },
      { alias: "__ap_daily.parquet",  url: `${base}daily.parquet` },
      { alias: "__ap_funnel.parquet", url: `${base}funnel.parquet` },
      { alias: "__ap_device.parquet", url: `${base}device.parquet` },
      { alias: "__ap_os.parquet",     url: `${base}os.parquet` },
      { alias: "__ap_source.parquet", url: `${base}source.parquet` },
    ],
    queries: {
      kpi:          `SELECT applies, job_views, ${days} AS days FROM read_parquet([${t("kpi.parquet")}])`,
      daily_trend:  `SELECT date, applies, job_views FROM read_parquet([${t("daily.parquet")}]) ORDER BY date`,
      funnel:       `SELECT name, count AS cnt FROM read_parquet([${t("funnel.parquet")}])`,
      device_dist:  `SELECT name, count FROM read_parquet([${t("device.parquet")}]) ORDER BY count DESC`,
      device_detail:`SELECT name AS device, count FROM read_parquet([${t("device.parquet")}]) ORDER BY count DESC`,
      os_detail:    `SELECT name AS os, count FROM read_parquet([${t("os.parquet")}]) ORDER BY count DESC`,
      source_dist:  `SELECT name, count FROM read_parquet([${t("source.parquet")}]) ORDER BY count DESC`,
    },
  };
}

// ════════════════════════════════════════════════════════════════
// 4. 功能互動 — feature-engagement
// ════════════════════════════════════════════════════════════════
function featurePlan(f) {
  const base = `${f.datasetRoot}report/feature-engagement/range=${f.dateFrom}_${f.dateTo}/`;
  const t = (file) => `'__fe_${file}'`;
  return {
    summary: `功能互動（T2）：${f.dateFrom} ~ ${f.dateTo}`,
    registerFiles: [
      { alias: "__fe_explore_jobs_features.parquet",      url: `${base}explore_jobs_features.parquet` },
      { alias: "__fe_explore_jobs_category_tabs.parquet", url: `${base}explore_jobs_category_tabs.parquet` },
      { alias: "__fe_explore_corp_features.parquet",      url: `${base}explore_corp_features.parquet` },
      { alias: "__fe_identity_main.parquet",              url: `${base}identity_main.parquet` },
      { alias: "__fe_identity_all.parquet",               url: `${base}identity_all.parquet` },
      { alias: "__fe_news_features.parquet",              url: `${base}news_features.parquet` },
    ],
    queries: {
      kpi: `
        SELECT
          (SELECT COALESCE(SUM(count), 0) FROM read_parquet([${t("explore_jobs_features.parquet")}])) AS explore_jobs,
          (SELECT COALESCE(SUM(count), 0) FROM read_parquet([${t("explore_corp_features.parquet")}])) AS explore_corp,
          (SELECT COALESCE(SUM(count), 0) FROM read_parquet([${t("identity_all.parquet")}]))          AS identity_total,
          (SELECT COALESCE(SUM(count), 0) FROM read_parquet([${t("news_features.parquet")}]))         AS news_total
      `,
      explore_job_category: `SELECT name, count FROM read_parquet([${t("explore_jobs_category_tabs.parquet")}]) ORDER BY count DESC`,
      explore_corp_feature: `SELECT name, count FROM read_parquet([${t("explore_corp_features.parquet")}]) ORDER BY count DESC`,
      identity_dist:        `SELECT name, count FROM read_parquet([${t("identity_main.parquet")}]) ORDER BY count DESC`,
      news_dist:            `SELECT name, count FROM read_parquet([${t("news_features.parquet")}]) ORDER BY count DESC`,
    },
  };
}

// ════════════════════════════════════════════════════════════════
// 5. 裝置平台 — device-platform
// ════════════════════════════════════════════════════════════════
function devicePlan(f) {
  const base = `${f.datasetRoot}report/device-platform/range=${f.dateFrom}_${f.dateTo}/`;
  const t = (file) => `'__dv_${file}'`;
  return {
    summary: `裝置平台（T2）：${f.dateFrom} ~ ${f.dateTo}`,
    registerFiles: [
      { alias: "__dv_summary.parquet",        url: `${base}summary.parquet` },
      { alias: "__dv_daily.parquet",           url: `${base}daily.parquet` },
      { alias: "__dv_os.parquet",              url: `${base}os.parquet` },
      { alias: "__dv_browser.parquet",         url: `${base}browser.parquet` },
      { alias: "__dv_device_behavior.parquet", url: `${base}device_behavior.parquet` },
      { alias: "__dv_os_behavior.parquet",     url: `${base}os_behavior.parquet` },
    ],
    queries: {
      kpi:             `SELECT mobile_total, desktop_total, os_count, browser_count FROM read_parquet([${t("summary.parquet")}])`,
      daily_trend:     `SELECT date, mobile, desktop FROM read_parquet([${t("daily.parquet")}]) ORDER BY date`,
      os_dist:         `SELECT name, count FROM read_parquet([${t("os.parquet")}]) ORDER BY count DESC LIMIT 15`,
      browser_dist:    `SELECT name, count FROM read_parquet([${t("browser.parquet")}]) ORDER BY count DESC LIMIT 10`,
      device_behavior: `SELECT device, total, views, clicks, applies FROM read_parquet([${t("device_behavior.parquet")}]) ORDER BY total DESC`,
      os_behavior:     `SELECT os, total, views, clicks, applies FROM read_parquet([${t("os_behavior.parquet")}]) ORDER BY total DESC LIMIT 10`,
    },
  };
}

// ════════════════════════════════════════════════════════════════
// 6. 頁面排行 — page-ranking
// ════════════════════════════════════════════════════════════════
function rankingPlan(f) {
  const base = `${f.datasetRoot}report/page-ranking/range=${f.dateFrom}_${f.dateTo}/`;
  const t = (file) => `'__rk_${file}'`;
  return {
    summary: `頁面排行（T2）：${f.dateFrom} ~ ${f.dateTo}`,
    registerFiles: [
      { alias: "__rk_summary.parquet",  url: `${base}summary.parquet` },
      { alias: "__rk_features.parquet", url: `${base}features.parquet` },
    ],
    queries: {
      kpi: `
        SELECT total_events AS total, total_features AS feature_count,
               top_feature_id AS top_feature, top_feature_total AS top_count
        FROM read_parquet([${t("summary.parquet")}])
      `,
      ranking: `
        SELECT featureId AS feature_id, total, views, clicks, category
        FROM read_parquet([${t("features.parquet")}])
        ORDER BY total DESC LIMIT 30
      `,
    },
  };
}

// ════════════════════════════════════════════════════════════════
// 7. 頁面導航 — page-navigation
// ════════════════════════════════════════════════════════════════
function navigationPlan(f) {
  const base = `${f.datasetRoot}report/page-navigation/range=${f.dateFrom}_${f.dateTo}/`;
  const t = (file) => `'__nav_${file}'`;
  const pageWhere = f.pagePath ? `WHERE page = ${quote(f.pagePath)}` : "";
  const pairWhere = f.pagePath ? `WHERE "from" = ${quote(f.pagePath)} OR "to" = ${quote(f.pagePath)}` : "";
  return {
    summary: `頁面導航（T2）：${f.dateFrom} ~ ${f.dateTo}${f.pagePath ? ` / ${f.pagePath}` : ""}`,
    registerFiles: [
      { alias: "__nav_summary.parquet",          url: `${base}summary.parquet` },
      { alias: "__nav_nav_pairs.parquet",         url: `${base}nav_pairs.parquet` },
      { alias: "__nav_entry_pages.parquet",       url: `${base}entry_pages.parquet` },
      { alias: "__nav_page_sources.parquet",      url: `${base}page_sources.parquet` },
      { alias: "__nav_page_destinations.parquet", url: `${base}page_destinations.parquet` },
    ],
    queries: {
      kpi: `
        SELECT total_nav AS nav_total, entry_total, tracked_pages AS page_count
        FROM read_parquet([${t("summary.parquet")}])
      `,
      entry_dist: `
        SELECT name, count FROM read_parquet([${t("entry_pages.parquet")}])
        ORDER BY count DESC LIMIT 15
      `,
      transition_ranking: `
        SELECT "from" AS from_page, "to" AS to_page, count
        FROM read_parquet([${t("nav_pairs.parquet")}])
        ${pairWhere}
        ORDER BY count DESC LIMIT 30
      `,
      page_sources: `
        SELECT page AS target, name AS source, count
        FROM read_parquet([${t("page_sources.parquet")}])
        ${pageWhere}
        ORDER BY target, rank
      `,
      page_targets: `
        SELECT page AS source, name AS target, count
        FROM read_parquet([${t("page_destinations.parquet")}])
        ${pageWhere}
        ORDER BY source, rank
      `,
    },
  };
}

// ════════════════════════════════════════════════════════════════
// 8. 點擊熱點 — click-heatmap
// ════════════════════════════════════════════════════════════════
function heatmapPlan(f) {
  const base = `${f.datasetRoot}report/click-heatmap/range=${f.dateFrom}_${f.dateTo}/`;
  const t = (file) => `'__hm_${file}'`;
  const pageWhere = f.pagePath ? `WHERE page_path = ${quote(f.pagePath)}` : "";
  const aggWhere  = f.pagePath ? `WHERE page_path = ${quote(f.pagePath)}` : "";
  return {
    summary: `點擊熱點（T2）：${f.dateFrom} ~ ${f.dateTo}${f.pagePath ? ` / ${f.pagePath}` : ""}`,
    registerFiles: [
      { alias: "__hm_click_counts.parquet", url: `${base}click_counts.parquet` },
    ],
    queries: {
      kpi: `
        SELECT
          SUM(feature_total) AS total_clicks,
          COUNT(*) AS feature_count,
          FIRST(feature_id ORDER BY feature_total DESC) AS top_feature,
          MAX(feature_total) AS top_count
        FROM (
          SELECT feature_id, SUM(count) AS feature_total
          FROM read_parquet([${t("click_counts.parquet")}])
          ${aggWhere}
          GROUP BY feature_id
        ) t
      `,
      ranking: `
        SELECT feature_id, count, page_path
        FROM read_parquet([${t("click_counts.parquet")}])
        ${pageWhere}
        ORDER BY count DESC LIMIT 30
      `,
      page_dist: `
        SELECT page_path AS name, SUM(count) AS count
        FROM read_parquet([${t("click_counts.parquet")}])
        GROUP BY page_path ORDER BY count DESC LIMIT 15
      `,
    },
  };
}

// ── 路由 ────────────────────────────────────────────────────────
const planBuilders = {
  overview: overviewPlan,
  search: searchPlan,
  apply: applyPlan,
  feature: featurePlan,
  device: devicePlan,
  ranking: rankingPlan,
  navigation: navigationPlan,
  heatmap: heatmapPlan,
};

export function buildQueryPlan(filters) {
  if (!filters.datasetRoot) throw new Error("datasetRoot 未設定，請確認 manifest.json 是否可存取");
  return (planBuilders[filters.viewMode] ?? overviewPlan)(filters);
}

export async function executeViewQueries(conn, filters, registerFile = null) {
  const plan = buildQueryPlan(filters);
  if (plan.registerFiles && registerFile) {
    await Promise.all(
      plan.registerFiles.map(({ alias, url }) => registerFile(alias, url).catch(() => {}))
    );
  }
  const outputs = [];
  for (const [name, sql] of Object.entries(plan.queries)) {
    const result = await conn.query(sql);
    outputs.push({ name, sql: sql.trim(), rows: result.toArray() });
  }
  return { summary: plan.summary, outputs };
}
