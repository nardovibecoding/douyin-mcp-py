"""Get Douyin video detail."""

import json
import logging
from patchright.async_api import Page

from browser_manager import get_browser
from utils import extract_video_detail_from_dom, sleep_random, safe_close_page

logger = logging.getLogger("douyin.feed_detail")

DETAIL_URL = "https://www.douyin.com/video/{video_id}"


async def _load_comments(page: Page, load_comments: bool, limit: int) -> list[dict]:
    """Load comments from the video detail page."""
    comments = []
    if not load_comments:
        return comments

    try:
        # Wait for comments section
        await page.wait_for_selector(
            '[class*="comment"], '
            '[data-e2e="comment-list"]',
            timeout=5000,
        )
    except Exception:
        logger.debug("No comments container found")
        return comments

    last_count = 0
    stagnant = 0
    max_attempts = 20

    for attempt in range(max_attempts):
        # Extract current comments
        raw = await page.evaluate("""() => {
            const comments = [];
            const commentEls = document.querySelectorAll(
                '[class*="comment-item"], ' +
                '[class*="comment-list"] > div, ' +
                '[data-e2e="comment-list-item"]'
            );
            commentEls.forEach(el => {
                const userEl = el.querySelector(
                    '[class*="user-name"], ' +
                    '[class*="nickname"], ' +
                    'a[href*="/user/"] span'
                );
                const contentEl = el.querySelector(
                    '[class*="comment-content"], ' +
                    '[class*="content"] span, ' +
                    '[data-e2e="comment-text"]'
                );
                const likeEl = el.querySelector(
                    '[class*="like-count"], ' +
                    '[class*="digg-count"]'
                );

                if (contentEl) {
                    const subComments = [];
                    el.querySelectorAll(
                        '[class*="reply-item"], ' +
                        '[class*="sub-comment"]'
                    ).forEach(sub => {
                        const subUser = sub.querySelector(
                            '[class*="user-name"], ' +
                            '[class*="nickname"]'
                        );
                        const subContent = sub.querySelector(
                            '[class*="comment-content"], ' +
                            '[class*="content"] span'
                        );
                        const subLike = sub.querySelector(
                            '[class*="like-count"]'
                        );
                        if (subContent) {
                            subComments.push({
                                user: subUser ? subUser.textContent.trim() : '',
                                content: subContent.textContent.trim(),
                                likes: subLike ? subLike.textContent.trim() : '0',
                            });
                        }
                    });

                    comments.push({
                        user: userEl ? userEl.textContent.trim() : '',
                        content: contentEl.textContent.trim(),
                        likes: likeEl ? likeEl.textContent.trim() : '0',
                        replies: subComments,
                    });
                }
            });
            return JSON.stringify(comments);
        }""")

        try:
            current = json.loads(raw) if raw else []
        except json.JSONDecodeError:
            current = []

        if len(current) >= limit:
            comments = current[:limit]
            break

        if len(current) == last_count:
            stagnant += 1
            if stagnant >= 5:
                break
        else:
            stagnant = 0
        last_count = len(current)

        # Scroll down to load more comments
        await page.evaluate("window.scrollBy(0, 400)")
        await sleep_random(0.5, 1.0)

        comments = current

    return comments[:limit]


async def get_feed_detail(video_id: str, load_comments: bool = False,
                          comment_limit: int = 20) -> dict:
    """Get video detail with optional comments. Returns full video data."""
    bm = await get_browser()
    page = await bm.new_page()
    try:
        url = DETAIL_URL.format(video_id=video_id)
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await sleep_random(2, 3)

        # Extract detail from DOM
        detail = await extract_video_detail_from_dom(page, video_id)

        if not detail:
            detail = {"video_id": video_id, "error": "Failed to extract video detail"}

        # Load comments if requested
        if load_comments:
            comments = await _load_comments(page, True, comment_limit)
            detail["comments"] = comments
            detail["comment_loaded_count"] = len(comments)
        else:
            detail["comments"] = []
            detail["comment_loaded_count"] = 0

        return detail
    finally:
        await safe_close_page(page)
