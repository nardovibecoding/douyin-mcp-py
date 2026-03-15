"""List homepage/recommend feeds from Douyin."""

import logging
from browser_manager import get_browser
from utils import extract_feeds_from_dom, wait_for_navigation, sleep_random, safe_close_page

logger = logging.getLogger("douyin.feeds")

DOUYIN_HOME = "https://www.douyin.com/"


async def list_feeds() -> dict:
    """Get homepage recommend feed list. Returns {feeds, count}."""
    bm = await get_browser()
    page = await bm.new_page()
    try:
        await wait_for_navigation(page, DOUYIN_HOME)

        # Wait for feed content to render
        try:
            await page.wait_for_selector(
                'a[href*="/video/"], '
                '[class*="feed"], '
                '[class*="recommend"], '
                '[class*="video-card"]',
                timeout=15000,
            )
        except Exception:
            logger.debug("No feed container found, will try extraction anyway")

        # Scroll a bit to trigger lazy loading
        await page.evaluate("window.scrollBy(0, 600)")
        await sleep_random(1.5, 2.5)

        feeds = await extract_feeds_from_dom(page)
        logger.info(f"Homepage extracted {len(feeds)} feeds via DOM")
        return {"feeds": feeds, "count": len(feeds)}
    finally:
        await safe_close_page(page)
