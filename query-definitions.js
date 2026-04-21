// ── feature id 常數 ────────────────────────────────────────────
const SEARCH_GENERAL_IDS = ["search-general-keyword", "search-general-submit", "search-general"];
const SEARCH_AI_IDS = [
  "search-ai-keyword", "search-ai-submit", "search-ai",
  "search-ai-voice-input", "search-ai-chat-mode",
];
const SEARCH_PAGE_IDS = ["search-job-page", "search-corp-page", "search-gig-page", "search-intern-page"];
const QUICK_FILTER_IDS = ["T-job-location", "T-job-category"];

// ── 輔助 ────────────────────────────────────────────────────────
function quote(value) { return `'${String(value).replaceAll("'", "''")}'`; }
function inList(values) { return `(${values.map(quote).join(", ")})`; }
function fileList(aliases) { return aliases.map(a => `'${a}'`).join(", "); }

// ── 多日 registerFiles 建構輔助 ───────────────────────────────
function dayFiles(reportName, date, roleMap, datasetRoot) {
  const base = `${datasetRoot}report/${reportName}/date=${date}/`;
  return Object.entries(roleMap).map(([role, filename]) => ({
    alias: `__${reportName.replace(/-/g, "_")}_${role}_${date.replaceAll("-", "")}.parquet`,
    url: `${base}${filename}`,
    date,
    role,
  }));
}

// ════════════════════════════════════════════════════════════════
// 1. 整體概覽 — traffic-overview
// ════════════════════════════════════════════════════════════════
function overviewPlan(f) {
  const roles = {
    daily_summary: "daily_summary.parquet",
    device_type:   "device_type.parquet",
    os:            "os.parquet",
    browser:       "browser.parquet",
  };
  return {
    summary: `整體概覽（T2）：${f.dateFrom} ~ ${f.dateTo}`,
    registerFiles: f.fetchDates.flatMap(d => dayFiles("traffic-overview", d, roles, f.datasetRoot)),
    buildQueries(loaded) {
      const ds = fileList(loaded.daily_summary || []);
      const dv = fileList(loaded.device_type || []);
      const os = fileList(loaded.os || []);
      const br = fileList(loaded.browser || []);
      if (!ds) return {};
      return {
        kpi:         `SELECT SUM(views) AS views, SUM(clicks) AS clicks, SUM(applies) AS applies, SUM(sessions) AS sessions FROM read_parquet([${ds}])`,
        daily_trend: `SELECT date, views, clicks, applies, sessions FROM read_parquet([${ds}]) ORDER BY date`,
        device_dist: dv ? `SELECT name, SUM(count) AS count FROM read_parquet([${dv}]) GROUP BY name ORDER BY count DESC` : null,
        os_dist:     os ? `SELECT name, SUM(count) AS count FROM read_parquet([${os}]) GROUP BY name ORDER BY count DESC LIMIT 16` : null,
        browser_top: br ? `SELECT name, SUM(count) AS count FROM read_parquet([${br}]) GROUP BY name ORDER BY count DESC LIMIT 10` : null,
      };
    },
  };
}

// ════════════════════════════════════════════════════════════════
// 2. 搜尋行為 — search-behavior
// ════════════════════════════════════════════════════════════════
function searchPlan(f) {
  const roles = {
    daily_summary:    "daily_summary.parquet",
    feature_counts:   "feature_counts.parquet",
    search_page_dist: "search_page_dist.parquet",
  };
  return {
    summary: `搜尋行為（T2）：${f.dateFrom} ~ ${f.dateTo}`,
    registerFiles: f.fetchDates.flatMap(d => dayFiles("search-behavior", d, roles, f.datasetRoot)),
    buildQueries(loaded) {
      const ds  = fileList(loaded.daily_summary || []);
      const fc  = fileList(loaded.feature_counts || []);
      const spd = fileList(loaded.search_page_dist || []);
      if (!ds) return {};
      return {
        kpi: `
          SELECT
            SUM(general) AS general_total, SUM(ai) AS ai_total,
            SUM(quick) AS quick_total, SUM(search_page) AS search_page_total,
            (SUM(general) + SUM(ai) + SUM(quick) + SUM(search_page)) AS search_total
          FROM read_parquet([${ds}])
        `,
        daily_trend: `SELECT date, general, ai FROM read_parquet([${ds}]) ORDER BY date`,
        search_page_dist: spd ? `SELECT name, SUM(count) AS count FROM read_parquet([${spd}]) GROUP BY name ORDER BY count DESC` : null,
        feature_detail: fc ? `
          SELECT feature_id, SUM(count) AS count,
            CASE
              WHEN feature_id IN ${inList(SEARCH_PAGE_IDS)}    THEN '搜尋結果頁'
              WHEN feature_id IN ${inList(SEARCH_GENERAL_IDS)} THEN '一般搜尋'
              WHEN feature_id IN ${inList(SEARCH_AI_IDS)}      THEN 'AI 搜尋'
              WHEN feature_id IN ${inList(QUICK_FILTER_IDS)}   THEN '快速篩選'
              ELSE '其他'
            END AS category
          FROM read_parquet([${fc}])
          GROUP BY feature_id ORDER BY count DESC
        ` : null,
      };
    },
  };
}

