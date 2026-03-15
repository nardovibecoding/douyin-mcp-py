"""Get Douyin user profile."""

import json
import logging
from browser_manager import get_browser
from utils import extract_feeds_from_dom, sleep_random, safe_close_page

logger = logging.getLogger("douyin.user_profile")

PROFILE_URL = "https://www.douyin.com/user/{user_id}"


async def user_profile(user_id: str) -> dict:
    """Get Douyin user profile info and recent videos."""
    bm = await get_browser()
    page = await bm.new_page()
    try:
        url = PROFILE_URL.format(user_id=user_id)
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await sleep_random(2, 3)

        # Extract profile info from DOM
        profile = await page.evaluate("""() => {
            const info = {};

            // Nickname
            const nameEl = document.querySelector(
                '[data-e2e="user-info"] [class*="name"], ' +
                '[class*="nickname"], ' +
                'h1[class*="name"], ' +
                'span[class*="user-page-nickname"]'
            );
            info.nickname = nameEl ? nameEl.textContent.trim() : '';

            // Description / bio
            const descEl = document.querySelector(
                '[data-e2e="user-info"] [class*="desc"], ' +
                '[class*="signature"], ' +
                '[class*="bio"], ' +
                'span[class*="user-page-signature"]'
            );
            info.desc = descEl ? descEl.textContent.trim() : '';

            // Avatar
            const avatarEl = document.querySelector(
                '[data-e2e="user-info"] img[class*="avatar"], ' +
                '[class*="avatar"] img, ' +
                'img[class*="user-page-avatar"]'
            );
            info.avatar = avatarEl ? (avatarEl.getAttribute('src') || '') : '';

            // Douyin ID
            const idEl = document.querySelector(
                '[class*="douyin-id"], ' +
                '[class*="unique-id"], ' +
                'span:has-text("抖音号")'
            );
            info.douyin_id = idEl ? idEl.textContent.trim().replace(/^抖音号：?/, '') : '';

            // IP location
            const ipEl = document.querySelector(
                '[class*="ip-location"], ' +
                '[class*="location"]'
            );
            info.ip_location = ipEl ? ipEl.textContent.trim() : '';

            // Stats — follower, following, likes counts
            // Douyin user pages have count blocks
            const countEls = document.querySelectorAll(
                '[data-e2e="user-info"] [class*="count"], ' +
                '[class*="follow-info"] [class*="item"], ' +
                '[class*="user-tab"] span'
            );
            const counts = {};
            countEls.forEach(el => {
                const text = el.textContent.trim();
                const parent = el.parentElement;
                const label = parent ? parent.textContent.trim() : '';
                if (label.includes('关注')) counts.following = text;
                else if (label.includes('粉丝')) counts.followers = text;
                else if (label.includes('获赞')) counts.likes = text;
            });

            // Alternative: try specific data attributes
            const followingEl = document.querySelector('[data-e2e="following-count"]');
            const followerEl = document.querySelector('[data-e2e="followers-count"]');
            const likeEl = document.querySelector('[data-e2e="likes-count"]');
            if (followingEl) counts.following = followingEl.textContent.trim();
            if (followerEl) counts.followers = followerEl.textContent.trim();
            if (likeEl) counts.likes = likeEl.textContent.trim();

            info.counts = counts;

            return JSON.stringify(info);
        }""")

        try:
            profile_data = json.loads(profile) if profile else {}
        except json.JSONDecodeError:
            profile_data = {}

        # Get user's recent videos
        feeds = await extract_feeds_from_dom(page)

        return {
            "userBasicInfo": {
                "nickname": profile_data.get("nickname", ""),
                "desc": profile_data.get("desc", ""),
                "avatar": profile_data.get("avatar", ""),
                "douyin_id": profile_data.get("douyin_id", ""),
                "ip_location": profile_data.get("ip_location", ""),
            },
            "counts": profile_data.get("counts", {}),
            "feeds": feeds,
            "feeds_count": len(feeds),
        }
    finally:
        await safe_close_page(page)
