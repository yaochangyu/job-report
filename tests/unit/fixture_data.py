"""
合成 T1 fixture 資料與對應的預期輸出值。
每份資料都直接從 rows 算出，不依賴 builder 邏輯。
"""

# ── traffic-overview ──────────────────────────────────────────────────────────

TRAFFIC_ROWS = [
    {"event_type": "view",  "action": None,    "session_id": "s1", "device_type": "mobile",  "os": "iOS",     "browser": "Safari"},
    {"event_type": "view",  "action": None,    "session_id": "s2", "device_type": "desktop", "os": "Windows", "browser": "Edge"},
    {"event_type": "view",  "action": None,    "session_id": "s1", "device_type": "mobile",  "os": "iOS",     "browser": "Safari"},
    {"event_type": "click", "action": None,    "session_id": "s1", "device_type": "mobile",  "os": "iOS",     "browser": "Safari"},
    {"event_type": "click", "action": None,    "session_id": "s2", "device_type": "desktop", "os": "Windows", "browser": "Edge"},
    {"event_type": "click", "action": "apply", "session_id": "s2", "device_type": "desktop", "os": "Windows", "browser": "Edge"},
]

EXPECTED_TRAFFIC = {
    "total":   6,
    "views":   3,
    "clicks":  3,
    "applies": 1,
    "sessions": 2,
}

# ── search-behavior ───────────────────────────────────────────────────────────

SEARCH_ROWS = [
    {"feature_id": "search-general-keyword", "event_type": "click"},
    {"feature_id": "search-general-submit",  "event_type": "click"},
    {"feature_id": "search-general",         "event_type": "view"},
    {"feature_id": "search-ai-keyword",      "event_type": "click"},
    {"feature_id": "search-ai-submit",       "event_type": "view"},
    {"feature_id": "T-job-location",         "event_type": "click"},
    {"feature_id": "search-job-page",        "event_type": "view"},
]

EXPECTED_SEARCH = {
    "general_click":     2,
    "general_view":      1,
    "ai_click":          1,
    "ai_view":           1,
    "quick_click":       1,
    "quick_view":        0,
    "search_page_click": 0,
    "search_page_view":  1,
}

# ── apply-conversion ──────────────────────────────────────────────────────────

APPLY_CONVERSION_ROWS = [
    {"system": "jobbank-web", "action": "apply", "feature_id": None,           "event_type": "click", "source": "email",  "device_type": "mobile",  "os": "iOS"},
    {"system": "jobbank-web", "action": "apply", "feature_id": None,           "event_type": "click", "source": "search", "device_type": "desktop", "os": "Windows"},
    {"system": "jobbank-web", "action": None,    "feature_id": "job-page",     "event_type": "view",  "source": None,     "device_type": "mobile",  "os": "iOS"},
    {"system": "jobbank-web", "action": None,    "feature_id": "home-page",    "event_type": "view",  "source": None,     "device_type": "desktop", "os": "Windows"},
    {"system": "jobbank-web", "action": None,    "feature_id": "search-job-page", "event_type": "view","source": None,    "device_type": "mobile",  "os": "Android"},
]

EXPECTED_APPLY_CONVERSION = {
    "applies":   2,
    "job_views": 1,
}

# ── apply-journey ─────────────────────────────────────────────────────────────

APPLY_JOURNEY_ROWS = [
    {"system": "jobbank-web", "session_id": "s1", "occurred_at": "2026-01-01T10:00:00+08:00", "page_path": "/",           "action": None},
    {"system": "jobbank-web", "session_id": "s1", "occurred_at": "2026-01-01T10:01:00+08:00", "page_path": "/search/job", "action": None},
    {"system": "jobbank-web", "session_id": "s1", "occurred_at": "2026-01-01T10:02:00+08:00", "page_path": "/job/123",    "action": "apply"},
    {"system": "jobbank-web", "session_id": "s2", "occurred_at": "2026-01-01T11:00:00+08:00", "page_path": "/",           "action": None},
    {"system": "jobbank-web", "session_id": "s2", "occurred_at": "2026-01-01T11:01:00+08:00", "page_path": "/job/456",    "action": "apply"},
    {"system": "jobbank-web", "session_id": "s3", "occurred_at": "2026-01-01T12:00:00+08:00", "page_path": "/",           "action": None},
]

