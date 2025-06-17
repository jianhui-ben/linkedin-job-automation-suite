import asyncio
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
import os
import json
from datetime import datetime
import csv
from typing import List, Optional
import logging
from dataclasses import dataclass
from utils import browser_utils


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
    job_title: str
    company_name: str
    job_description: str

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
        self._browser, self._context, self._page = await browser_utils.initialize_browser(
            cookie_file=self.cookie_file,
            headless=self.headless
        )

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

    async def extract_text_content(self, selector: str, error_message: str, current_url: str) -> str:
        """Common method to extract text content from a selector"""
        element = self._page.locator(selector).first
        if await element.count() > 0:
            return (await element.text_content()).strip()
        else:
            logger.warning(f"{error_message} for URL: {current_url}")
            return ""
    
    async def extract_job_title(self, current_url: str) -> str:
        container = self._page.locator("div[class*='job-details-jobs-unified-top-card__job-title']").first
        job_title = ""
        if await container.count() > 0:
            job_title_node = container.locator("a").first

            if await job_title_node.count() > 0:
                job_title = (await job_title_node.text_content()).strip()
            else:
                job_title = ""
                logger.warning(f"Could not find <a> inside job title container for URL: {current_url}")
        else:
            logger.warning(f"Could not find job title container for URL: {current_url}")
        return job_title

    async def extract_job_description(self, current_url: str) -> str:
        """Extract job description from the page"""
        job_description = ""
        # Step 1: Locate the "About the job" section heading
        heading = self._page.locator("h2:text-is('About the job')").first
        
        if await heading.count() > 0:
            # Step 2: Get the parent container
            container = heading.locator("xpath=following-sibling::div").first
            
            if await container.count() > 0:
                # Step 3: Extract all paragraphs inside the container
                paragraphs = container.locator("p").all()
                texts = []
                for p in await paragraphs:
                    text = await p.text_content()
                    if text:
                        texts.append(text)
                job_description = "\n".join(texts).strip()
            else:
                logger.warning(f"Could not find description container for URL: {current_url}")
        else:
            logger.warning(f"Could not find 'About the job' heading for URL: {current_url}")
        return job_description

    async def process_job_card(self, card) -> Optional[ScrapingResult]:
        """Process a single job card and extract all relevant information"""
        try:
            await card.scroll_into_view_if_needed()
            await card.click(timeout=5000, force=True)
            await self._page.wait_for_timeout(1000) # Give page time to load content after click

            current_url = self._page.url
            job_id = None
            job_url = current_url
            
            # Extract job ID and construct standard LinkedIn job URL
            if "currentJobId=" in current_url:
                job_id = current_url.split("currentJobId=")[-1].split("&")[0]
                job_url = f"https://www.linkedin.com/jobs/view/{job_id}/"
            else:
                logger.warning(f"Could not extract job ID from URL: {current_url}. Using original URL as fallback.")

            # Extract job title
            job_title = await self.extract_job_title(current_url)
            
            # Extract company name
            company_name = await self.extract_text_content(
                "div[class*='p-card__company-name'] a",
                "Could not find company name",
                current_url
            )
            
            # Extract job description
            job_description = await self.extract_job_description(current_url)
            return ScrapingResult(
                job_id=job_id or "",
                url=job_url,
                job_title=job_title,
                company_name=company_name,
                job_description=job_description
            )

        except Exception as e:
            logger.error(f"Failed to process job card for URL: {current_url}: {e}")
            return None

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

                result = await self.process_job_card(card)
                if result:
                    self.job_data.append(result)
                    logger.info(f"Scraped job {len(self.job_data)}/{self.search_config.num_jobs}: '{result.job_title}' at '{result.company_name}'")

            # Break if no new cards were found after processing the current set
            if len(current_cards) == len(job_cards):
                break

            job_cards = current_cards
            await asyncio.sleep(2) # Wait a bit before trying to scroll more

        return self.job_data

    def save_results(self):
        """Save the scraped results to a CSV file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"linkedin_jobs_{self.search_config.title.replace(' ', '_')}_{self.search_config.location.replace(' ', '_')}_{timestamp}.csv"
        
        os.makedirs(self.output_dir, exist_ok=True)
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["job_id", "url", "job_title", "company_name", "job_description"])
            writer.writeheader()
            writer.writerows([{
                "job_id": job.job_id,
                "url": job.url,
                "job_title": job.job_title,
                "company_name": job.company_name,
                "job_description": job.job_description
            } for job in self.job_data])

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