# Copyright (c) 2026 Nardo. AGPL-3.0 — see LICENSE
"""Login status check and QR code retrieval for Douyin."""

import asyncio
import logging
from browser_manager import get_browser
from utils import sleep_random, safe_close_page

logger = logging.getLogger("douyin.login")

DOUYIN_HOME = "https://www.douyin.com/"
# Douyin logged-in indicators — avatar or user info in sidebar/header
LOGIN_INDICATOR = (
    '[class*="header"] [class*="avatar"], '
    '[class*="user-avatar"], '
    '[data-e2e="user-info"]'
)
QRCODE_SELECTOR = (
    '[class*="qrcode"] img, '
    '[class*="login"] img[src*="qrcode"], '
    'img[class*="qr"]'
)


async def check_login_status() -> dict:
    """Check if user is logged into Douyin. Returns {is_logged_in, username}."""
    bm = await get_browser()
    page = await bm.new_page()
    try:
        await page.goto(DOUYIN_HOME, wait_until="domcontentloaded", timeout=60000)
        await sleep_random(2, 3)

        # Check for logged-in indicator
        try:
            elem = await page.wait_for_selector(LOGIN_INDICATOR, timeout=5000)
            if elem:
                # Try to get username
                username_el = await page.query_selector(
                    '[class*="user-name"], '
                    '[class*="nickname"]'
                )
                username = ""
                if username_el:
                    username = await username_el.text_content() or ""
                return {"is_logged_in": True, "username": username.strip()}
        except Exception:
            pass

        return {"is_logged_in": False, "username": ""}
    finally:
        await safe_close_page(page)


async def get_login_qrcode() -> dict:
    """Get QR code for Douyin login. Returns {timeout, is_logged_in, img}."""
    bm = await get_browser()
    page = await bm.new_page()
    try:
        await page.goto(DOUYIN_HOME, wait_until="domcontentloaded", timeout=60000)
        await sleep_random(2, 3)

        # Already logged in?
        try:
            elem = await page.wait_for_selector(LOGIN_INDICATOR, timeout=5000)
            if elem:
                await safe_close_page(page)
                return {"timeout": "0s", "is_logged_in": True, "img": ""}
        except Exception:
            pass

        # Click 登录 button to trigger login dialog
        try:
            login_btn = await page.query_selector('text=登录')
            if login_btn:
                await login_btn.click()
                await sleep_random(2, 3)
            # Click 扫码登录 tab if visible
            scan_tab = await page.query_selector('text=扫码登录')
            if scan_tab:
                await scan_tab.click()
                await sleep_random(1, 2)
        except Exception:
            pass

        # Take screenshot of QR code and return as base64
        try:
            import base64
            screenshot = await page.screenshot()
            b64 = "data:image/png;base64," + base64.b64encode(screenshot).decode()
            asyncio.create_task(_poll_login_success(page, bm))
            return {"timeout": "4m0s", "is_logged_in": False, "img": b64}
        except Exception as e:
            logger.error(f"Failed to get QR code: {e}")

        await safe_close_page(page)
        return {"timeout": "0s", "is_logged_in": False, "img": ""}
    except Exception:
        await safe_close_page(page)
        raise


async def _poll_login_success(page, bm):
    """Background task: poll for login success, save cookies when detected."""
    try:
        for _ in range(480):  # 4 minutes at 500ms intervals
            await asyncio.sleep(0.5)
            try:
                elem = await page.query_selector(LOGIN_INDICATOR)
                if elem:
                    logger.info("Login detected via QR code")
                    await bm.save_current_cookies()
                    break
            except Exception:
                break  # Page likely closed
    finally:
        await safe_close_page(page)
