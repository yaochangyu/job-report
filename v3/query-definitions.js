const SEARCH_GENERAL_IDS = ["search-general-keyword", "search-general-submit", "search-general"];
const SEARCH_AI_IDS = [
  "search-ai-keyword",
  "search-ai-submit",
  "search-ai",
  "search-ai-voice-input",
  "search-ai-chat-mode",
];
const SEARCH_PAGE_IDS = ["search-job-page", "search-corp-page", "search-gig-page", "search-intern-page"];
const QUICK_FILTER_IDS = ["T-job-location", "T-job-category"];
const EXPLORE_JOB_IDS = ["explore-jobs-organic", "explore-jobs-organic-corp"];
const EXPLORE_CORP_IDS = [
  "explore-company-corp",
  "explore-company-job1",
  "explore-company-job2",
  "explore-company-job-more",
  "explore-company-manufacturing",
  "explore-company-service",
  "explore-company-next",
];
const IDENTITY_IDS = [
  "identify-returning",
  "identify-student",
  "identify-worker",
  "identify-professional",
  "identify-senior",
  "identify-fresh",
  "identify-personal",
];
const NEWS_IDS = ["news-card-1", "news-card-2", "news-card-3", "news-card-4", "news-workplace", "news-industry"];

function quote(value) {
  return `'${String(value).replaceAll("'", "''")}'`;
}

function inList(values) {
  return `(${values.map(quote).join(", ")})`;
}

function dateClause(filters) {
  return `date BETWEEN DATE ${quote(filters.dateFrom)} AND DATE ${quote(filters.dateTo)}`;
}

function pagePathClause(filters) {
  if (!filters.pagePath) {
    return null;
  }
  return `page_path = ${quote(filters.pagePath)}`;
}

function buildWhere(filters, extraClauses = []) {
  return [dateClause(filters), pagePathClause(filters), ...extraClauses].filter(Boolean).join(" AND ");
}

function overviewPlan(filters) {
  return {
    summary: `概覽查詢：${filters.dateFrom} ~ ${filters.dateTo}`,
    queries: {
      kpi: `
        SELECT
          COUNT(*) AS total,
          COUNT(*) FILTER (WHERE event_type = 'view') AS views,
          COUNT(*) FILTER (WHERE event_type = 'click') AS clicks,
          COUNT(*) FILTER (WHERE action = 'apply') AS applies,
          COUNT(DISTINCT session_id) FILTER (WHERE session_id IS NOT NULL) AS sessions
        FROM events
        WHERE ${buildWhere(filters)}
      `,
      trend: `
        SELECT
          date,
          COUNT(*) AS total,
          COUNT(*) FILTER (WHERE event_type = 'view') AS views,
          COUNT(*) FILTER (WHERE event_type = 'click') AS clicks,
          COUNT(*) FILTER (WHERE action = 'apply') AS applies
        FROM events
        WHERE ${buildWhere(filters)}
        GROUP BY 1
        ORDER BY 1
      `,
      distribution: `
        SELECT COALESCE(device_type, 'unknown') AS name, COUNT(*) AS count
        FROM events
        WHERE ${buildWhere(filters)}
        GROUP BY 1
        ORDER BY count DESC
      `,
      ranking: `
        SELECT COALESCE(feature_id, '(empty)') AS name, COUNT(*) AS count
        FROM events
        WHERE ${buildWhere(filters)}
        GROUP BY 1
        ORDER BY count DESC
        LIMIT 20
      `,
    },
  };
}

function searchPlan(filters) {
  const searchIds = [...SEARCH_GENERAL_IDS, ...SEARCH_AI_IDS, ...SEARCH_PAGE_IDS, ...QUICK_FILTER_IDS];
  return {
    summary: `搜尋行為查詢：${filters.dateFrom} ~ ${filters.dateTo}`,
    queries: {
      kpi: `
        SELECT
          COUNT(*) FILTER (WHERE feature_id IN ${inList(SEARCH_PAGE_IDS)}) AS search_page_total,
          COUNT(*) FILTER (WHERE feature_id IN ${inList(SEARCH_GENERAL_IDS)}) AS general_total,
          COUNT(*) FILTER (WHERE feature_id IN ${inList(SEARCH_AI_IDS)}) AS ai_total,
          COUNT(*) FILTER (WHERE feature_id IN ${inList(QUICK_FILTER_IDS)}) AS quick_total
        FROM events
        WHERE ${buildWhere(filters, [`feature_id IN ${inList(searchIds)}`])}
      `,
      trend: `
        SELECT
          date,
          COUNT(*) FILTER (WHERE feature_id IN ${inList(SEARCH_GENERAL_IDS)}) AS general,
          COUNT(*) FILTER (WHERE feature_id IN ${inList(SEARCH_AI_IDS)}) AS ai
        FROM events
        WHERE ${buildWhere(filters, [`feature_id IN ${inList([...SEARCH_GENERAL_IDS, ...SEARCH_AI_IDS])}`])}
        GROUP BY 1
        ORDER BY 1
      `,
      distribution: `
        SELECT COALESCE(feature_id, '(empty)') AS name, COUNT(*) AS count
        FROM events
        WHERE ${buildWhere(filters, [`feature_id IN ${inList(searchIds)}`])}
        GROUP BY 1
        ORDER BY count DESC
      `,
    },
  };
}

