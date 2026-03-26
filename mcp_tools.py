# Copyright (c) 2026 Nardo. AGPL-3.0 — see LICENSE
"""MCP tool definitions for Douyin MCP server."""

import json
from mcp.server.fastmcp import FastMCP

from cookie_manager import delete_cookies as _delete_cookies
from dy_actions.login import check_login_status as _check_login, get_login_qrcode as _get_qrcode
from dy_actions.feeds import list_feeds as _list_feeds
from dy_actions.search import search_feeds as _search_feeds
from dy_actions.feed_detail import get_feed_detail as _get_feed_detail
from dy_actions.user_profile import user_profile as _user_profile
from dy_actions.video_parse import (
    get_download_link as _get_download_link,
    parse_video_info as _parse_video_info,
    extract_text_from_share_link as _extract_text,
    recognize_audio_from_url as _recognize_audio_url,
    recognize_audio_from_file as _recognize_audio_file,
)

mcp = FastMCP("douyin")


@mcp.tool()
async def check_login_status() -> dict:
    """Check Douyin login status."""
    return await _check_login()


@mcp.tool()
async def get_login_qrcode() -> dict:
    """Get QR code for Douyin login (Base64 image + timeout)."""
    return await _get_qrcode()


@mcp.tool()
async def delete_cookies() -> dict:
    """Delete cookies file to reset login status."""
    path = _delete_cookies()
    return {"cookie_path": path, "message": "Cookies deleted"}


@mcp.tool()
async def list_feeds() -> dict:
    """Get Douyin homepage/recommend feed list."""
    return await _list_feeds()


@mcp.tool()
async def search_feeds(keyword: str, sort_by: str = "综合排序",
                       publish_time: str = "不限") -> dict:
    """Search Douyin videos by keyword.

    Args:
        keyword: Search keyword
        sort_by: 综合排序|最新发布|最多点赞
        publish_time: 不限|一天内|一周内|半年内
    """
    return await _search_feeds(keyword, sort_by, publish_time)


@mcp.tool()
async def get_feed_detail(video_id: str, load_comments: bool = False,
                          comment_limit: int = 20) -> dict:
    """Get Douyin video detail (title, description, author, engagement stats).

    Args:
        video_id: Douyin video ID (numeric)
        load_comments: Whether to load comments (default: false)
        comment_limit: Max comments to load (default: 20)
    """
    return await _get_feed_detail(video_id, load_comments, comment_limit)


@mcp.tool()
async def user_profile(user_id: str) -> dict:
    """Get Douyin user profile (basic info, followers, recent videos).

    Args:
        user_id: Douyin user ID from video page
    """
    return await _user_profile(user_id)


@mcp.tool()
async def parse_douyin_video_info(share_link: str) -> dict:
    """Parse a Douyin share link to get video info (no browser needed).

    Args:
        share_link: Douyin share link or text containing a share URL
    """
    return _parse_video_info(share_link)


@mcp.tool()
async def get_douyin_download_link(share_link: str) -> dict:
    """Get watermark-free download link from a Douyin share link (no browser needed).

    Args:
        share_link: Douyin share link or text containing a share URL
    """
    return _get_download_link(share_link)


@mcp.tool()
async def extract_douyin_text(share_link: str, model: str = None) -> dict:
    """Extract text from Douyin video audio via speech recognition.

    Requires API_KEY env var for Alibaba Cloud Dashscope.

    Args:
        share_link: Douyin share link or text containing a share URL
        model: Speech recognition model (default: paraformer-v2)
    """
    return _extract_text(share_link, model)


@mcp.tool()
async def recognize_audio_url(url: str, model: str = None) -> dict:
    """Recognize speech from an audio URL using Dashscope.

    Requires API_KEY env var.

    Args:
        url: Audio file URL
        model: Speech recognition model (default: paraformer-v2)
    """
    return _recognize_audio_url(url, model)


@mcp.tool()
async def recognize_audio_file(file_path: str, model: str = None) -> dict:
    """Recognize speech from a local audio file (placeholder).

    Args:
        file_path: Local audio file path
        model: Speech recognition model (default: paraformer-v2)
    """
    return _recognize_audio_file(file_path, model)
