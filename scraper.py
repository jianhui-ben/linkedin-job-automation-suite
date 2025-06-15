import asyncio
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
import os
import json
from datetime import datetime
import csv
from typing import List, Optional
import logging
from dataclasses import dataclass


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SearchConfig:
    """Configuration for job search"""
    title: str
    location: str
    num_jobs: int
    time_filter: str = "Past 24 hours"

@dataclass
class ScrapingResult:
    """Container for scraped job data"""
    job_id: str
    url: str

class LinkedInJobScraper:
    """A class to scrape LinkedIn job listings"""
    
    def __init__(self, cookie_file: str, search_config: SearchConfig, 
                 headless: bool = False, output_dir: str = "results"):
        self.cookie_file = cookie_file
        self.search_config = search_config
        self.headless = headless
        self.output_dir = output_dir
        self.job_data: List[ScrapingResult] = []
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup()

    async def initialize(self):
        """Initialize the browser and context"""
        playwright = await async_playwright().start()
        self._browser = await playwright.chromium.launch(
            headless=self.headless,
            args=["--no-sandbox"]
        )
        self._context = await self._browser.new_context()
        
        # Load cookies
        try:
            with open(self.cookie_file, "r") as f:
                cookies = json.load(f)
            await self._context.add_cookies(cookies)
        except FileNotFoundError:
            logger.warning(f"Cookie file {self.cookie_file} not found. Proceeding without cookies.")

        self._page = await self._context.new_page()

    async def cleanup(self):
        """Clean up resources"""
        if self._browser:
            await self._browser.close()

    async def navigate_to_jobs_page(self):
        """Navigate to LinkedIn jobs search page"""
        await self._page.goto("https://www.linkedin.com/jobs/search/")
        await self._page.wait_for_timeout(1000)

    async def perform_search(self):
        """Perform the job search with configured parameters"""
        await self._page.get_by_role("combobox", name="Search by title, skill, or").fill(
            self.search_config.title
        )
        await self._page.get_by_role("combobox", name="City, state, or zip code").fill(
            self.search_config.location
        )
        await self._page.get_by_role("button", name="Search", exact=True).click()
        await self._page.wait_for_timeout(3000)

    async def apply_time_filter(self):
        """Apply the time filter to the search results"""
        await self._page.get_by_role("button", name="Date posted filter. Clicking").click()
        await self._page.wait_for_timeout(1000)
        await self._page.locator("label").filter(
            has_text=f"{self.search_config.time_filter} Filter by {self.search_config.time_filter}"
        ).click()
        await self._page.wait_for_timeout(1000)
        await self._page.get_by_role("button", name="Apply current filter to show").click()
        await self._page.wait_for_timeout(2000)

    async def scroll_job_list(self) -> List[ScrapingResult]:
        """Scroll through the job list and collect job data"""
        logger.info("Scrolling through job list container...")
        job_cards = []
        
        while len(self.job_data) < self.search_config.num_jobs:
            current_cards = await self._page.locator("li.scaffold-layout__list-item").all()
            
            if not current_cards:
                logger.warning("⚠️ No job cards found yet. Waiting...")
                await asyncio.sleep(1)
                continue

            for card in current_cards:
                if len(self.job_data) >= self.search_config.num_jobs:
                    break

                try:
                    await card.scroll_into_view_if_needed()
                    await card.click(timeout=5000, force=True)
                    await self._page.wait_for_timeout(1000)

                    current_url = self._page.url
                    job_id = None
                    if "currentJobId=" in current_url:
                        job_id = current_url.split("currentJobId=")[-1].split("&")[0]

                    self.job_data.append(ScrapingResult(
                        job_id=job_id or "",
                        url=current_url
                    ))
                    logger.info(f"Scraped job {len(self.job_data)}/{self.search_config.num_jobs}")

                except Exception as e:
                    logger.error(f"Failed to process job card: {e}")

            if len(current_cards) == len(job_cards):
                break

            job_cards = current_cards
            await asyncio.sleep(2)

        return self.job_data

    def save_results(self):
        """Save the scraped results to a CSV file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"linkedin_jobs_{self.search_config.title.replace(' ', '_')}_{self.search_config.location.replace(' ', '_')}_{timestamp}.csv"
        
        os.makedirs(self.output_dir, exist_ok=True)
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["job_id", "url"])
            writer.writeheader()
            writer.writerows([{"job_id": job.job_id, "url": job.url} for job in self.job_data])

        logger.info(f"✅ Saved {len(self.job_data)} jobs to: {filepath}")

    async def scrape(self):
        """Main method to perform the scraping process"""
        try:
            await self.navigate_to_jobs_page()
            await self.perform_search()
            await self.apply_time_filter()
            await self.scroll_job_list()
            self.save_results()
        except Exception as e:
            logger.error(f"An error occurred during scraping: {e}")
            raise

async def main():
    # Example usage
    search_config = SearchConfig(
        title="product manager",
        location="United States",
        num_jobs=30
    )
    
    async with LinkedInJobScraper(
        cookie_file="linkedin_cookies.json",
        search_config=search_config,
        headless=False
    ) as scraper:
        await scraper.scrape()

if __name__ == "__main__":
    asyncio.run(main())