function applyPlan(filters) {
  return {
    summary: `應徵轉換查詢：${filters.dateFrom} ~ ${filters.dateTo}`,
    queries: {
      kpi: `
        SELECT
          COUNT(*) FILTER (WHERE feature_id = 'job-page') AS job_views,
          COUNT(*) FILTER (WHERE action = 'apply') AS applies,
          COUNT(*) FILTER (WHERE feature_id = 'home-page') AS home_page_views,
          COUNT(*) FILTER (WHERE feature_id = 'search-job-page') AS search_page_views
        FROM events
        WHERE ${buildWhere(filters)}
      `,
      trend: `
        SELECT
          date,
          COUNT(*) FILTER (WHERE action = 'apply') AS applies,
          COUNT(*) FILTER (WHERE feature_id = 'job-page') AS job_views
        FROM events
        WHERE ${buildWhere(filters)}
        GROUP BY 1
        ORDER BY 1
      `,
      distribution: `
        SELECT COALESCE(source, 'unknown') AS name, COUNT(*) AS count
        FROM events
        WHERE ${buildWhere(filters, ["action = 'apply'"])}
        GROUP BY 1
        ORDER BY count DESC
      `,
      hourly: `
        SELECT hour, COUNT(*) AS apply_count
        FROM events
        WHERE ${buildWhere(filters, ["action = 'apply'"])}
        GROUP BY 1
        ORDER BY 1
      `,
    },
  };
}

function featurePlan(filters) {
  const featureIds = [...EXPLORE_JOB_IDS, ...EXPLORE_CORP_IDS, ...IDENTITY_IDS, ...NEWS_IDS];
  return {
    summary: `功能互動查詢：${filters.dateFrom} ~ ${filters.dateTo}`,
    queries: {
      kpi: `
        SELECT
          COUNT(*) FILTER (WHERE feature_id IN ${inList(EXPLORE_JOB_IDS)}) AS explore_jobs,
          COUNT(*) FILTER (WHERE feature_id IN ${inList(EXPLORE_CORP_IDS)}) AS explore_corp,
          COUNT(*) FILTER (WHERE feature_id IN ${inList(IDENTITY_IDS)}) AS identity_total,
          COUNT(*) FILTER (WHERE feature_id IN ${inList(NEWS_IDS)}) AS news_total
        FROM events
        WHERE ${buildWhere(filters, [`feature_id IN ${inList(featureIds)}`])}
      `,
      distribution: `
        SELECT COALESCE(feature_id, '(empty)') AS name, COUNT(*) AS count
        FROM events
        WHERE ${buildWhere(filters, [`feature_id IN ${inList(featureIds)}`])}
        GROUP BY 1
        ORDER BY count DESC
      `,
      categories: `
        SELECT COALESCE(category_tab, 'unknown') AS name, COUNT(*) AS count
        FROM events
        WHERE ${buildWhere(filters, [`feature_id IN ${inList([...EXPLORE_JOB_IDS, ...NEWS_IDS])}`])}
        GROUP BY 1
        ORDER BY count DESC
      `,
    },
  };
}

function devicePlan(filters) {
  return {
    summary: `裝置平台查詢：${filters.dateFrom} ~ ${filters.dateTo}`,
    queries: {
      kpi: `
        SELECT
          COUNT(*) FILTER (WHERE device_type = 'mobile') AS mobile_total,
          COUNT(*) FILTER (WHERE device_type = 'desktop') AS desktop_total,
          COUNT(*) FILTER (WHERE os IS NOT NULL) AS os_total,
          COUNT(*) FILTER (WHERE browser IS NOT NULL) AS browser_total
        FROM events
        WHERE ${buildWhere(filters)}
      `,
      trend: `
        SELECT
          date,
          COUNT(*) FILTER (WHERE device_type = 'mobile') AS mobile,
          COUNT(*) FILTER (WHERE device_type = 'desktop') AS desktop
        FROM events
        WHERE ${buildWhere(filters)}
        GROUP BY 1
        ORDER BY 1
      `,
      distribution: `
        SELECT COALESCE(os, 'unknown') AS name, COUNT(*) AS count
        FROM events
        WHERE ${buildWhere(filters)}
        GROUP BY 1
        ORDER BY count DESC
        LIMIT 15
      `,
      browser: `
        SELECT COALESCE(browser, 'unknown') AS name, COUNT(*) AS count
        FROM events
        WHERE ${buildWhere(filters)}
        GROUP BY 1
        ORDER BY count DESC
        LIMIT 15
      `,
    },
  };
}

