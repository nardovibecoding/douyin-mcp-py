# Copyright (c) 2026 Nardo. AGPL-3.0 — see LICENSE
"""Douyin MCP Server — Starlette app with MCP + REST on same port.

F2-based: uses pure Python A-Bogus token generation, no browser needed.
"""

import argparse
import asyncio
import logging
import signal
from contextlib import asynccontextmanager

# Configure logging BEFORE any F2 imports to suppress noise
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("douyin.server")

# Apply F2 patches (must happen before f2.apps.douyin imports)
import f2_patch  # noqa: F401

import uvicorn
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.requests import Request
from starlette.routing import Route, Mount

from mcp_tools import mcp

# Suppress noisy F2 internal logs
logging.getLogger("f2").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# Create MCP app — this also creates the session manager internally
mcp_app = mcp.streamable_http_app()
_session_manager = mcp.session_manager


# Health check
async def health(request: Request):
    return JSONResponse({"status": "ok", "backend": "f2"})


# Hot-reload: reset ttwid + cookie cache without restarting the server
async def reload_handler(request: Request):
    from dy_actions.f2_client import reset_ttwid
    reset_ttwid()
    return JSONResponse({"status": "ok", "reloaded": "ttwid"})


# Import REST route handlers
from api_routes import (
    login_status_handler, login_qrcode_handler, delete_cookies_handler,
    list_feeds_handler, search_feeds_handler, feed_detail_handler,
    user_profile_handler,
    parse_video_info_handler, download_link_handler,
    extract_text_handler,
    recognize_audio_url_handler, recognize_audio_file_handler,
)


rest_routes = [
    Route("/health", health),
    Route("/api/v1/reload", reload_handler, methods=["POST"]),
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
]


@asynccontextmanager
async def lifespan(app: Starlette):
    logger.info("Douyin MCP Server starting (F2 backend, no browser)")

    # Pre-generate ttwid for guest mode
    try:
        from dy_actions.f2_client import get_f2_kwargs
        kwargs = get_f2_kwargs()
        logger.info("F2 client initialized (guest ttwid ready)")
    except Exception as e:
        logger.warning(f"F2 client init warning: {e}")

    # SIGHUP → reset ttwid without restart
    from dy_actions.f2_client import reset_ttwid
    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGHUP, reset_ttwid)
    logger.info("SIGHUP handler installed (kill -HUP <pid> to reset ttwid)")

    # Start MCP session manager (needed for /mcp endpoint)
    async with _session_manager.run():
        logger.info("MCP session manager ready")
        yield

    logger.info("Douyin MCP Server stopped")


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
    parser = argparse.ArgumentParser(description="Douyin MCP Server (F2)")
    parser.add_argument("--port", type=int, default=18070, help="Server port (default: 18070)")
    args = parser.parse_args()

    uvicorn.run(app, host="0.0.0.0", port=args.port, log_level="info")


if __name__ == "__main__":
    main()
