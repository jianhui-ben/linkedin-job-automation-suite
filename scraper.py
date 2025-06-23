import asyncio
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from datetime import datetime
from typing import List, Optional
import logging
from dataclasses import dataclass
from utils import browser_utils
import sqlite3
from browser_use import BrowserSession
import random


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define database file
DB_FILE = "linkedin_jobs.db"

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
    """A class to scrape LinkedIn job listings with anti-detection features."""
    
    def __init__(self, search_config: SearchConfig, 
                 cookie_file: str = None, headless: bool = False, output_dir: str = "results", profile_name: str = None):
        self.cookie_file = cookie_file
        self.search_config = search_config
        self.headless = headless
        self.output_dir = output_dir
        self.job_data: List[ScrapingResult] = []
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self.profile_name = profile_name
        self._browser_session: Optional[BrowserSession] = None  # browser_user session
        self._db_conn: Optional[sqlite3.Connection] = None  # Database connection
        self._db_cursor: Optional[sqlite3.Cursor] = None    # Database cursor
        self.table_name: str = "" # To store the dynamically generated table name

    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        self.connect_db() # Connect to DB on entry
        await self.create_jobs_table() # Create table for this run
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup()
        self.close_db() # Close DB on exit

    async def initialize(self):
        """Initialize the browser and context"""
        if self.profile_name:
            self._browser_session, self._page = await browser_utils.initialize_browser_with_profile(
                profile_name=self.profile_name,
                headless=self.headless
            )
            self._browser = None
            self._context = None
        elif self.cookie_file:
            self._browser, self._context, self._page = await browser_utils.initialize_browser(
                cookie_file=self.cookie_file,
                headless=self.headless
            )
            self._browser_session = None
        else:
            raise ValueError("Either profile_name or cookie_file must be provided for authentication.")

    async def cleanup(self):
        """Clean up resources"""
        if self._browser_session:
            await self._browser_session.stop()
        elif self._browser:
            await self._browser.close()

    async def navigate_to_jobs_page(self):
        """Navigate to LinkedIn jobs search page"""
        await self._page.goto("https://www.linkedin.com/jobs/search/")
        await self._page.wait_for_timeout(1000)

    async def perform_search(self):
        """Perform the job search with human-like typing."""
        title_box = self._page.get_by_role("combobox", name="Search by title, skill, or")
        await title_box.click()
        await title_box.type(self.search_config.title, delay=random.randint(60, 150))
        await self._random_sleep()

        location_box = self._page.get_by_role("combobox", name="City, state, or zip code")
        await location_box.click()
        await location_box.type(self.search_config.location, delay=random.randint(70, 180))
        await self._random_sleep()

        await self._page.get_by_role("button", name="Search", exact=True).click()
        await self._random_sleep(2000, 4000)

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
        """Process a single job card with anti-detection measures."""
        try:
            await card.scroll_into_view_if_needed()
            await self._random_sleep(500, 1200)
            await card.click(timeout=5000, force=True)
            await self._random_sleep(1500, 3000) # Wait longer for page content to load

            await self._human_scroll() # Add human-like scroll

            current_url = self._page.url
            job_id = None
            job_url = current_url
            
            if "currentJobId=" in current_url:
                job_id = current_url.split("currentJobId=")[-1].split("&")[0]
                job_url = f"https://www.linkedin.com/jobs/view/{job_id}/"
            else:
                logger.warning(f"Could not extract job ID from URL: {current_url}. Using original URL as fallback.")

            job_title = await self.extract_text_content("div[class*='job-details-jobs-unified-top-card__job-title'] a", "Could not find job title", current_url)
            company_name = await self.extract_text_content("div[class*='p-card__company-name'] a", "Could not find company name", current_url)
            job_description = await self.extract_job_description(current_url)

            return ScrapingResult(job_id=job_id or "", url=job_url, job_title=job_title, company_name=company_name, job_description=job_description)

        except Exception as e:
            logger.error(f"Failed to process job card for URL: {self._page.url}: {e}")
            return None

    async def scroll_job_list(self) -> List[ScrapingResult]:
        """Scroll through the job list and collect job data"""
        logger.info("Scrolling through job list container...")
        job_cards = []
        
        while len(self.job_data) < self.search_config.num_jobs:
            current_cards = await self._page.locator("li.scaffold-layout__list-item").all()

            if not current_cards:
                logger.warning("⚠️ No job cards found yet. Waiting...")
                await self._random_sleep()
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
            await self._random_sleep() # Wait a bit before trying to scroll more

        return self.job_data

    def connect_db(self):
        """Connect to the SQLite database."""
        try:
            self._db_conn = sqlite3.connect(DB_FILE)
            self._db_cursor = self._db_conn.cursor()
            logger.info(f"Connected to database: {DB_FILE}")
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {e}")
            self._db_conn = None
            self._db_cursor = None

    def close_db(self):
        """Close the database connection."""
        if self._db_conn:
            self._db_conn.close()
            logger.info("Database connection closed.")

    async def create_jobs_table(self):
        """Create a new table for the scraped jobs, named with a timestamp."""
        sanitized_title = self.search_config.title.replace(' ', '_').replace('/', '_').replace('\\', '_').replace('.', '')
        sanitized_location = self.search_config.location.replace(' ', '_').replace('/', '_').replace('\\', '_').replace('.', '')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.table_name = f"jobs_{sanitized_title}_{sanitized_location}_{timestamp}"
        
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS "{self.table_name}" (
            job_id TEXT PRIMARY KEY, url TEXT, job_title TEXT, company_name TEXT,
            job_description TEXT, scraped_date TEXT, scraped_timestamp TEXT
        );"""
        try:
            if self._db_cursor:
                self._db_cursor.execute(create_table_sql)
                self._db_conn.commit()
                logger.info(f"Table '{self.table_name}' is ready.")
        except sqlite3.Error as e:
            logger.error(f"Error creating table '{self.table_name}': {e}")

    def save_results(self):
        """Save the scraped results to the SQLite database in a single transaction."""
        if not self._db_cursor:
            logger.error("Database not connected. Cannot save results.")
            return

        scraped_date = datetime.now().strftime("%Y-%m-%d")
        scraped_timestamp = datetime.now().strftime("%H:%M:%S")
        
        insert_sql = f"""INSERT OR IGNORE INTO "{self.table_name}" 
                         (job_id, url, job_title, company_name, job_description, scraped_date, scraped_timestamp) 
                         VALUES (?, ?, ?, ?, ?, ?, ?);"""
        
        jobs_to_insert = [
            (job.job_id, job.url, job.job_title, job.company_name, job.job_description, scraped_date, scraped_timestamp)
            for job in self.job_data
        ]
        
        try:
            self._db_cursor.executemany(insert_sql, jobs_to_insert)
            self._db_conn.commit()
            logger.info(f"✅ Saved {self._db_cursor.rowcount} new jobs to database table '{self.table_name}'.")
        except sqlite3.Error as e:
            logger.error(f"Error bulk saving jobs to database: {e}")

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

    # --- Anti-Detection Helper Methods ---
    async def _random_sleep(self, min_ms: int = 800, max_ms: int = 2500):
        """Sleep for a random duration to mimic human behavior."""
        await asyncio.sleep(random.uniform(min_ms, max_ms) / 1000)

    async def _human_scroll(self):
        """Simulate human-like scrolling on the page."""
        for _ in range(random.randint(2, 5)):
            await self._page.mouse.wheel(0, random.randint(200, 500))
            await self._random_sleep(300, 800)

async def main():
    # Example usage
    search_config = SearchConfig(
        title="product manager",
        location="United States",
        num_jobs=10
    )
    
    async with LinkedInJobScraper(
        # cookie_file="linkedin_cookies.json",  // don't use the cookie directly
        profile_name="yahoo_email_account",  # Use browser-use profile
        search_config=search_config,
        headless=False
    ) as scraper:
        await scraper.scrape()

if __name__ == "__main__":
    asyncio.run(main())