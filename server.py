# Copyright (c) 2026 Nardo. AGPL-3.0 — see LICENSE
"""Douyin MCP Server — Starlette app with MCP + REST on same port."""

import argparse
import logging
from contextlib import asynccontextmanager

import uvicorn
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.requests import Request
from starlette.routing import Route, Mount

from browser_manager import get_browser
from mcp_tools import mcp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("douyin.server")

# Headless flag
_headless = True

# Create MCP app — this also creates the session manager internally
mcp_app = mcp.streamable_http_app()
_session_manager = mcp.session_manager


# Health check
async def health(request: Request):
    return JSONResponse({"status": "ok"})


# Import REST route handlers
from api_routes import (
    login_status_handler, login_qrcode_handler, delete_cookies_handler,
    list_feeds_handler, search_feeds_handler, feed_detail_handler,
    user_profile_handler,
    parse_video_info_handler, download_link_handler,
    extract_text_handler,
    recognize_audio_url_handler, recognize_audio_file_handler,
    debug_screenshot,
)


rest_routes = [
    Route("/health", health),
    Route("/api/v1/login/status", login_status_handler),
    Route("/api/v1/login/qrcode", login_qrcode_handler),
    Route("/api/v1/login/cookies", delete_cookies_handler, methods=["DELETE"]),
    Route("/api/v1/feeds/list", list_feeds_handler),
    Route("/api/v1/feeds/search", search_feeds_handler, methods=["GET", "POST"]),
    Route("/api/v1/feeds/detail", feed_detail_handler, methods=["POST"]),
    Route("/api/v1/user/profile", user_profile_handler, methods=["POST"]),
    Route("/api/v1/video/parse", parse_video_info_handler, methods=["GET", "POST"]),
    Route("/api/v1/video/download", download_link_handler, methods=["GET", "POST"]),
    Route("/api/v1/video/extract_text", extract_text_handler, methods=["POST"]),
    Route("/api/v1/audio/recognize_url", recognize_audio_url_handler, methods=["POST"]),
    Route("/api/v1/audio/recognize_file", recognize_audio_file_handler, methods=["POST"]),
    Route("/api/v1/debug/screenshot", debug_screenshot),
]


@asynccontextmanager
async def lifespan(app: Starlette):
    # Start browser
    logger.info("Starting browser...")
    bm = await get_browser()
    await bm.start(headless=_headless)
    logger.info("Browser ready")

    # Start MCP session manager (needed for /mcp endpoint)
    async with _session_manager.run():
        logger.info("MCP session manager ready")
        yield

    # Shutdown browser
    logger.info("Shutting down browser...")
    bm = await get_browser()
    await bm.stop()
    logger.info("Browser stopped")


# Build combined app
# MCP's internal route handler expects path="/mcp", so mount at "/"
# REST routes are listed first and take priority
app = Starlette(
    routes=[
        *rest_routes,
        Mount("/", app=mcp_app),
    ],
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def main():
    global _headless
    parser = argparse.ArgumentParser(description="Douyin MCP Server (Patchright)")
    parser.add_argument("--port", type=int, default=18070, help="Server port (default: 18070)")
    parser.add_argument("--headless", action="store_true", default=True, help="Run browser headless (default)")
    parser.add_argument("--no-headless", action="store_true", help="Run browser with GUI")
    args = parser.parse_args()

    if args.no_headless:
        _headless = False

    uvicorn.run(app, host="0.0.0.0", port=args.port, log_level="info")


if __name__ == "__main__":
    main()