// ════════════════════════════════════════════════════════════════
// 3. 應徵轉換 — apply-conversion
// ════════════════════════════════════════════════════════════════
function applyPlan(f) {
  const roles = {
    daily_summary: "daily_summary.parquet",
    funnel:        "funnel.parquet",
    device:        "device.parquet",
    os:            "os.parquet",
    source:        "source.parquet",
  };
  return {
    summary: `應徵轉換（T2）：${f.dateFrom} ~ ${f.dateTo}`,
    registerFiles: f.fetchDates.flatMap(d => dayFiles("apply-conversion", d, roles, f.datasetRoot)),
    buildQueries(loaded) {
      const ds  = fileList(loaded.daily_summary || []);
      const fn  = fileList(loaded.funnel || []);
      const dv  = fileList(loaded.device || []);
      const os  = fileList(loaded.os || []);
      const src = fileList(loaded.source || []);
      if (!ds) return {};
      const days = f.fetchDates.length;
      return {
        kpi:          `SELECT SUM(applies) AS applies, SUM(job_views) AS job_views, ${days} AS days FROM read_parquet([${ds}])`,
        daily_trend:  `SELECT date, applies, job_views FROM read_parquet([${ds}]) ORDER BY date`,
        funnel:       fn  ? `SELECT name, SUM(count) AS cnt FROM read_parquet([${fn}]) GROUP BY name` : null,
        device_dist:  dv  ? `SELECT name, SUM(count) AS count FROM read_parquet([${dv}]) GROUP BY name ORDER BY count DESC` : null,
        device_detail:dv  ? `SELECT name AS device, SUM(count) AS count FROM read_parquet([${dv}]) GROUP BY name ORDER BY count DESC` : null,
        os_detail:    os  ? `SELECT name AS os, SUM(count) AS count FROM read_parquet([${os}]) GROUP BY name ORDER BY count DESC` : null,
        source_dist:  src ? `SELECT name, SUM(count) AS count FROM read_parquet([${src}]) GROUP BY name ORDER BY count DESC` : null,
      };
    },
  };
}

// ════════════════════════════════════════════════════════════════
// 4. 功能互動 — feature-engagement
// ════════════════════════════════════════════════════════════════
function featurePlan(f) {
  const roles = {
    daily_summary:              "daily_summary.parquet",
    explore_jobs_features:      "explore_jobs_features.parquet",
    explore_jobs_category_tabs: "explore_jobs_category_tabs.parquet",
    explore_corp_features:      "explore_corp_features.parquet",
    identity_main:              "identity_main.parquet",
    identity_all:               "identity_all.parquet",
    news_features:              "news_features.parquet",
  };
  return {
    summary: `功能互動（T2）：${f.dateFrom} ~ ${f.dateTo}`,
    registerFiles: f.fetchDates.flatMap(d => dayFiles("feature-engagement", d, roles, f.datasetRoot)),
    buildQueries(loaded) {
      const ds   = fileList(loaded.daily_summary || []);
      const ejf  = fileList(loaded.explore_jobs_features || []);
      const ejct = fileList(loaded.explore_jobs_category_tabs || []);
      const ecf  = fileList(loaded.explore_corp_features || []);
      const im   = fileList(loaded.identity_main || []);
      const ia   = fileList(loaded.identity_all || []);
      const nf   = fileList(loaded.news_features || []);
      if (!ds) return {};
      return {
        kpi: `SELECT SUM(explore_jobs) AS explore_jobs, SUM(explore_corp) AS explore_corp, SUM(identity) AS identity_total, SUM(news) AS news_total FROM read_parquet([${ds}])`,
        explore_job_category: ejct ? `SELECT name, SUM(count) AS count FROM read_parquet([${ejct}]) GROUP BY name ORDER BY count DESC` : null,
        explore_corp_feature: ecf  ? `SELECT name, SUM(count) AS count FROM read_parquet([${ecf}]) GROUP BY name ORDER BY count DESC` : null,
        identity_dist:        im   ? `SELECT name, SUM(count) AS count FROM read_parquet([${im}]) GROUP BY name ORDER BY count DESC` : null,
        news_dist:            nf   ? `SELECT name, SUM(count) AS count FROM read_parquet([${nf}]) GROUP BY name ORDER BY count DESC` : null,
      };
    },
  };
}

