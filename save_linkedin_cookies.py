import asyncio
import json
from playwright.async_api import async_playwright

COOKIE_FILE = "linkedin_cookies.json"

async def save_linkedin_cookies():
    async with async_playwright() as p:
        # browser = await p.chromium.launch(channel="chrome", headless=False)
        browser = await p.chromium.launch(headless=False)

        context = await browser.new_context()
        page = await context.new_page()

        await page.goto("https://www.linkedin.com/login")
        print("👤 Log in manually. You have 30 seconds.")
        await page.wait_for_timeout(30000)

        cookies = await context.cookies()
        with open(COOKIE_FILE, "w") as f:
            json.dump(cookies, f)
        print(f"✅ Cookies saved to {COOKIE_FILE}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(save_linkedin_cookies())
