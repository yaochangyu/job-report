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
// KPI: 總事件數、View、Click、Apply、Unique Sessions、Click Rate、Apply Rate
// 圖表: 每日流量趨勢、每小時流量分佈、裝置分佈、OS 分佈
// 表格: OS 詳細數據、瀏覽器 Top10
// ════════════════════════════════════════════════════════════════
function overviewPlan(f) {
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
// KPI: 搜尋相關事件、搜尋結果頁瀏覽、一般搜尋互動、AI 搜尋互動、快速篩選
// 圖表: 搜尋功能使用量總覽(bar)、AI vs 一般趨勢(line)、搜尋結果頁分佈(doughnut)、AI 互動方式(doughnut)、快速篩選趨勢(line)
// 表格: featureId 詳細數據（含類別欄）
// ════════════════════════════════════════════════════════════════
function searchPlan(f) {
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
// KPI: 總應徵數、每日平均應徵、職缺頁瀏覽、應徵轉換率
// 圖表: 每日應徵趨勢(line)、轉換漏斗(bar)、應徵來源分佈(doughnut)、應徵裝置分佈(bar)、應徵時段(bar)
// 表格: 應徵裝置、應徵OS、應徵來源
// ════════════════════════════════════════════════════════════════
function applyPlan(f) {
  const days = Math.max(
    1,
    Math.round((new Date(f.dateTo) - new Date(f.dateFrom)) / 86400000) + 1
  );
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
// KPI: 探索職缺、探索企業、身份辨識、新聞互動
// 圖表: 探索職缺 categoryTab(doughnut)、identityType(doughnut)、每日趨勢(line)
//        探索企業 featureId(bar)、industryTab(bar)
//        身份辨識分佈(bar)、新聞卡片點擊(bar)
// 表格: 身份辨識詳細、新聞互動詳細
// ════════════════════════════════════════════════════════════════
function featurePlan(f) {
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
// KPI: Mobile 事件數、Desktop 事件數、OS 種類、瀏覽器種類
// 圖表: 裝置每日趨勢(line+右軸%)、OS 分佈(doughnut)、瀏覽器(bar-y)、裝置×行為(grouped bar)
// 表格: OS 詳細、瀏覽器詳細、裝置×行為交叉、OS×行為交叉
// ════════════════════════════════════════════════════════════════
function devicePlan(f) {
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
// KPI: 總事件數、功能數量(不重複 featureId)、Top1 功能
// 圖表: Top20 水平 bar、功能類別佔比 doughnut
// 表格: 完整 featureId 排行（#、featureId、總計、View、Click、CTR、類別）
// ════════════════════════════════════════════════════════════════
function rankingPlan(f) {
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
// KPI: 導航轉換事件(top30合計)、初始進入事件、追蹤頁面數
// 圖表: 初始進入頁面分佈(doughnut)、Top20 轉換路徑(bar-y)
// 表格: 各頁面Top來源、各頁面Top目標、完整轉換路徑排行
// ════════════════════════════════════════════════════════════════
function navigationPlan(f) {
  const pageFilter = f.pagePath ? `AND (page_path = ${quote(f.pagePath)} OR previous_page = ${quote(f.pagePath)})` : "";
  return {
    summary: `頁面導航：${f.dateFrom} ~ ${f.dateTo}${f.pagePath ? ` / ${f.pagePath}` : ""}`,
    // 將 window function 物化一次，避免 5 個查詢各自重跑全表排序
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
        FROM __nav WHERE previous_page IS NOT NULL AND previous_page <> page_path
          ${pageFilter}
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
// (v1 用截圖+badge，v3 改用表格+圖表呈現)
// KPI: 總點擊數、不重複功能數、Top1 點擊 featureId
// 圖表: Top20 點擊 bar、分佈 doughnut
// 表格: featureId 點擊排行（含 page_path 過濾）
// ════════════════════════════════════════════════════════════════
function heatmapPlan(f) {
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

export async function executeViewQueries(conn, filters) {
  const plan = buildQueryPlan(filters);
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