// ════════════════════════════════════════════════════════════════
// 5. 裝置平台 — device-platform
// ════════════════════════════════════════════════════════════════
function devicePlan(f) {
  const roles = {
    daily_summary:   "daily_summary.parquet",
    os:              "os.parquet",
    browser:         "browser.parquet",
    device_behavior: "device_behavior.parquet",
    os_behavior:     "os_behavior.parquet",
  };
  return {
    summary: `裝置平台（T2）：${f.dateFrom} ~ ${f.dateTo}`,
    registerFiles: f.fetchDates.flatMap(d => dayFiles("device-platform", d, roles, f.datasetRoot)),
    buildQueries(loaded) {
      const ds  = fileList(loaded.daily_summary || []);
      const os  = fileList(loaded.os || []);
      const br  = fileList(loaded.browser || []);
      const dvb = fileList(loaded.device_behavior || []);
      const osb = fileList(loaded.os_behavior || []);
      if (!ds) return {};
      return {
        kpi:             `SELECT SUM(mobile) AS mobile_total, SUM(desktop) AS desktop_total FROM read_parquet([${ds}])`,
        daily_trend:     `SELECT date, mobile, desktop FROM read_parquet([${ds}]) ORDER BY date`,
        os_dist:         os  ? `SELECT name, SUM(count) AS count FROM read_parquet([${os}]) GROUP BY name ORDER BY count DESC LIMIT 15` : null,
        browser_dist:    br  ? `SELECT name, SUM(count) AS count FROM read_parquet([${br}]) GROUP BY name ORDER BY count DESC LIMIT 10` : null,
        device_behavior: dvb ? `SELECT device, SUM(total) AS total, SUM(views) AS views, SUM(clicks) AS clicks, SUM(applies) AS applies FROM read_parquet([${dvb}]) GROUP BY device ORDER BY total DESC` : null,
        os_behavior:     osb ? `SELECT os, SUM(total) AS total, SUM(views) AS views, SUM(clicks) AS clicks, SUM(applies) AS applies FROM read_parquet([${osb}]) GROUP BY os ORDER BY total DESC LIMIT 10` : null,
      };
    },
  };
}

// ════════════════════════════════════════════════════════════════
// 6. 頁面排行 — page-ranking
// ════════════════════════════════════════════════════════════════
function rankingPlan(f) {
  const roles = {
    daily_summary: "daily_summary.parquet",
    features:      "features.parquet",
    categories:    "categories.parquet",
  };
  return {
    summary: `頁面排行（T2）：${f.dateFrom} ~ ${f.dateTo}`,
    registerFiles: f.fetchDates.flatMap(d => dayFiles("page-ranking", d, roles, f.datasetRoot)),
    buildQueries(loaded) {
      const ds  = fileList(loaded.daily_summary || []);
      const ft  = fileList(loaded.features || []);
      const cat = fileList(loaded.categories || []);
      if (!ds) return {};
      return {
        kpi: `
          SELECT SUM(total_events) AS total, SUM(total_features) AS feature_count,
            FIRST(top_feature_id ORDER BY total_events DESC) AS top_feature,
            MAX(top_feature_total) AS top_count
          FROM read_parquet([${ds}])
        `,
        ranking: ft ? `
          SELECT featureId AS feature_id, SUM(total) AS total, SUM(views) AS views, SUM(clicks) AS clicks, ANY_VALUE(category) AS category
          FROM read_parquet([${ft}])
          GROUP BY featureId ORDER BY total DESC LIMIT 30
        ` : null,
        categories: cat ? `SELECT name, SUM(count) AS count FROM read_parquet([${cat}]) GROUP BY name ORDER BY count DESC` : null,
      };
    },
  };
}

