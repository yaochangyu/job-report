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
        kpi: `
          SELECT
            SUM(total) AS total,
            SUM(views) AS views,
            SUM(clicks) AS clicks,
            SUM(applies) AS applies,
            SUM(sessions) AS sessions
          FROM read_parquet([${ds}])
        `,
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
            SUM(general_click)     AS general_click_total,
            SUM(general_view)      AS general_view_total,
            SUM(ai_click)          AS ai_click_total,
            SUM(ai_view)           AS ai_view_total,
            SUM(quick_click)       AS quick_click_total,
            SUM(quick_view)        AS quick_view_total,
            SUM(search_page_click) AS search_page_click_total,
            SUM(search_page_view)  AS search_page_view_total,
            (SUM(general_click) + SUM(ai_click) + SUM(quick_click) + SUM(search_page_click)) AS search_click_total,
            (SUM(general_view)  + SUM(ai_view)  + SUM(quick_view)  + SUM(search_page_view))  AS search_view_total
          FROM read_parquet([${ds}])
        `,
        daily_trend: `SELECT date, general_click, general_view, ai_click, ai_view FROM read_parquet([${ds}]) ORDER BY date`,
        search_page_dist: spd ? `SELECT name, SUM(count) AS count FROM read_parquet([${spd}]) WHERE event_type = 'click' GROUP BY name ORDER BY count DESC` : null,
        feature_detail: fc ? `
          SELECT feature_id, ANY_VALUE(feature_name) AS feature_name, event_type, SUM(count) AS count,
            CASE
              WHEN feature_id IN ${inList(SEARCH_PAGE_IDS)}    THEN '搜尋結果頁'
              WHEN feature_id IN ${inList(SEARCH_GENERAL_IDS)} THEN '一般搜尋'
              WHEN feature_id IN ${inList(SEARCH_AI_IDS)}      THEN 'AI 搜尋'
              WHEN feature_id IN ${inList(QUICK_FILTER_IDS)}   THEN '快速篩選'
              ELSE '其他'
            END AS category
          FROM read_parquet([${fc}])
          GROUP BY feature_id, event_type ORDER BY event_type, count DESC
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
// 4. 應徵路徑 — apply-journey
// ════════════════════════════════════════════════════════════════
function applyJourneyPlan(f) {
  const roles = {
    daily_summary:     "daily_summary.parquet",
    path_ranking:      "path_ranking.parquet",
    step_distribution: "step_distribution.parquet",
    entry_page:        "entry_page.parquet",
  };
  return {
    summary: `應徵路徑（T2）：${f.dateFrom} ~ ${f.dateTo}`,
    registerFiles: f.fetchDates.flatMap(d => dayFiles("apply-journey", d, roles, f.datasetRoot)),
    buildQueries(loaded) {
      const ds  = fileList(loaded.daily_summary || []);
      const pr  = fileList(loaded.path_ranking || []);
      const sd  = fileList(loaded.step_distribution || []);
      const ep  = fileList(loaded.entry_page || []);
      if (!ds && !pr) return {};
      return {
        kpi: ds ? `
          SELECT
            SUM(applies)        AS applies,
            SUM(apply_sessions) AS apply_sessions,
            SUM(total_steps) / NULLIF(SUM(applies), 0) AS avg_steps
          FROM read_parquet([${ds}])
        ` : null,
        path_ranking: pr ? `
          SELECT path, SUM(count) AS count, ANY_VALUE(step_count) AS step_count
          FROM read_parquet([${pr}])
          GROUP BY path ORDER BY count DESC LIMIT 30
        ` : null,
        step_distribution: sd ? `
          SELECT
            CASE WHEN steps >= 5 THEN 5 ELSE steps END AS steps_group,
            SUM(count) AS count
          FROM read_parquet([${sd}])
          GROUP BY steps_group ORDER BY steps_group
        ` : null,
        entry_page: ep ? `
          SELECT name, SUM(count) AS count
          FROM read_parquet([${ep}])
          GROUP BY name ORDER BY count DESC LIMIT 15
        ` : null,
        daily_trend: ds ? `
          SELECT date, applies, apply_sessions,
            total_steps / NULLIF(applies, 0) AS avg_steps
          FROM read_parquet([${ds}]) ORDER BY date
        ` : null,
      };
    },
  };
}