# s1: home-page > search-job-page > job-page > apply (4 steps)
# s2: home-page > job-page > apply (3 steps)
EXPECTED_APPLY_JOURNEY = {
    "applies":       2,
    "apply_sessions": 2,
    "total_steps":   7,
}

# ── feature-engagement ────────────────────────────────────────────────────────

FEATURE_ENGAGEMENT_ROWS = [
    {"system": "jobbank-web", "event_type": "click", "feature_id": "explore-jobs-organic",      "feature_name": "非廣告職缺"},
    {"system": "jobbank-web", "event_type": "click", "feature_id": "explore-jobs-organic-corp", "feature_name": "非廣告職缺廠商"},
    {"system": "jobbank-web", "event_type": "view",  "feature_id": "explore-jobs-organic",      "feature_name": "非廣告職缺"},
    {"system": "jobbank-web", "event_type": "click", "feature_id": "explore-company-corp",      "feature_name": "廠商"},
    {"system": "jobbank-web", "event_type": "view",  "feature_id": "explore-company-job1",      "feature_name": "廠商職缺1"},
    {"system": "jobbank-web", "event_type": "click", "feature_id": "identify-student",          "feature_name": "學生"},
    {"system": "jobbank-web", "event_type": "view",  "feature_id": "identify-worker",           "feature_name": "上班族"},
    {"system": "jobbank-web", "event_type": "click", "feature_id": "news-card-1",               "feature_name": "新聞1"},
    {"system": "jobbank-web", "event_type": "view",  "feature_id": "news-card-2",               "feature_name": "新聞2"},
    {"system": "jobbank-web", "event_type": "view",  "feature_id": "news-card-3",               "feature_name": "新聞3"},
]

EXPECTED_FEATURE_ENGAGEMENT = {
    "explore_jobs_click": 2,
    "explore_jobs_view":  1,
    "explore_corp_click": 1,
    "explore_corp_view":  1,
    "identity_click":     1,
    "identity_view":      1,
    "news_click":         1,
    "news_view":          2,
}

# ── device-platform ───────────────────────────────────────────────────────────

DEVICE_PLATFORM_ROWS = [
    {"system": "jobbank-web", "device_type": "mobile",  "os": "iOS",     "browser": "Safari", "event_type": "view",  "action": None},
    {"system": "jobbank-web", "device_type": "mobile",  "os": "iOS",     "browser": "Safari", "event_type": "click", "action": None},
    {"system": "jobbank-web", "device_type": "mobile",  "os": "Android", "browser": "Chrome", "event_type": "view",  "action": None},
    {"system": "jobbank-web", "device_type": "desktop", "os": "Windows", "browser": "Chrome", "event_type": "view",  "action": None},
    {"system": "jobbank-web", "device_type": "desktop", "os": "Mac",     "browser": "Safari", "event_type": "click", "action": "apply"},
]

EXPECTED_DEVICE_PLATFORM = {
    "mobile":  3,
    "desktop": 2,
}

# ── page-ranking ──────────────────────────────────────────────────────────────

PAGE_RANKING_ROWS = [
    {"system": "jobbank-web", "feature_id": "home-page",      "feature_name": "首頁", "event_type": "view"},
    {"system": "jobbank-web", "feature_id": "home-page",      "feature_name": "首頁", "event_type": "view"},
    {"system": "jobbank-web", "feature_id": "home-page",      "feature_name": "首頁", "event_type": "click"},
    {"system": "jobbank-web", "feature_id": "job-page",       "feature_name": "職缺", "event_type": "view"},
    {"system": "jobbank-web", "feature_id": "job-page",       "feature_name": "職缺", "event_type": "view"},
    {"system": "jobbank-web", "feature_id": "search-job-page","feature_name": "搜尋", "event_type": "click"},
]

EXPECTED_PAGE_RANKING = {
    "total_events":   6,
    "total_features": 3,
    "top_feature_id": "home-page",
    "features": {
        "home-page":       {"total": 3, "views": 2, "clicks": 1},
        "job-page":        {"total": 2, "views": 2, "clicks": 0},
        "search-job-page": {"total": 1, "views": 0, "clicks": 1},
    },
}

# ── page-navigation ───────────────────────────────────────────────────────────

