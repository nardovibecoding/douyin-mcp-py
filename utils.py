"""Shared helpers for Douyin actions."""

import asyncio
import random
import json
import logging
from patchright.async_api import Page

logger = logging.getLogger("douyin.utils")


async def sleep_random(min_s: float = 0.5, max_s: float = 1.5):
    """Random sleep to appear human."""
    await asyncio.sleep(random.uniform(min_s, max_s))


async def wait_for_navigation(page: Page, url: str, timeout: int = 60000):
    """Navigate to URL and wait for load."""
    await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
    await sleep_random(1.5, 2.5)


async def extract_feeds_from_dom(page: Page) -> list[dict]:
    """Extract video feed cards directly from Douyin DOM elements.

    Works for both search results and homepage/recommend feed.
    Douyin uses various card layouts — this tries multiple selectors.
    """
    result = await page.evaluate("""() => {
        const feeds = [];

        // Strategy 1: Search result video cards
        // Douyin search results typically use <li> items or card-like divs
        const searchCards = document.querySelectorAll(
            '[class*="search-result-card"], ' +
            '[class*="video-card"], ' +
            'ul[class*="list"] > li, ' +
            '[class*="recommend-card"], ' +
            '[class*="player-card"], ' +
            '[class*="feed-card"]'
        );

        searchCards.forEach(card => {
            let video_id = '';
            let title = '';
            let cover_url = '';
            let author_name = '';
            let author_id = '';
            let author_avatar = '';
            let play_count = '';
            let like_count = '';
            let duration = '';
            let url = '';

            // Find link to video
            const links = card.querySelectorAll('a[href*="/video/"]');
            if (links.length > 0) {
                const href = links[0].getAttribute('href') || '';
                const m = href.match(/\\/video\\/(\\d+)/);
                if (m) video_id = m[1];
                url = href.startsWith('http') ? href : 'https://www.douyin.com' + href;
            }

            // Title from various possible elements
            const titleEl = card.querySelector(
                '[class*="title"], ' +
                '[class*="desc"], ' +
                'a[href*="/video/"] span, ' +
                'p[class*="title"], ' +
                'h2, h3'
            );
            if (titleEl) title = titleEl.textContent.trim();

            // If no title found, try the card's own text (excluding author/stats)
            if (!title) {
                const textEls = card.querySelectorAll('span, p, div');
                for (const el of textEls) {
                    const t = el.textContent.trim();
                    if (t.length > 5 && t.length < 200 && !t.match(/^[\\d.]+[万亿]?$/)) {
                        title = t;
                        break;
                    }
                }
            }

            // Cover image
            const imgEl = card.querySelector('img[src*="douyin"], img[src*="bytimg"], img[src*="byteimg"], img');
            if (imgEl) cover_url = imgEl.getAttribute('src') || '';

            // Author
            const authorEl = card.querySelector(
                '[class*="author"] span, ' +
                '[class*="nickname"], ' +
                'a[href*="/user/"] span, ' +
                '[class*="user-name"], ' +
                '[class*="name"]'
            );
            if (authorEl) author_name = authorEl.textContent.trim().replace(/^@/, '');

            // Author link
            const authorLink = card.querySelector('a[href*="/user/"]');
            if (authorLink) {
                const authorHref = authorLink.getAttribute('href') || '';
                const am = authorHref.match(/\\/user\\/([^?/]+)/);
                if (am) author_id = am[1];
            }

            // Author avatar
            const avatarEl = card.querySelector(
                '[class*="author"] img, ' +
                '[class*="avatar"] img, ' +
                'a[href*="/user/"] img'
            );
            if (avatarEl) author_avatar = avatarEl.getAttribute('src') || '';

            // Play count / view count
            const playEl = card.querySelector(
                '[class*="play-count"], ' +
                '[class*="view-count"], ' +
                '[class*="play_count"], ' +
                'svg + span'
            );
            if (playEl) play_count = playEl.textContent.trim();

            // Like count
            const likeEl = card.querySelector(
                '[class*="like-count"], ' +
                '[class*="like_count"], ' +
                '[class*="digg"] span'
            );
            if (likeEl) like_count = likeEl.textContent.trim();

            // Duration
            const durationEl = card.querySelector(
                '[class*="duration"], ' +
                '[class*="time-tag"], ' +
                'span[class*="time"]'
            );
            if (durationEl) duration = durationEl.textContent.trim();

            if (video_id || title) {
                feeds.push({
                    video_id, title, description: '', cover_url,
                    play_count, like_count, comment_count: '', share_count: '',
                    duration, author_id, author_name, author_avatar, url,
                });
            }
        });

        // Strategy 2: If no cards found, try generic approach with all video links
        if (feeds.length === 0) {
            const allVideoLinks = document.querySelectorAll('a[href*="/video/"]');
            const seen = new Set();
            allVideoLinks.forEach(link => {
                const href = link.getAttribute('href') || '';
                const m = href.match(/\\/video\\/(\\d+)/);
                if (!m || seen.has(m[1])) return;
                seen.add(m[1]);

                const video_id = m[1];
                const url = href.startsWith('http') ? href : 'https://www.douyin.com' + href;

                // Get text content near the link
                const parent = link.closest('li, div[class*="card"], div[class*="item"]') || link.parentElement;
                let title = '';
                if (parent) {
                    const titleEl = parent.querySelector('[class*="title"], p, span, h2, h3');
                    if (titleEl) title = titleEl.textContent.trim();
                }
                if (!title) title = link.textContent.trim();

                // Cover image
                let cover_url = '';
                if (parent) {
                    const img = parent.querySelector('img');
                    if (img) cover_url = img.getAttribute('src') || '';
                }

                if (video_id) {
                    feeds.push({
                        video_id, title: title.substring(0, 200), description: '',
                        cover_url, play_count: '', like_count: '',
                        comment_count: '', share_count: '', duration: '',
                        author_id: '', author_name: '', author_avatar: '', url,
                    });
                }
            });
        }

        return JSON.stringify(feeds);
    }""")
    try:
        return json.loads(result) if result else []
    except json.JSONDecodeError:
        return []


