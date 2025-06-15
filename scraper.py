import asyncio
from playwright.async_api import async_playwright
import os
import asyncio
import json
from datetime import datetime
import csv


## class level variables
LINKEDIN_EMAIL = "jianhui.ben@icloud.com"
LINKEDIN_PASSWORD = "bjh291808475"
COOKIE_FILE = "linkedin_cookies.json"

## job setting related variable
search_title = "product manager"
search_location = "United States"
num_jobs_scrapped_per_run = 100


job_data = []

async def login_linkedin():
    async with async_playwright() as p:
        # browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        browser = await p.chromium.launch(headless=False, args=["--no-sandbox"])


        # page = await browser.new_page()
        # await page.goto("https://www.linkedin.com/login")

        # await page.fill("input#username", LINKEDIN_EMAIL)
        # await page.fill("input#password", LINKEDIN_PASSWORD)
        # await page.click("button[type=submit]")

        context = await browser.new_context()
        # Load cookies
        with open(COOKIE_FILE, "r") as f:
            cookies = json.load(f)
        await context.add_cookies(cookies)

        page = await context.new_page()
        await page.goto("https://www.linkedin.com/jobs/search/")
        await page.wait_for_timeout(1000)

        # Search settings
        await page.get_by_role("combobox", name="Search by title, skill, or").fill(search_title)
        await page.get_by_role("combobox", name="City, state, or zip code").fill(search_location)
        await page.get_by_role("button", name="Search", exact=True).click()

        # Apply "Past 24 hours" filter 
        await page.wait_for_timeout(3000)
        await page.get_by_role("button", name="Date posted filter. Clicking").click()
        await page.wait_for_timeout(1000)
        await page.locator("label").filter(has_text="Past 24 hours Filter by Past").click()
        await page.wait_for_timeout(1000)
        await page.get_by_role("button", name="Apply current filter to show").click()
        await page.wait_for_timeout(2000)

        page_id = 0
        while len(job_data) < num_jobs_scrapped_per_run:
            
            ## if not the first page, then go to the next page
            if len(job_data):
                ## append &start = len(job_data) to the current url
                await page.goto(page.url + f"&start={len(job_data)}")
                await page.wait_for_timeout(2000)
            
            # Select all job cards using the reliable .job-card-list__actions-container
            job_cards = await scroll_job_list(page, list_selector=".scaffold-layout__list-container")   

            ## no more jobs available to scrape
            if not len(job_cards):
                break

            for idx, actions_container in enumerate(job_cards):
                print(f"\nClicking job card {idx + 1} on page {page_id}...")

                try:
                    await actions_container.scroll_into_view_if_needed()
                    await actions_container.click(timeout=5000, force=True)
                    await page.wait_for_timeout(1000)

                    # Get and parse current URL
                    current_url = page.url
                    job_id = None
                    if "currentJobId=" in current_url:
                        job_id = current_url.split("currentJobId=")[-1].split("&")[0]

                    print(f"Job ID: {job_id}")
                    print(f"URL: {current_url}")

                    job_data.append({
                        "job_id": job_id or "",
                        "url": current_url
                    })

                except Exception as e:
                    print(f"⚠️ Failed to click job card {idx + 1}: {e}")
            page_id += 1

        # Save results to CSV
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"linkedin_jobs_{search_title.replace(' ', '_')}_{search_location.replace(' ', '_')}_{timestamp}.csv"
        os.makedirs("results", exist_ok=True)
        filepath = os.path.join("results", filename)

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["job_id", "url"])
            writer.writeheader()
            writer.writerows(job_data)

        print(f"✅ Saved {len(job_data)} jobs to: {filepath}")

        # await page.pause()

        await browser.close()

async def scroll_job_list(page, list_selector=".scaffold-layout__list-container", job_card_selector="li.scaffold-layout__list-item"):
    print("🔁 Scrolling through job list container by last job card...")

    while True:
        job_cards = await page.locator(job_card_selector).all()
        current_count = len(job_cards)
        print(f"📦 Currently found {current_count} job cards")

        if current_count == 0:
            print("⚠️ No job cards found yet. Waiting...")
            await asyncio.sleep(1)
            continue

        last_job_card = job_cards[-1]
        await last_job_card.scroll_into_view_if_needed()
        print("🔽 Scrolled last job card into view.")

        await asyncio.sleep(2)

        new_job_cards = await page.locator(job_card_selector).all()
        new_count = len(new_job_cards)

        if new_count == current_count:
            print("✅ No new job cards loaded. Reached bottom.")
            break

    return job_cards


        
async def main():
    await login_linkedin()



if __name__ == "__main__":
    asyncio.run(main())