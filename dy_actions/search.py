"""Search Douyin feeds by keyword."""

import logging
import urllib.parse

from browser_manager import get_browser
from utils import extract_feeds_from_dom, wait_for_navigation, sleep_random, safe_close_page

logger = logging.getLogger("douyin.search")

SEARCH_URL = "https://www.douyin.com/search/{keyword}?type=video"


async def search_feeds(keyword: str, sort_by: str = "综合排序",
                       publish_time: str = "不限") -> dict:
    """Search Douyin by keyword. Returns {feeds, count}."""
    bm = await get_browser()
    page = await bm.new_page()
    try:
        encoded = urllib.parse.quote(keyword)
        url = SEARCH_URL.format(keyword=encoded)
        await wait_for_navigation(page, url)

        # Wait for search results to render
        try:
            await page.wait_for_selector(
                '[class*="search-result"], '
                '[class*="video-card"], '
                'a[href*="/video/"], '
                '[class*="result-card"], '
                'ul[class*="list"]',
                timeout=15000,
            )
        except Exception:
            logger.debug("No search result container found in DOM, will try extraction anyway")
        await sleep_random(2, 3)

        # Apply sort filter if not default
        if sort_by and sort_by != "综合排序":
            try:
                # Look for sort/filter dropdown
                filter_btns = await page.query_selector_all(
                    '[class*="filter"] [class*="item"], '
                    '[class*="sort"] [class*="item"], '
                    '[class*="tab"] [class*="item"]'
                )
                for btn in filter_btns:
                    text = await btn.text_content()
                    if text and sort_by in text.strip():
                        await btn.click()
                        await sleep_random(1, 2)
                        break
            except Exception as e:
                logger.warning(f"Failed to apply sort filter: {e}")

        # Apply publish time filter if not default
        if publish_time and publish_time != "不限":
            try:
                filter_btns = await page.query_selector_all(
                    '[class*="filter"] [class*="item"], '
                    '[class*="time"] [class*="item"]'
                )
                for btn in filter_btns:
                    text = await btn.text_content()
                    if text and publish_time in text.strip():
                        await btn.click()
                        await sleep_random(1, 2)
                        break
            except Exception as e:
                logger.warning(f"Failed to apply time filter: {e}")

        # Scroll down a bit to trigger lazy loading
        await page.evaluate("window.scrollBy(0, 500)")
        await sleep_random(1, 1.5)

        # Extract feeds from DOM
        feeds = await extract_feeds_from_dom(page)
        logger.info(f"Search '{keyword}' extracted {len(feeds)} feeds via DOM")
        return {"feeds": feeds, "count": len(feeds)}
    finally:
        await safe_close_page(page)