function rankingPlan(filters) {
  return {
    summary: `頁面排行查詢：${filters.dateFrom} ~ ${filters.dateTo}`,
    queries: {
      ranking: `
        SELECT
          COALESCE(feature_id, '(empty)') AS name,
          COUNT(*) AS total,
          COUNT(*) FILTER (WHERE event_type = 'view') AS views,
          COUNT(*) FILTER (WHERE event_type = 'click') AS clicks
        FROM events
        WHERE ${buildWhere(filters)}
        GROUP BY 1
        ORDER BY total DESC
        LIMIT 30
      `,
    },
  };
}

function navigationChainCtes(filters) {
  const pagePathFilter = filters.pagePath
    ? `AND MAX(CASE WHEN page_path = ${quote(filters.pagePath)} THEN 1 ELSE 0 END) = 1`
    : "";
  return `
    filtered_nav AS (
      SELECT
        session_id,
        occurred_at,
        COALESCE(page_path, '/') AS page_path
      FROM events
      WHERE ${dateClause(filters)}
        AND event_type = 'view'
        AND session_id IS NOT NULL
        AND page_path IS NOT NULL
    ),
    dedup_nav AS (
      SELECT
        session_id,
        occurred_at,
        page_path,
        LAG(page_path) OVER (
          PARTITION BY session_id
          ORDER BY occurred_at, page_path
        ) AS previous_page
      FROM filtered_nav
    ),
    chain_steps AS (
      SELECT
        session_id,
        occurred_at,
        page_path,
        ROW_NUMBER() OVER (
          PARTITION BY session_id
          ORDER BY occurred_at, page_path
        ) AS seq
      FROM dedup_nav
      WHERE previous_page IS NULL OR previous_page <> page_path
    ),
    session_chains AS (
      SELECT
        session_id,
        MIN(occurred_at) AS started_at,
        MAX(occurred_at) AS ended_at,
        COUNT(*) AS steps,
        MIN(page_path) FILTER (WHERE seq = 1) AS entry_page,
        string_agg(page_path, ' -> ' ORDER BY seq) AS chain
      FROM chain_steps
      GROUP BY session_id
      HAVING COUNT(*) >= 2
      ${pagePathFilter}
    )
  `;
}

function navigationPlan(filters) {
  return {
    summary: `頁面導航鏈路查詢：${filters.dateFrom} ~ ${filters.dateTo}${filters.pagePath ? ` / 包含 ${filters.pagePath}` : ""}`,
    queries: {
      kpi: `
        WITH ${navigationChainCtes(filters)}
        SELECT
          COUNT(*) AS sessions,
          COUNT(DISTINCT chain) AS unique_chains,
          COALESCE(ROUND(AVG(steps), 2), 0) AS avg_steps,
          COALESCE(MAX(steps), 0) AS max_steps
        FROM session_chains
      `,
      ranking: `
        WITH ${navigationChainCtes(filters)}
        SELECT
          chain AS name,
          COUNT(*) AS count,
          MAX(steps) AS steps
        FROM session_chains
        GROUP BY 1
        ORDER BY count DESC
        LIMIT 30
      `,
      steps: `
        WITH ${navigationChainCtes(filters)}
        SELECT
          CAST(steps AS VARCHAR) AS name,
          COUNT(*) AS count
        FROM session_chains
        GROUP BY 1
        ORDER BY CAST(name AS INTEGER)
      `,
      entry: `
        WITH ${navigationChainCtes(filters)}
        SELECT
          entry_page AS name,
          COUNT(*) AS count
        FROM session_chains
        GROUP BY 1
        ORDER BY count DESC
        LIMIT 15
      `,
    },
  };
}

function heatmapPlan(filters) {
  return {
    summary: `點擊熱點查詢：${filters.dateFrom} ~ ${filters.dateTo}${filters.pagePath ? ` / ${filters.pagePath}` : ""}`,
    queries: {
      ranking: `
        SELECT
          COALESCE(feature_id, '(empty)') AS name,
          COUNT(*) AS count
        FROM events
        WHERE ${buildWhere(filters, ["event_type = 'click'"])}
        GROUP BY 1
        ORDER BY count DESC
        LIMIT 30
      `,
    },
  };
}

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
  const builder = planBuilders[filters.viewMode] ?? overviewPlan;
  return builder(filters);
}

export async function executeViewQueries(conn, filters) {
  const plan = buildQueryPlan(filters);
  const outputs = [];

  for (const [name, sql] of Object.entries(plan.queries)) {
    const result = await conn.query(sql);
    outputs.push({
      name,
      sql: sql.trim(),
      rows: result.toArray(),
    });
  }

  return {
    summary: plan.summary,
    outputs,
  };
}
