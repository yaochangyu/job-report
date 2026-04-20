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
function dateClause(f) { return `date BETWEEN DATE ${quote(f.dateFrom)} AND DATE ${quote(f.dateTo)}`; }
function pagePathClause(f) { return f.pagePath ? `page_path = ${quote(f.pagePath)}` : null; }
function buildWhere(f, extra = []) {
  return [dateClause(f), pagePathClause(f), ...extra].filter(Boolean).join(" AND ");
}

// ════════════════════════════════════════════════════════════════
// 1. 整體概覽 — traffic-overview
// ════════════════════════════════════════════════════════════════
function overviewPlan(f) {
  // T2 path (only when no pagePath filter — T2 is pre-aggregated without pagePath)
  if (f.datasetRoot && !f.pagePath) {
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

  return {
    summary: `整體概覽：${f.dateFrom} ~ ${f.dateTo}`,
    queries: {
      kpi: `
        SELECT
          COUNT(*) AS total,
          COUNT(*) FILTER (WHERE event_type = 'view') AS views,
          COUNT(*) FILTER (WHERE event_type = 'click') AS clicks,
          COUNT(*) FILTER (WHERE action = 'apply') AS applies,
          COUNT(DISTINCT session_id) FILTER (WHERE session_id IS NOT NULL) AS sessions
        FROM events WHERE ${buildWhere(f)}
      `,
      daily_trend: `
        SELECT date,
          COUNT(*) FILTER (WHERE event_type = 'view') AS views,
          COUNT(*) FILTER (WHERE event_type = 'click') AS clicks,
          COUNT(*) FILTER (WHERE action = 'apply') AS applies,
          COUNT(DISTINCT session_id) FILTER (WHERE session_id IS NOT NULL) AS sessions
        FROM events WHERE ${buildWhere(f)}
        GROUP BY 1 ORDER BY 1
      `,
      hourly_dist: `
        SELECT hour,
          ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT date), 1) AS avg_events
        FROM events WHERE ${buildWhere(f)}
        GROUP BY 1 ORDER BY 1
      `,
      device_dist: `
        SELECT COALESCE(device_type, 'unknown') AS name, COUNT(*) AS count
        FROM events WHERE ${buildWhere(f)}
        GROUP BY 1 ORDER BY count DESC
      `,
      os_dist: `
        SELECT COALESCE(os, 'unknown') AS name, COUNT(*) AS count
        FROM events WHERE ${buildWhere(f)}
        GROUP BY 1 ORDER BY count DESC LIMIT 16
      `,
      browser_top: `
        SELECT COALESCE(browser, 'unknown') AS name, COUNT(*) AS count
        FROM events WHERE ${buildWhere(f)} AND browser IS NOT NULL
        GROUP BY 1 ORDER BY count DESC LIMIT 10
      `,
    },
  };
}

// ════════════════════════════════════════════════════════════════
// 2. 搜尋行為 — search-behavior
// ════════════════════════════════════════════════════════════════
function searchPlan(f) {
  if (f.datasetRoot) {
    const base = `${f.datasetRoot}report/search-behavior/range=${f.dateFrom}_${f.dateTo}/`;
    const t = (file) => `'__sr_${file}'`;
    return {
      summary: `搜尋行為（T2）：${f.dateFrom} ~ ${f.dateTo}`,
      registerFiles: [
        { alias: "__sr_summary.parquet",         url: `${base}summary.parquet` },
        { alias: "__sr_feature_counts.parquet",  url: `${base}feature_counts.parquet` },
        { alias: "__sr_daily_trend.parquet",     url: `${base}daily_trend.parquet` },
        { alias: "__sr_search_page_dist.parquet", url: `${base}search_page_dist.parquet` },
      ],
      queries: {
        kpi: `
          SELECT
            (search_page_total + general_total + ai_total + quick_total) AS search_total,
            search_page_total, general_total, ai_total, quick_total
          FROM read_parquet([${t("summary.parquet")}])
        `,
        daily_trend:     `SELECT date, general, ai FROM read_parquet([${t("daily_trend.parquet")}]) ORDER BY date`,
        search_page_dist:`SELECT name, count FROM read_parquet([${t("search_page_dist.parquet")}]) ORDER BY count DESC`,
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

  const allIds = [...SEARCH_GENERAL_IDS, ...SEARCH_AI_IDS, ...SEARCH_PAGE_IDS, ...QUICK_FILTER_IDS];
  return {
    summary: `搜尋行為：${f.dateFrom} ~ ${f.dateTo}`,
    queries: {
      kpi: `
        SELECT
          COUNT(*) AS search_total,
          COUNT(*) FILTER (WHERE feature_id IN ${inList(SEARCH_PAGE_IDS)}) AS search_page_total,
          COUNT(*) FILTER (WHERE feature_id IN ${inList(SEARCH_GENERAL_IDS)}) AS general_total,
          COUNT(*) FILTER (WHERE feature_id IN ${inList(SEARCH_AI_IDS)}) AS ai_total,
          COUNT(*) FILTER (WHERE feature_id IN ${inList(QUICK_FILTER_IDS)}) AS quick_total
        FROM events WHERE ${buildWhere(f, [`feature_id IN ${inList(allIds)}`])}
      `,
      daily_trend: `
        SELECT date,
          COUNT(*) FILTER (WHERE feature_id IN ${inList(SEARCH_GENERAL_IDS)}) AS general,
          COUNT(*) FILTER (WHERE feature_id IN ${inList(SEARCH_AI_IDS)}) AS ai
        FROM events
        WHERE ${buildWhere(f, [`feature_id IN ${inList([...SEARCH_GENERAL_IDS, ...SEARCH_AI_IDS])}`])}
        GROUP BY 1 ORDER BY 1
      `,
      quick_filter_trend: `
        SELECT date,
          COUNT(*) FILTER (WHERE feature_id = 'T-job-location') AS location,
          COUNT(*) FILTER (WHERE feature_id = 'T-job-category') AS category
        FROM events
        WHERE ${buildWhere(f, [`feature_id IN ${inList(QUICK_FILTER_IDS)}`])}
        GROUP BY 1 ORDER BY 1
      `,
      search_page_dist: `
        SELECT COALESCE(feature_id, '(empty)') AS name, COUNT(*) AS count
        FROM events WHERE ${buildWhere(f, [`feature_id IN ${inList(SEARCH_PAGE_IDS)}`])}
        GROUP BY 1 ORDER BY count DESC
      `,
      ai_dist: `
        SELECT COALESCE(feature_id, '(empty)') AS name, COUNT(*) AS count
        FROM events WHERE ${buildWhere(f, [`feature_id IN ${inList(SEARCH_AI_IDS)}`])}
        GROUP BY 1 ORDER BY count DESC
      `,
      feature_detail: `
        SELECT
          COALESCE(feature_id, '(empty)') AS feature_id,
          COUNT(*) AS count,
          CASE
            WHEN feature_id IN ${inList(SEARCH_PAGE_IDS)} THEN '搜尋結果頁'
            WHEN feature_id IN ${inList(SEARCH_GENERAL_IDS)} THEN '一般搜尋'
            WHEN feature_id IN ${inList(SEARCH_AI_IDS)} THEN 'AI 搜尋'
            WHEN feature_id IN ${inList(QUICK_FILTER_IDS)} THEN '快速篩選'
            ELSE '其他'
          END AS category
        FROM events WHERE ${buildWhere(f, [`feature_id IN ${inList(allIds)}`])}
        GROUP BY 1, 3 ORDER BY count DESC
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

  if (f.datasetRoot) {
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
        kpi:         `SELECT applies, job_views, ${days} AS days FROM read_parquet([${t("kpi.parquet")}])`,
        daily_trend: `SELECT date, applies, job_views FROM read_parquet([${t("daily.parquet")}]) ORDER BY date`,
        funnel:      `SELECT name, count AS cnt FROM read_parquet([${t("funnel.parquet")}])`,
        device_dist: `SELECT name, count FROM read_parquet([${t("device.parquet")}]) ORDER BY count DESC`,
        device_detail:`SELECT name AS device, count FROM read_parquet([${t("device.parquet")}]) ORDER BY count DESC`,
        os_detail:   `SELECT name AS os, count FROM read_parquet([${t("os.parquet")}]) ORDER BY count DESC`,
        source_dist: `SELECT name, count FROM read_parquet([${t("source.parquet")}]) ORDER BY count DESC`,
      },
    };
  }

  return {
    summary: `應徵轉換：${f.dateFrom} ~ ${f.dateTo}`,
    queries: {
      kpi: `
        SELECT
          COUNT(*) FILTER (WHERE action = 'apply') AS applies,
          COUNT(*) FILTER (WHERE feature_id = 'job-page') AS job_views,
          COUNT(*) FILTER (WHERE feature_id = 'home-page') AS home_views,
          COUNT(*) FILTER (WHERE feature_id = 'search-job-page') AS search_views,
          ${days} AS days
        FROM events WHERE ${buildWhere(f)}
      `,
      daily_trend: `
        SELECT date,
          COUNT(*) FILTER (WHERE action = 'apply') AS applies,
          COUNT(*) FILTER (WHERE feature_id = 'job-page') AS job_views
        FROM events WHERE ${buildWhere(f)}
        GROUP BY 1 ORDER BY 1
      `,
      funnel: `
        SELECT name, cnt FROM (
          VALUES
            ('首頁瀏覽',       (SELECT COUNT(*) FROM events WHERE ${buildWhere(f)} AND feature_id = 'home-page')),
            ('搜尋結果頁瀏覽', (SELECT COUNT(*) FROM events WHERE ${buildWhere(f)} AND feature_id = 'search-job-page')),
            ('職缺詳情頁瀏覽', (SELECT COUNT(*) FROM events WHERE ${buildWhere(f)} AND feature_id = 'job-page')),
            ('應徵送出',       (SELECT COUNT(*) FROM events WHERE ${buildWhere(f)} AND action = 'apply'))
        ) t(name, cnt)
      `,
      source_dist: `
        SELECT COALESCE(source, 'unknown') AS name, COUNT(*) AS count
        FROM events WHERE ${buildWhere(f, ["action = 'apply'"])}
        GROUP BY 1 ORDER BY count DESC
      `,
      device_dist: `
        SELECT COALESCE(device_type, 'unknown') AS name, COUNT(*) AS count
        FROM events WHERE ${buildWhere(f, ["action = 'apply'"])}
        GROUP BY 1 ORDER BY count DESC
      `,
      hourly: `
        SELECT hour, COUNT(*) AS apply_count
        FROM events WHERE ${buildWhere(f, ["action = 'apply'"])}
        GROUP BY 1 ORDER BY 1
      `,
      device_detail: `
        SELECT COALESCE(device_type, 'unknown') AS device, COUNT(*) AS count
        FROM events WHERE ${buildWhere(f, ["action = 'apply'"])}
        GROUP BY 1 ORDER BY count DESC
      `,
      os_detail: `
        SELECT COALESCE(os, 'unknown') AS os, COUNT(*) AS count
        FROM events WHERE ${buildWhere(f, ["action = 'apply'"])}
        GROUP BY 1 ORDER BY count DESC
      `,
    },
  };
}

// ════════════════════════════════════════════════════════════════
// 4. 功能互動 — feature-engagement
// ════════════════════════════════════════════════════════════════
function featurePlan(f) {
  if (f.datasetRoot) {
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

  const allIds = [...EXPLORE_JOB_IDS, ...EXPLORE_CORP_IDS, ...IDENTITY_IDS, ...NEWS_IDS];
  return {
    summary: `功能互動：${f.dateFrom} ~ ${f.dateTo}`,
    queries: {
      kpi: `
        SELECT
          COUNT(*) FILTER (WHERE feature_id IN ${inList(EXPLORE_JOB_IDS)}) AS explore_jobs,
          COUNT(*) FILTER (WHERE feature_id IN ${inList(EXPLORE_CORP_IDS)}) AS explore_corp,
          COUNT(*) FILTER (WHERE feature_id IN ${inList(IDENTITY_IDS)}) AS identity_total,
          COUNT(*) FILTER (WHERE feature_id IN ${inList(NEWS_IDS)}) AS news_total
        FROM events WHERE ${buildWhere(f, [`feature_id IN ${inList(allIds)}`])}
      `,
      explore_job_daily: `
        SELECT date,
          COUNT(*) FILTER (WHERE feature_id = 'explore-jobs-organic') AS organic,
          COUNT(*) FILTER (WHERE feature_id = 'explore-jobs-organic-corp') AS organic_corp
        FROM events WHERE ${buildWhere(f, [`feature_id IN ${inList(EXPLORE_JOB_IDS)}`])}
        GROUP BY 1 ORDER BY 1
      `,
      explore_job_category: `
        SELECT COALESCE(category_tab, 'unknown') AS name, COUNT(*) AS count
        FROM events WHERE ${buildWhere(f, [`feature_id IN ${inList(EXPLORE_JOB_IDS)}`])}
        GROUP BY 1 ORDER BY count DESC
      `,
      explore_job_identity: `
        SELECT COALESCE(identity_type, 'unknown') AS name, COUNT(*) AS count
        FROM events WHERE ${buildWhere(f, [`feature_id IN ${inList(EXPLORE_JOB_IDS)}`])}
        GROUP BY 1 ORDER BY count DESC
      `,
      explore_corp_feature: `
        SELECT COALESCE(feature_id, '(empty)') AS name, COUNT(*) AS count
        FROM events WHERE ${buildWhere(f, [`feature_id IN ${inList(EXPLORE_CORP_IDS)}`])}
        GROUP BY 1 ORDER BY count DESC
      `,
      explore_corp_industry: `
        SELECT COALESCE(industry_tab, 'unknown') AS name, COUNT(*) AS count
        FROM events WHERE ${buildWhere(f, [`feature_id IN ${inList(EXPLORE_CORP_IDS)}`])}
        GROUP BY 1 ORDER BY count DESC
      `,
      identity_dist: `
        SELECT COALESCE(feature_id, '(empty)') AS name, COUNT(*) AS count
        FROM events WHERE ${buildWhere(f, [`feature_id IN ${inList(IDENTITY_IDS)}`])}
        GROUP BY 1 ORDER BY count DESC
      `,
      news_dist: `
        SELECT COALESCE(feature_id, '(empty)') AS name, COUNT(*) AS count
        FROM events WHERE ${buildWhere(f, [`feature_id IN ${inList(NEWS_IDS)}`])}
        GROUP BY 1 ORDER BY count DESC
      `,
    },
  };
}

// ════════════════════════════════════════════════════════════════
// 5. 裝置平台 — device-platform
// ════════════════════════════════════════════════════════════════
function devicePlan(f) {
  if (f.datasetRoot) {
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

  return {
    summary: `裝置平台：${f.dateFrom} ~ ${f.dateTo}`,
    queries: {
      kpi: `
        SELECT
          COUNT(*) FILTER (WHERE device_type = 'mobile') AS mobile_total,
          COUNT(*) FILTER (WHERE device_type = 'desktop') AS desktop_total,
          COUNT(DISTINCT os) FILTER (WHERE os IS NOT NULL) AS os_count,
          COUNT(DISTINCT browser) FILTER (WHERE browser IS NOT NULL) AS browser_count
        FROM events WHERE ${buildWhere(f)}
      `,
      daily_trend: `
        SELECT date,
          COUNT(*) FILTER (WHERE device_type = 'mobile') AS mobile,
          COUNT(*) FILTER (WHERE device_type = 'desktop') AS desktop
        FROM events WHERE ${buildWhere(f)}
        GROUP BY 1 ORDER BY 1
      `,
      os_dist: `
        SELECT COALESCE(os, 'unknown') AS name, COUNT(*) AS count
        FROM events WHERE ${buildWhere(f)}
        GROUP BY 1 ORDER BY count DESC LIMIT 15
      `,
      browser_dist: `
        SELECT COALESCE(browser, 'unknown') AS name, COUNT(*) AS count
        FROM events WHERE ${buildWhere(f)} AND browser IS NOT NULL
        GROUP BY 1 ORDER BY count DESC LIMIT 10
      `,
      device_behavior: `
        SELECT COALESCE(device_type, 'unknown') AS device,
          COUNT(*) AS total,
          COUNT(*) FILTER (WHERE event_type = 'view') AS views,
          COUNT(*) FILTER (WHERE event_type = 'click') AS clicks,
          COUNT(*) FILTER (WHERE action = 'apply') AS applies
        FROM events WHERE ${buildWhere(f)}
        GROUP BY 1 ORDER BY total DESC
      `,
      os_behavior: `
        SELECT COALESCE(os, 'unknown') AS os,
          COUNT(*) AS total,
          COUNT(*) FILTER (WHERE event_type = 'view') AS views,
          COUNT(*) FILTER (WHERE event_type = 'click') AS clicks,
          COUNT(*) FILTER (WHERE action = 'apply') AS applies
        FROM events WHERE ${buildWhere(f)}
        GROUP BY 1 ORDER BY total DESC LIMIT 10
      `,
    },
  };
}

// ════════════════════════════════════════════════════════════════
// 6. 頁面排行 — page-ranking
// ════════════════════════════════════════════════════════════════
function rankingPlan(f) {
  // T2 only when no pagePath — T2 aggregates across all pages
  if (f.datasetRoot && !f.pagePath) {
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

  return {
    summary: `頁面排行：${f.dateFrom} ~ ${f.dateTo}`,
    queries: {
      kpi: `
        SELECT
          COUNT(*) AS total,
          COUNT(DISTINCT feature_id) FILTER (WHERE feature_id IS NOT NULL) AS feature_count,
          FIRST(feature_id ORDER BY cnt DESC) AS top_feature,
          MAX(cnt) AS top_count
        FROM (
          SELECT feature_id, COUNT(*) AS cnt
          FROM events WHERE ${buildWhere(f)} AND feature_id IS NOT NULL
          GROUP BY feature_id
        ) t
      `,
      ranking: `
        SELECT
          COALESCE(feature_id, '(empty)') AS feature_id,
          COUNT(*) AS total,
          COUNT(*) FILTER (WHERE event_type = 'view') AS views,
          COUNT(*) FILTER (WHERE event_type = 'click') AS clicks,
          CASE
            WHEN feature_id IN ${inList(SEARCH_PAGE_IDS)} THEN '搜尋'
            WHEN feature_id IN ${inList([...SEARCH_GENERAL_IDS, ...SEARCH_AI_IDS])} THEN '搜尋'
            WHEN feature_id IN ${inList(QUICK_FILTER_IDS)} THEN '快速篩選'
            WHEN feature_id = 'job-page' THEN '頁面瀏覽'
            WHEN feature_id = 'home-page' THEN '頁面瀏覽'
            WHEN feature_id IN ${inList(EXPLORE_JOB_IDS)} THEN '探索功能'
            WHEN feature_id IN ${inList(EXPLORE_CORP_IDS)} THEN '企業互動'
            WHEN feature_id IN ${inList(IDENTITY_IDS)} THEN '身份辨識'
            WHEN feature_id IN ${inList(NEWS_IDS)} THEN '新聞'
            WHEN feature_id LIKE '%apply%' OR feature_id = 'action-apply' THEN '應徵'
            ELSE '其他'
          END AS category
        FROM events WHERE ${buildWhere(f)}
        GROUP BY 1, 5 ORDER BY total DESC LIMIT 30
      `,
    },
  };
}

// ════════════════════════════════════════════════════════════════
// 7. 頁面導航 — page-navigation
// ════════════════════════════════════════════════════════════════
function navigationPlan(f) {
  // 有 datasetRoot 時直接讀 T2 預聚合 parquet，跳過 T1 window function
  if (f.datasetRoot) {
    const base = `${f.datasetRoot}report/page-navigation/range=${f.dateFrom}_${f.dateTo}/`;
    const t2 = (file) => `'__nav_${file}'`;
    const pageWhere  = f.pagePath ? `WHERE page = ${quote(f.pagePath)}` : "";
    const pairWhere  = f.pagePath ? `WHERE "from" = ${quote(f.pagePath)} OR "to" = ${quote(f.pagePath)}` : "";
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
          FROM read_parquet([${t2("summary.parquet")}])
        `,
        entry_dist: `
          SELECT name, count FROM read_parquet([${t2("entry_pages.parquet")}])
          ORDER BY count DESC LIMIT 15
        `,
        transition_ranking: `
          SELECT "from" AS from_page, "to" AS to_page, count
          FROM read_parquet([${t2("nav_pairs.parquet")}])
          ${pairWhere}
          ORDER BY count DESC LIMIT 30
        `,
        page_sources: `
          SELECT page AS target, name AS source, count
          FROM read_parquet([${t2("page_sources.parquet")}])
          ${pageWhere}
          ORDER BY target, rank
        `,
        page_targets: `
          SELECT page AS source, name AS target, count
          FROM read_parquet([${t2("page_destinations.parquet")}])
          ${pageWhere}
          ORDER BY source, rank
        `,
      },
    };
  }

  // fallback：無 datasetRoot 時用 T1（temp table 物化避免重複掃描）
  const pageFilter = f.pagePath ? `AND (page_path = ${quote(f.pagePath)} OR previous_page = ${quote(f.pagePath)})` : "";
  return {
    summary: `頁面導航：${f.dateFrom} ~ ${f.dateTo}${f.pagePath ? ` / ${f.pagePath}` : ""}`,
    prepare: `
      CREATE OR REPLACE TEMP TABLE __nav AS
      SELECT page_path,
        LAG(page_path)  OVER (PARTITION BY session_id ORDER BY occurred_at) AS previous_page,
        LEAD(page_path) OVER (PARTITION BY session_id ORDER BY occurred_at) AS next_page
      FROM events
      WHERE ${dateClause(f)} AND event_type = 'view' AND session_id IS NOT NULL AND page_path IS NOT NULL
    `,
    teardown: `DROP TABLE IF EXISTS __nav`,
    queries: {
      kpi: `
        SELECT
          COUNT(*) FILTER (WHERE previous_page IS NOT NULL ${pageFilter}) AS nav_total,
          COUNT(*) FILTER (WHERE previous_page IS NULL) AS entry_total,
          COUNT(DISTINCT page_path) AS page_count
        FROM __nav
      `,
      entry_dist: `
        SELECT page_path AS name, COUNT(*) AS count
        FROM __nav WHERE previous_page IS NULL
        GROUP BY 1 ORDER BY count DESC LIMIT 15
      `,
      transition_ranking: `
        SELECT previous_page AS from_page, page_path AS to_page, COUNT(*) AS count
        FROM __nav WHERE previous_page IS NOT NULL AND previous_page <> page_path ${pageFilter}
        GROUP BY 1, 2 ORDER BY count DESC LIMIT 30
      `,
      page_sources: `
        WITH ranked AS (
          SELECT page_path AS target, previous_page AS source, COUNT(*) AS cnt,
            ROW_NUMBER() OVER (PARTITION BY page_path ORDER BY COUNT(*) DESC) AS rn
          FROM __nav WHERE previous_page IS NOT NULL AND previous_page <> page_path
          GROUP BY 1, 2
        )
        SELECT target, source, cnt AS count FROM ranked WHERE rn <= 5 ORDER BY target, rn
      `,
      page_targets: `
        WITH ranked AS (
          SELECT page_path AS source, next_page AS target, COUNT(*) AS cnt,
            ROW_NUMBER() OVER (PARTITION BY page_path ORDER BY COUNT(*) DESC) AS rn
          FROM __nav WHERE next_page IS NOT NULL AND next_page <> page_path
          GROUP BY 1, 2
        )
        SELECT source, target, cnt AS count FROM ranked WHERE rn <= 5 ORDER BY source, rn
      `,
    },
  };
}

// ════════════════════════════════════════════════════════════════
// 8. 點擊熱點 — click-heatmap
// ════════════════════════════════════════════════════════════════
function heatmapPlan(f) {
  if (f.datasetRoot) {
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

  return {
    summary: `點擊熱點：${f.dateFrom} ~ ${f.dateTo}${f.pagePath ? ` / ${f.pagePath}` : ""}`,
    queries: {
      kpi: `
        SELECT
          COUNT(*) AS total_clicks,
          COUNT(DISTINCT feature_id) FILTER (WHERE feature_id IS NOT NULL) AS feature_count,
          FIRST(feature_id ORDER BY cnt DESC) AS top_feature,
          MAX(cnt) AS top_count
        FROM (
          SELECT feature_id, COUNT(*) AS cnt
          FROM events WHERE ${buildWhere(f, ["event_type = 'click'"])} AND feature_id IS NOT NULL
          GROUP BY feature_id
        ) t
      `,
      ranking: `
        SELECT COALESCE(feature_id, '(empty)') AS feature_id,
          COUNT(*) AS count,
          COALESCE(page_path, '(all)') AS page_path
        FROM events WHERE ${buildWhere(f, ["event_type = 'click'"])}
        GROUP BY 1, 3 ORDER BY count DESC LIMIT 30
      `,
      page_dist: `
        SELECT COALESCE(page_path, 'unknown') AS name, COUNT(*) AS count
        FROM events WHERE ${buildWhere(f, ["event_type = 'click'"])}
        GROUP BY 1 ORDER BY count DESC LIMIT 15
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
  return (planBuilders[filters.viewMode] ?? overviewPlan)(filters);
}

export async function executeViewQueries(conn, filters, registerFile = null) {
  const plan = buildQueryPlan(filters);
  if (plan.registerFiles && registerFile) {
    await Promise.all(
      plan.registerFiles.map(({ alias, url }) => registerFile(alias, url).catch(() => {}))
    );
  }
  if (plan.prepare) await conn.query(plan.prepare);
  const outputs = [];
  try {
    for (const [name, sql] of Object.entries(plan.queries)) {
      const result = await conn.query(sql);
      outputs.push({ name, sql: sql.trim(), rows: result.toArray() });
    }
  } finally {
    if (plan.teardown) await conn.query(plan.teardown);
  }
  return { summary: plan.summary, outputs };
}
