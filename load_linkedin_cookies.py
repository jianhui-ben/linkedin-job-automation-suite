import asyncio
from playwright.async_api import async_playwright
import json

COOKIE_FILE = "linkedin_cookies.json"

async def load_linkedin_with_cookies():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()

        # Load cookies
        with open(COOKIE_FILE, "r") as f:
            cookies = json.load(f)
        await context.add_cookies(cookies)

        page = await context.new_page()
        await page.goto("https://www.linkedin.com/jobs/search/")

        # Check if logged in
        await page.wait_for_timeout(3000)
        title = await page.title()
        print("📄 Page title:", title)

        await page.pause()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(load_linkedin_with_cookies())

