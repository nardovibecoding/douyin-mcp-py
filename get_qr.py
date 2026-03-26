# Copyright (c) 2026 Nardo. AGPL-3.0 — see LICENSE
"""Get Douyin QR code locally on Mac (clean IP), save cookies, sync to VPS."""
import asyncio
import sys
sys.path.insert(0, "/Users/bernard/douyin-mcp-py")
from browser_manager import get_browser
from utils import safe_close_page

async def get_qr():
    bm = await get_browser()
    await bm.start(headless=False)  # Visible browser on Mac
    page = await bm.new_page()
    await page.goto("https://www.douyin.com/", wait_until="domcontentloaded", timeout=60000)
    await asyncio.sleep(3)

    print("Browser open. Login dialog should appear.")
    print("If not, click 登录 manually.")
    print("Scan QR with Douyin app. Waiting 4 minutes...")

    # Poll for login
    for i in range(240):
        await asyncio.sleep(1)
        try:
            # Check if logged in
            logged = await page.evaluate("""() => {
                const avatar = document.querySelector('[class*="avatar"]');
                const userInfo = document.querySelector('[data-e2e="user-info"]');
                return !!(avatar || userInfo);
            }""")
            if logged:
                print("Login detected!")
                await bm.save_current_cookies()
                print("Cookies saved to ~/douyin-mcp-py/cookies.json")
                break
        except:
            pass
        if i % 30 == 0 and i > 0:
            print(f"Still waiting... {i}s elapsed")

    await safe_close_page(page)
    await bm.stop()

asyncio.run(get_qr())
