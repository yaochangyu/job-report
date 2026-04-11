#!/usr/bin/env python3
"""
click_heatmap_discover.py
──────────────────────────
自動探索頁面上所有可點擊元素，產生 click_heatmap_config.json 的元素對應範本。

用 Playwright 載入每個頁面，掃描 <a>、<button>、[role="button"] 等元素，
匯出 bounding box + 文字內容，供使用者填入 featureId 對應。

執行方式：
    uv run python click_heatmap_discover.py
"""

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

CONFIG_PATH = Path(__file__).parent / "click_heatmap_config.json"
OUTPUT_DIR = Path(__file__).parent / "output" / "click-heatmap"


def _make_fingerprint(el: dict) -> str:
    """產生元素的 fingerprint，供 featureId 配對使用。"""
    return f"{el['tag']}|{el['text'][:30]}|{el['href'][:40]}|{el['id']}"


def discover_page(page, page_config: dict, existing_elements: list[dict]) -> list[dict]:
    """掃描頁面上所有可點擊元素，回傳位置與文字資訊。"""
    url = page_config["url"]
    vp = page_config.get("viewport", {"width": 1440, "height": 900})
    page.set_viewport_size(vp)
    page.goto(url, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2000)

    # 關閉常見彈窗（與 report 腳本保持一致）
    close_selectors = [
        "button:has-text('稍後再說')",
        "button:has-text('關閉')",
        "button:has-text('我知道了')",
        "button:has-text('×')",
        "button:has-text('✕')",
        "[class*='close']",
        "[aria-label='close']",
        "[aria-label='關閉']",
    ]
    for selector in close_selectors:
        try:
            btn = page.locator(selector).first
            if btn.is_visible(timeout=500):
                btn.click()
                page.wait_for_timeout(300)
        except Exception:
            pass

    # 移除蓋板廣告（與 report 腳本保持一致）
    page.evaluate("""() => {
        const vw = window.innerWidth, vh = window.innerHeight;
        const minArea = vw * vh * 0.5;
        for (const el of document.querySelectorAll('*')) {
            const style = window.getComputedStyle(el);
            if (style.position !== 'fixed') continue;
            if (style.display === 'none' || style.visibility === 'hidden') continue;
            const zIndex = parseInt(style.zIndex) || 0;
            if (zIndex < 100) continue;
            const rect = el.getBoundingClientRect();
            if (rect.width * rect.height >= minArea) {
                const closeBtn = el.querySelector(
                    'button, [role="button"], [class*="close"], [aria-label="close"]'
                );
                if (closeBtn) { closeBtn.click(); } else { el.remove(); }
            }
        }
    }""")
    page.wait_for_timeout(500)

    # 展開 viewport 至整頁高度（與 report 腳本保持一致）
    img_width = vp["width"]
    img_height = page.evaluate("() => document.documentElement.scrollHeight")
    page.set_viewport_size({"width": img_width, "height": img_height})
    page.wait_for_timeout(300)

    # 截圖供參考
    screenshots_dir = OUTPUT_DIR / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    safe_name = page_config["page_path"].strip("/").replace("/", "_") or "home"
    screenshot_path = screenshots_dir / f"{safe_name}.png"
    page.screenshot(path=str(screenshot_path), full_page=False)
    print(f"  截圖：{screenshot_path}")

    # 掃描所有可點擊元素
    elements = page.evaluate("""() => {
        const selectors = 'a, button, [role="button"], input[type="submit"], [onclick]';
        const els = document.querySelectorAll(selectors);
        const results = [];
        els.forEach((el, idx) => {
            const rect = el.getBoundingClientRect();
            if (rect.width < 10 || rect.height < 10) return;
            if (rect.top < 0 || rect.left < 0) return;

            const text = (el.textContent || '').trim().replace(/\\s+/g, ' ').substring(0, 60);
            if (!text && !el.href) return;

            results.push({
                index: idx,
                tag: el.tagName,
                text: text,
                href: el.href ? el.href.substring(0, 120) : '',
                id: el.id || '',
                x: Math.round(rect.left),
                y: Math.round(rect.top + window.scrollY),
                width: Math.round(rect.width),
                height: Math.round(rect.height),
                feature_id: ''
            });
        });
        return results;
    }""")

    # 用 fingerprint 還原舊的 featureId
    old_map = {_make_fingerprint(e): e["feature_id"] for e in existing_elements if e.get("feature_id")}
    restored = 0
    for el in elements:
        fp = _make_fingerprint(el)
        if fp in old_map:
            el["feature_id"] = old_map[fp]
            restored += 1
    print(f"  還原 featureId：{restored}/{len([e for e in existing_elements if e.get('feature_id')])} 個")

    return elements


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            ignore_https_errors=True,
            locale="zh-TW",
        )
        page = context.new_page()

        for page_config in config["pages"]:
            page_name = page_config["page_name"]
            print(f"\n[INFO] 探索頁面：{page_name} ({page_config['url']})")

            elements = discover_page(page, page_config, page_config.get("elements", []))
            page_config["elements"] = elements
            print(f"  找到 {len(elements)} 個可點擊元素")

        browser.close()

    # 寫回 config
    CONFIG_PATH.write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n[OK] 已更新 {CONFIG_PATH}")
    print("請編輯 click_heatmap_config.json，為每個元素填入對應的 feature_id")


if __name__ == "__main__":
    main()
