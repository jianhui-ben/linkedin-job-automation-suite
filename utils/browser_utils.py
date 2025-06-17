import json
import logging
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

logger = logging.getLogger(__name__)

async def initialize_browser(cookie_file: str, headless: bool = False) -> tuple[Browser, BrowserContext, Page]:
    """Initialize browser with cookies"""
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=headless,
        args=["--no-sandbox"]
    )
    context = await browser.new_context()
    
    # Load cookies
    try:
        with open(cookie_file, "r") as f:
            cookies = json.load(f)
        await context.add_cookies(cookies)
    except FileNotFoundError:
        logger.warning(f"Cookie file {cookie_file} not found. Proceeding without cookies.")

    page = await context.new_page()
    return browser, context, page