// ════════════════════════════════════════════════════════════════
// 5. 功能互動 — feature-engagement
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
        kpi: `
          SELECT
            SUM(explore_jobs_click) AS explore_jobs_click, SUM(explore_jobs_view) AS explore_jobs_view,
            SUM(explore_corp_click) AS explore_corp_click, SUM(explore_corp_view) AS explore_corp_view,
            SUM(identity_click)     AS identity_click,     SUM(identity_view)     AS identity_view,
            SUM(news_click)         AS news_click,         SUM(news_view)         AS news_view
          FROM read_parquet([${ds}])
        `,
        explore_job_category: ejct ? `SELECT name, SUM(count) AS count FROM read_parquet([${ejct}]) WHERE event_type = 'click' GROUP BY name ORDER BY count DESC` : null,
        explore_corp_feature: ecf  ? `SELECT name, SUM(count) AS count FROM read_parquet([${ecf}]) WHERE event_type = 'click' GROUP BY name ORDER BY count DESC` : null,
        identity_dist:        im   ? `SELECT name, SUM(count) AS count FROM read_parquet([${im}])  WHERE event_type = 'click' GROUP BY name ORDER BY count DESC` : null,
        news_dist:            nf   ? `SELECT name, SUM(count) AS count FROM read_parquet([${nf}])  WHERE event_type = 'click' GROUP BY name ORDER BY count DESC` : null,
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
        kpi:             `
          SELECT
            SUM(mobile) AS mobile_total,
            SUM(desktop) AS desktop_total,
            ${os ? `(SELECT COUNT(DISTINCT name) FROM read_parquet([${os}]))` : "0"} AS os_count,
            ${br ? `(SELECT COUNT(DISTINCT name) FROM read_parquet([${br}]))` : "0"} AS browser_count
          FROM read_parquet([${ds}])
        `,
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
      if (!ds && !ft) return {};
      return {
        kpi: ft ? `
          WITH feature_agg AS (
            SELECT featureId, SUM(total) AS total
            FROM read_parquet([${ft}])
            GROUP BY featureId
          )
          SELECT
            (SELECT COALESCE(SUM(total), 0) FROM feature_agg) AS total,
            (SELECT COUNT(*) FROM feature_agg) AS feature_count,
            (SELECT featureId FROM feature_agg ORDER BY total DESC, featureId LIMIT 1) AS top_feature,
            (SELECT total FROM feature_agg ORDER BY total DESC, featureId LIMIT 1) AS top_count
        ` : `
          SELECT
            SUM(total_events) AS total,
            SUM(total_features) AS feature_count,
            FIRST(top_feature_id ORDER BY total_events DESC) AS top_feature,
            MAX(top_feature_total) AS top_count
          FROM read_parquet([${ds}])
        `,
        ranking: ft ? `
          SELECT featureId AS feature_id, ANY_VALUE(feature_name) AS feature_name, SUM(total) AS total, SUM(views) AS views, SUM(clicks) AS clicks, ANY_VALUE(category) AS category
          FROM read_parquet([${ft}])
          GROUP BY featureId ORDER BY total DESC, feature_id
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
  const pageRelationLimit = f.pagePath ? 500 : 300;
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
        kpi: `
          SELECT
            SUM(nav_click)   AS nav_click,
            SUM(nav_view)    AS nav_view,
            SUM(nav_click)  + SUM(nav_view)   AS nav_total,
            SUM(entry_click) AS entry_click,
            SUM(entry_view)  AS entry_view,
            SUM(entry_click) + SUM(entry_view) AS entry_total,
            ${
              ps && pd
                ? `(SELECT COUNT(DISTINCT page) FROM (
                    SELECT page FROM read_parquet([${ps}]) WHERE event_type = 'view'
                    UNION
                    SELECT page FROM read_parquet([${pd}]) WHERE event_type = 'view'
                  ))`
                : "SUM(tracked_pages)"
            } AS page_count
          FROM read_parquet([${ds}])
        `,
        entry_dist: ep ? `SELECT name, SUM(count) AS count FROM read_parquet([${ep}]) WHERE event_type = 'view' GROUP BY name ORDER BY count DESC LIMIT 15` : null,
        transition_ranking: np ? `
          SELECT "from" AS from_page, "to" AS to_page, SUM(count) AS count
          FROM read_parquet([${np}])
          WHERE event_type = 'view' ${pairWhere ? "AND (" + pairWhere.replace("WHERE ", "") + ")" : ""}
          GROUP BY "from", "to" ORDER BY count DESC LIMIT 30
        ` : null,
        page_sources: ps ? `
          SELECT page AS target, name AS source, SUM(count) AS count
          FROM read_parquet([${ps}])
          WHERE event_type = 'view' ${pageWhere ? "AND (" + pageWhere.replace("WHERE ", "") + ")" : ""}
          GROUP BY page, name ORDER BY count DESC, target, source LIMIT ${pageRelationLimit}
        ` : null,
        page_targets: pd ? `
          SELECT page AS source, name AS target, SUM(count) AS count
          FROM read_parquet([${pd}])
          WHERE event_type = 'view' ${pageWhere ? "AND (" + pageWhere.replace("WHERE ", "") + ")" : ""}
          GROUP BY page, name ORDER BY count DESC, source, target LIMIT ${pageRelationLimit}
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
      if (!ds && !cc) return {};
      return {
        kpi: cc ? `
          WITH click_agg AS (
            SELECT feature_id, SUM(count) AS total_count
            FROM read_parquet([${cc}])
            GROUP BY feature_id
          )
          SELECT
            (SELECT COALESCE(SUM(count), 0) FROM read_parquet([${cc}])) AS total_clicks,
            (SELECT COUNT(*) FROM click_agg) AS feature_count,
            (SELECT feature_id FROM click_agg ORDER BY total_count DESC, feature_id LIMIT 1) AS top_feature,
            (SELECT total_count FROM click_agg ORDER BY total_count DESC, feature_id LIMIT 1) AS top_count
        ` : `
          SELECT
            SUM(total_clicks) AS total_clicks,
            SUM(feature_count) AS feature_count,
            FIRST(top_feature_id ORDER BY total_clicks DESC) AS top_feature,
            MAX(top_count) AS top_count
          FROM read_parquet([${ds}])
        `,
        ranking: cc ? `
          SELECT feature_id, ANY_VALUE(feature_name) AS feature_name, SUM(count) AS count, ANY_VALUE(page_path) AS page_path
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

// ════════════════════════════════════════════════════════════════
// 9. 首頁區塊點擊 — homepage-blocks
// ════════════════════════════════════════════════════════════════
const HB_SEARCH_IDS = [
  "T-job-category", "T-job-location",
  "search-general-keyword", "search-general-submit",
  "search-ai-keyword", "search-ai-voice-input", "search-ai-chat-mode", "search-ai-submit",
];
const HB_IDENTITY_IDS = [
  "identify-personal", "identify-worker", "identify-student",
  "identify-fresh", "identify-senior", "identify-returning",
];
const HB_EXPLORE_JOBS_IDS = [
  "identify-personal-tab-1", "identify-personal-tab-2", "identify-personal-tab-3",
  "identify-worker-tab-1",   "identify-worker-tab-2",   "identify-worker-tab-3",
  "identify-student-tab-1",  "identify-student-tab-2",  "identify-student-tab-3",
  "identify-fresh-tab-1",    "identify-fresh-tab-2",    "identify-fresh-tab-3",
  "identify-senior-tab-1",   "identify-senior-tab-2",   "identify-senior-tab-3",
  "identify-returning-tab-1","identify-returning-tab-2","identify-returning-tab-3",
  "explore-jobs-organic", "explore-jobs-organic-corp",
  "explore-jobs-prev", "explore-jobs-next", "explore-jobs-more",
];
const HB_EXPLORE_CORP_IDS = [
  "explore-company-hospitality", "explore-company-manufacturing",
  "explore-company-healthcare",  "explore-company-tech",
  "explore-company-education",   "explore-company-retail", "explore-company-service",
  "explore-company-corp", "explore-company-job-1", "explore-company-job-2",
  "explore-company-job-more",
  "explore-company-prev", "explore-company-next", "explore-company-more",
];

function homepageBlocksPlan(f) {
  const roles = {
    daily_summary:  "daily_summary.parquet",
    feature_counts: "feature_counts.parquet",
  };
  return {
    summary: `首頁區塊點擊／瀏覽（T2）：${f.dateFrom} ~ ${f.dateTo}`,
    registerFiles: f.fetchDates.flatMap(d => dayFiles("homepage-blocks", d, roles, f.datasetRoot)),
    buildQueries(loaded) {
      const ds = fileList(loaded.daily_summary  || []);
      const fc = fileList(loaded.feature_counts || []);
      if (!fc) return {};
      const searchIn   = inList(HB_SEARCH_IDS);
      const identityIn = inList(HB_IDENTITY_IDS);
      const jobsIn     = inList(HB_EXPLORE_JOBS_IDS);
      const corpIn     = inList(HB_EXPLORE_CORP_IDS);
      return {
        kpi: `
          SELECT
            SUM(CASE WHEN event_type='click' THEN count ELSE 0 END) AS total_clicks,
            SUM(CASE WHEN event_type='view'  THEN count ELSE 0 END) AS total_views,
            SUM(CASE WHEN event_type='click' AND feature_id IN ${searchIn}   THEN count ELSE 0 END) AS search_click,
            SUM(CASE WHEN event_type='view'  AND feature_id IN ${searchIn}   THEN count ELSE 0 END) AS search_view,
            SUM(CASE WHEN event_type='click' AND feature_id IN ${identityIn} THEN count ELSE 0 END) AS identity_click,
            SUM(CASE WHEN event_type='view'  AND feature_id IN ${identityIn} THEN count ELSE 0 END) AS identity_view,
            SUM(CASE WHEN event_type='click' AND feature_id IN ${jobsIn}     THEN count ELSE 0 END) AS explore_jobs_click,
            SUM(CASE WHEN event_type='view'  AND feature_id IN ${jobsIn}     THEN count ELSE 0 END) AS explore_jobs_view,
            SUM(CASE WHEN event_type='click' AND feature_id IN ${corpIn}     THEN count ELSE 0 END) AS explore_corp_click,
            SUM(CASE WHEN event_type='view'  AND feature_id IN ${corpIn}     THEN count ELSE 0 END) AS explore_corp_view
          FROM read_parquet([${fc}])
        `,
        daily_trend: `
          SELECT
            date,
            SUM(CASE WHEN event_type='click' AND feature_id IN ${searchIn}   THEN count ELSE 0 END) AS search_click,
            SUM(CASE WHEN event_type='view'  AND feature_id IN ${searchIn}   THEN count ELSE 0 END) AS search_view,
            SUM(CASE WHEN event_type='click' AND feature_id IN ${identityIn} THEN count ELSE 0 END) AS identity_click,
            SUM(CASE WHEN event_type='view'  AND feature_id IN ${identityIn} THEN count ELSE 0 END) AS identity_view,
            SUM(CASE WHEN event_type='click' AND feature_id IN ${jobsIn}     THEN count ELSE 0 END) AS explore_jobs_click,
            SUM(CASE WHEN event_type='view'  AND feature_id IN ${jobsIn}     THEN count ELSE 0 END) AS explore_jobs_view,
            SUM(CASE WHEN event_type='click' AND feature_id IN ${corpIn}     THEN count ELSE 0 END) AS explore_corp_click,
            SUM(CASE WHEN event_type='view'  AND feature_id IN ${corpIn}     THEN count ELSE 0 END) AS explore_corp_view
          FROM read_parquet([${fc}])
          GROUP BY date ORDER BY date
        `,
        feature_detail: `
          SELECT
            feature_id,
            ANY_VALUE(feature_name) AS feature_name,
            event_type,
            SUM(count) AS count,
            CASE
              WHEN feature_id IN ${searchIn}   THEN '搜尋類別'
              WHEN feature_id IN ${identityIn} THEN '身分類別'
              WHEN feature_id IN ${jobsIn}     THEN '探索工作'
              WHEN feature_id IN ${corpIn}     THEN '探索企業'
              ELSE '其他'
            END AS block
          FROM read_parquet([${fc}])
          GROUP BY feature_id, event_type ORDER BY event_type, count DESC
        `,
      };
    },
  };
}

// ── 路由 ────────────────────────────────────────────────────────
const planBuilders = {
  overview:   overviewPlan,
  search:     searchPlan,
  apply:      applyPlan,
  "apply-journey": applyJourneyPlan,
  feature:    featurePlan,
  device:     devicePlan,
  ranking:    rankingPlan,
  navigation:       navigationPlan,
  heatmap:          heatmapPlan,
  "homepage-blocks": homepageBlocksPlan,
  "monthly-report":  () => ({ registerFiles: [], buildQueries: () => [] }),
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