// ════════════════════════════════════════════════════════════════
// 7. 頁面導航 — page-navigation
// ════════════════════════════════════════════════════════════════
function navigationPlan(f) {
  const roles = {
    daily_summary:     "daily_summary.parquet",
    nav_pairs:         "nav_pairs.parquet",
    entry_pages:       "entry_pages.parquet",
    page_sources:      "page_sources.parquet",
    page_destinations: "page_destinations.parquet",
  };
  const pageWhere = f.pagePath ? `WHERE page = ${quote(f.pagePath)}` : "";
  const pairWhere = f.pagePath ? `WHERE "from" = ${quote(f.pagePath)} OR "to" = ${quote(f.pagePath)}` : "";
  return {
    summary: `頁面導航（T2）：${f.dateFrom} ~ ${f.dateTo}${f.pagePath ? ` / ${f.pagePath}` : ""}`,
    registerFiles: f.fetchDates.flatMap(d => dayFiles("page-navigation", d, roles, f.datasetRoot)),
    buildQueries(loaded) {
      const ds  = fileList(loaded.daily_summary || []);
      const np  = fileList(loaded.nav_pairs || []);
      const ep  = fileList(loaded.entry_pages || []);
      const ps  = fileList(loaded.page_sources || []);
      const pd  = fileList(loaded.page_destinations || []);
      if (!ds) return {};
      return {
        kpi: `SELECT SUM(nav_total) AS nav_total, SUM(entry_total) AS entry_total, SUM(tracked_pages) AS page_count FROM read_parquet([${ds}])`,
        entry_dist: ep ? `SELECT name, SUM(count) AS count FROM read_parquet([${ep}]) GROUP BY name ORDER BY count DESC LIMIT 15` : null,
        transition_ranking: np ? `
          SELECT "from" AS from_page, "to" AS to_page, SUM(count) AS count
          FROM read_parquet([${np}])
          ${pairWhere}
          GROUP BY "from", "to" ORDER BY count DESC LIMIT 30
        ` : null,
        page_sources: ps ? `
          SELECT page AS target, name AS source, SUM(count) AS count
          FROM read_parquet([${ps}])
          ${pageWhere}
          GROUP BY page, name ORDER BY target, count DESC
        ` : null,
        page_targets: pd ? `
          SELECT page AS source, name AS target, SUM(count) AS count
          FROM read_parquet([${pd}])
          ${pageWhere}
          GROUP BY page, name ORDER BY source, count DESC
        ` : null,
      };
    },
  };
}

// ════════════════════════════════════════════════════════════════
// 8. 點擊熱點 — click-heatmap
// ════════════════════════════════════════════════════════════════
function heatmapPlan(f) {
  const roles = {
    daily_summary: "daily_summary.parquet",
    click_counts:  "click_counts.parquet",
  };
  const pageWhere = f.pagePath ? `WHERE page_path = ${quote(f.pagePath)}` : "";
  return {
    summary: `點擊熱點（T2）：${f.dateFrom} ~ ${f.dateTo}${f.pagePath ? ` / ${f.pagePath}` : ""}`,
    registerFiles: f.fetchDates.flatMap(d => dayFiles("click-heatmap", d, roles, f.datasetRoot)),
    buildQueries(loaded) {
      const ds = fileList(loaded.daily_summary || []);
      const cc = fileList(loaded.click_counts || []);
      if (!ds) return {};
      return {
        kpi: `
          SELECT SUM(total_clicks) AS total_clicks, SUM(feature_count) AS feature_count,
            FIRST(top_feature_id ORDER BY total_clicks DESC) AS top_feature,
            MAX(top_count) AS top_count
          FROM read_parquet([${ds}])
        `,
        ranking: cc ? `
          SELECT feature_id, SUM(count) AS count, ANY_VALUE(page_path) AS page_path
          FROM read_parquet([${cc}])
          ${pageWhere}
          GROUP BY feature_id ORDER BY count DESC LIMIT 30
        ` : null,
        page_dist: cc ? `
          SELECT page_path AS name, SUM(count) AS count
          FROM read_parquet([${cc}])
          GROUP BY page_path ORDER BY count DESC LIMIT 15
        ` : null,
      };
    },
  };
}

// ── 路由 ────────────────────────────────────────────────────────
const planBuilders = {
  overview:   overviewPlan,
  search:     searchPlan,
  apply:      applyPlan,
  feature:    featurePlan,
  device:     devicePlan,
  ranking:    rankingPlan,
  navigation: navigationPlan,
  heatmap:    heatmapPlan,
};

export function buildQueryPlan(filters) {
  if (!filters.datasetRoot) throw new Error("datasetRoot 未設定，請確認 manifest.json 是否可存取");
  if (!filters.fetchDates?.length) throw new Error("fetchDates 為空，所選日期區間無可用 T2 資料");
  return (planBuilders[filters.viewMode] ?? overviewPlan)(filters);
}

export async function executeViewQueries(conn, filters, registerFile = null) {
  const plan = buildQueryPlan(filters);

  const missingDates = new Set();
  const loadedByRole = {};

  if (plan.registerFiles && registerFile) {
    await Promise.all(
      plan.registerFiles.map(async ({ alias, url, date, role }) => {
        try {
          await registerFile(alias, url);
          if (role) {
            (loadedByRole[role] = loadedByRole[role] || []).push(alias);
          }
        } catch {
          if (date && role === "daily_summary") missingDates.add(date);
        }
      })
    );
  }

  const queries = plan.buildQueries(loadedByRole);
  const outputs = [];
  for (const [name, sql] of Object.entries(queries)) {
    if (!sql) continue;
    try {
      const result = await conn.query(sql);
      outputs.push({ name, sql: sql.trim(), rows: result.toArray() });
    } catch {
      outputs.push({ name, sql: sql.trim(), rows: [] });
    }
  }

  return { summary: plan.summary, outputs, missingDates: [...missingDates].sort() };
}
