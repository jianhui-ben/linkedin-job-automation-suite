import json
import logging
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from browser_use import BrowserSession,BrowserProfile
from browser_use import BrowserSession
import os

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

# function for manual login and saving credentials using browser_use
async def manual_login_with_profile(profile_name: str, website_url: str):
    """
    Launch a browser-use session with a given profile name and website URL,
    pause for manual login, and save credentials to the profile.
    """
    user_data_dir = os.path.expanduser(f"~/.config/browseruse/profiles/{profile_name}")
    browser_session = BrowserSession(user_data_dir=user_data_dir)
    await browser_session.start()
    page = await browser_session.get_current_page()
    await page.goto(website_url)
    await page.pause()  # User logs in manually, then resumes
    ## here you need to manually close the insepctor
    await browser_session.stop()
    logger.info(f"Credentials for {website_url} saved to profile '{profile_name}' at {user_data_dir}")


async def initialize_browser_with_profile(profile_name: str, headless: bool = False):
    """
    Initialize a browser-use BrowserSession with a given profile.
    Returns (browser_session, page).
    """
    user_data_dir = os.path.expanduser(f"~/.config/browseruse/profiles/{profile_name}")
    browser_profile = BrowserProfile(user_data_dir=user_data_dir)
    browser_session = BrowserSession(browser_profile=browser_profile, headless=headless)
    await browser_session.start()
    page = await browser_session.get_current_page()
    return browser_session, page