PAGE_NAVIGATION_ROWS = [
    {"system": "jobbank-web", "event_type": "view",  "page_path": "/",           "previous_page_path": None},
    {"system": "jobbank-web", "event_type": "view",  "page_path": "/search/job", "previous_page_path": "/"},
    {"system": "jobbank-web", "event_type": "view",  "page_path": "/job/123",    "previous_page_path": "/search/job"},
    {"system": "jobbank-web", "event_type": "click", "page_path": "/",           "previous_page_path": None},
    {"system": "jobbank-web", "event_type": "click", "page_path": "/search/job", "previous_page_path": "/"},
]

# nav_pairs (non-entry): view: (/ → /search/job, 1) + (/search/job → /job/123, 1); click: (/ → /search/job, 1)
# entry: view(/,1) click(/,1)
EXPECTED_PAGE_NAVIGATION = {
    "nav_click":    1,
    "nav_view":     2,
    "entry_click":  1,
    "entry_view":   1,
    "tracked_pages": 2,
}

# ── click-heatmap ─────────────────────────────────────────────────────────────

CLICK_HEATMAP_ROWS = [
    {"system": "jobbank-web", "event_type": "click", "page_path": "/",           "feature_id": "search-general-keyword", "feature_name": "關鍵字搜尋"},
    {"system": "jobbank-web", "event_type": "click", "page_path": "/",           "feature_id": "search-general-keyword", "feature_name": "關鍵字搜尋"},
    {"system": "jobbank-web", "event_type": "click", "page_path": "/",           "feature_id": "identify-student",       "feature_name": "學生"},
    {"system": "jobbank-web", "event_type": "click", "page_path": "/search/job", "feature_id": "search-ai-submit",       "feature_name": "AI送出"},
    {"system": "jobbank-web", "event_type": "view",  "page_path": "/",           "feature_id": "home-page",              "feature_name": "首頁"},
]

EXPECTED_CLICK_HEATMAP = {
    "total_clicks":  4,
    "feature_count": 3,
    "top_feature_id": "search-general-keyword",
    "top_count":     2,
}

# ── homepage-blocks ───────────────────────────────────────────────────────────

HOMEPAGE_BLOCKS_ROWS = [
    {"system": "jobbank-web", "event_type": "click", "feature_id": "identify-student",    "feature_name": "學生"},
    {"system": "jobbank-web", "event_type": "click", "feature_id": "identify-student",    "feature_name": "學生"},
    {"system": "jobbank-web", "event_type": "view",  "feature_id": "identify-student",    "feature_name": "學生"},
    {"system": "jobbank-web", "event_type": "click", "feature_id": "explore-jobs-organic","feature_name": "非廣告職缺"},
    {"system": "jobbank-web", "event_type": "view",  "feature_id": "explore-jobs-organic","feature_name": "非廣告職缺"},
    {"system": "jobbank-web", "event_type": "view",  "feature_id": "search-general-keyword","feature_name": "關鍵字搜尋"},
    {"system": "jobbank-web", "event_type": "click", "feature_id": "unknown-feature",     "feature_name": "未知"},
]

EXPECTED_HOMEPAGE_BLOCKS = {
    "total_clicks":  3,
    "total_views":   3,
    "feature_count": 3,
    "top_feature_id": "identify-student",
    "top_count":     2,
}

# ── apply-demographics ────────────────────────────────────────────────────────
# user_id 1: 男, 1990-01-15 → 36歲 → 35-39
# user_id 2: 女, 2000-06-01 → 25歲 → 25-29
# user_id 3: 未知 birth_dt  → 未知年齡
# user_id 4: 無 metadata   → 未知性別, 未知年齡
APPLY_DEMOGRAPHICS_ROWS = [
    {"system": "jobbank-web", "action": "apply", "user_id": "1", "sex_i": 1,    "birth_dt": "1990-01-15"},
    {"system": "jobbank-web", "action": "apply", "user_id": "2", "sex_i": 2,    "birth_dt": "2000-06-01"},
    {"system": "jobbank-web", "action": "apply", "user_id": "3", "sex_i": None, "birth_dt": None},
    {"system": "jobbank-web", "action": "apply", "user_id": "4", "sex_i": None, "birth_dt": None},
]

EXPECTED_APPLY_DEMOGRAPHICS = {
    "total_applies":         4,
    "applies_with_metadata": 2,  # sex_i notna: user 1 & 2
    "gender_counts": {"男": 1, "女": 1, "未知": 2},
}
