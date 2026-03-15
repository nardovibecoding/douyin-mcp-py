import asyncio, json, sys
sys.path.insert(0, "/home/bernard/douyin-mcp-py")
from browser_manager import get_browser
from utils import safe_close_page

async def debug():
    bm = await get_browser()
    await bm.start(headless=True)
    page = await bm.new_page()
    await page.goto("https://www.douyin.com/search/美食", wait_until="domcontentloaded", timeout=60000)
    await asyncio.sleep(6)

    result = await page.evaluate("""() => {
        const links = [...document.querySelectorAll('a[href*="/video/"]')];
        const cards = document.querySelectorAll('li, [class*="card"], [class*="item"]');
        let firstCard = null;
        for (const c of cards) {
            const a = c.querySelector('a[href*="/video/"]');
            if (a) {
                firstCard = {
                    tag: c.tagName,
                    cls: c.className.substring(0, 100),
                    allLinks: [...c.querySelectorAll('a')].map(a => ({href: a.href.substring(0, 80), text: a.textContent.substring(0, 30)})),
                    imgs: [...c.querySelectorAll('img')].map(i => i.src.substring(0, 80)).slice(0, 2),
                    text: c.textContent.substring(0, 200)
                };
                break;
            }
        }
        const e2e = [...document.querySelectorAll('[data-e2e]')].map(el => el.getAttribute('data-e2e'));
        const unique_e2e = [...new Set(e2e)].slice(0, 20);
        return {link_count: links.length, card_count: cards.length, e2e: unique_e2e, first_card: firstCard,
                sample_hrefs: links.slice(0, 3).map(a => a.href.substring(0, 80))};
    }""")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    await safe_close_page(page)
    await bm.stop()

asyncio.run(debug())
