"""Singleton Patchright browser manager — shared context across requests."""

import asyncio
import logging
from patchright.async_api import async_playwright, Browser, BrowserContext, Playwright, Page

from cookie_manager import load_cookies, save_cookies

logger = logging.getLogger("douyin.browser")

_instance: "BrowserManager | None" = None


class BrowserManager:
    """Manages a single Patchright Chromium instance with a persistent context."""

    def __init__(self):
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._lock = asyncio.Lock()
        self._started = False

    async def start(self, headless: bool = True):
        """Launch browser and create context with cookies."""
        async with self._lock:
            if self._started:
                return
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
            self._context = await self._browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                locale="zh-CN",
            )
            # Load existing cookies
            cookies = load_cookies()
            if cookies:
                await self._context.add_cookies(cookies)
                logger.info(f"Loaded {len(cookies)} cookies")
            self._started = True
            logger.info("Browser started")

    async def stop(self):
        """Shut down browser."""
        async with self._lock:
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
            self._started = False
            logger.info("Browser stopped")

    async def new_page(self) -> Page:
        """Create a new page in the shared context."""
        if not self._started:
            await self.start()
        return await self._context.new_page()

    async def save_current_cookies(self):
        """Persist current browser cookies to disk in CDP format."""
        if self._context:
            cookies = await self._context.cookies()
            save_cookies(cookies)
            logger.info(f"Saved {len(cookies)} cookies")

    async def reload_cookies(self):
        """Reload cookies from disk into the browser context."""
        if self._context:
            cookies = load_cookies()
            if cookies:
                await self._context.add_cookies(cookies)
                logger.info(f"Reloaded {len(cookies)} cookies")

    async def clear_context_cookies(self):
        """Clear cookies from browser context."""
        if self._context:
            await self._context.clear_cookies()


async def get_browser() -> BrowserManager:
    """Get or create the singleton BrowserManager."""
    global _instance
    if _instance is None:
        _instance = BrowserManager()
    return _instance
