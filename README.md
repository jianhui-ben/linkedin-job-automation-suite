# LinkedIn Job Automation Suite

An end-to-end automation system for job hunting on LinkedIn, powered by multiple AI agents working together to streamline the job search and application process.

## System Components

### 1. Job Scraper Agent
- Automatically searches and collects job listings from LinkedIn
- Filters jobs based on customizable criteria
- Saves job data for further processing (now supports saving to SQLite database)

### 2. Resume Analysis Agent (Coming Soon)
- Analyzes job descriptions
- Identifies key requirements and skills
- Suggests resume modifications
- Optimizes resume for specific job postings

### 3. Application Agent (Coming Soon)
- Automates the job application process
- Fills out application forms
- Handles file uploads
- Manages application tracking

## Prerequisites

- Python 3.7 or higher
- pip3 (Python package installer)
- LinkedIn account
- OpenAI API key (for future AI-powered features)

## Installation

1. Clone the repository:
```bash
git clone <your-repository-url>
cd linkedin-job-automation-suite
```

2. Create and activate a virtual environment (recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
```

3. Install the required packages:
```bash
pip3 install -r requirements.txt
```

## Usage

### Step 1: Save LinkedIn Cookies or Set Up a Browser Profile

Before scraping, you need to authenticate with LinkedIn. You can either:
- Use cookies (see `save_linkedin_cookies.py`), or
- Use a persistent browser profile (recommended for browser-use integration)

### Step 2: Scrape Jobs

Run the scraper with your desired search parameters. Example:
```python
search_config = SearchConfig(
    title="product manager",
    location="United States",
    num_jobs=100
)

async with LinkedInJobScraper(
    # cookie_file="linkedin_cookies.json",  # Use this if using cookies
    profile_name="your_browser_profile",     # Use this if using browser-use profile
    search_config=search_config,
    headless=False
) as scraper:
    await scraper.scrape()
```

By default, the scraper will:
- Search for your specified job title and location
- Scrape the specified number of jobs
- Save results in a SQLite database (`linkedin_jobs.db`)

### Step 3: Query and Visualize Results with Query Client

A command-line query client is provided to easily inspect and manage your scraped data.

#### List all tables:
```bash
python query_client.py list
```

#### Query a table (pretty print, truncates long job descriptions):
```bash
python query_client.py query <table_name> [limit]
# Example:
python query_client.py query jobs_product_manager_United_States 10
```

#### Purge (drop) a table:
```bash
python query_client.py purge <table_name>
# Example:
python query_client.py purge jobs_product_manager_United_States
```

## Output

- Scraped jobs are saved in a SQLite database (`linkedin_jobs.db`).
- Each search run creates or updates a table named after the job title and location (e.g., `jobs_product_manager_United_States`).
- Each row contains: `job_id`, `url`, `job_title`, `company_name`, `job_description`, `scraped_date`, `scraped_timestamp`.

## Overall Flow

1. **Authenticate** (via cookies or browser profile)
2. **Run the scraper** to collect jobs and save to SQLite
3. **Query or visualize results** using the query client
4. (Optional) Purge tables you no longer need

## Future Features

### Resume Analysis Agent
- Job description analysis
- Skill matching
- Resume optimization suggestions
- ATS compatibility checking

### Application Agent
- Automated form filling
- Resume and cover letter upload
- Application tracking
- Follow-up automation

## Troubleshooting

1. If you get authentication errors:
   - Delete the existing `linkedin_cookies.json`
   - Run `save_linkedin_cookies.py` again to create fresh cookies

2. If the browser doesn't start:
   - Make sure you have the latest version of Playwright
   - Run `playwright install` to install browser dependencies

## Notes

- The scraper uses a visible browser by default for debugging
- To run in headless mode, set `headless=True` in the `LinkedInJobScraper` initialization
- Be mindful of LinkedIn's rate limits and terms of service
- Consider adding delays between requests to avoid being blocked

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License
