# Copyright (c) 2026 Nardo. AGPL-3.0 — see LICENSE
"""Starlette REST API routes for Douyin MCP server."""

import base64
from starlette.requests import Request
from starlette.responses import JSONResponse

from models import SearchFeedsArgs, FeedDetailArgs, UserProfileArgs
from cookie_manager import delete_cookies as _delete_cookies
from dy_actions.login import check_login_status, get_login_qrcode
from dy_actions.feeds import list_feeds
from dy_actions.search import search_feeds
from dy_actions.feed_detail import get_feed_detail
from dy_actions.user_profile import user_profile
from dy_actions.video_parse import (
    get_download_link, parse_video_info,
    extract_text_from_share_link,
    recognize_audio_from_url, recognize_audio_from_file,
)
from browser_manager import get_browser
from utils import safe_close_page


def _ok(data: dict) -> JSONResponse:
    return JSONResponse({"code": 0, "data": data})


def _err(msg: str, code: int = 500) -> JSONResponse:
    return JSONResponse({"code": code, "message": msg}, status_code=code)


# --- Login ---

async def login_status_handler(request: Request):
    try:
        result = await check_login_status()
        return _ok(result)
    except Exception as e:
        return _err(str(e))


async def login_qrcode_handler(request: Request):
    try:
        result = await get_login_qrcode()
        return _ok(result)
    except Exception as e:
        return _err(str(e))


async def delete_cookies_handler(request: Request):
    try:
        path = _delete_cookies()
        return _ok({"cookie_path": path, "message": "Cookies deleted"})
    except Exception as e:
        return _err(str(e))


# --- Feeds ---

async def list_feeds_handler(request: Request):
    try:
        result = await list_feeds()
        return _ok(result)
    except Exception as e:
        return _err(str(e))


async def search_feeds_handler(request: Request):
    try:
        if request.method == "POST":
            body = await request.json()
        else:
            body = dict(request.query_params)

        keyword = body.get("keyword", "")
        if not keyword:
            return _err("keyword is required", 400)

        sort_by = body.get("sort_by", "综合排序")
        publish_time = body.get("publish_time", "不限")

        result = await search_feeds(keyword, sort_by, publish_time)
        return _ok(result)
    except Exception as e:
        return _err(str(e))


async def feed_detail_handler(request: Request):
    try:
        body = await request.json()
        args = FeedDetailArgs(**body)
        result = await get_feed_detail(
            args.video_id, args.load_comments, args.comment_limit,
        )
        return _ok(result)
    except Exception as e:
        return _err(str(e))


# --- User ---

async def user_profile_handler(request: Request):
    try:
        body = await request.json()
        args = UserProfileArgs(**body)
        result = await user_profile(args.user_id)
        return _ok(result)
    except Exception as e:
        return _err(str(e))


# --- Video Parse (HTTP-based, no browser) ---

async def parse_video_info_handler(request: Request):
    try:
        if request.method == "POST":
            body = await request.json()
        else:
            body = dict(request.query_params)
        share_link = body.get("share_link", "")
        if not share_link:
            return _err("share_link is required", 400)
        result = parse_video_info(share_link)
        return _ok(result)
    except Exception as e:
        return _err(str(e))


async def download_link_handler(request: Request):
    try:
        if request.method == "POST":
            body = await request.json()
        else:
            body = dict(request.query_params)
        share_link = body.get("share_link", "")
        if not share_link:
            return _err("share_link is required", 400)
        result = get_download_link(share_link)
        return _ok(result)
    except Exception as e:
        return _err(str(e))


async def extract_text_handler(request: Request):
    try:
        body = await request.json()
        share_link = body.get("share_link", "")
        model = body.get("model")
        if not share_link:
            return _err("share_link is required", 400)
        result = extract_text_from_share_link(share_link, model)
        return _ok(result)
    except Exception as e:
        return _err(str(e))


async def recognize_audio_url_handler(request: Request):
    try:
        body = await request.json()
        url = body.get("url", "")
        model = body.get("model")
        if not url:
            return _err("url is required", 400)
        result = recognize_audio_from_url(url, model)
        return _ok(result)
    except Exception as e:
        return _err(str(e))


async def recognize_audio_file_handler(request: Request):
    try:
        body = await request.json()
        file_path = body.get("file_path", "")
        model = body.get("model")
        if not file_path:
            return _err("file_path is required", 400)
        result = recognize_audio_from_file(file_path, model)
        return _ok(result)
    except Exception as e:
        return _err(str(e))


# --- Debug ---

async def debug_screenshot(request: Request):
    """Navigate to a URL, save screenshot to /tmp, return page info."""
    url = request.query_params.get("url", "https://www.douyin.com/search/test?type=video")
    bm = await get_browser()
    page = await bm.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        import asyncio
        await asyncio.sleep(5)
        path = "/tmp/douyin_debug.png"
        await page.screenshot(path=path, full_page=True)
        title = await page.title()
        page_url = page.url
        html_len = await page.evaluate("() => document.documentElement.outerHTML.length")
        # Check for video links in DOM
        dom_info = await page.evaluate("""() => {
            const videoLinks = document.querySelectorAll('a[href*="/video/"]');
            const allLinks = [...document.querySelectorAll('a')].filter(a => a.href && a.href.includes('douyin.com'));
            const cards = document.querySelectorAll('li, [class*="card"], [class*="item"]');
            // Find first card that has a video/note link
            let firstCard = null;
            for (const c of cards) {
                const a = c.querySelector('a[href*="/video/"], a[href*="/note/"]');
                if (a) {
                    firstCard = {
                        tag: c.tagName, cls: c.className.substring(0, 100),
                        links: [...c.querySelectorAll('a')].map(a => a.href.substring(0, 80)).slice(0, 5),
                        text: c.textContent.substring(0, 200).replace(/\\s+/g, ' '),
                    };
                    break;
                }
            }
            const e2e = [...new Set([...document.querySelectorAll('[data-e2e]')].map(el => el.getAttribute('data-e2e')))].slice(0, 20);
            const sampleHrefs = allLinks.slice(0, 10).map(a => a.href.substring(0, 80));
            return {
                video_link_count: videoLinks.length,
                card_count: cards.length,
                first_card: firstCard,
                e2e_attrs: e2e,
                sample_hrefs: sampleHrefs,
            };
        }""")
        return _ok({
            "title": title, "url": page_url,
            "html_length": html_len, "screenshot": path,
            "dom_info": dom_info,
        })
    finally:
        await safe_close_page(page)