async def extract_video_detail_from_dom(page: Page, video_id: str) -> dict:
    """Extract video detail directly from Douyin DOM elements."""
    result = await page.evaluate("""(videoId) => {
        const detail = { video_id: videoId };

        // Title — Douyin video pages show title in various places
        const titleEl = document.querySelector(
            '[class*="video-info"] [class*="title"], ' +
            '[class*="video-title"], ' +
            'h1, ' +
            '[data-e2e="video-desc"], ' +
            '[class*="desc"] span, ' +
            '[class*="content"] [class*="title"]'
        );
        detail.title = titleEl ? titleEl.textContent.trim() : '';

        // Description / video text content
        const descEl = document.querySelector(
            '[data-e2e="video-desc"], ' +
            '[class*="video-info-detail"], ' +
            '[class*="desc"], ' +
            '[class*="video-meta"] [class*="text"]'
        );
        detail.description = descEl ? descEl.textContent.trim() : '';

        // If title is empty, use description
        if (!detail.title && detail.description) {
            detail.title = detail.description.substring(0, 100);
        }
        // If still empty, use page title
        if (!detail.title) {
            detail.title = document.title.replace(/ - 抖音$/, '').trim();
        }

        // Author info
        const authorNameEl = document.querySelector(
            '[data-e2e="video-author-title"], ' +
            '[class*="author-name"], ' +
            '[class*="nickname"], ' +
            'a[href*="/user/"] [class*="name"], ' +
            '[class*="info"] [class*="name"]'
        );
        detail.author_name = authorNameEl ? authorNameEl.textContent.trim().replace(/^@/, '') : '';

        const authorLink = document.querySelector('a[href*="/user/"]');
        detail.author_id = '';
        if (authorLink) {
            const m = (authorLink.getAttribute('href') || '').match(/\\/user\\/([^?/]+)/);
            if (m) detail.author_id = m[1];
        }

        const authorAvatar = document.querySelector(
            '[class*="author"] img[class*="avatar"], ' +
            '[class*="avatar"] img, ' +
            'a[href*="/user/"] img'
        );
        detail.author_avatar = authorAvatar ? (authorAvatar.getAttribute('src') || '') : '';

        // Follower count
        const followerEl = document.querySelector(
            '[class*="follower"] [class*="count"], ' +
            '[class*="fans-count"]'
        );
        detail.author_follower_count = followerEl ? followerEl.textContent.trim() : '';

        // Interaction counts — Douyin uses data-e2e attributes
        const likeEl = document.querySelector(
            '[data-e2e="video-player-digg-count"], ' +
            '[class*="like-count"], ' +
            '[data-e2e="digg-count"]'
        );
        detail.like_count = likeEl ? likeEl.textContent.trim() : '0';

        const commentEl = document.querySelector(
            '[data-e2e="video-player-comment-count"], ' +
            '[class*="comment-count"], ' +
            '[data-e2e="comment-count"]'
        );
        detail.comment_count = commentEl ? commentEl.textContent.trim() : '0';

        const shareEl = document.querySelector(
            '[data-e2e="video-player-share-count"], ' +
            '[class*="share-count"], ' +
            '[data-e2e="share-count"]'
        );
        detail.share_count = shareEl ? shareEl.textContent.trim() : '0';

        const collectEl = document.querySelector(
            '[data-e2e="video-player-collect-count"], ' +
            '[class*="collect-count"], ' +
            '[data-e2e="collect-count"]'
        );
        detail.collect_count = collectEl ? collectEl.textContent.trim() : '0';

        // Play count
        const playEl = document.querySelector(
            '[class*="play-count"], ' +
            '[class*="view-count"]'
        );
        detail.play_count = playEl ? playEl.textContent.trim() : '';

        // Cover image
        const posterEl = document.querySelector(
            'video[poster], ' +
            '[class*="poster"] img, ' +
            'xg-poster img'
        );
        if (posterEl) {
            detail.cover_url = posterEl.getAttribute('poster') || posterEl.getAttribute('src') || '';
        } else {
            detail.cover_url = '';
        }

        // Tags / hashtags
        detail.tags = [];
        document.querySelectorAll(
            '[class*="hashtag"], ' +
            'a[href*="/hashtag/"], ' +
            '[data-e2e="desc-hashtag"]'
        ).forEach(tag => {
            const text = tag.textContent.trim().replace(/^#/, '');
            if (text) detail.tags.push(text);
        });

        // Publish time
        const timeEl = document.querySelector(
            '[class*="publish-time"], ' +
            '[class*="create-time"], ' +
            '[class*="time"]'
        );
        detail.publish_time = timeEl ? timeEl.textContent.trim() : '';

        // Video URL (if available in DOM)
        const videoEl = document.querySelector('video source, video');
        detail.video_url = '';
        if (videoEl) {
            detail.video_url = videoEl.getAttribute('src') || '';
            if (!detail.video_url) {
                const sourceEl = videoEl.querySelector('source');
                if (sourceEl) detail.video_url = sourceEl.getAttribute('src') || '';
            }
        }

        // Duration
        const durationEl = document.querySelector(
            '[class*="duration"], ' +
            'xg-controls [class*="time"]'
        );
        detail.duration = durationEl ? durationEl.textContent.trim() : '';

        return JSON.stringify(detail);
    }""", video_id)
    try:
        return json.loads(result) if result else {}
    except json.JSONDecodeError:
        return {}


async def safe_close_page(page: Page):
    """Close page, ignoring errors."""
    try:
        await page.close()
    except Exception:
        pass
